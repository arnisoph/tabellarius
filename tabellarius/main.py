#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from argparse import ArgumentParser
from getpass import getpass
from sys import stderr, exc_info, version_info as python_version
from time import sleep
from traceback import print_exception

from tabellarius.imap import IMAP
from tabellarius.mail_filter import MailFilter
from tabellarius.misc import ConfigParser, Helper

__version__ = '1.2.1'


def main():
    program_name = 'tabellarius'
    allowed_log_levels = ['DEBUG', 'ERROR', 'INFO']

    if python_version[0] < 3:
        print('Your need to use Python 3 to run {0}! Your version: {1}'.format(program_name, python_version))

    parser = ArgumentParser(prog=program_name, description='A mail-sorting tool that is less annoying')

    # General args
    parser.add_argument('-V', action='version', version='%(prog)s {version}'.format(version=__version__))
    parser.add_argument('-t', '--test',
                        action='store_true',
                        dest='test',
                        help='Run in test mode, run read-only IMAP commands only (WARNING: Bare Implementation!)',
                        default=None)
    parser.add_argument('-l', '--loglevel',
                        action='store',
                        dest='log_level',
                        help='Override log level setting ({0})'.format(', '.join(allowed_log_levels)),
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

    log_level = parser_results.log_level.upper()
    if log_level and log_level not in allowed_log_levels:
        print('LOG_LEVEL {0} is not supported, supported log levels are: {1}'.format(log_level, ', '.join(allowed_log_levels)))
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

    # Setup gnupg if necessary
    for acc, acc_settings in config.get('accounts').items():
        if 'password_enc' in acc_settings:
            import gnupg

            gpg_homedir = config.get('settings').get('gpg_homedir', gpg_homedir)

            gpg = gnupg.GPG(homedir=gpg_homedir,
                            use_agent=config.get('settings').get('gpg_use_agent', False),
                            binary=config.get('settings').get('gpg_binary', 'gpg2'))
            gpg.encoding = 'utf-8'

    # Initialize connection pools
    imap_pool = {}
    for acc_id, acc_settings in sorted(config.get('accounts').items()):
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
                acc_password = getpass('Please enter the IMAP password for {0} ({1}): '.format(acc_id, acc_settings.get('username')))

        logger.info('%s: Setting up IMAP connection', acc_settings.get('username'))
        imap_pool[acc_id] = IMAP(logger=logger,
                                 server=acc_settings.get('server'),
                                 port=acc_settings.get('port', 143),
                                 starttls=acc_settings.get('starttls', True),
                                 imaps=acc_settings.get('imaps', False),
                                 tlsverify=acc_settings.get('tlsverify', True),
                                 username=acc_settings.get('username'),
                                 password=acc_password,
                                 test=test)
        connect = imap_pool[acc_id].connect()

        if not connect.code:
            logger.error('%s: Failed to login, please check your account credentials: %s', acc_settings.get('username'), connect.data)
            exit(127)
        else:
            logger.info('%s: Sucessfully logged in!', acc_settings.get('username'))

    logger.info('Entering mail-sorting loop')
    while True:
        for acc_id, acc_settings in sorted(config.get('accounts').items()):
            pre_inbox = acc_settings.get('pre_inbox', 'PreInbox')
            pre_inbox_search = acc_settings.get('pre_inbox_search', 'ALL')
            sort_mailbox = acc_settings.get('sort_mailbox', None)

            try:
                if not imap_pool[acc_id].mailbox_exists(pre_inbox).data:
                    imap_pool[acc_id].logger.info('%s: Destination mailbox %s doesn\'t exist, creating it for you',
                                                  acc_settings.get('username'), pre_inbox)

                    result = imap_pool[acc_id].create_mailbox(mailbox=pre_inbox)
                    if not result.code:
                        imap_pool[acc_id].logger.error('%s: Failed to create the mailbox %s: %s', acc_settings.get('username'), pre_inbox,
                                                       result.data)
                        return result

                mail_uids = imap_pool[acc_id].search_mails(mailbox=pre_inbox, criteria=pre_inbox_search, autocreate_mailbox=True).data
                if not mail_uids:
                    logger.debug('%s: No mails found to sort', acc_settings.get('username'))
                    continue

                mails = imap_pool[acc_id].fetch_mails(uids=mail_uids, mailbox=pre_inbox).data
                mails_without_match = []
                for uid, mail in mails.items():
                    match = False

                    if mail.get_header('message-id') is None:
                        logger.error('Mail with uid={} and subject=\'{}\' doesn\'t have a message-id! Abort..'.format(
                            uid, mail.get_header('subject')))
                        exit(1)

                    for filter_name, filter_settings in Helper().sort_dict(config.get('filters').get(acc_id)).items():
                        mail_filter = MailFilter(logger=logger,
                                                 imap=imap_pool[acc_id],
                                                 mail=mail,
                                                 config=filter_settings,
                                                 mailbox=pre_inbox)
                        match = mail_filter.check_rules_match()
                        if match:
                            break

                    if match:
                        continue

                    if sort_mailbox:
                        mails_without_match.append(uid)
                    else:
                        imap_pool[acc_id].set_mailflags(uids=[uid],
                                                        mailbox=pre_inbox,
                                                        flags=acc_settings.get('unmatched_mail_flags', ['\\FLAGGED']))

                if sort_mailbox and mails_without_match:
                    logger.info('%s: Moving mails that did not match any filter to %s', acc_settings.get('username'), sort_mailbox)

                    for uid in mails_without_match:
                        mail = mails[uid]
                        imap_pool[acc_id].move_mail(message_ids=[mail.get_header('message-id')],
                                                    source=pre_inbox,
                                                    destination=sort_mailbox,
                                                    set_flags=[])

            # except IMAPClient.Error as e:
            #    logger.error('%s: Catching exception: %s. This is bad and I am sad. Going to sleep for a few seconds and trying again..',
            #                 acc_settings.get('username'), e)
            #    sleep(10)

            except Exception as e:
                trace_info = exc_info()
                logger.error('%s: Catching unknown exception: %s. Showing stack trace and going to die..', acc_settings.get('username'), e)

                print_exception(*trace_info)
                del trace_info

                exit(1)

        logger.debug('All accounts checked, going to sleep for %s seconds before checking again..', imap_sleep_time)
        sleep(imap_sleep_time)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nBye!', file=stderr)
        exit(1)
