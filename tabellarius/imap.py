# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import email
from imapclient import IMAPClient
from logging import DEBUG as loglevel_DEBUG
from sys import exc_info
from time import sleep
from traceback import print_exception
import backports.ssl as ssl

from mail import Mail


class IMAP(object):
    def __init__(self, logger, username, password,
                 server='localhost',
                 port=143,
                 starttls=False,
                 imaps=False,
                 tlsverify=True,
                 test=False,
                 timeout=None):
        """
        Central class for IMAP server communication
        """
        self.logger = logger
        self.username = username
        self.password = password
        self.server = server
        self.port = port
        self.imaps = imaps
        self.starttls = starttls
        self.timeout = timeout

        self.sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)  # TODO add proto arg
        if tlsverify:
            self.sslcontext.verify_mode = ssl.CERT_REQUIRED
        else:
            self.sslcontext.verify_mode = ssl.CERT_NONE  # TODO improve?

        self.test = test

    def process_error(self, exception):
        """
        Process Python exception by logging a message and optionally showing traceback
        """
        trace_info = exc_info()
        self.logger.error('Catching IMAP exception %s: %s', type(exception), exception)

        if self.logger.isEnabledFor(loglevel_DEBUG):
            print_exception(*trace_info)
        del trace_info
        return exception

    def connect(self, retry=True, logout=False):
        """
        Connect to IMAP server and login
        """
        if self.starttls:
            self.logger.debug('Establishing IMAP connection using STARTTLS/143 to %s and logging in with user %s', self.server,
                              self.username)
        elif self.imaps:
            self.logger.debug('Establishing IMAP connection using SSL/993 (imaps) to %s and logging in with user %s', self.server,
                              self.username)

        login = ''
        try:
            self.conn = IMAPClient(host=self.server,
                                   port=self.port,
                                   use_uid=True,
                                   ssl=self.imaps,
                                   ssl_context=self.sslcontext,
                                   timeout=self.timeout)

            if self.starttls:
                self.conn.starttls(ssl_context=self.sslcontext)
            login = self.conn.login(self.username, self.password)

            if logout:
                return (login == b'Logged in', self.conn.logout())
            else:
                return (login == b'Logged in', login)
        except IMAPClient.Error as e:
            self.process_error(e)
            if retry:
                self.logger.error('Trying one more time to login')
                sleep(2)
                return self.connect(retry=False, logout=logout)
            return (False, str(e))

    def disconnect(self):
        """
        Disconnect from IMAP server
        """
        return self.conn.logout()  # TODO do more?  #TODO check if logged in

    def list_mailboxes(self, directory='', pattern='*'):
        """
        Get a listing of folders (mailboxes) on the server
        """
        raw_list = self.conn.list_folders(directory, pattern)
        nice_list = []

        for mailbox in raw_list:
            flags = []
            for flag in mailbox[0]:
                flags.append(flag.decode("utf-8"))
            nice_list.append({'name': mailbox[2], 'flags': flags, 'delimiter': mailbox[1].decode("utf-8")})
        return nice_list

    def select_mailbox(self, mailbox):
        self.logger.debug('Switching to mailbox %s', mailbox)
        try:
            return self.conn.select_folder(mailbox)  # TODO convert byte strings
        except IMAPClient.Error as e:
            self.process_error(e)
            return None

    def search_mails(self, mailbox, criteria='ALL'):
        self.logger.debug('Searching for mails in mailbox %s and criteria=\'%s\'', mailbox, criteria)
        try:
            result = self.select_mailbox(mailbox)
            result = self.conn.search(criteria=criteria)
            return list(result)
        except IMAPClient.Error as e:
            self.process_error(e)
            return []

    def fetch_raw_mails(self, uids, mailbox, return_fields=[b'RFC822']):
        if len(uids) == 0:
            return []
        self.logger.debug('Fetching raw mails with uids %s', uids)

        mails = {}
        try:
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
            mail = Mail(logger=self.logger,
                        uid=raw_uid,
                        mail=email.message_from_bytes(raw_mails[raw_uid][b'RFC822']))  # TODO doesn't work with PY27
            mails[raw_uid] = mail
        return mails

    def move_mail(self, mail, source, destination, delete_old=True, expunge=True, set_flags=None):
        if self.test:
            self.logger.info('Would have moved mail message-id="%s" from "%s" to "%s", skipping because of beeing in testmode',
                             mail.get('message-id'), source, destination)
        else:
            self.select_mailbox(source)
            self._move_mail(mail, source, destination, delete_old, expunge, set_flags)

    def set_mailflags(self, uids, mailbox, flags=[]):
        if self.test:
            self.logger.info('Would have set mail flags on message uids "%s"', str(uids))
        else:
            self.select_mailbox(mailbox)
            return self._set_mailflags(uids, flags)

    def _move_mail(self, mail, source, destination, delete_old=True, expunge=True, set_flags=None):
        self.logger.debug('Moving mail message-id="%s" from "%s" to "%s"', mail.get('message-id'), source, destination)
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
            return self.conn.set_flags(uids, flags)
        except IMAPClient.Error as e:
            self.process_error(e)
            return None

    def _expunge(self):
        self.logger.debug('Expunge mails')
        try:
            return self.conn.expunge()
        except IMAPClient.Error as e:
            self.process_error(e)
            return None

    def _create_mailbox(self, mailbox):
        self.logger.debug('Creating mailbox %s', mailbox)
        try:
            return self.conn.create_folder(mailbox)
        except IMAPClient.Error as e:
            self.process_error(e)
            return None

    def _mailbox_exists(self, mailbox):
        self.logger.debug('Checking wether mailbox %s exists', mailbox)
        try:
            return self.conn.folder_exists(mailbox)
        except IMAPClient.Error as e:
            self.process_error(e)
            return None

    def _delete_mails(self, uids):
        self.logger.debug('Deleting mails uid="%s"', uids)
        try:
            return self.conn.delete_messages(uids)
        except IMAPClient.Error as e:
            self.process_error(e)
            return None

    def _copy_mail(self, uids, destination):
        self.logger.debug('Copying mails uid="%s" to "%s"', uids, destination)
        try:
            return self.conn.copy(uids, destination)
        except IMAPClient.Error as e:
            self.process_error(e)
            if not self._mailbox_exists(destination):
                self.logger.debug('Mailbox %s doesn\'t even exist! Creating it for you now', destination)
                self._create_mailbox(destination)
                return self._copy_mail(uids, destination)

            return None
