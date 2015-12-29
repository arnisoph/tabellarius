#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup


setup(name='tabellarius',
      version='0.9.0',
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
      ],
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.2',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',])
