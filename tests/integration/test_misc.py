# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import misc

from .tabellarius_test import TabellariusTest


class HelperTest(TabellariusTest):
    def test_logger(self):
        import logging
        self.assertIsInstance(misc.Helper().create_logger('program_name', {}), logging.Logger)


class ConfigParserTest(TabellariusTest):
    def test_configparser(self):
        cfg_parser = misc.ConfigParser('config.dist')
        config = cfg_parser.dump()

        # Check accounts
        self.assertTrue(config.get('accounts', {}).get('local_imap_server', {}).get('starttls'))
        self.assertEqual(config.get('accounts', {}).get('local_imap_server', {}).get('username'), 'test')

        # Check settings
        self.assertIn('settings', config)

        # Check filters
        self.assertIn('Twitter', config.get('filters', {}).get('test', {}))
