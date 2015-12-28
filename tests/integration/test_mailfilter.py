# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import mail_filter

from .tabellarius_test import TabellariusTest


class MailFilterTest(TabellariusTest):
    def test_check_match_basic(self):
        mailfilter = mail_filter.MailFilter(logger=None, imap=None, mail=None, config=None, mailbox=None)

        self.assertTrue(mailfilter.check_match('foo@example.com', '@example.com'))
        self.assertTrue(mailfilter.check_match('foo@example.com', 'foo@example.com'))
        self.assertFalse(mailfilter.check_match('', 'foo'))
        self.assertTrue(mailfilter.check_match('foo', 'foo'))
        self.assertTrue(mailfilter.check_match('Sönderzäichen', 'nderz'))
        self.assertTrue(mailfilter.check_match('Sönderzäichen', 'Sönder'))

    def test_check_match_regex(self):
        mailfilter = mail_filter.MailFilter(logger=None, imap=None, mail=None, config=None, mailbox=None)

        self.assertTrue(mailfilter.check_match('foo', '^.*$'))
        self.assertTrue(mailfilter.check_match('foo', '^fo+$'))
        self.assertTrue(mailfilter.check_match('foo@example.com', '^.*@example.com$'))
        self.assertTrue(mailfilter.check_match('foo@example.com', '^.*@example.(com|net)$'))
        self.assertTrue(mailfilter.check_match('Sönderzäichen', '^Sönder.*'))
        self.assertFalse(mailfilter.check_match('foo', '^fo+!$'))
