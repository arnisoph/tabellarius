# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from __future__ import print_function

import email
import os
import redis
import sys
import time
import unittest

sys.path.insert(0, './tabellarius')

import imap
import mail
import misc


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
        imapconn = imap.IMAP(logger=self.logger,
                             server='127.0.0.1',
                             port=10993,
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

        return mail.Mail(logger=self.logger, headers=_headers, body=body)

    def parse_message_files(self, directory='tests/mails/'):
        """
        Parse message files that were found on public Github repositories

        Search URL: https://github.com/search?utf8=✓&q=path%3Atxt+Return-Path&type=Code&ref=searchresults
        """

        file_names = os.listdir(directory)

        emails = []
        for file_name in misc.Helper().natural_sort(file_names):
            if '.msg' in file_name or '.txt' in file_name:
                fh = open(directory + os.sep + file_name, 'rb')
                raw_mail = fh.read()
                mail_native = email.message_from_bytes(raw_mail)
                emails.append(mail_native)

        return emails

    logger = LoggerDummy()
    rconn = redis.StrictRedis(host='127.0.0.1', port=6379)


if __name__ == "__main__":
    unittest.main()
