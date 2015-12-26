# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from imapclient import IMAPClient
from imapclient.fixed_offset import FixedOffset
from logging import DEBUG as loglevel_DEBUG
from re import compile as regex_compile
from six import text_type
from sys import exc_info
from time import sleep
from traceback import print_exception
import backports.ssl as ssl
import email
import imapclient  # TODO required for _append

from mail import Mail


class IMAP():
    """
    Central class for IMAP server communication
    """

    def __init__(self, logger, username, password,
                 server='localhost',
                 port=143,
                 starttls=False,
                 imaps=False,
                 tlsverify=True,
                 test=False,
                 timeout=None):
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
            self.logger.debug('Establishing IMAP connection using STARTTLS/%s to %s and logging in with user %s', self.port, self.server,
                              self.username)
        elif self.imaps:
            self.logger.debug('Establishing IMAP connection using SSL/%s (imaps) to %s and logging in with user %s', self.port, self.server,
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

            # Test login/auth status
            noop = self.conn.noop()
            noop_response = noop[0].decode('utf-8')
            noop_resp_pattern_re = regex_compile('(Success|NOOP completed\.)')
            login_success = noop_resp_pattern_re.match(noop_response)

            if logout:
                return self.disconnect()
            elif login_success:
                return (True, login)
            else:
                return (False, login)  # pragma: no cover
        except Exception as e:
            err_return = self.process_error(e)

            if str(e) == "b'[AUTHENTICATIONFAILED] Authentication failed.'":  # TODO
                return (False, str(e))

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
            if isinstance(message, Mail):
                message_native = message.get_native()
            else:
                message_native = message
                message = Mail(logger=self.logger, mail_native=message)

            #self.conn.append(mailbox, message, flags, msg_time)
            self._append(mailbox, str(message_native), flags, msg_time)

            # According to rfc4315 we must not return the UID from the response, so we are fetching it ourselves
            uids = self.search_mails(mailbox=mailbox, criteria='HEADER Message-Id "{0}"'.format(message.get_header('Message-Id')))[1]
            return (True, uids[0])
        except IMAPClient.Error as e:
            return self.process_error(e)

    @do_select_mailbox
    def search_mails(self, mailbox, criteria='ALL', autocreate_mailbox=False):
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
                    #mails[uid] = Mail(logger=self.logger, uid=uid, mail_native=email.message_from_bytes(result[uid][b'RFC822']))
                    mails[uid] = Mail(logger=self.logger, mail_native=email.message_from_bytes(result[uid][b'RFC822']))
            return (True, mails)

        except IMAPClient.Error as e:
            return self.process_error(e)

    @do_select_mailbox
    def get_mailflags(self, uids, mailbox):
        """
        Retrieve flags from mails
        """
        try:
            result = self.conn.get_flags(uids)
            flags = {}

            for uid in uids:
                flags[uid] = []
                if uid not in result.keys():
                    self.logger.error('Failed to get flags for mail with uid=%s: %s', uid, result)
                    return (False, None)
                for flag in result[uid]:
                    flags[uid].append(flag.decode('utf-8'))
            return (True, flags)

        except IMAPClient.Error as e:
            return self.process_error(e)

    @do_select_mailbox
    def set_mailflags(self, uids, mailbox, flags=[]):
        """
        Set and retrieve flags from mails
        """
        if self.test:
            self.logger.info('Would have set mail flags on message uids "%s"', str(uids))
            return (True, None)
        else:
            self.logger.debug('Setting flags=%s on mails uid=%s', flags, uids)
            try:
                result = self.conn.set_flags(uids, flags)

                _flags = {}
                for uid in uids:
                    _flags[uid] = []
                    if uid not in result.keys():
                        self.logger.error('Failed to set and get flags for mail with uid=%s: %s', uid, result)
                        return (False, None)
                    for flag in result[uid]:
                        _flags[uid].append(flag.decode('utf-8'))
                return (True, _flags)
            except IMAPClient.Error as e:
                return self.process_error(e)

    @do_select_mailbox
    def add_mailflags(self, uids, mailbox, flags=[]):
        """
        Add and retrieve flags from mails
        """
        if self.test:
            self.logger.info('Would have added mail flags on message uids "%s"', str(uids))
            return (True, None)
        else:
            self.logger.debug('Adding flags=%s on mails uid=%s', flags, uids)
            try:
                result = self.conn.add_flags(uids, flags)

                _flags = {}
                for uid in uids:
                    _flags[uid] = []
                    if uid not in result.keys():
                        self.logger.error('Failed to add and get flags for mail with uid=%s: %s', uid, result)
                        return (False, None)
                    for flag in result[uid]:
                        _flags[uid].append(flag.decode('utf-8'))
                return (True, _flags)
            except IMAPClient.Error as e:
                return self.process_error(e)

    @do_select_mailbox
    def move_mail(self, message_ids, source, destination, delete_old=True, expunge=True, add_flags=None, set_flags=None):
        """
        Move a mail from a mailbox to another
        """
        return self.copy_mails(message_ids=message_ids,
                               source=source,
                               destination=destination,
                               delete_old=delete_old,
                               expunge=expunge,
                               add_flags=add_flags,
                               set_flags=set_flags)

    @do_select_mailbox
    def copy_mails(self, source, destination, message_ids=None, delete_old=False, expunge=False, add_flags=None, set_flags=None):
        """
        Copies one or more mails from a mailbox into another
        """
        if self.test:
            if delete_old:
                self.logger.info('Would have moved mail Message-Ids="%s" from "%s" to "%s", skipping because of beeing in testmode',
                                 message_ids, source, destination)
            else:
                self.logger.info('Would have copied mails with Message-Ids="%s" from "%s" to "%s", skipping because of beeing in testmode',
                                 message_ids, source, destination)
            return (True, None)
        else:
            try:
                if delete_old:
                    self.logger.debug('Moving mail Message-Ids="%s" from "%s" to "%s"', message_ids, source, destination)
                else:
                    self.logger.debug('Copying mail Message-Ids="%s" from "%s" to "%s"', message_ids, source, destination)

                #if message_ids is None:
                #    message_ids = []
                #    result = self.fetch_mails(uids=uids, mailbox=source)
                #    if not result[0]:
                #        self.logger.error('Failed to determine Message-Id by uids for mail with uids "%s"', uids)
                #        return result
                #    message_ids.append(result[1].keys())

                if not self.mailbox_exists(destination)[1]:
                    self.logger.info('Destination mailbox %s doesn\'t exist, creating it for you', destination)

                    result = self.create_mailbox(mailbox=destination)
                    if not result[0]:
                        self.logger.error('Failed to create the mailbox %s: %s', source, result[1])  # pragma: no cover
                        return result  # pragma: no cover

                uids = []
                for message_id in message_ids:
                    result = self.search_mails(mailbox=source, criteria='HEADER Message-Id "{0}"'.format(message_id))

                    if not result[0] or len(result[1]) == 0:
                        self.logger.error('Failed to determine uid by Message-Id for mail with Message-Id "%s"', message_id)
                        return (False, result[1])
                    uids.append(result[1][0])

                result = self.select_mailbox(source)
                if not result[0]:
                    return result  # pragma: no cover

                self.conn.copy(uids, destination)

                if delete_old:
                    result = self.delete_mails(uids=uids, mailbox=source)
                    if not result[0]:
                        self.logger.error('Failed to remove old mail with Message-Id="%s"/uids="%s": %s', message_ids, uids,
                                          result[1])  # pragma: no cover
                        return result  # pragma: no cover

                    if expunge:  # TODO don't expunge by default
                        result = self.expunge(mailbox=source)
                        if not result[0]:
                            self.logger.error('Failed to expunge on mailbox %s: %s', source, result[1])  # pragma: no cover
                            return result  # pragma: no cover

                dest_uids = []
                for message_id in message_ids:
                    result = self.search_mails(mailbox=destination, criteria='HEADER Message-Id "{0}"'.format(message_id))
                    if not result[0]:
                        self.logger.error('Failed to determine uid by Message-Id for mail with Message-Id "%s"',
                                          message_id)  # pragma: no cover
                        return result  # pragma: no cover
                    dest_uids.append(result[1][0])

                if isinstance(set_flags, list):
                    self.set_mailflags(uids=dest_uids, mailbox=destination, flags=set_flags)
                if add_flags:
                    self.add_mailflags(uids=dest_uids, mailbox=destination, flags=add_flags)

                return (True, dest_uids)

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
        """
        Expunge mails form a mailbox
        """
        self.logger.debug('Expunge mails from mailbox %s', mailbox)
        try:
            return (True, b'Expunge completed.' in self.conn.expunge())
        except IMAPClient.Error as e:  # pragma: no cover
            return self.process_error(e)  # pragma: no cover

    def create_mailbox(self, mailbox):
        """
        Create a mailbox
        """
        self.logger.debug('Creating mailbox %s', mailbox)
        try:
            return (True, self.conn.create_folder(mailbox) == b'Create completed.')
        except IMAPClient.Error as e:
            return self.process_error(e)

    def mailbox_exists(self, mailbox):
        """
        Check whether a mailbox exists
        """
        try:
            return (True, self.conn.folder_exists(mailbox))
        except IMAPClient.Error as e:  # pragma: no cover
            return self.process_error(e)  # pragma: no cover

    @do_select_mailbox
    def delete_mails(self, uids, mailbox):
        """
        Delete mails
        """
        self.logger.debug('Deleting mails with uid="%s"', uids)
        try:
            result = self.conn.delete_messages(uids)
            flags = {}

            for uid in uids:
                flags[uid] = []
                if uid not in result.keys():
                    self.logger.error('Failed to get flags for mail with uid=%s after deleting it: %s', uid, result)
                    return (False, None)
                for flag in result[uid]:
                    flags[uid].append(flag.decode('utf-8'))
            return (True, flags)
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
    return s  # pragma: no cover
