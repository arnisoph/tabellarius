# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import misc

from .tabellarius_test import TabellariusTest


class HelperTest(TabellariusTest):
    def test_check_match(self):
        # Basic match
        self.assertTrue(misc.Helper().check_match('foo@example.com', '@example.com'))
        self.assertTrue(misc.Helper().check_match('foo@example.com', 'foo@example.com'))
        self.assertFalse(misc.Helper().check_match('', 'foo'))
        self.assertTrue(misc.Helper().check_match('foo', 'foo'))
        self.assertTrue(misc.Helper().check_match('Sönderzäichen', 'nderz'))
        self.assertTrue(misc.Helper().check_match('Sönderzäichen', 'Sönder'))

        # RegEx match
        self.assertTrue(misc.Helper().check_match('foo', '^.*$'))
        self.assertTrue(misc.Helper().check_match('foo', '^fo+$'))
        self.assertTrue(misc.Helper().check_match('foo@example.com', '^.*@example.com$'))
        self.assertTrue(misc.Helper().check_match('foo@example.com', '^.*@example.(com|net)$'))
        self.assertTrue(misc.Helper().check_match('Sönderzäichen', '^Sönder.*'))
        self.assertFalse(misc.Helper().check_match('foo', '^fo+!$'))

    def test_clean_field_name(self):
        self.assertEqual(misc.Helper().clean_field_name('from'), ('from', 'from', False))
        self.assertEqual(misc.Helper().clean_field_name('from!'), ('from!', 'from', True))
        self.assertNotEqual(misc.Helper().clean_field_name('from!'), ('from!', 'from', False))

    def test_logger(self):
        import logging
        self.assertIsInstance(misc.Helper().create_logger('program_name', {}), logging.Logger)


class ConfigParserTest(TabellariusTest):
    def test_configparser(self):
        cfg_parser = misc.ConfigParser('config.dist')
        config = cfg_parser.dump()

        self.assertIn('accounts', config)
        self.assertIn('settings', config)
        self.assertIn('Twitter', config.get('filters', {}).get('test', {}))
