# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import email
import os
import redis
import time
import unittest

from tabellarius.imap import IMAP
from tabellarius.mail import Mail
from tabellarius.misc import Helper


class TabellariusTest(unittest.TestCase):
    class LoggerDummy:
        def isEnabledFor(self, *arg):
            return True

        def debug(self, *arg):
            print(*arg)

        info = debug
        error = debug

    def create_imap_user(self, username=None, password=None):
        if username is None:
            username = 'test-{0}@example.com'.format(int(round(time.time() * 1000)))
        if password is None:
            password = 'test'

        for authdb in ['userdb', 'passdb']:
            name = 'dovecot/{0}/{1}'.format(authdb, username)
            value = '{{"uid":"65534","gid":"65534","home":"/tmp/{0}","username":"{0}","password":"{1}"}}'.format(username, password)
            self.rconn.set(name=name, value=value)  # TODO
        return (username, password)

    def remove_imap_user(self, username='test'):
        for authdb in ['userdb', 'passdb']:
            self.rconn.delete('dovecot/{0}/{1}'.format(authdb, username))  # TODO

    def create_basic_imap_object(self, username, password, starttls=False, imaps=True, test=None):

        imapconn = IMAP(logger=self.logger,
                        server=self.INTEGRATION_ADDR_IMAPSERVER,
                        port=self.INTEGRATION_PORT_IMAPS,
                        starttls=starttls,
                        imaps=imaps,
                        tlsverify=False,  # TODO
                        username=username,
                        password=password,
                        test=test,
                        timeout=5)
        return imapconn

    def create_email(self, headers=None, body='This is a test mäil.', reset_message_id=False):
        _headers = {'From': '<test@example.com>', 'To': '<test@example.com>', 'Subject': 'Testmäil'}

        if headers is not None:
            _headers.update(headers)
        if reset_message_id:
            _headers['Message-Id'] = '<very_unique_id_{0}@example.com>'.format(int(round(time.time() * 1000)))

        return Mail(logger=self.logger, headers=_headers, body=body)

    def parse_message_files(self, directory='tests/mails/'):
        """
        Parse message files that were found on public Github repositories

        Search URL: https://github.com/search?utf8=✓&q=path%3Atxt+Return-Path&type=Code&ref=searchresults
        """

        file_names = os.listdir(directory)

        emails = {}
        for file_name in Helper().natural_sort(file_names):
            if '.msg' in file_name or '.txt' in file_name:
                fh = open(directory + os.sep + file_name, 'rb')
                raw_mail = fh.read()
                mail_native = email.message_from_bytes(raw_mail)
                emails[file_name] = mail_native

        return emails

    INTEGRATION_ADDR_IMAPSERVER = os.getenv('INTEGRATION_ADDR_IMAPSERVER', '127.0.0.1')
    INTEGRATION_PORT_IMAP = os.getenv('INTEGRATION_PORT_IMAP', 10143)
    INTEGRATION_PORT_IMAPS = os.getenv('INTEGRATION_PORT_IMAPS', 10993)
    INTEGRATION_PORT_REDIS = os.getenv('INTEGRATION_PORT_REDIS', 6379)
    logger = LoggerDummy()
    rconn = redis.StrictRedis(host=INTEGRATION_ADDR_IMAPSERVER, port=INTEGRATION_PORT_REDIS)


if __name__ == "__main__":
    unittest.main()
