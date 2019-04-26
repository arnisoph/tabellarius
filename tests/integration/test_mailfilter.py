# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from tabellarius.mail_filter import MailFilter
from tabellarius.misc import ConfigParser, Helper

from .tabellarius_test import TabellariusTest


class MailFilterTest(TabellariusTest):
    def test_check_match_basic(self):
        mailfilter = MailFilter(logger=self.logger, imap=None, mail=None, config=None, mailbox=None)

        self.assertTrue(mailfilter.check_match('foo@example.com', '@example.com'))
        self.assertTrue(mailfilter.check_match('foo@example.com', 'foo@example.com'))
        self.assertFalse(mailfilter.check_match('', 'foo'))
        self.assertTrue(mailfilter.check_match('foo', 'foo'))
        self.assertTrue(mailfilter.check_match('Sönderzäichen', 'nderz'))
        self.assertTrue(mailfilter.check_match('Sönderzäichen', 'Sönder'))
        self.assertTrue(mailfilter.check_match('UPPERCASE', 'Uppercase'))

    def test_check_match_regex(self):
        mailfilter = MailFilter(logger=self.logger, imap=None, mail=None, config=None, mailbox=None)

        self.assertTrue(mailfilter.check_match('foo', '^.*$'))
        self.assertTrue(mailfilter.check_match('foo', '^fo+$'))
        self.assertTrue(mailfilter.check_match('foo@example.com', '^.*@example.com$'))
        self.assertTrue(mailfilter.check_match('foo@example.com', '^.*@example.(com|net)$'))
        self.assertTrue(mailfilter.check_match('Sönderzäichen', '^Sönder.*'))
        self.assertFalse(mailfilter.check_match('foo', '^fo+!$'))
        self.assertTrue(mailfilter.check_match('UPPERCASE', '^Uppercase$'))

    def test_mail_filter_matching(self):
        username, password = self.create_imap_user()
        native_test_emails = self.parse_message_files()
        imapconn = self.create_basic_imap_object(username, password)
        self.assertEqual(imapconn.connect(), (True, 'Logged in'))

        cfg_parser = ConfigParser()
        config = cfg_parser.load('tests/configs/integration/valid/')

        validation_error_error = cfg_parser.validate()
        self.assertIsNone(validation_error_error)

        self.assertEqual(imapconn.create_mailbox(mailbox='ParsedMessages'), (True, True))

        for source_filename, native_email in Helper().sort_dict(native_test_emails).items():
            add_mail_result = imapconn.add_mail(mailbox='ParsedMessages', message=native_email)
            uid_no = add_mail_result.data
            self.assertTrue(add_mail_result.code)

            fetch_result = imapconn.fetch_mails(uids=[uid_no], mailbox='ParsedMessages')
            self.assertEqual(len(fetch_result.data), 1)
            self.assertIn(uid_no, fetch_result.data)
            mail = fetch_result.data[uid_no]
            message_id = mail.get_message_id()

            match = False
            self.logger.debug('TEST: Check filters for mail with message-id=\'{}\' source-file=\'{}\''.format(message_id, source_filename))
            for filter_name, filter_settings in Helper().sort_dict(config.get('filters').get('test')).items():
                mailfilter = MailFilter(logger=self.logger,
                                        imap=imapconn,
                                        mail=mail,
                                        config=filter_settings,
                                        mailbox='ParsedMessages')
                match = mailfilter.check_rules_match()

                if match:
                    break

            # Suppose we found a matching filter
            self.assertTrue(match)

            # Suppose that the first command does copy or move
            cmd = filter_settings.get('commands')[0]
            cmd_target = cmd.get('target')

            # Check whether the mail is found its destination
            search_result = imapconn.search_mails(mailbox=cmd_target, criteria='HEADER Message-Id "{0}"'.format(message_id))
            self.assertTrue(len(search_result.data) == 1)

            uid_no = search_result.data[0]
            fetch_result = imapconn.fetch_mails(uids=[uid_no], mailbox=cmd_target)

            self.assertEqual(fetch_result.data[uid_no].get_message_id(), message_id)

        self.assertEqual(imapconn.disconnect(), (True, 'Logging out'))
