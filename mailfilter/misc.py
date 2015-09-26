#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import re
import logging
import logging.config


class Helper(object):
    """
    Contains helper functions
    """

    @staticmethod
    def check_match(string, pattern):
        if string is None or len(string) == 0:
            return False

        # Basic match
        if pattern in string:
            return True

        # RegEx match
        pattern_re = re.compile(pattern)
        if pattern_re.match(string):
            return True

        return False

    @staticmethod
    def clean_field_names(field):
        if field[-1:] == '!':
            return (field, field[0:-1], True)
        else:
            return (field, field, False)

    @staticmethod
    def create_logger(program_name, config=None):
        if not config:
            config = {'version': 1}
        logger = logging.getLogger(program_name)
        logging.config.dictConfig(config)
        return logger
