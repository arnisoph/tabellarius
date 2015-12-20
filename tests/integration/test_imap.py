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

    def test_connect(self):  # TODO test is damn slow, reduce test time
        # Test simple plaintext imap connection
        username, password = self.create_imap_user()
        self.assertEqual(imap.IMAP(logger=self.logger,
                                   server='127.0.0.1',
                                   port=10143,
                                   username=username,
                                   password=password).connect(logout=True), (True, b'Logging out'))

        if PY3:
            expect = "b'[AUTHENTICATIONFAILED] Authentication failed.'"  # TODO looks strange
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
        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

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
            self.assertEqual(imapconn.process_error(exception=e)[1], '\'test\'')
            self.assertIsInstance(imapconn.process_error(exception=e, simple_return=True), KeyError)

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
        self.assertEqual(imapconn.list_mailboxes()[1], expect)

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_select_mailbox(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        result = imapconn.select_mailbox(mailbox='INBOX')
        self.assertEqual(result[1][b'FLAGS'], (b'\\Answered', b'\\Flagged', b'\\Deleted', b'\\Seen', b'\\Draft'))

        result = imapconn.select_mailbox(mailbox='DoesNotExist')
        self.assertEqual(result[1], 'select failed: Mailbox doesn\'t exist: DoesNotExist')

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_add_mail(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        example_date = datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))
        self.assertTrue(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['FLAG', 'WAVE'])[0])
        self.assertTrue(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['\\Seen'])[0])

        self.assertEqual(
            imapconn.add_mail(mailbox='DoesNotExist',
                              message=self.create_email(),
                              flags=['FLAG', 'WAVE'],
                              msg_time=example_date)[1], 'append failed: [TRYCREATE] Mailbox doesn\'t exist: DoesNotExist')

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_search_mail(self):  # TODO see meth impl
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        example_date = datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))
        self.assertTrue(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['FLAG', 'WAVE'])[0])
        self.assertTrue(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['\\Seen'])[0])
        self.assertTrue(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['FLAG', 'WAVE'], msg_time=example_date)[0])

        self.assertEqual(imapconn.search_mails(mailbox='INBOX', criteria='ALL')[1], [1, 2, 3])
        self.assertEqual(imapconn.search_mails(mailbox='INBOX', criteria='UNSEEN')[1], [1, 3])
        self.assertEqual(imapconn.search_mails(mailbox='INBOX', criteria='SEEN')[1], [2])
        self.assertEqual(imapconn.search_mails(mailbox='INBOX', criteria='SINCE 13-Apr-2015')[1], [1, 2])
        self.assertRaises(RuntimeError, imapconn.search_mails, mailbox='DoesNotExist', criteria='ALL')
        self.assertEqual(imapconn.search_mails(mailbox='INBOX',
                                               criteria='DoesNotExist')[1],
                         'SEARCH command error: BAD [b\'Error in IMAP command UID SEARCH: Unknown argument DOESNOTEXIST\']')

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_fetch_mails(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        example_date = datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))
        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['FLAG', 'WAVE'])[1], 1)
        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['\\Seen'])[1], 2)
        self.assertEqual(imapconn.add_mail(mailbox='INBOX',
                                           message=self.create_email(),
                                           flags=['FLAG', 'WAVE'],
                                           msg_time=example_date)[1], 3)

        self.assertIn(b'RFC822', imapconn.fetch_mails(uids=[2], mailbox='INBOX', return_fields=[b'RFC822'])[1][2])
        self.assertEqual(imapconn.fetch_mails(uids=[2], mailbox='INBOX')[1][2]['subject'], 'Testmäil')
        self.assertEqual(imapconn.fetch_mails(uids=[1, 2], mailbox='INBOX')[1][2]['subject'], 'Testmäil')
        self.assertEqual(imapconn.fetch_mails(uids=[1337], mailbox='INBOX')[1], {})
        self.assertEqual(imapconn.fetch_mails(uids=[-1337],
                                              mailbox='INBOX')[1],
                         'FETCH command error: BAD [b\'Error in IMAP command UID FETCH: Invalid uidset\']')

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_move_mail(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        self.assertTrue(imapconn.add_mail(mailbox='INBOX',
                                          message=self.create_email(headers={'Subject': 'Moved Mail'}),
                                          flags=['FLAG', 'WAVE'])[0])

        message_id = imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get('message-id')
        self.assertTrue(message_id.startswith('<very_unique_id_'))

        self.assertTrue(imapconn.move_mail(message_id=message_id, source='INBOX', destination='Trash')[0])
        self.assertEqual(imapconn.search_mails(mailbox='Trash', criteria='HEADER Subject "Moved Mail"')[1], [1])

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

        # Test the test mode
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password, test=True)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        self.assertTrue(imapconn.add_mail(mailbox='INBOX',
                                          message=self.create_email(headers={'Subject': 'Moved Mail'}),
                                          flags=['FLAG', 'WAVE'])[0])

        message_id = imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get('message-id')
        self.assertTrue(message_id.startswith('<very_unique_id_'))

        self.assertTrue(imapconn.move_mail(message_id=message_id, source='INBOX', destination='Trash')[0])

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))
