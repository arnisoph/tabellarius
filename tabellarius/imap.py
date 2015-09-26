# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
"""
Notes:

* before calling a private function, always issue a new SELECT command
"""
import sys

# Third party libs
import email.message
sys.path.insert(0, './imapclient/imapclient')  # TODO this is ugly, improve it
from imapclient import IMAPClient

from mail import Mail


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
