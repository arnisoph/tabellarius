# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from collections import namedtuple
from imapclient import IMAPClient, exceptions
from logging import DEBUG as loglevel_DEBUG
from re import compile as regex_compile
from sys import exc_info
import ssl
from time import sleep
from traceback import print_exception
import email

from tabellarius.mail import Mail
from tabellarius.misc import Helper


class IMAP():
    """
    Central class for IMAP server communication
    """
    Retval = namedtuple('Retval', 'code data')

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

        self.conn = None

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
            if not result.code:
                raise RuntimeError(result.data)
            return func(*args, **kwargs)

        return wrapper

    def process_error(self, exception, simple_return=False):
        """
        Process Python exception by logging a message and optionally showing traceback
        """
        trace_info = exc_info()
        err_msg = str(exception)

        if isinstance(exception, IMAPClient.Error):
            err_msg = Helper().byte_to_str(exception.args[0])

        self.logger.error("Catching IMAP exception {}: {}".format(type(exception), err_msg))

        if self.logger.isEnabledFor(loglevel_DEBUG):
            print_exception(*trace_info)
        del trace_info

        if simple_return:
            return exception
        else:
            return self.Retval(False, err_msg)

    def connect(self, retry=True, logout=False):
        """
        Connect to IMAP server and login
        """
        if self.starttls:
            self.logger.debug('Establishing IMAP connection using STARTTLS/{} to {} and logging in with user {}'.format(self.port, self.server,
                                                                                                                        self.username))
        elif self.imaps:
            self.logger.debug('Establishing IMAP connection using SSL/{} (imaps) to {} and logging in with user {}'.format(self.port, self.server,
                                                                                                                           self.username))

        login = ''
        err_return = None
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
            login_response = Helper().byte_to_str(login)

            # Test login/auth status
            login_success = False
            noop = self.noop()
            if noop.code and noop.data:
                login_success = True

            if logout:
                return self.disconnect()
            elif login_success:
                return self.Retval(True, login_response)
            else:
                return self.Retval(False, login_response)  # pragma: no cover

        except exceptions.LoginError as e:
            return self.process_error(e)

        except Exception as e:
            err_return = self.process_error(e)

            if retry:
                self.logger.error('Trying one more time to login')
                sleep(2)
                return self.connect(retry=False, logout=logout)
            return err_return

    def noop(self):
        """
        Do a noop to test login status
        """
        try:
            noop = self.conn.noop()
            noop_response = Helper().byte_to_str(noop[0])
            noop_resp_pattern_re = regex_compile('^(Success|NOOP completed)')
            login_success = noop_resp_pattern_re.match(noop_response)
            return self.Retval(True, login_success)
        except IMAPClient.Error as e:
            return self.process_error(e)

    def disconnect(self):
        """
        Disconnect from IMAP server
        """
        result = self.conn.logout()
        response = Helper().byte_to_str(result)
        return self.Retval(response == 'Logging out', response)

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
            return self.Retval(True, nice_list)
        except IMAPClient.Error as e:
            return self.process_error(e)

    def select_mailbox(self, mailbox):
        """
        Select a mailbox to work on
        """
        self.logger.debug('Switching to mailbox {}'.format(mailbox))
        try:
            result = self.conn.select_folder(mailbox)
            response = {}
            for key, value in result.items():
                unicode_key = Helper().byte_to_str(key)
                if unicode_key == 'FLAGS':
                    flags = []
                    for flag in value:
                        flags.append(Helper().byte_to_str(flag))
                    response[unicode_key] = tuple(flags)
                else:
                    response[unicode_key] = value
            return self.Retval(True, response)
        except IMAPClient.Error as e:
            return self.process_error(e)

    def add_mail(self, mailbox, message, flags=(), msg_time=None):
        """
        Add/append a mail to a mailbox
        """
        self.logger.debug('Adding a mail into mailbox {}'.format(mailbox))
        try:
            if not isinstance(message, Mail):
                message = Mail(logger=self.logger, mail_native=message)

            self.conn.append(mailbox, str(message.get_native()), flags, msg_time)

            # According to rfc4315 we must not return the UID from the response, so we are fetching it ourselves
            uids = self.search_mails(mailbox=mailbox, criteria='HEADER Message-Id "{}"'.format(message.get_header('Message-Id'))).data[0]

            return self.Retval(True, uids)
        except IMAPClient.Error as e:
            return self.process_error(e)

    @do_select_mailbox
    def search_mails(self, mailbox, criteria='ALL', autocreate_mailbox=False):
        """
        Search for mails in a mailbox
        """
        self.logger.debug('Searching for mails in mailbox {} and criteria=\'{}\''.format(mailbox, criteria))
        try:
            return self.Retval(True, list(self.conn.search(criteria=criteria)))
        except IMAPClient.Error as e:
            return self.process_error(e)

    @do_select_mailbox
    def fetch_mails(self, uids, mailbox, return_fields=None):
        """
        Retrieve mails from a mailbox
        """
        self.logger.debug('Fetching mails with uids {}'.format(uids))

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
                    # mails[uid] = Mail(logger=self.logger, uid=uid, mail_native=email.message_from_bytes(result[uid][b'RFC822']))
                    mails[uid] = Mail(logger=self.logger, mail_native=email.message_from_bytes(result[uid][b'RFC822']))
            return self.Retval(True, mails)

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
                    self.logger.error('Failed to get flags for mail with uid={}: {}'.format(uid, result))
                    return self.Retval(False, None)
                for flag in result[uid]:
                    flags[uid].append(flag.decode('utf-8'))
            return self.Retval(True, flags)

        except IMAPClient.Error as e:
            return self.process_error(e)

    @do_select_mailbox
    def set_mailflags(self, uids, mailbox, flags=[]):
        """
        Set and retrieve flags from mails
        """
        if self.test:
            self.logger.info('Would have set mail flags on message uids "{}"'.format(str(uids)))
            return self.Retval(True, None)
        else:
            self.logger.debug('Setting flags={} on mails uid={}', flags, uids)
            try:
                result = self.conn.set_flags(uids, flags)

                _flags = {}
                for uid in uids:
                    _flags[uid] = []
                    if uid not in result.keys():
                        self.logger.error('Failed to set and get flags for mail with uid={}: {}'.format(uid, result))
                        return self.Retval(False, None)
                    for flag in result[uid]:
                        _flags[uid].append(flag.decode('utf-8'))
                return self.Retval(True, _flags)
            except IMAPClient.Error as e:
                return self.process_error(e)

    @do_select_mailbox
    def add_mailflags(self, uids, mailbox, flags=[]):
        """
        Add and retrieve flags from mails
        """
        if self.test:
            self.logger.info('Would have added mail flags on message uids "{}"'.format(str(uids)))
            return self.Retval(True, None)
        else:
            self.logger.debug('Adding flags={} on mails uid={}', flags, uids)
            try:
                result = self.conn.add_flags(uids, flags)

                _flags = {}
                for uid in uids:
                    _flags[uid] = []
                    if uid not in result.keys():
                        self.logger.error('Failed to add and get flags for mail with uid={}: {}'.format(uid, result))
                        return self.Retval(False, None)
                    for flag in result[uid]:
                        _flags[uid].append(flag.decode('utf-8'))
                return self.Retval(True, _flags)
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
                self.logger.info('Would have moved mail Message-Ids="{}" from "{}" to "{}", skipping because of beeing in testmode'.format(
                    message_ids, source, destination))
            else:
                self.logger.info('Would have copied mails with Message-Ids="{}" from "{}" to "{}", skipping because of beeing in testmode'.format(
                    message_ids, source, destination))
            return self.Retval(True, None)
        else:
            try:
                if delete_old:
                    self.logger.debug('Moving mail Message-Ids="{}" from "{}" to "{}"'.format(message_ids, source, destination))
                else:
                    self.logger.debug('Copying mail Message-Ids="{}" from "{}" to "{}"'.format(message_ids, source, destination))

                # if message_ids is None:
                #    message_ids = []
                #    result = self.fetch_mails(uids=uids, mailbox=source)
                #    if not result.code:
                #        self.logger.error('Failed to determine Message-Id by uids for mail with uids "{}"', uids)
                #        return result
                #    message_ids.append(result.data.keys())

                if not self.mailbox_exists(destination).data:
                    self.logger.info('Destination mailbox {} doesn\'t exist, creating it for you'.format(destination))

                    result = self.create_mailbox(mailbox=destination)
                    if not result.code:
                        self.logger.error('Failed to create the mailbox {}: {}'.format(source, result.data))  # pragma: no cover
                        return result  # pragma: no cover

                uids = []
                for message_id in message_ids:
                    result = self.search_mails(mailbox=source, criteria='HEADER Message-Id "{}"'.format(message_id))

                    if not result.code or len(result.data) == 0:
                        self.logger.error('Failed to determine uid by Message-Id for mail with Message-Id "{}"'.format(message_id))
                        return self.Retval(False, result.data)
                    uids.append(result.data[0])

                result = self.select_mailbox(source)
                if not result.code:
                    return result  # pragma: no cover

                self.conn.copy(uids, destination)

                if delete_old:
                    result = self.delete_mails(uids=uids, mailbox=source)
                    if not result.code:
                        self.logger.error('Failed to remove old mail with Message-Id="{}"/uids="{}": {}'.format(message_ids, uids,
                                                                                                                result.data))  # pragma: no cover
                        return result  # pragma: no cover

                    if expunge:  # TODO don't expunge by default
                        result = self.expunge(mailbox=source)
                        if not result.code:
                            self.logger.error('Failed to expunge on mailbox {}: {}'.format(source, result.data))  # pragma: no cover
                            return result  # pragma: no cover

                dest_uids = []
                for message_id in message_ids:
                    result = self.search_mails(mailbox=destination, criteria='HEADER Message-Id "{}"'.format(message_id))
                    if not result.code:
                        self.logger.error('Failed to determine uid by Message-Id for mail with Message-Id "{}"'.format(
                            message_id))  # pragma: no cover
                        return result  # pragma: no cover
                    dest_uids.append(result.data[0])

                if isinstance(set_flags, list):
                    self.set_mailflags(uids=dest_uids, mailbox=destination, flags=set_flags)
                if add_flags:
                    self.add_mailflags(uids=dest_uids, mailbox=destination, flags=add_flags)

                return self.Retval(True, dest_uids)

            except IMAPClient.Error as e:
                return self.process_error(e)

    @do_select_mailbox
    def expunge(self, mailbox):
        """
        Expunge mails form a mailbox
        """
        self.logger.debug('Expunge mails from mailbox {}'.format(mailbox))
        try:
            return self.Retval(True, b'Expunge completed.' in self.conn.expunge())
        except IMAPClient.Error as e:  # pragma: no cover
            return self.process_error(e)  # pragma: no cover

    def create_mailbox(self, mailbox):
        """
        Create a mailbox
        """
        self.logger.debug('Creating mailbox {}'.format(mailbox))
        try:
            return self.Retval(True, self.conn.create_folder(mailbox) == b'Create completed.')
        except IMAPClient.Error as e:
            return self.process_error(e)

    def mailbox_exists(self, mailbox):
        """
        Check whether a mailbox exists
        """
        try:
            return self.Retval(True, self.conn.folder_exists(mailbox))
        except IMAPClient.Error as e:  # pragma: no cover
            return self.process_error(e)  # pragma: no cover

    @do_select_mailbox
    def delete_mails(self, uids, mailbox):
        """
        Delete mails
        """
        self.logger.debug('Deleting mails with uid="{}"'.format(uids))
        try:
            result = self.conn.delete_messages(uids)
            flags = {}

            for uid in uids:
                flags[uid] = []
                if uid not in result.keys():
                    self.logger.error('Failed to get flags for mail with uid={} after deleting it: {}'.format(uid, result))
                    return self.Retval(False, None)
                for flag in result[uid]:
                    flags[uid].append(flag.decode('utf-8'))
            return self.Retval(True, flags)
        except IMAPClient.Error as e:
            return self.process_error(e)
