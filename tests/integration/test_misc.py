# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import misc

from .tabellarius_test import TabellariusTest

from misc import CaseInsensitiveDict


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

#class CaseInsensitiveDictTest(TabellariusTest):
#    def test_case_insensitive_dict():
#        config = {}
#        print(config)
#        sorted_dcit Helper().sort_dict(config.get('filters').get(acc_id)).items():


class CaseInsensitiveDictTest(TabellariusTest):
    def test_case_insensitive_dict(self):
        headers = {'From': '<test@example.com>', 'To': '<test2@example.com>', }

        header_insensitive = CaseInsensitiveDict(headers)

        self.assertEqual(header_insensitive['From'], '<test@example.com>')
        self.assertEqual(header_insensitive['FrOm'], '<test@example.com>')
        self.assertEqual(header_insensitive['from'], '<test@example.com>')
        self.assertNotIn('From!', header_insensitive)

        self.assertEqual(header_insensitive['To'], '<test2@example.com>')
        self.assertEqual(header_insensitive['to'], '<test2@example.com>')
        self.assertEqual(header_insensitive['tO'], '<test2@example.com>')

        del header_insensitive['from']
        self.assertNotIn('From', header_insensitive)

        del header_insensitive['To']
        self.assertNotIn('To', header_insensitive)
