# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import os
import collections
import jsonschema
import logging
import logging.config
import re
import yaml
from pathlib import Path


class ConfigParser():
    config = {'settings': {}, 'accounts': {}, 'filters': {}}

    """
    Recursive YAML file parsing for tabellarius configuration
    """
    def load(self, path):
        """
        Recursively parse a path (directory or/of YAML files) and generate runtime configuration
        """
        if path.endswith('.yaml'):  # TODO simply check whether path is a file (ignore extension)
            with open(path, 'rb') as stream:
                data = yaml.load(stream, yaml.FullLoader)
            if data:
                self.config = Helper().merge_dict(data, self.config)
        else:
            for dirname, subdirectories, files in os.walk(path):
                for file_name in files:
                    self.load('{0}/{1}'.format(dirname, file_name))

        return self.config

    def dump(self):
        """
        Return config
        """
        return self.config

    def validate(self):
        """
        Validate config against config schema
        """
        with open('{}/config/schema.yaml'.format(Path(__file__).parent), 'rb') as stream:
            schema = yaml.load(stream, yaml.FullLoader)

        try:
            jsonschema.validate(self.config, schema)
        except Exception as err:
            return err

        return None


class Helper:
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

    @staticmethod
    def merge_dict(a, b, path=None):
        """"
        Merges b into a (based on https://stackoverflow.com/questions/7204805/dictionaries-of-dictionaries-merge/7205107#7205107)
        """
        if path is None:
            path = []

        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    Helper().merge_dict(a[key], b[key], path + [str(key)])
                elif a[key] == b[key]:
                    pass  # same leaf value
                elif isinstance(a[key], list):
                    pass  # ignore lists
                else:
                    raise Exception('Conflict at {}'.format('.'.join(path + [str(key)])))
            else:
                a[key] = b[key]
        return a


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
