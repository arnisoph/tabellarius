# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

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

    def test_connect_simple_plaintext(self):
        username, password = self.create_imap_user()
        self.assertEqual(imap.IMAP(logger=self.logger,
                                   server='127.0.0.1',
                                   port=10143,
                                   username=username,
                                   password=password).connect(logout=True), (True, b'Logging out'))

    def test_connect_error_auth_failed(self):
        username, password = self.create_imap_user()

        expect = "b'[AUTHENTICATIONFAILED] Authentication failed.'"  # TODO looks strange
        self.assertEqual(imap.IMAP(logger=self.logger,
                                   server='127.0.0.1',
                                   port=10143,
                                   username=username,
                                   password='wrongpassword').connect(logout=True), (False, expect))

    def test_connect_manual_logout(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(logout=False), (True, b'Logged in'))
        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_connect_starttls(self):
        username, password = self.create_imap_user()
        self.assertEqual(imap.IMAP(logger=self.logger,
                                   server='127.0.0.1',
                                   port=10143,
                                   starttls=True,
                                   imaps=False,
                                   tlsverify=False,  # TODO test tls verification?
                                   username=username,
                                   password=password).connect(logout=True), (True, b'Logging out'))

    def test_connect_imaps(self):
        username, password = self.create_imap_user()
        self.assertEqual(imap.IMAP(logger=self.logger,
                                   server='127.0.0.1',
                                   port=10993,
                                   starttls=False,
                                   imaps=True,
                                   tlsverify=False,  # TODO test tls verification?
                                   username=username,
                                   password=password).connect(logout=True), (True, b'Logging out'))

    def test_connect_error_refused(self):
        username, password = self.create_imap_user()
        self.assertTrue(imap.IMAP(logger=self.logger,
                                  server='127.0.0.1',
                                  port=1337,
                                  starttls=False,
                                  imaps=True,
                                  tlsverify=False,  # TODO test tls verification?
                                  username=username,
                                  password=password).connect(), (False, '] Connection refused'))

    def test_process_error(self):
        try:
            raise KeyError('test')
        except KeyError as e:
            username, password = self.create_imap_user()
            imapconn = self.create_basic_imap_object(username, password)
            self.assertEqual(imapconn.process_error(exception=e), (False, '\'test\''))
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
        self.assertEqual(imapconn.list_mailboxes(), (True, expect))
        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

        # Test exception handling
        self.assertEqual(imapconn.list_mailboxes(), (False, 'command LIST illegal in state LOGOUT, only allowed in states AUTH, SELECTED'))

    def test_select_mailbox(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        result = imapconn.select_mailbox(mailbox='INBOX')
        self.assertEqual(result[1][b'FLAGS'], (b'\\Answered', b'\\Flagged', b'\\Deleted', b'\\Seen', b'\\Draft'))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_select_mailbox_nonexisting_mailbox(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        result = imapconn.select_mailbox(mailbox='DoesNotExist')
        self.assertEqual(result, (False, 'select failed: Mailbox doesn\'t exist: DoesNotExist'))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_add_mail(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        example_date = datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))
        self.assertTrue(imapconn.add_mail(mailbox='INBOX',
                                          message=self.create_email(headers={'Subject': 'Testmäil'}),
                                          flags=['FLAG', 'WAVE'])[0])
        self.assertTrue(imapconn.add_mail(mailbox='INBOX',
                                          message=self.create_email(headers={'Subject': 'Testmäil'}).get_native(),
                                          flags=['\\Seen'])[0])

        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_header('Subject'), 'Testmäil')
        self.assertEqual(imapconn.fetch_mails(uids=[2], mailbox='INBOX')[1][2].get_header('Subject'), 'Testmäil')

        self.assertEqual(
            imapconn.add_mail(mailbox='DoesNotExist',
                              message=self.create_email(),
                              flags=['FLAG', 'WAVE'],
                              msg_time=example_date), (False, 'append failed: [TRYCREATE] Mailbox doesn\'t exist: DoesNotExist'))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_search_mail(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        example_date = datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))
        self.assertTrue(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['FLAG', 'WAVE'])[0])
        self.assertTrue(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['\\Seen'])[0])
        self.assertTrue(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['FLAG', 'WAVE'], msg_time=example_date)[0])

        self.assertEqual(imapconn.search_mails(mailbox='INBOX', criteria='ALL'), (True, [1, 2, 3]))
        self.assertEqual(imapconn.search_mails(mailbox='INBOX', criteria='UNSEEN'), (True, [1, 3]))
        self.assertEqual(imapconn.search_mails(mailbox='INBOX', criteria='SEEN'), (True, [2]))
        self.assertEqual(imapconn.search_mails(mailbox='INBOX', criteria='SINCE 13-Apr-2015'), (True, [1, 2]))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_search_mail_errors(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        self.assertRaises(RuntimeError, imapconn.search_mails, mailbox='DoesNotExist', criteria='ALL')  # tests do_select_mailbox
        self.assertRaises(AttributeError, imapconn.search_mails, 'DoesNotExist', criteria='ALL')  # tests do_select_mailbox
        self.assertRaises(KeyError, imapconn.search_mails, criteria='ALL')  # tests do_select_mailbox
        self.assertEqual(imapconn.search_mails(mailbox='INBOX',
                                               criteria='DoesNotExist'),
                         (False, 'SEARCH command error: BAD [b\'Error in IMAP command UID SEARCH: Unknown argument DOESNOTEXIST\']'))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_fetch_mails(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        example_date = datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))
        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['FLAG', 'WAVE']), (True, 1))
        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['\\Seen']), (True, 2))
        self.assertEqual(imapconn.add_mail(mailbox='INBOX',
                                           message=self.create_email(),
                                           flags=['FLAG', 'WAVE'],
                                           msg_time=example_date), (True, 3))

        self.assertIn(b'RFC822', imapconn.fetch_mails(uids=[2], mailbox='INBOX', return_fields=[b'RFC822'])[1][2])
        self.assertEqual(imapconn.fetch_mails(uids=[2], mailbox='INBOX')[1][2].get_header('Subject'), 'Testmäil')
        self.assertEqual(imapconn.fetch_mails(uids=[1, 2], mailbox='INBOX')[1][2].get_header('Subject'), 'Testmäil')
        self.assertEqual(imapconn.fetch_mails(uids=[1337], mailbox='INBOX'), (True, {}))
        self.assertEqual(imapconn.fetch_mails(uids=[-1337],
                                              mailbox='INBOX'),
                         (False, 'FETCH command error: BAD [b\'Error in IMAP command UID FETCH: Invalid uidset\']'))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_get_and_set_mailflags(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email()), (True, 1))
        self.assertEqual(imapconn.get_mailflags(uids=[1], mailbox='INBOX'), (True, {1: []}))

        self.assertEqual(imapconn.set_mailflags(uids=[1], mailbox='INBOX', flags=['\Seen']), (True, {1: ['\\Seen']}))
        self.assertEqual(imapconn.get_mailflags(uids=[1], mailbox='INBOX'), (True, {1: ['\\Seen']}))

        result = imapconn.set_mailflags(uids=[1], mailbox='INBOX', flags=['\Seen', '\Answered', '\Flagged', '\Deleted', '\Draft', 'CUSTOM'])

        self.assertTrue(result[0])
        self.assertIn('\\Seen', result[1][1])
        self.assertIn('\\Answered', result[1][1])
        self.assertIn('\\Flagged', result[1][1])
        self.assertIn('\\Deleted', result[1][1])
        self.assertIn('\\Draft', result[1][1])
        self.assertIn('CUSTOM', result[1][1])

    def test_get_and_set_mailflags_testmode(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password, test=True)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        self.assertEqual(imapconn.set_mailflags(uids=[1], mailbox='INBOX', flags=['\Seen']), (True, None))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_get_and_set_mailflags_error(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email()), (True, 1))
        self.assertEqual(imapconn.set_mailflags(uids=[1],
                                                mailbox='INBOX',
                                                flags=['\S!een']),
                         (False, 'UID command error: BAD [b\'Error in IMAP command UID STORE: Invalid system flag \\\\S!EEN\']'))

        self.assertEqual(imapconn.set_mailflags(uids=[1337], mailbox='INBOX'), (False, None))
        self.assertEqual(imapconn.get_mailflags(uids=[1337], mailbox='INBOX'), (False, None))
        self.assertEqual(imapconn.get_mailflags(uids=['INVALID'],
                                                mailbox='INBOX'),
                         (False, 'FETCH command error: BAD [b\'Error in IMAP command UID FETCH: Invalid uidset\']'))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_move_mail(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        self.assertTrue(imapconn.add_mail(mailbox='INBOX',
                                          message=self.create_email(headers={'Subject': 'Moved Mäil'},
                                                                    reset_message_id=True),
                                          flags=['FLAG', 'WAVE'])[0])

        message_id = imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_header('Message-Id')
        self.assertTrue(message_id.startswith('<very_unique_id_'))

        # Move
        self.assertEqual(imapconn.move_mail(message_ids=[message_id], source='INBOX', destination='Trash'), (True, [1]))

        # Check old and copied
        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='INBOX'), (True, {}))
        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='Trash')[1][1].get_header('Message-Id'), message_id)

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_move_mail_testmode(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password, test=True)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        self.assertTrue(imapconn.add_mail(mailbox='INBOX',
                                          message=self.create_email(headers={'Subject': 'Moved Mäil'},
                                                                    reset_message_id=True),
                                          flags=['FLAG', 'WAVE'])[0])

        message_id = imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_header('Message-Id')
        self.assertTrue(message_id.startswith('<very_unique_id_'))

        # Move
        self.assertEqual(imapconn.move_mail(message_ids=[message_id], source='INBOX', destination='Trash'), (True, None))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_copy_mails(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        example_date = datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))
        self.assertTrue(imapconn.add_mail(mailbox='INBOX',
                                          message=self.create_email(headers={'Subject': 'Copied Mäil'},
                                                                    reset_message_id=True),
                                          flags=['FLAG', 'WAVE'])[0])
        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['\\Seen']), (True, 2))
        self.assertEqual(imapconn.get_mailflags(uids=[2], mailbox='INBOX'), (True, {2: ['\\Seen']}))
        self.assertEqual(imapconn.add_mail(mailbox='INBOX',
                                           message=self.create_email(),
                                           flags=['FLAG', 'WAVE'],
                                           msg_time=example_date), (True, 3))

        message_id = imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_header('Message-Id')
        self.assertTrue(message_id.startswith('<very_unique_id_'))

        # Copy
        self.assertTrue(imapconn.copy_mails(message_ids=[message_id], source='INBOX', destination='Trash', set_flags=['\Flagged'])[0])
        self.assertEqual(imapconn.copy_mails(message_ids=['<w00t>'], source='INBOX', destination='Trash'), (False, []))

        # Check old and copied
        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_header('Message-Id'), message_id)
        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='Trash')[1][1].get_header('Message-Id'), message_id)

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_copy_mails_errors(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        example_date = datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))
        self.assertTrue(imapconn.add_mail(mailbox='INBOX',
                                          message=self.create_email(headers={'Subject': 'Copied Mäil'},
                                                                    reset_message_id=True),
                                          flags=['FLAG', 'WAVE'])[0])
        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['\\Seen']), (True, 2))
        self.assertEqual(imapconn.add_mail(mailbox='INBOX',
                                           message=self.create_email(),
                                           flags=['FLAG', 'WAVE'],
                                           msg_time=example_date), (True, 3))

        message_id = imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_header('Message-Id')
        self.assertTrue(message_id.startswith('<very_unique_id_'))

        # Copy
        self.assertEqual(imapconn.copy_mails(message_ids=[message_id], source='INBOX', destination='CustomMailbox'), (True, [1]))

        # Check old and copied
        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_header('Message-Id'), message_id)
        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='CustomMailbox')[1][1].get_header('Message-Id'), message_id)

        self.assertEqual(imapconn.copy_mails(message_ids=[message_id],
                                             source='INBOX',
                                             destination=''), (False, 'copy failed: [CANNOT] Invalid mailbox name: Name is empty'))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_copy_mails_testmode(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password, test=True)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        example_date = datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))
        self.assertTrue(imapconn.add_mail(mailbox='INBOX',
                                          message=self.create_email(headers={'Subject': 'Copied Mäil'},
                                                                    reset_message_id=True),
                                          flags=['FLAG', 'WAVE'])[0])
        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['\\Seen']), (True, 2))
        self.assertEqual(imapconn.add_mail(mailbox='INBOX',
                                           message=self.create_email(),
                                           flags=['FLAG', 'WAVE'],
                                           msg_time=example_date), (True, 3))

        message_id = imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_header('Message-Id')
        self.assertTrue(message_id.startswith('<very_unique_id_'))

        # Copy
        self.assertTrue(imapconn.copy_mails(message_ids=[message_id], source='INBOX', destination='Trash'), (True, None))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_mailbox_exists(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        self.assertEqual(imapconn.mailbox_exists(mailbox='INBOX'), (True, True))

        self.assertEqual(imapconn.mailbox_exists(mailbox='INBOX!'), (True, False))
        self.assertEqual(imapconn.create_mailbox(mailbox='INBOX!'), (True, True))
        self.assertEqual(imapconn.mailbox_exists(mailbox='INBOX!'), (True, True))

        self.assertEqual(imapconn.mailbox_exists(mailbox='Ördnerß'), (True, False))

        # Test create_mailbox() exception
        self.assertEqual(imapconn.create_mailbox(mailbox=''), (False, 'create failed: [CANNOT] Invalid mailbox name: Name is empty'))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_delete_mails_and_expunge(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['FLAG', 'WAVE']), (True, 1))
        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['\\Seen']), (True, 2))

        # Test fetching works
        self.assertIn(b'RFC822', imapconn.fetch_mails(uids=[2], mailbox='INBOX', return_fields=[b'RFC822'])[1][2])
        self.assertEqual(imapconn.fetch_mails(uids=[2], mailbox='INBOX')[1][2].get_header('Subject'), 'Testmäil')
        self.assertEqual(imapconn.fetch_mails(uids=[1, 2], mailbox='INBOX')[1][2].get_header('Subject'), 'Testmäil')

        # Delete mails
        self.assertTrue(imapconn.delete_mails(uids=[1], mailbox='INBOX'))
        self.assertTrue(imapconn.delete_mails(uids=[2], mailbox='INBOX'))

        # Check their flags
        self.assertIn('\\Deleted', imapconn.get_mailflags(uids=[1], mailbox='INBOX')[1][1])
        self.assertIn('FLAG', imapconn.get_mailflags(uids=[1], mailbox='INBOX')[1][1])
        self.assertIn('WAVE', imapconn.get_mailflags(uids=[1], mailbox='INBOX')[1][1])

        self.assertIn('\\Deleted', imapconn.get_mailflags(uids=[2], mailbox='INBOX')[1][2])
        self.assertIn('\\Seen', imapconn.get_mailflags(uids=[2], mailbox='INBOX')[1][2])

        # Expuuuuunge
        self.assertEqual(imapconn.expunge(mailbox='INBOX'), (True, True))

        # Check whether they are still there
        self.assertEqual(imapconn.fetch_mails(uids=[2], mailbox='INBOX', return_fields=[b'RFC822']), (True, {}))
        self.assertEqual(imapconn.fetch_mails(uids=[2], mailbox='INBOX'), (True, {}))
        self.assertEqual(imapconn.fetch_mails(uids=[1, 2], mailbox='INBOX'), (True, {}))

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_delete_mails_and_expunge_errors(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Adding some mails to search for
        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['FLAG', 'WAVE']), (True, 1))
        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=self.create_email(), flags=['\\Seen']), (True, 2))

        # Test fetching works
        self.assertIn(b'RFC822', imapconn.fetch_mails(uids=[2], mailbox='INBOX', return_fields=[b'RFC822'])[1][2])
        self.assertEqual(imapconn.fetch_mails(uids=[2], mailbox='INBOX')[1][2].get_header('Subject'), 'Testmäil')
        self.assertEqual(imapconn.fetch_mails(uids=[1, 2], mailbox='INBOX')[1][2].get_header('Subject'), 'Testmäil')

        # Delete mails
        self.assertEqual(imapconn.delete_mails(uids=[42], mailbox='INBOX'), (False, None))
        self.assertEqual(imapconn.delete_mails(uids=['INVALID'],
                                               mailbox='INBOX'),
                         (False, 'UID command error: BAD [b\'Error in IMAP command UID STORE: Invalid uidset\']'))

        # Expuuuuunge
        self.assertEqual(imapconn.expunge(mailbox='INBOX'), (True, True))

        # Check whether they are still there
        self.assertIn(2, imapconn.fetch_mails(uids=[2], mailbox='INBOX', return_fields=[b'RFC822'])[1])
        self.assertIn(2, imapconn.fetch_mails(uids=[2], mailbox='INBOX')[1])
        self.assertIn(1, imapconn.fetch_mails(uids=[1, 2], mailbox='INBOX')[1])

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))
