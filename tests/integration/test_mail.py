# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from .tabellarius_test import TabellariusTest


class MailTest(TabellariusTest):
    def test_set_header(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Plain
        subject = 'The subject is the subject'
        mail = self.create_email()
        mail.set_header('Subject', subject)

        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=mail), (True, 1))
        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_header('Subject'), subject)

        # Unicode
        subject = 'The sübject is the sübject'
        mail = self.create_email()
        mail.set_header('Subject', subject)

        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=mail), (True, 2))
        self.assertEqual(imapconn.fetch_mails(uids=[2], mailbox='INBOX')[1][2].get_header('Subject'), subject)

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_update_headers(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        subject = 'The subject is the subject'
        mail = self.create_email()
        mail.update_headers({'Subject': subject})

        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=mail), (True, 1))
        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_header('Subject'), subject)

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))

    def test_set_and_get_body(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        # Plain
        body = 'Testmail Body!'
        mail = self.create_email()
        mail.set_body(body)

        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=mail), (True, 1))
        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_body(), body)

        # Unicode
        body = 'Testmäil Bödy!'
        mail = self.create_email()
        mail.set_body(body)

        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=mail), (True, 2))
        self.assertEqual(imapconn.fetch_mails(uids=[2], mailbox='INBOX')[1][2].get_body(), body)

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))
