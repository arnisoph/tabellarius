# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from six import PY3
import datetime
import imapclient.fixed_offset

import imap

from .tabellarius_test import TabellariusTest


class IMAPTest(TabellariusTest):
    #imap_users = {'test@example.com': 'test'}

    #def setUp(self):
    #    for username, password in sorted(self.imap_users.items()):
    #        self.create_imap_user(username, password)
    #def tearDown(self):
    #    for username, password in sorted(self.imap_users.items()):  # TODO
    #        self.remove_imap_user(username)

    def test_connect(self):
        # Test simple plaintext imap connection
        username, password = self.create_imap_user()
        self.assertEqual(imap.IMAP(logger=self.logger,
                                   server='127.0.0.1',
                                   port=10143,
                                   username=username,
                                   password=password).connect(logout=True), (True, b'Logging out'))

        if PY3:
            expect = "b'[AUTHENTICATIONFAILED] Authentication failed.'"
        else:
            expect = '[AUTHENTICATIONFAILED] Authentication failed.'

        username, password = self.create_imap_user()
        self.assertEqual(imap.IMAP(logger=self.logger,
                                   server='127.0.0.1',
                                   port=10143,
                                   username=username,
                                   password='wrongpassword').connect(logout=True), (False, expect))

        # Manually logging out
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(logout=False), (True, b'Logged in'))
        self.assertEqual(imapconn.disconnect(), b'Logging out')

        # Test simple imap via STARTTLS connection
        username, password = self.create_imap_user()
        self.assertEqual(imap.IMAP(logger=self.logger,
                                   server='127.0.0.1',
                                   port=10143,
                                   starttls=True,
                                   imaps=False,
                                   tlsverify=False,  # TODO test tls verification?
                                   username=username,
                                   password=password).connect(logout=True), (True, b'Logging out'))

        # Test simple imaps connection
        username, password = self.create_imap_user()
        self.assertEqual(imap.IMAP(logger=self.logger,
                                   server='127.0.0.1',
                                   port=10993,
                                   starttls=False,
                                   imaps=True,
                                   tlsverify=False,  # TODO test tls verification?
                                   username=username,
                                   password=password).connect(logout=True), (True, b'Logging out'))

    def test_process_error(self):
        try:
            raise KeyError('test')
        except KeyError as e:
            username, password = self.create_imap_user()
            imapconn = self.create_basic_imap_object(username, password)
            self.assertIsInstance(imapconn.process_error(e), KeyError)

    def test_list_mailboxes(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        expect = [{'delimiter': '/',
                   'flags': ['\\HasNoChildren', '\\Trash'],
                   'name': 'Trash'}, {'delimiter': '/',
                                      'flags': ['\\HasNoChildren', '\\Drafts'],
                                      'name': 'Drafts'}, {'delimiter': '/',
                                                          'flags': ['\\HasNoChildren', '\\Sent'],
                                                          'name': 'Sent'},
                  {'delimiter': '/',
                   'flags': ['\\HasNoChildren', '\\Junk'],
                   'name': 'Junk'}, {'delimiter': '/',
                                     'flags': ['\\HasNoChildren'],
                                     'name': 'INBOX'}]
        self.assertEqual(imapconn.list_mailboxes(), expect)

        self.assertEqual(imapconn.disconnect(), b'Logging out')

    def test_select_mailbox(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        result = imapconn.select_mailbox(mailbox='INBOX')
        self.assertEqual(result[b'FLAGS'], (b'\\Answered', b'\\Flagged', b'\\Deleted', b'\\Seen', b'\\Draft'))

        result = imapconn.select_mailbox(mailbox='DoesNotExist')
        self.assertEqual(result, 'select failed: Mailbox doesn\'t exist: DoesNotExist')

        self.assertEqual(imapconn.disconnect(), b'Logging out')

    def test_add_mail(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        self.assertTrue(imapconn.add_mail(mailbox='INBOX', message='hi', flags=['FLAG', 'WAVE']))
        self.assertTrue(imapconn.add_mail(mailbox='INBOX',
                                          message=b'bye',
                                          flags=['FLAG', 'WAVE'],
                                          msg_time=datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))))
        self.assertEqual(
            imapconn.add_mail(mailbox='DoesNotExist',
                              message=b'bye',
                              flags=['FLAG', 'WAVE'],
                              msg_time=datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))),
            'append failed: [TRYCREATE] Mailbox doesn\'t exist: DoesNotExist')

        self.assertEqual(imapconn.disconnect(), b'Logging out')

    def test_search_mail(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        self.assertTrue(imapconn.add_mail(mailbox='INBOX', message='hi', flags=['FLAG', 'WAVE']))
        self.assertTrue(imapconn.add_mail(mailbox='INBOX', message='I am Arnold', flags=['\\Seen']))
        self.assertTrue(imapconn.add_mail(mailbox='INBOX',
                                          message=b'bye',
                                          flags=['FLAG', 'WAVE'],
                                          msg_time=datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))))

        self.assertEqual(imapconn.search_mails(mailbox='INBOX', criteria='ALL'), [1, 2, 3])
        self.assertEqual(imapconn.search_mails(mailbox='INBOX', criteria='UNSEEN'), [1, 3])
        self.assertEqual(imapconn.search_mails(mailbox='INBOX', criteria='SEEN'), [2])
        self.assertEqual(imapconn.search_mails(mailbox='INBOX', criteria='SINCE 13-Apr-2015'), [1, 2])
        self.assertEqual(imapconn.search_mails(mailbox='DoesNotExist',
                                               criteria='ALL'), 'select failed: Mailbox doesn\'t exist: DoesNotExist')
        self.assertEqual(imapconn.search_mails(mailbox='INBOX',
                                               criteria='DoesNotExist'),
                         'SEARCH command error: BAD [b\'Error in IMAP command UID SEARCH: Unknown argument DOESNOTEXIST\']')
