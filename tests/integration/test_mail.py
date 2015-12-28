# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from .tabellarius_test import TabellariusTest


class MailTest(TabellariusTest):
    def test_set_header(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, 'Logged in'))

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

        self.assertEqual(imapconn.disconnect(), (True, 'Logging out'))

    def test_update_headers(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, 'Logged in'))

        subject = 'The subject is the subject'
        mail = self.create_email()
        mail.update_headers({'Subject': subject})

        self.assertEqual(imapconn.add_mail(mailbox='INBOX', message=mail), (True, 1))
        self.assertEqual(imapconn.fetch_mails(uids=[1], mailbox='INBOX')[1][1].get_header('Subject'), subject)

        self.assertEqual(imapconn.disconnect(), (True, 'Logging out'))

    def test_set_and_get_body(self):
        username, password = self.create_imap_user()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, 'Logged in'))

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

        self.assertEqual(imapconn.disconnect(), (True, 'Logging out'))

    def test_mail_parser(self):
        username, password = self.create_imap_user()
        native_test_emails = self.parse_message_files()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, 'Logged in'))

        self.assertEqual(imapconn.create_mailbox(mailbox='ParsedMessages'), (True, True))

        uid_no = 1

        for native_email in native_test_emails:
            self.assertTrue(imapconn.add_mail(mailbox='ParsedMessages', message=native_email)[0])

            self.assertEqual(len(imapconn.fetch_mails(uids=[uid_no], mailbox='ParsedMessages')[1]), 1)

            mail = imapconn.fetch_mails(uids=[uid_no], mailbox='ParsedMessages')[1][uid_no]

            if uid_no == 1:
                self.assertEqual(mail.get_header('Subject'), 'Your Registration at www.youth4work.com')
                self.assertEqual(mail.get_header('from'), '"Youth4work" <admin@youth4work.com>')
                self.assertEqual(mail.get_header('x-Priority'), '1')
                self.assertEqual(mail.get_header('Content-Type'), 'text/html; charset=us-ascii')
                self.assertEqual(mail.get_header('Message-Id'), '<72EA803C0B6343E6860E74E31AF8437F.MAI@jagbros.in>')
                self.assertEqual(mail.get_header('Delivered-to'), '<shubham@cyberzonec.in>')
            elif uid_no == 10:
                self.assertEqual(mail.get_header('Received'), [
                    'from mail-storage-2.main-hosting.eu\r\n\tby mail-storage-2 (Dovecot) with LMTP id lFp5FIl/mVWhNQAA7jq/7w\r\n\tfor <shubham@cyberzonec.in>; Sun, 05 Jul 2015 19:03:37 +0000',  # noqa
                    'from mx2.main-hosting.eu (mx-mailgw [10.0.25.254])\r\n\tby mail-storage-2.main-hosting.eu (Postfix) with ESMTP id 52F182132074\r\n\tfor <shubham@cyberzonec.in>; Sun,  5 Jul 2015 19:03:37 +0000 (UTC)',  # noqa
                    'from cr80.mta.exacttarget.com (cr80.mta.exacttarget.com [136.147.176.80])\r\n\tby mx2.main-hosting.eu ([Main-Hosting.eu Mail System]) with ESMTPS id 102A532BD58\r\n\tfor <shubham@cyberzonec.in>; Sun,  5 Jul 2015 19:03:36 +0000 (UTC)',  # noqa
                    'by cr80.mta.exacttarget.com id hj5voi163hsr for <shubham@cyberzonec.in>; Sun, 5 Jul 2015 19:03:34 +0000 (envelope-from <bounce-11045_HTML-44842668-18161-7218422-50801@bounce.s7.exacttarget.com>)',  # noqa
                    'from orionsmtp-123.s7.exacttarget.com (172.28.29.19) by QANV1IMS01.qa.local id hj5vh81l1h05 for <shubham@cyberzonec.in>; Sun, 5 Jul 2015 13:01:40 -0600 (envelope-from <undelivered+65682+82324166@pd25.com>)',  # noqa
                    'from localhost (localhost [127.0.0.1])\r\n\tby orionsmtp-123.s7.exacttarget.com (Postfix) with ESMTP id 88D931024B9\r\n\tfor <shubham@cyberzonec.in>; Sun,  5 Jul 2015 19:01:40 +0000 (UTC)',  # noqa
                    'from orionsmtp-123.s7.exacttarget.com ([127.0.0.1])\r\n\tby localhost (orionsmtp-123.s7.exacttarget.com [127.0.0.1]) (amavisd-new, port 10024)\r\n\twith ESMTP id XsDvr_APlfBW for <shubham@cyberzonec.in>;\r\n\tSun,  5 Jul 2015 19:01:40 +0000 (UTC)',  # noqa
                    'from [127.0.0.1] (unknown [50.97.84.235])\r\n\t(Authenticated sender: pardot@s7)\r\n\tby orionsmtp-123.s7.exacttarget.com (Postfix) with ESMTPSA id 5D1A5102296\r\n\tfor <shubham@cyberzonec.in>; Sun,  5 Jul 2015 19:01:40 +0000 (UTC)'  # noqa
                ])
                self.assertEqual(
                    mail.get_header('Authentication-Results'),
                    'mx2.main-hosting.eu;\r\n\tdkim=pass (1024-bit key) header.d=websummit.net header.i=p@websummit.net header.b=LvtRd7ys')
                self.assertEqual(mail.get_header('x-recEIVER'), 'shubham@cyberzonec.in')
            elif uid_no == 13:
                self.assertEqual(mail.get_header('Subject'), 'Shubham <> Jenny')
                self.assertEqual(mail.get_header('from'), 'John Doe (über Google Docs) <drive-shares-noreply@google.com>')
            elif uid_no == 14:
                self.assertEqual(mail.get_header('Subject'), 'Fwd: Resume for Internship')
                self.assertEqual(mail.get_header('from'), 'Shubham Sharma <shubham.ks494@gmail.com>')
            elif uid_no == 15:
                self.assertEqual(mail.get_header('Subject'), 'w00t läuft im Debugmodus')
                self.assertEqual(mail.get_header('from'), 'Shubham Sharma <shhubhamsharma@gmail.com>')
                self.assertEqual(
                    mail.get_header('Received-SPF'),
                    'Pass (sender SPF authorized) identity=mailfrom; client-ip=209.85.218.48; helo=mail-oi0-f48.google.com; envelope-from=shhubhamsharma@gmail.com; receiver=shubham@cyberzonec.in')  # noqa
            uid_no = uid_no + 1

        self.assertEqual(imapconn.disconnect(), (True, 'Logging out'))
