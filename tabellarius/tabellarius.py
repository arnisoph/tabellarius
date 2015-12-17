#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
"""tabellarius

Loglevels in use:
* DEBUG
* ERROR
* CRITICAL
* INFO

TODO:
* TLS communication is UNCONFIGURED (using library defaults)
* support IDLE connections
* improve error handling, throw excetions?
* filtering fields like deliverd-to/ received/ body are not supported yet
* manage different namespaces
* expunge at the end only
"""
# Third party libs
import argparse

from imap import IMAP
from ruleset import RuleSet
from misc import ConfigParser, Helper


def main():
    version = '0.1.1'
    program_name = 'tabellarius'
    parser = argparse.ArgumentParser(prog=program_name, description='A mail-sorting tool that is less annoying')

    # General args
    parser.add_argument('-V', action='version', version='%(prog)s {version}'.format(version=version))
    parser.add_argument('-t', '--test',
                        action='store_true',
                        dest='test',
                        help='Run in test mode, run read-only IMAP commands only',
                        default=None)
    parser.add_argument('--confdir',
                        action='store',
                        dest='confdir',
                        help='directory to search for configuration files (default: config/)',
                        default='config/')

    parser_results = parser.parse_args()
    confdir = parser_results.confdir
    test = parser_results.test

    # Config Parsing
    cfg_parser = ConfigParser(confdir)
    config = cfg_parser.dump()
    if test is not None:
        config['settings']['test'] = test

    # Logging
    logconfig = config.get('settings', {}).get('logging', {})
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
        gpg = gnupg.GPG(homedir=config.get('settings').get('gpg_homedir', '~/.gnupg/'),
                        use_agent=config.get('settings').get('gpg_use_agent', True),
                        binary=config.get('settings').get('gpg_binary', 'gpg2'))
        gpg.encoding = 'utf-8'

    # Initialize connection pools
    imap_pool = {}
    for acc, acc_settings in config.get('accounts').items():
        if not acc_settings.get('enabled', False):
            continue

        # Check whether we got a plaintext password
        acc_password = acc_settings.get('password')
        if not acc_password:
            # Switch to GPG-encrypted password
            enc_password = gpg.decrypt(acc_settings.get('password_enc'))
            if not enc_password.ok:
                logger.error('%s: Failed to decrypt GPG message: %s', acc_settings.get('username'), enc_password.status)
                logger.debug('%s: GPG error: %s', acc_settings.get('username'), enc_password.stderr)
                exit(1)
            acc_password = str(enc_password)

        imap_pool[acc] = IMAP(logger=logger,
                              server=acc_settings.get('server'),
                              port=acc_settings.get('port', 143),
                              username=acc_settings.get('username'),
                              password=acc_password,
                              test=test)
        imap_pool[acc].connect()  # TODO error handling

    while True:
        for acc, acc_settings in config.get('accounts').items():
            if not acc_settings.get('enabled', False):
                continue
            pre_inbox = acc_settings.get('pre_inbox', 'PreInbox')
            pre_inbox_search = acc_settings.get('pre_inbox_search', 'ALL')
            sort_mailbox = acc_settings.get('sort_mailbox', None)

            mail_uids = imap_pool[acc].search_mails(pre_inbox, pre_inbox_search)
            if not mail_uids:
                logger.debug('%s: No mails found, continue with next mail account..', acc_settings.get('username'))
                continue

            mails = imap_pool[acc].fetch_mails(uids=mail_uids, mailbox=pre_inbox)
            for uid, mail in mails.items():
                match = False
                for filter_name, filter_rulesets in sorted(config.get('filters').get(acc).items()):
                    set_commands = filter_rulesets.get('commands', None)
                    set_rules = filter_rulesets.get('rules', None)
                    ruleset = RuleSet(logger=logger,
                                      name=filter_name,
                                      ruleset=set_rules,
                                      commands=set_commands,
                                      imap=imap_pool[acc],
                                      mail=(uid, mail),
                                      mailbox=pre_inbox)
                    match = ruleset.process()
                    if match:
                        break
                if not match and not sort_mailbox:
                    imap_pool[acc].set_mailflags([uid], pre_inbox, acc_settings.get('unmatched_mail_flags', ['\FLAGGED']))

            if sort_mailbox:
                logger.info('%s: Searching for mails that did not match any filter and moving them to %s', acc_settings.get('username'),
                            sort_mailbox)
                uids = imap_pool[acc].search_mails(pre_inbox)
                mails = imap_pool[acc].fetch_mails(uids=uids, mailbox=pre_inbox)
                for mail in mails:
                    imap_pool[acc].move_mail(mails[mail], pre_inbox, sort_mailbox, set_flags=[])

        break

    logger.debug('Shutting down tabellarius instance..')


if __name__ == '__main__':
    exit(main())
