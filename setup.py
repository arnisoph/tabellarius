#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from setuptools import setup

# Get the version (borrowed from hyper)
version_regex = r'__version__ = ["\']([^"\']*)["\']'
with open('tabellarius/tabellarius.py', 'r') as f:
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
      install_requires=[
          'PyYAML==3.11',
          'gnupg==2.0.2',
          'IMAPClient==1.0.0',
          'backports.ssl==0.0.9',
      ],
      classifiers=[
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Topic :: Communications :: Email :: Filters',])
