# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import collections
import sys

sys.path.insert(0, './')
from tabellarius.misc import CaseInsensitiveDict, ConfigParser, Helper

from .tabellarius_test import TabellariusTest


class HelperTest(TabellariusTest):
    def test_logger(self):
        import logging
        self.assertIsInstance(Helper().create_logger('program_name', {}), logging.Logger)


class ConfigParserTest(TabellariusTest):
    def test_configparser(self):
        cfg_parser = ConfigParser('tests/configs/integration')
        config = cfg_parser.dump()

        # Check accounts
        self.assertTrue(config.get('accounts', {}).get('local_imap_server', {}).get('starttls'))
        self.assertEqual(config.get('accounts', {}).get('local_imap_server', {}).get('username'), 'test')

        # Check settings
        self.assertIn('settings', config)

        # Check filters
        self.assertIn('Twitter', config.get('filters', {}).get('test', {}))

    def test_sorted_dict(self):
        config = {'55': 0, '42': 0, '11': 0, '10': 0, '1': 0, '111': 0, '110': 0}
        sorted_dict = Helper().sort_dict(config)

        self.assertEqual(sorted_dict, collections.OrderedDict([('1', 0), ('10', 0), ('11', 0), ('42', 0), ('55', 0), ('110', 0),
                                                               ('111', 0)]))


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
