# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import tabellarius.misc

from .tabellarius_test import TabellariusTest


class HelperTest(TabellariusTest):
    def test_check_match(self):
        # Basic match
        self.assertTrue(tabellarius.misc.Helper().check_match('foo@example.com', '@example.com'))
        self.assertTrue(tabellarius.misc.Helper().check_match('foo@example.com', 'foo@example.com'))
        self.assertFalse(tabellarius.misc.Helper().check_match('', 'foo'))
        self.assertTrue(tabellarius.misc.Helper().check_match('foo', 'foo'))
        self.assertTrue(tabellarius.misc.Helper().check_match('Sönderzäichen', 'nderz'))
        self.assertTrue(tabellarius.misc.Helper().check_match('Sönderzäichen', 'Sönder'))

        # RegEx match
        self.assertTrue(tabellarius.misc.Helper().check_match('foo', '^.*$'))
        self.assertTrue(tabellarius.misc.Helper().check_match('foo', '^fo+$'))
        self.assertTrue(tabellarius.misc.Helper().check_match('foo@example.com', '^.*@example.com$'))
        self.assertTrue(tabellarius.misc.Helper().check_match('foo@example.com', '^.*@example.(com|net)$'))
        self.assertTrue(tabellarius.misc.Helper().check_match('Sönderzäichen', '^Sönder.*'))

    def test_clean_field_name(self):
        self.assertEqual(tabellarius.misc.Helper().clean_field_name('from'), ('from', 'from', False))
        self.assertEqual(tabellarius.misc.Helper().clean_field_name('from!'), ('from!', 'from', True))
        self.assertNotEqual(tabellarius.misc.Helper().clean_field_name('from!'), ('from!', 'from', False))

    def test_logger(self):
        import logging
        self.assertIsInstance(tabellarius.misc.Helper().create_logger('program_name', {}), logging.Logger)
