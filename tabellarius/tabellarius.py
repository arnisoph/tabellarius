#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
"""tabellarius

TODO:
* TLS communication is UNCONFIGURED (using library defaults)
* support IDLE connections
* improve error handling, throw excetions?
* filtering fields like deliverd-to/ received/ body are not supported yet
* manage different namespaces
* expunge at the end only
* use decorators for imap methods (refresh_folder, check_login, etc.)
"""

from argparse import ArgumentParser
from getpass import getpass
from time import sleep

from imap import IMAP
from ruleset import RuleSet
from misc import ConfigParser, Helper


def main():
    version = '0.1.3'
    program_name = 'tabellarius'
    parser = ArgumentParser(prog=program_name, description='A mail-sorting tool that is less annoying')

    # General args
    parser.add_argument('-V', action='version', version='%(prog)s {version}'.format(version=version))
    parser.add_argument('-t', '--test',
                        action='store_true',
                        dest='test',
                        help='Run in test mode, run read-only IMAP commands only (WARNING: Bare Implementation!)',
                        default=None)
    parser.add_argument('-l', '--log-level',
                        action='store',
                        dest='log_level',
                        help='Override log level setting (DEBUG|ERROR|CRITICAL|INFO)',
                        default='')
    parser.add_argument('--gpg-homedir',
                        action='store',
                        dest='gpg_homedir',
                        help='Override gpg home dir setting (default: ~/.gnupg/)',
                        default='~/.gnupg/')
    parser.add_argument('--sleep',
                        action='store',
                        dest='imap_sleep_time',
                        help='Sleep time between IMAP parsing for e-mails (default: 2)',
                        type=int,
                        default=2)
    parser.add_argument('--confdir',
                        action='store',
                        dest='confdir',
                        help='Directory to search for configuration files (default: config/)',
                        default='config/',
                        required=True)

    parser_results = parser.parse_args()
    confdir = parser_results.confdir
    test = parser_results.test

    log_level = parser_results.log_level
    if log_level and log_level not in ['DEBUG', 'ERROR', 'CRITICAL', 'INFO']:
        print('LOG_LEVEL %s is not supported, supported log levels are DEBUG, ERROR, CRITICAL, INFO', log_level)
        exit(127)

    gpg_homedir = parser_results.gpg_homedir
    imap_sleep_time = parser_results.imap_sleep_time

    # Config Parsing
    cfg_parser = ConfigParser(confdir)
    config = cfg_parser.dump()
    if test is not None:
        config['settings']['test'] = test

    # Logging
    logconfig = config.get('settings', {}).get('logging', {})
    if log_level:
        logconfig['root']['level'] = log_level
    logger = Helper().create_logger(program_name, logconfig)

    # Let's start working now
    logger.debug('Starting new instance of %s', program_name)
    logger.debug('Raw configuration: %s', config)

    # Import gnupg if necessary
    use_gpg = False
    # There is a better solution for the following for sure
    for acc, acc_settings in config.get('accounts').items():
        if acc_settings.get('enabled', False) and 'password_enc' in acc_settings:
            use_gpg = True
            break
    if use_gpg:
        import gnupg
        if config.get('settings').get('gpg_homedir', None):
            gpg_homedir = config.get('settings').get('gpg_homedir')

        gpg = gnupg.GPG(homedir=gpg_homedir,
                        use_agent=config.get('settings').get('gpg_use_agent', False),
                        binary=config.get('settings').get('gpg_binary', 'gpg2'))
        gpg.encoding = 'utf-8'

    # Initialize connection pools
    imap_pool = {}
    for acc, acc_settings in sorted(config.get('accounts').items()):
        if not acc_settings.get('enabled', False):
            continue

        # Check whether we got a plaintext password
        acc_password = acc_settings.get('password')
        if not acc_password:
            # Switch to GPG-encrypted password
            enc_password = None

            # Shall we use gpg-agent or use Python's getpass to retreive the plain text password
            if config.get('settings').get('gpg_use_agent', False):
                enc_password = gpg.decrypt(message=acc_settings.get('password_enc'))

                if not enc_password.ok:
                    logger.error('%s: Failed to decrypt GPG message: %s', acc_settings.get('username'), enc_password.status)
                    logger.debug('%s: GPG error: %s', acc_settings.get('username'), enc_password.stderr)
                    exit(1)
                acc_password = str(enc_password)
            else:
                acc_password = getpass('Please enter the IMAP password for {0} ({1}): '.format(acc, acc_settings.get('username')))

        logger.info('%s: Setting up IMAP connection', acc_settings.get('username'))
        imap_pool[acc] = IMAP(logger=logger,
                              server=acc_settings.get('server'),
                              port=acc_settings.get('port', 143),
                              username=acc_settings.get('username'),
                              password=acc_password,
                              test=test)
        connect = imap_pool[acc].connect()

        if not connect:
            logger.error('%s: Failed to login, abort..', acc_settings.get('username'))
            exit(127)

    while True:
        for acc, acc_settings in sorted(config.get('accounts').items()):
            if not acc_settings.get('enabled', False):
                continue
            pre_inbox = acc_settings.get('pre_inbox', 'PreInbox')
            pre_inbox_search = acc_settings.get('pre_inbox_search', 'ALL')
            sort_mailbox = acc_settings.get('sort_mailbox', None)

            try:
                mail_uids = imap_pool[acc].search_mails(pre_inbox, pre_inbox_search)
                if not mail_uids:
                    logger.debug('%s: No mails found, continue with next mail account..', acc_settings.get('username'))
                    continue

                mails = imap_pool[acc].fetch_mails(uids=mail_uids, mailbox=pre_inbox)
                for uid, mail in mails.items():
                    match = False
                    for filter_name, filter_rulesets in sorted(config.get('filters').get(acc).items()):
                        ruleset = RuleSet(logger=logger,
                                          name=filter_name,
                                          ruleset=filter_rulesets.get('rules', None),
                                          commands=filter_rulesets.get('commands', None),
                                          imap=imap_pool[acc],
                                          mail=(uid, mail),
                                          mailbox=pre_inbox)
                        match = ruleset.process()
                        if match:
                            break
                    if not match and not sort_mailbox:
                        imap_pool[acc].set_mailflags([uid], pre_inbox, acc_settings.get('unmatched_mail_flags', ['\FLAGGED']))

                if sort_mailbox:
                    logger.debug('%s: Searching for mails that did not match any filter and moving them to %s',
                                 acc_settings.get('username'), sort_mailbox)
                    uids = imap_pool[acc].search_mails(pre_inbox)
                    mails = imap_pool[acc].fetch_mails(uids=uids, mailbox=pre_inbox)
                    for mail in mails:
                        imap_pool[acc].move_mail(mails[mail], pre_inbox, sort_mailbox, set_flags=[])
            #except IMAPClient.Error as e:
            #    logger.error('%s: Catching exception: %s. This is bad and I am sad. Going to sleep for a few seconds and trying again..',
            #                 acc_settings.get('username'), e)
            #    sleep(10)

            except Exception as e:
                logger.error('%s: Catching unknown exception: %s. Going to die hard now..', acc_settings.get('username'), e)
                exit(1)

        sleep(imap_sleep_time)


if __name__ == '__main__':
    exit(main())
