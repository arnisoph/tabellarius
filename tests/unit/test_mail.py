# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from .tabellarius_test import TabellariusTest


class MailTest(TabellariusTest):
    def test_set_header(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, b'Logged in'))

        mail = self.create_email()

        mail.set_header('Subject', 'The subject is the subject')
        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=mail, flags=['FLAG', 'WAVE']), (True, 1))

        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_header('Subject'), 'The subject is the subject')

        self.assertEqual(imapconn.disconnect(), (True, b'Logging out'))
