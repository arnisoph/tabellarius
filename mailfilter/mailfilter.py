#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
"""mailfilter

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

Notes:

Imap class:
* before calling a private function, always issue a new SELECT command
"""

#from time import sleep
import os
import re
#import ssl
import sys
import yaml
import logging
import logging.config

# Third party libs
import argparse
import email.message
#import pprint
sys.path.insert(0, './imapclient/imapclient')  # TODO this is ugly, improve it
from imapclient import IMAPClient


class Mail(dict):
    mail_native = email.message.Message()

    def __init__(self, mail=None):
        self.mail_native = mail
        self.parse_email_object()

    def parse_email_object(self):
        fields_to_store = {
            'content-type': None,
            'date': None,
            'delivered-to': {'multiple': True},
            'from': None,
            'list-id': None,
            'message-id': None,
            'received': {'multiple': True, 'split': True},
            'return-path': None,
            'subject': None,
            'to': None,
            'user-agent': None,
        }

        for field, properties in fields_to_store.items():
            if type(properties) is dict:
                if properties.get('multiple', None):
                    fields = self.mail_native.get_all(field)
                    if properties.get('split', None):
                        _fields = []
                        for f in fields:
                            _fields.append(f.split('\r\n'))
                        _fields = fields
                    self[field] = fields
                else:
                    self[field] = self.mail_native.get(field)
            else:
                self[field] = self.mail_native.get(field)


class RuleSet(object):
    def __init__(self, logger, name, mailbox, ruleset=[], commands=[], imap=None):
        self.logger = logger
        self.name = name
        self.mailbox = mailbox
        self.ruleset = ruleset
        self.commands = commands
        self.imap = imap
        self.supported_rule_operators = ['or', 'and']

    def process(self):
        mail_uids = self.imap.search_mails(self.mailbox)
        mails = self.imap.fetch_mails(uids=mail_uids, mailbox=self.mailbox)
        match = False
        for uid, mail in mails.items():
            self.logger.debug('Checking whether mail uid="%s"; message-id="%s"; subject="%s" matches to ruleset %s', uid,
                              mail.get('message-id'), mail.get('subject'), self.name)
            match = self.parse_ruleset(mail, self.ruleset)
            if match:
                self.logger.debug('Ruleset matches!')
                self.apply_commands(uid, mail, self.mailbox)

    def apply_commands(self, uid, mail, mailbox):
        self.logger.debug('Applying commands for mail message-id="%s" of ruleset %s', mail.get('message-id'), self.name)

        for command in self.commands:
            cmd_type = command.get('type')
            cmd_flags_set = command.get('all_flags', [])
            #cmd_flags_delete = command.get('delete_flags', [])
            #cmd_flags_add = command.get('add_flags', [])

            if cmd_type == 'move':
                cmd_target = command.get('target')
                self.imap.move_mail(mail, mailbox, cmd_target, set_flags=cmd_flags_set)

    def parse_ruleset(self, mail, ruleset):
        for rule in ruleset:
            operator = sorted(rule.keys())[0]
            conditions = rule.get(operator)
            match = self.filter_match(mail, operator, conditions)
            if match:
                return match

    def filter_match(self, mail, operator, conditions):
        #print('Check match: operator={0} conditions={1}'.format(operator, conditions))
        if operator == 'or':
            last_match = True
            for condition in conditions:
                field_original, field, invert = clean_field_names(sorted(condition.keys())[0])
                pattern = condition.get(field_original)
                #print('field: {0}/ {1}'.format(field, pattern))
                if field in self.supported_rule_operators:
                    last_match = self.filter_match(mail=mail, operator=field, conditions=pattern)
                    if last_match:
                        return True
                else:
                    lines = mail.get(field)
                    if lines is None:
                        last_match = False
                        continue
                    if type(lines) is not list:
                        lines = [lines]
                    for line in lines:
                        last_match = check_match(line, pattern)  # TODO improve
                        if last_match:
                            break
                    if invert:
                        last_match = not last_match
                    if last_match:
                        return True
            return last_match
        elif operator == 'and':
            for condition in conditions:
                field_original, field, invert = clean_field_names(sorted(condition.keys())[0])
                pattern = condition.get(field_original)
                if field in self.supported_rule_operators:
                    last_match = self.filter_match(mail=mail, operator=field, conditions=pattern)
                    if not last_match:
                        return False
                else:
                    lines = mail.get(field)
                    #if lines is None:
                    #    continue
                    if type(lines) is not list:
                        lines = [lines]
                    for line in lines:
                        last_match = check_match(line, pattern)  # TODO improve
                        if not last_match:
                            break
                    if invert:
                        last_match = not last_match
                    if not last_match:
                        return False
            return True
        else:
            print('operator {0} is not supported yet'.format(operator))


class IMAP(object):
    def __init__(self, logger, username, password, server='localhost', port=143, test=False):
        self.logger = logger
        self.username = username
        self.password = password
        self.server = server
        self.port = port
        self.test = test

    def connect(self):
        self.logger.debug('Establishing IMAP TLS connection to %s and logging in with user %s', self.server, self.username)
        self.conn = IMAPClient(host=self.server, port=self.port, use_uid=True, starttls=True)
        self.conn.login(self.username, self.password)

    def process_error(self, exception):
        self.logger.error('Catching IMAP exception: %s', exception)

    def select_mailbox(self, mailbox):
        self.logger.debug('Switching to mailbox %s', mailbox)
        try:
            result = self.conn.select_folder(mailbox)
        except IMAPClient.Error as e:
            self.process_error(e)
            result = None
        return result

    def search_mails(self, mailbox, criteria='ALL'):
        self.logger.debug('Searching for mails in mailbox %s and criteria=\'%s\'', mailbox, criteria)
        try:
            result = self.select_mailbox(mailbox)
            result = self.conn.search(criteria=criteria)
            mail_uids = result
        except IMAPClient.Error as e:
            self.process_error(e)
            mail_uids = []
        return list(mail_uids)

    def fetch_raw_mails(self, uids, mailbox, return_fields=[b'RFC822']):
        if len(uids) == 0:
            return []
        self.logger.debug('Fetching raw mails with uids %s', uids)

        try:
            mails = {}
            for uid in uids:
                result = self.select_mailbox(mailbox)
                result = self.conn.fetch(uid, return_fields)
                for fetch_uid, fetch_mail in result.items():
                    mails[fetch_uid] = fetch_mail
        except IMAPClient.Error as e:
            self.process_error(e)
        return mails

    def fetch_mails(self, uids, mailbox):
        if type(uids) is not list:
            uids = [uids]
        if len(uids) == 0:
            return {}
        self.logger.debug('Fetching mails with uids %s', uids)

        raw_mails = self.fetch_raw_mails(uids, mailbox)
        mails = {}
        for raw_uid, raw_mail in raw_mails.items():
            mail = Mail(mail=email.message_from_bytes(raw_mails[raw_uid][b'RFC822']))
            mails[raw_uid] = mail
        return mails

    def move_mail(self, mail, source, destination, delete_old=True, expunge=True, set_flags=None):
        if self.test:
            self.logger.info('Would have moved mail message-id="%s" from "%s" to "%s", skipping because of beeing in testmode',
                             mail.get('message-id'), source, destination)
        else:
            self.select_mailbox(source)
            self._move_mail(mail, source, destination, delete_old, expunge, set_flags)

    def _move_mail(self, mail, source, destination, delete_old=True, expunge=True, set_flags=None):
        self.logger.info('Moving mail message-id="%s" from "%s" to "%s"', mail.get('message-id'), source, destination)
        result = self.search_mails(source, criteria='HEADER MESSAGE-ID "{0}"'.format(mail.get('message-id')))
        uid = result[0]

        self._copy_mail(uid, destination)

        if delete_old:
            self._delete_mails(uid)

            if expunge:
                self._expunge()

        if type(set_flags) is list:
            self.select_mailbox(destination)
            uids = self.search_mails(destination, criteria='HEADER MESSAGE-ID "{0}"'.format(mail.get('message-id')))
            self._set_mailflags(uids, set_flags)

    def _set_mailflags(self, uids, flags=[]):
        self.logger.debug('Setting flags=%s on mails uid=%s', flags, uids)
        try:
            result = self.conn.set_flags(uids, flags)
        except IMAPClient.Error as e:
            self.process_error(e)
            result = None
        return result

    def _expunge(self):
        self.logger.info('Expunge mails')
        try:
            result = self.conn.expunge()
        except IMAPClient.Error as e:
            self.process_error(e)
            result = None
        return result

    def _create_mailbox(self, mailbox):
        self.logger.info('Creating mailbox %s', mailbox)
        try:
            result = self.conn.create_folder(mailbox)
        except IMAPClient.Error as e:
            self.process_error(e)
            result = None
        return result

    def _mailbox_exists(self, mailbox):
        self.logger.debug('Checking wether mailbox %s exists', mailbox)
        try:
            result = self.conn.folder_exists(mailbox)
        except IMAPClient.Error as e:
            self.process_error(e)
            result = None
        return result

    def _delete_mails(self, uids):
        self.logger.info('Deleting mails uid="%s"', uids)
        try:
            result = self.conn.delete_messages(uids)
        except IMAPClient.Error as e:
            self.process_error(e)
            result = None
        return result

    def _copy_mail(self, uids, destination):
        self.logger.info('Copying mails uid="%s" to "%s"', uids, destination)
        try:
            result = self.conn.copy(uids, destination)
        except IMAPClient.Error as e:
            self.process_error(e)
            if not self._mailbox_exists(destination):
                self.logger.info('Mailbox %s doesn\'t even exist! Creating it for you now', destination)
                result = self._create_mailbox(destination)
                result = self._copy_mail(uids, destination)
            else:
                result = None
        return result


def check_match(string, pattern):
    if string is None or len(string) == 0:
        return False

    # Basic match
    if pattern in string:
        return True

    # RegEx match
    pattern_re = re.compile(pattern)
    if pattern_re.match(string):
        return True

    return False


def clean_field_names(field):
    if field[-1:] == '!':
        return (field, field[0:-1], True)
    else:
        return (field, field, False)


class ConfigParser(object):
    def __init__(self, confdir, config=None):
        self.confdir = confdir

        if not config:
            config = {'settings': {}, 'accounts': {}, 'filters': {}}
        self.config = config

        self.parse_directory()

    def parse_directory(self):
        for dirname, subdirectories, files in os.walk(self.confdir):
            for file_name in files:
                file_path = '{0}/{1}'.format(dirname, file_name)
                if file_name.endswith('.yaml'):
                    with open(file_path, 'r') as stream:
                        data = yaml.load(stream)
                    if data:
                        for root, value in data.items():
                            if root == 'settings':
                                self.config[root] = value
                            elif root == 'accounts':
                                for account, settings in value.items():
                                    if account not in self.config[root].keys():
                                        self.config[root][account] = settings
                                    else:
                                        self.config[root][account].update(settings)
                            elif root == 'filters':
                                for account, filter_set in value.items():
                                    for filterset_name, filterset_data in filter_set.items():
                                        if account not in self.config[root].keys():
                                            self.config[root][account] = {}
                                        self.config[root][account].update({filterset_name: filterset_data})

    def dump(self):
        return self.config


def create_logger(program_name, config=None):
    if not config:
        config = {'version': 1}
    logger = logging.getLogger(program_name)
    logging.config.dictConfig(config)
    return logger


def main():
    version = '0.0.1'
    program_name = 'mailfilter'
    parser = argparse.ArgumentParser(prog=program_name, description='A mail filtering tool that is less annoying')

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
    logger = create_logger(program_name, logconfig)

    # Let's start working now
    logger.debug('Starting new instance of %s', program_name)
    logger.debug('Raw configuration: %s', config)

    # Initialize connection pools
    imap_pool = {}
    for acc, acc_settings in config.get('accounts').items():
        imap = IMAP(logger=logger,
                    server=acc_settings.get('server'),
                    username=acc_settings.get('username'),
                    password=acc_settings.get('password'),
                    test=test)
        imap.connect()  # TODO error handling
        imap_pool[acc] = imap

    while True:
        for acc, acc_settings in config.get('accounts').items():
            if not acc_settings.get('enabled', False):
                continue
            pre_inbox = acc_settings.get('pre_inbox', 'PreInbox')
            sort_mailbox = acc_settings.get('sort_mailbox', 'INBOX')
            for filter_name, filter_rulesets in sorted(config.get('filters').get(acc).items()):
                set_commands = filter_rulesets.get('commands', None)
                set_rules = filter_rulesets.get('rules', None)
                set_mailbox = filter_rulesets.get('mailbox', pre_inbox)
                ruleset = RuleSet(logger=logger,
                                  name=filter_name,
                                  ruleset=set_rules,
                                  commands=set_commands,
                                  imap=imap_pool[acc],
                                  mailbox=set_mailbox)
                ruleset.process()

            logger.info('Searching for mails that did not match any filter and moving them to %s', sort_mailbox)
            uids = imap_pool[acc].search_mails(pre_inbox, 'ALL')
            mails = imap_pool[acc].fetch_mails(uids=uids, mailbox=pre_inbox)
            for mail in mails:
                imap_pool[acc].move_mail(mails[mail], pre_inbox, sort_mailbox, set_flags=[])

        break

    logger.debug('Shutting down mailfilter instance..')


if __name__ == '__main__':
    exit(main())
