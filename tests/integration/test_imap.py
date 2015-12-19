# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import imap

from .tabellarius_test import TabellariusTest


class IMAPTest(TabellariusTest):
    imap_users = {'test@example.com': 'test'}

    def setUp(self):
        for username, password in sorted(self.imap_users.items()):
            self.create_imap_user(username, password)

    def test_connect(self):
        username = 'test@example.com'
        password = self.imap_users['test@example.com']

        # Test simple plaintext imap connection
        self.assertEqual(imap.IMAP(logger=self.logger,
                                   server='127.0.0.1',
                                   port=10143,
                                   username=username,
                                   password=password).connect(logout=True), (True, b'Logging out'))

        # manually logging out
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(logout=False), (True, b'Logged in'))
        self.assertEqual(imapconn.disconnect(), b'Logging out')

        # Test simple imap via STARTTLS connection
        self.assertEqual(imap.IMAP(logger=self.logger,
                                   server='127.0.0.1',
                                   port=10143,
                                   starttls=True,
                                   imaps=False,
                                   tlsverify=False,  # TODO test tls verification?
                                   username=username,
                                   password=password).connect(logout=True), (True, b'Logging out'))

        # Test simple imaps connection
        self.assertEqual(imap.IMAP(logger=self.logger,
                                   server='127.0.0.1',
                                   port=10993,
                                   starttls=False,
                                   imaps=True,
                                   tlsverify=False,  # TODO test tls verification?
                                   username=username,
                                   password=password).connect(logout=True), (True, b'Logging out'))

    def test_process_error(self):
        username = 'test@example.com'
        password = self.imap_users['test@example.com']

        try:
            raise KeyError('test')
        except KeyError as e:
            imapconn = self.create_basic_imap_object(username, password)
            self.assertIsInstance(imapconn.process_error(e), KeyError)

    def tearDown(self):
        for username, password in sorted(self.imap_users.items()):
            self.remove_imap_user(username)
