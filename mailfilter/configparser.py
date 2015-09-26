# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
#from time import sleep
import os
import yaml


class ConfigParser(object):
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
