# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import os
import collections
import logging
import logging.config
import re
import yaml


class ConfigParser():
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
        """
        Recursively parse a directory of YAML files and generate runtime configuration
        """
        for dirname, subdirectories, files in os.walk(self.confdir):
            for file_name in files:
                file_path = '{0}/{1}'.format(dirname, file_name)
                if file_name.endswith('.yaml'):
                    with open(file_path, 'rb') as stream:
                        data = yaml.load(stream, yaml.FullLoader)
                    if data:
                        for root, value in data.items():
                            if root == 'settings':
                                self.config[root] = value
                            elif root == 'accounts':
                                for account, settings in value.items():
                                    # Ignore disabled accounts
                                    if 'enabled' in settings.keys() and not settings.get('enabled'):
                                        continue

                                    if account not in self.config[root].keys():
                                        self.config[root][account] = {}
                                    self.config[root][account].update(settings)
                            elif root == 'filters':
                                for account, filter_set in value.items():
                                    for filterset_name, filterset_data in filter_set.items():
                                        if account not in self.config[root].keys():
                                            self.config[root][account] = {}
                                        self.config[root][account].update({filterset_name: filterset_data})
        return self.config

    def dump(self):
        """
        Return config
        """
        return self.config


class Helper():
    """
    Contains helper functions
    """

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

    @staticmethod
    def natural_sort(l):
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        return sorted(l, key=alphanum_key)

    @staticmethod
    def sort_dict(old_dict):
        """
        Return a sorted and ordered dictionary
        """
        retval = collections.OrderedDict()
        for key in Helper().natural_sort(old_dict.keys()):
            retval[key] = old_dict[key]
        return retval

    @staticmethod
    def byte_to_str(text, encoding='utf-8'):
        """
        Convert to string
        """
        if not isinstance(text, str):
            return text.decode(encoding, 'ignore')
        return text

    @staticmethod
    def str_to_bytes(text, encoding='utf-8'):
        """
        Convert string to bytes
        """
        return text.encode(encoding)


class CaseInsensitiveDict(dict):
    """
    Basic case insensitive dict with strings only keys.

    From requests / http://stackoverflow.com/questions/3296499/case-insensitive-dictionary-search-with-python
    """

    proxy = {}

    def __init__(self, data={}):
        self.proxy = dict((k.lower(), k) for k in data)
        for k in data:
            self[k] = data[k]

    def __contains__(self, k):
        return k.lower() in self.proxy

    def __delitem__(self, k):
        key = self.proxy[k.lower()]
        super(CaseInsensitiveDict, self).__delitem__(key)
        del self.proxy[k.lower()]

    def __getitem__(self, k):
        key = self.proxy[k.lower()]
        return super(CaseInsensitiveDict, self).__getitem__(key)

    def get(self, k, default=None):
        return self[k] if k in self else default

    def __setitem__(self, k, v):
        super(CaseInsensitiveDict, self).__setitem__(k, v)
        self.proxy[k.lower()] = k
