# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from __future__ import print_function

import redis
import sys
import unittest
import time
import email.charset
import email.message

sys.path.insert(0, './tabellarius')

import imap


class TabellariusTest(unittest.TestCase):
    class LoggerDummy:
        def isEnabledFor(self, *arg):
            return True

        def debug(self, *arg):
            print(*arg)

        info = debug
        critical = debug
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

    def create_basic_imap_object(self, username, password):
        imapconn = imap.IMAP(logger=self.logger,
                             server='127.0.0.1',
                             port=10993,
                             starttls=False,
                             imaps=True,
                             tlsverify=False,  # TODO
                             username=username,
                             password=password,
                             timeout=5)
        return imapconn

    def create_email(self, headers=None, body='This is a test mäil.'):
        _headers = {'From': '<test@example.com>', 'To': '<test@example.com>', 'Subject': 'Testmäil'}

        if headers is not None:
            _headers.update(headers)

        if 'Message-Id' not in _headers.keys():
            _headers['Message-Id'] = '<very_unique_id_{0}@example.com>'.format(int(round(time.time() * 1000)))

        message = email.message.Message()
        email.charset.add_charset('utf-8', email.charset.QP, email.charset.QP)
        c = email.charset.Charset('utf-8')
        message.set_charset(c)
        for field_name, field_value in _headers.items():
            message[field_name] = field_value
        message.set_payload(body)

        return message

    logger = LoggerDummy()
    rconn = redis.StrictRedis(host='127.0.0.1', port=6379)


if __name__ == "__main__":
    unittest.main()
