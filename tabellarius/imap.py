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

    def do_select_mailbox(func):
        """
        Decorator to do a fresh mailbox SELECT
        """

        def wrapper(*args, **kwargs):
            if len(args) != 1:
                raise AttributeError(
                    'Size of *args tuple "{0}" isn\'t 1. It looks like you haven\'t specified all '
                    'method arguments as named arguments!'.format(
                        args))

            mailbox = None
            for key in ['mailbox', 'source']:
                if key in kwargs.keys():
                    mailbox = kwargs[key]
                    break

            if mailbox is None:
                raise KeyError('Unable to SELECT a mailbox, kwargs "{0}" doesn\'t contain a mailbox name'.format(kwargs))

            result = args[0].select_mailbox(mailbox)
            if not result[0]:
                raise RuntimeError(result[1])
            return func(*args, **kwargs)

        return wrapper

    def process_error(self, exception, simple_return=False):
        """
        Process Python exception by logging a message and optionally showing traceback
        """
        trace_info = exc_info()
        self.logger.error('Catching IMAP exception %s: %s', type(exception), exception)

        if self.logger.isEnabledFor(loglevel_DEBUG):
            print_exception(*trace_info)
        del trace_info

        if not simple_return:
            return (False, str(exception))
        else:
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
            err_return = self.process_error(e)
            if retry:
                self.logger.error('Trying one more time to login')
                sleep(2)
                return self.connect(retry=False, logout=logout)
            return err_return

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
        try:
            raw_list = self.conn.list_folders(directory, pattern)
            nice_list = []

            for mailbox in raw_list:
                flags = []
                for flag in mailbox[0]:
                    flags.append(flag.decode('utf-8'))

                nice_list.append({'name': mailbox[2], 'flags': flags, 'delimiter': mailbox[1].decode("utf-8")})
            return (True, nice_list)
        except IMAPClient.Error as e:
            return self.process_error(e)

    def select_mailbox(self, mailbox):
        """
        Select a mailbox to work on
        """
        self.logger.debug('Switching to mailbox %s', mailbox)
        try:
            return (True, self.conn.select_folder(mailbox))  # TODO convert byte strings
        except IMAPClient.Error as e:
            return self.process_error(e)

    def add_mail(self, mailbox, message, flags=(), msg_time=None):
        """
        Add/append a mail to a mailbox
        """
        self.logger.debug('Adding a mail into mailbox %s', mailbox)
        try:
            #self.conn.append(mailbox, message, flags, msg_time)
            self._append(mailbox, str(message), flags, msg_time)
            # According to rfc4315 we must not return the UID from the response, so we are fetching it ourselves
            return (True, self.search_mails(mailbox=mailbox, criteria='HEADER Message-Id "{0}"'.format(message.get('message-id')))[1][0])
        except IMAPClient.Error as e:
            return self.process_error(e)

    @do_select_mailbox
    def search_mails(self, mailbox, criteria='ALL'):
        """
        Search for mails in a mailbox
        """
        self.logger.debug('Searching for mails in mailbox %s and criteria=\'%s\'', mailbox, criteria)
        try:
            return (True, list(self.conn.search(criteria=criteria)))
        except IMAPClient.Error as e:
            return self.process_error(e)

    @do_select_mailbox
    def fetch_mails(self, uids, mailbox, return_fields=None):
        """
        Retrieve mails from a mailbox
        """
        self.logger.debug('Fetching mails with uids %s', uids)

        return_raw = True
        if return_fields is None:
            return_raw = False
            return_fields = [b'RFC822']

        mails = {}
        try:
            for uid in uids:
                result = self.conn.fetch(uid, return_fields)

                if not result:
                    continue

                if return_raw:
                    mails[uid] = result[uid]
                else:
                    mails[uid] = Mail(logger=self.logger, uid=uid, mail=email.message_from_bytes(result[uid][b'RFC822']))
            return (True, mails)

        except IMAPClient.Error as e:
            return self.process_error(e)

    @do_select_mailbox
    def set_mailflags(self, uids, mailbox, flags=[]):
        if self.test:
            self.logger.info('Would have set mail flags on message uids "%s"', str(uids))
            return (True, None)
        else:
            self.logger.debug('Setting flags=%s on mails uid=%s', flags, uids)
            try:
                return (True, self.conn.set_flags(uids, flags))
            except IMAPClient.Error as e:
                return self.process_error(e)

    @do_select_mailbox
    def move_mail(self, message_ids, source, destination, delete_old=True, expunge=True, set_flags=None):
        """
        Move a mail from a mailbox to another
        """
        return self.copy_mails(message_ids=message_ids,
                               source=source,
                               destination=destination,
                               delete_old=delete_old,
                               expunge=expunge,
                               set_flags=set_flags)

    @do_select_mailbox
    def copy_mails(self, source, destination, message_ids=None, delete_old=False, expunge=False, set_flags=None):
        """
        Copies one or more mails from a mailbox into another
        """
        if self.test:
            if delete_old:
                self.logger.info('Would have moved mail message-ids="%s" from "%s" to "%s", skipping because of beeing in testmode',
                                 message_ids, source, destination)
            else:
                self.logger.info('Would have copied mails with message-ids="%s" from "%s" to "%s", skipping because of beeing in testmode',
                                 message_ids, source, destination)
            return (True, None)
        else:
            try:
                if delete_old:
                    self.logger.debug('Moving mail message-ids="%s" from "%s" to "%s"', message_ids, source, destination)
                else:
                    self.logger.debug('Copying mail message-ids="%s" from "%s" to "%s"', message_ids, source, destination)

                #if message_ids is None:
                #    message_ids = []
                #    result = self.fetch_mails(uids=uids, mailbox=source)
                #    if not result[0]:
                #        self.logger.error('Failed to determine message-id by uids for mail with uids "%s"', uids)
                #        return result
                #    message_ids.append(result[1].keys())

                if not self.mailbox_exists(destination):
                    self.logger.info('Destination mailbox %s doesn\'t exist, creating it for you', destination)

                    result = self.create_mailbox(destination)
                    if not result[0]:
                        self.logger.error('Failed to create the mailbox %s: %s', source, result[1])
                        return result

                uids = []
                for message_id in message_ids:
                    result = self.search_mails(mailbox=source, criteria='HEADER MESSAGE-ID "{0}"'.format(message_id))
                    if not result[0]:
                        self.logger.error('Failed to determine uid by message-id for mail with message-id "%s"', message_id)
                        return result
                    uids.append(result[1][0])

                result = self.select_mailbox(source)
                if not result[0]:
                    return result

                self.conn.copy(uids, destination)

                #if result is None:
                #    if delete_old:
                #        self.logger.error('Failed to move mail with message-id="%s" from "%s" to "%s": %s', message_ids, source,
                #                          destination, result)
                #    else:
                #        self.logger.error('Failed to copy mail with message-id="%s" from "%s" to "%s": %s', message_ids, source,
                #                          destination, result)
                #    return (False, result)

                if delete_old:
                    result = self.delete_mails(uids=uids, mailbox=source)
                    if not result[0]:
                        self.logger.error('Failed to remove old mail with message-id="%s"/uids="%s": %s', message_ids, uids, result[1])
                        return result

                    if expunge:  # TODO don't expunge by default
                        result = self.expunge(mailbox=source)
                        if not result[0]:
                            self.logger.error('Failed to expunge on mailbox %s: %s', source, result[1])
                            return result

                if type(set_flags) is list:  # TODO
                    result = self.select_mailbox(destination)
                    if not result[0]:
                        return result
                    uids = []
                    for message_id in message_ids:
                        result = self.search_mails(mailbox=destination, criteria='HEADER MESSAGE-ID "{0}"'.format(message_id))
                        if not result[0]:
                            self.logger.error('Failed to determine uid by message-id for mail with message-id "%s"', message_id)
                            return result
                        uids.append(result[1][0])
                    self._set_mailflags(uids, set_flags)
                return (True, None)

            except IMAPClient.Error as e:
                return self.process_error(e)

    def _append(self, folder, msg, flags=(), msg_time=None):  # TODO
        """
        FORKED FORM IMAPCLIENT
        """
        if msg_time:
            if not msg_time.tzinfo:  # pragma: no cover
                msg_time = msg_time.replace(tzinfo=FixedOffset.for_system())  # pragma: no cover

            time_val = '"{0}"'.format(msg_time.strftime("%d-%b-%Y %H:%M:%S %z"))
            time_val = imapclient.imapclient.to_unicode(time_val)
        else:
            time_val = None

        return self.conn._command_and_check('append', self.conn._normalise_folder(folder), imapclient.imapclient.seq_to_parenstr(flags),
                                            time_val, to_bytes(s=msg,
                                                               encoding='utf-8'),
                                            unpack=True)

    @do_select_mailbox
    def expunge(self, mailbox):
        self.logger.debug('Expunge mails')
        try:
            return (True, self.conn.expunge())
        except IMAPClient.Error as e:
            return self.process_error(e)

    def create_mailbox(self, mailbox):
        self.logger.debug('Creating mailbox %s', mailbox)
        try:
            return (True, self.conn.create_folder(mailbox))
        except IMAPClient.Error as e:
            return self.process_error(e)

    def mailbox_exists(self, mailbox):
        self.logger.debug('Checking wether mailbox %s exists', mailbox)
        try:
            return (True, self.conn.folder_exists(mailbox))
        except IMAPClient.Error as e:
            return self.process_error(e)

    @do_select_mailbox
    def delete_mails(self, uids, mailbox):
        self.logger.debug('Deleting mails with uid="%s"', uids)
        try:
            return (True, self.conn.delete_messages(uids))
        except IMAPClient.Error as e:
            return self.process_error(e)

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
