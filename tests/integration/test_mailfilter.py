# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

#import datetime
#import imapclient
#
#from .tabellarius_test import TabellariusTest

#class MailFilterTest(TabellariusTest):
#    def test_foo(self):
#        username, password = self.create_imap_user()
#        username, password = ('test', 'test')
#        imapconn = self.create_basic_imap_object(username, password)
#        self.assertEqual(imapconn.connect(), (True, b'Logged in'))
#
#        #self.assertEqual(imapconn.create_mailbox(mailbox='PreInbox'), (True, True))
#
#        example_date = datetime.datetime(2009, 4, 5, 11, 0, 5, 0, imapclient.fixed_offset.FixedOffset(2 * 60))
#        self.assertTrue(imapconn.add_mail(mailbox='PreInbox',
#                                          message=self.create_email(headers={'Subject': 'Testmäil'}),
#                                          flags=['FLAG', 'WAVE'])[0])
#        self.assertTrue(imapconn.add_mail(mailbox='PreInbox',
#                                          message=self.create_email(headers={'Subject': 'Testmäil'}).get_native(),
#                                          flags=['\\Seen'])[0])
#        self.assertTrue(
#            imapconn.add_mail(mailbox='PreInbox',
#                              message=self.create_email(
#                                  headers={'From': '<test@amazon.com>',
#                                           'To': '<test@example.com>',
#                                           'Subject': 'Testmäil'}).get_native(),
#                              flags=['\\Seen'])[0])
#
#        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='PreInbox')[1][1].get_header('Subject'), 'Testmäil')
#        self.assertEqual(imapconn.fetch_mails(uids=[2], mailbox='PreInbox')[1][2].get_header('Subject'), 'Testmäil')
#
#    def test_check_match_basic(self):
#        self.assertTrue(misc.Helper().check_match('foo@example.com', '@example.com'))
#        self.assertTrue(misc.Helper().check_match('foo@example.com', 'foo@example.com'))
#        self.assertFalse(misc.Helper().check_match('', 'foo'))
#        self.assertTrue(misc.Helper().check_match('foo', 'foo'))
#        self.assertTrue(misc.Helper().check_match('Sönderzäichen', 'nderz'))
#        self.assertTrue(misc.Helper().check_match('Sönderzäichen', 'Sönder'))
#
#    def test_check_match_regex(self):
#        self.assertTrue(misc.Helper().check_match('foo', '^.*$'))
#        self.assertTrue(misc.Helper().check_match('foo', '^fo+$'))
#        self.assertTrue(misc.Helper().check_match('foo@example.com', '^.*@example.com$'))
#        self.assertTrue(misc.Helper().check_match('foo@example.com', '^.*@example.(com|net)$'))
#        self.assertTrue(misc.Helper().check_match('Sönderzäichen', '^Sönder.*'))
#        self.assertFalse(misc.Helper().check_match('foo', '^fo+!$'))
#
#    def test_clean_field_name(self):
#        self.assertEqual(misc.Helper().clean_field_name('from'), ('from', 'from', False))
#        self.assertEqual(misc.Helper().clean_field_name('from!'), ('from!', 'from', True))
#        self.assertNotEqual(misc.Helper().clean_field_name('from!'), ('from!', 'from', False))
