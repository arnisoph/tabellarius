#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup


setup(name='tabellarius',
      version='0.1.3',
      description='A mail-sorting tool that is less annoying',
      author='Arnold Bechtoldt',
      author_email='mail@arnoldbechtoldt.com',
      url='https://github.com/bechtoldt/tabellarius',
      packages=['tabellarius'],
      install_requires=[
          'PyYAML==3.11',
          'gnupg==2.0.2',
          'IMAPClient==1.0.0',
          'backports.ssl==0.0.9',
      ])
