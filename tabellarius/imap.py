# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from imapclient import IMAPClient
from imapclient.fixed_offset import FixedOffset
from logging import DEBUG as loglevel_DEBUG
from six import moves, iteritems, text_type, integer_types, PY3, binary_type, string_types  # noqa
from sys import exc_info
from time import sleep
from traceback import print_exception
import backports.ssl as ssl
import email
import imapclient  # TODO required for _append

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
                if login != b'Logged in':
                    return (False, login)
                return self.disconnect()
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
        result = self.conn.logout()  # TODO do more?  #TODO check if logged in or do a silent fail
        return (result == b'Logging out', result)

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
        """
        Select a mailbox to work on
        """
        self.logger.debug('Switching to mailbox %s', mailbox)
        try:
            return self.conn.select_folder(mailbox)  # TODO convert byte strings
        except IMAPClient.Error as e:
            self.process_error(e)
            return str(e)

    def add_mail(self, mailbox, message, flags=(), msg_time=None):
        """
        Add/append a mail to a mailbox
        """
        self.logger.debug('Adding a mail into mailbox %s', mailbox)
        try:
            #self.conn.append(mailbox, message, flags, msg_time)
            self._append(mailbox, message, flags, msg_time)
            # According to rfc4315 we must not return the UID of the appended message
            return True
        except IMAPClient.Error as e:
            self.process_error(e)
            return str(e)

    def search_mails(self, mailbox, criteria='ALL'):
        """
        Search for mails in a mailbox
        """
        self.logger.debug('Searching for mails in mailbox %s and criteria=\'%s\'', mailbox, criteria)
        try:
            result = self.select_mailbox(mailbox)
            if str(result).startswith('select failed: Mailbox doesn\'t exist: '):
                return result

            result = self.conn.search(criteria=criteria)
            return list(result)
        except IMAPClient.Error as e:
            self.process_error(e)
            return str(e)

    def fetch_mails(self, uids, return_fields=None):
        """
        Retrieve mails
        """
        self.logger.debug('Fetching mails with uids %s', uids)

        return_raw = True
        if return_fields is None:
            return_raw = False

        mails = {}
        try:
            if return_raw:
                for uid in uids:
                    result = self.conn.fetch(uid, return_fields)
                    for fetch_uid, fetch_mail in result.items():
                        mails[uid] = fetch_mail
            else:
                for uid in uids:
                    result = self.conn.fetch(uid, [b'RFC822'])
                    for fetch_uid, raw_mail in result.items():
                        mail = Mail(logger=self.logger, uid=uid, mail=email.message_from_bytes(raw_mail[b'RFC822']))
                        mails[uid] = mail
            return mails
        except IMAPClient.Error as e:
            self.process_error(e)
            return str(e)

    def set_mailflags(self, uids, mailbox, flags=[]):
        if self.test:
            self.logger.info('Would have set mail flags on message uids "%s"', str(uids))
            return True
        else:
            self.select_mailbox(mailbox)
            return self._set_mailflags(uids, flags)

    def move_mail(self, message_id, source, destination, delete_old=True, expunge=True, set_flags=None):  # TODO error handling is missing
        """
        Move a mail from a mailbox to another
        """
        if self.test:
            self.logger.info('Would have moved mail message-id="%s" from "%s" to "%s", skipping because of beeing in testmode', message_id,
                             source, destination)
            return True
        else:
            try:
                self.select_mailbox(source)
                self.logger.debug('Moving mail message-id="%s" from "%s" to "%s"', message_id, source, destination)
                result = self.search_mails(source, criteria='HEADER MESSAGE-ID "{0}"'.format(message_id))
                uid = result[0]

                result = self.copy_mails([uid], source, destination)
                if not result[0]:
                    self.logger.error('Failed to move mail with message-id="%s": %s', message_id, result[1])
                    return result

                if delete_old:
                    self._delete_mails(uid)

                    if expunge:
                        self._expunge()

                if type(set_flags) is list:
                    self.select_mailbox(destination)
                    uids = self.search_mails(destination, criteria='HEADER MESSAGE-ID "{0}"'.format(message_id))
                    self._set_mailflags(uids, set_flags)

                return True
            except IMAPClient.Error as e:
                self.process_error(e)
                return str(e)

    def copy_mails(self, uids, source, destination):
        """
        Copies one or more mails from a mailbox into another
        """
        if self.test:
            self.logger.info('Would have copied mails with uids="%s" from "%s" to "%s", skipping because of beeing in testmode', uids,
                             source, destination)
            return (True, None)
        else:
            self.logger.debug('Copying mails with uids="%s" from "%s" to "%s"', uids, destination)
            try:
                if not self._mailbox_exists(destination):
                    self.logger.info('Destination mailbox %s to copy mails doesn\'t exist, creating it for you', destination)
                    self._create_mailbox(destination)  # TODO error handling

                result = self.select_mailbox(source)
                if str(result).startswith('select failed: Mailbox doesn\'t exist: '):
                    return (False, result)
                return (True, self.conn.copy(uids, destination))
            except IMAPClient.Error as e:
                self.process_error(e)
                return (True, str(e))

    def _append(self, folder, msg, flags=(), msg_time=None):  # TODO
        """
        FORKED FORM IMAPCLIENT
        """
        if msg_time:
            if not msg_time.tzinfo:
                msg_time = msg_time.replace(tzinfo=FixedOffset.for_system())

            time_val = '"{0}"'.format(msg_time.strftime("%d-%b-%Y %H:%M:%S %z"))
            time_val = imapclient.imapclient.to_unicode(time_val)
        else:
            time_val = None

        return self.conn._command_and_check('append', self.conn._normalise_folder(folder), imapclient.imapclient.seq_to_parenstr(flags),
                                            time_val, to_bytes(s=msg,
                                                               encoding='utf-8'),
                                            unpack=True)

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


#def to_unicode(s, encoding='ascii'):
#    if isinstance(s, binary_type):
#        return s.decode(encoding)
#    return s


def to_bytes(s, encoding='ascii'):
    if isinstance(s, text_type):
        return s.encode(encoding)
#        if PY3:
#        else:
#        return bytearray(s)
    return s
