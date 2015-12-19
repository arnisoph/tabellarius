# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import os
import re
import logging
import logging.config
import yaml


class ConfigParser(object):
    """
    Recursive YAML file parsing for Tabellarius configuration
    """

    def __init__(self, confdir, config=None):
        self.confdir = confdir

        if not config:
            config = {'settings': {}, 'accounts': {}, 'filters': {}}
        self.config = config

        self.parse_directory()

    def parse_directory(self):
        for dirname, subdirectories, files in os.walk(self.confdir):
            for file_name in files:
                file_path = '{0}/{1}'.format(dirname, file_name)
                if file_name.endswith('.yaml'):
                    with open(file_path, 'r') as stream:
                        data = yaml.load(stream)
                    if data:
                        for root, value in data.items():
                            if root == 'settings':
                                self.config[root] = value
                            elif root == 'accounts':
                                for account, settings in value.items():
                                    if account not in self.config[root].keys():
                                        self.config[root][account] = settings
                                    else:
                                        self.config[root][account].update(settings)
                            elif root == 'filters':
                                for account, filter_set in value.items():
                                    for filterset_name, filterset_data in filter_set.items():
                                        if account not in self.config[root].keys():
                                            self.config[root][account] = {}
                                        self.config[root][account].update({filterset_name: filterset_data})

    def dump(self):
        return self.config


class Helper(object):
    """
    Contains helper functions
    """

    @staticmethod
    def check_match(string, pattern):
        """
        Test whether a string matches a pattern
        """
        if string is None or len(string) == 0:
            return False

        # Basic match
        if pattern in string:
            return True

        # RegEx match
        pattern_re = re.compile(pattern)
        if pattern_re.match(string):
            return True
        else:
            return False

    @staticmethod
    def clean_field_name(field):
        """
        Parse a rule field name and return a tuple

        'from' results to ('from', 'from', false)
        'from!' results to ('from!', 'from', true)
        'to!' results to ('to!', 'to', true)
        """
        if field[-1:] == '!':
            return (field, field[0:-1], True)
        else:
            return (field, field, False)

    @staticmethod
    def create_logger(program_name, config=None):
        """
        Setup and return Python logger
        """
        if not config:
            config = {'version': 1}
        logger = logging.getLogger(program_name)
        logging.config.dictConfig(config)
        return logger
