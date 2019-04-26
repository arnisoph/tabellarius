#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from setuptools import setup

# Parse base requirements
with open('requirements/base.txt') as f:
    required_packages = f.read().splitlines()

# Get the version (borrowed from hyper)
version_regex = r'__version__ = ["\']([^"\']*)["\']'
with open('tabellarius/main.py', 'r') as f:
    text = f.read()
    match = re.search(version_regex, text)

    if match:
        version = match.group(1)
    else:
        raise RuntimeError('No version number found!')


setup(name='tabellarius',
      version=version,
      description='A mail-sorting tool that is less annoying',
      author='Arnold Bechtoldt',
      author_email='mail@arnoldbechtoldt.com',
      url='https://github.com/bechtoldt/tabellarius',
      packages=['tabellarius'],
      license='Apache 2.0',
      install_requires=required_packages,
      classifiers=[
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Topic :: Communications :: Email :: Filters'])
