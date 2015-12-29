===========
tabellarius
===========


.. image:: https://img.shields.io/badge/donate-flattr-red.svg
    :alt: Donate via flattr
    :target: https://flattr.com/profile/bechtoldt

.. image:: https://img.shields.io/badge/license-Apache--2.0-blue.svg
    :alt: Apache-2.0-licensed
    :target: https://github.com/bechtoldt/tabellarius/blob/master/LICENSE

.. image:: https://img.shields.io/badge/chat-gitter-brightgreen.svg
    :alt: Join Gitter Chat
    :target: https://gitter.im/bechtoldt/tabellarius?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

.. image:: https://travis-ci.org/bechtoldt/tabellarius.svg?branch=master
    :alt: Travis CI
    :target: https://travis-ci.org/bechtoldt/tabellarius

.. image:: https://img.shields.io/pypi/pyversions/tabellarius.svg
    :alt: Python versions supported
    :target: https://pypi.python.org/pypi/tabellarius

.. image:: https://coveralls.io/repos/bechtoldt/tabellarius/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/bechtoldt/tabellarius?branch=master

.. image:: https://img.shields.io/pypi/dm/tabellarius.svg
    :target: https://pypi.python.org/pypi/tabellarius
    :alt: Number of Pypi package downloads

A mail-sorting tool that is less annoying

.. contents::
    :backlinks: none
    :local:


General
-------

Tabellarius is written in Python 3 compatible source code that uses a YAML Python module to parse config files and an IMAP Python module to read and operate on e-mails via IMAP.

Supported Protocols
'''''''''''''''''''

IMAP over Plaintext Transport (don't use it!):

::

    accounts:
      myaccount:
        server: imap.server.de
        username: imap@account.de
        password: mypassword
        port: 143
        starttls: false
        imaps: false

IMAP via STARTTLS (usally port 143):

::

    accounts:
      myaccount:
        server: imap.server.de
        username: imap@account.de
        password: mypassword
        port: 143
        starttls: true
        imaps: false

IMAP via Force-TLS/SSL (usally port 993):

::

    accounts:
      myaccount:
        server: imap.server.de
        username: imap@account.de
        password: mypassword
        port: 993
        starttls: false
        imaps: true

Authentication
''''''''''''''

Plain text in configuration file (don't use it!):

::

    accounts:
      myaccount:
        server: imap.server.de
        username: imap@account.de
        password: mypassword
        port: 993
        starttls: false
        imaps: true

GPG-encrypted text with or without GPG agent in configuration file (experimental):

::

    accounts:
      myaccount:
        server: imap.server.de
        username: imap@account.de
        passsword_enc: | #echo pass | gpg2 --encrypt -r <ID> --armor
          -----BEGIN PGP MESSAGE-----
          ...
          -----END PGP MESSAGE-----
        port: 993
        starttls: false
        imaps: true

Prompt for password (native):

::

    accounts:
      myaccount:
        server: imap.server.de
        username: imap@account.de
        port: 993
        starttls: false
        imaps: true


Contributing
------------

Bug reports and pull requests are welcome! If you plan to work on the code, please assure that you have basic understanding of `RFC822 <http://www.rfcreader.com/#rfc822>`_, `RFC3501 <http://www.rfcreader.com/#rfc3501>`_, `RFC4551 <http://www.rfcreader.com/#rfc4551>`_ and `RFC681 <http://www.rfcreader.com/#rfc6851>`_.

In general:

1. Fork this repo on Github
2. Add changes, test them, update docs (README.rst) if possible
3. Submit your pull request (PR) on Github, wait for feedback

But it’s better to `file an issue <https://github.com/bechtoldt/tabellarius/issues/new>`_ with your idea first.


Testing
-------

Integration tests require a running Docker daemon with Internet connection. The `container image <https://hub.docker.com/r/bechtoldt/tabellarius_tests-docker/>`_ that is beeing downloaded contains Dovecot and Redis.

Run integration tests:

::

    $ tox -e app_tests_min

Check code style (pep8/flake8) of the main/test code:

::

    $ tox -e app_flake8
    $ tox -e tests_flake8

All important tests also run on `Travis CI <https://travis-ci.org/bechtoldt/tabellarius>`_.


Configuring
-----------

All you need to know to configure Tabellarius is `YAML <http://www.yaml.org/>`_ and the configuration scheme that can also be found in files from the ``tests/configs/`` directory.


Operating
---------

Tabellarius requires Python 3 and a few additional modules (see ``requirements/`` directory).

Run in Docker container:

::

    $ docker run -it -v /path/to/config:/config:ro bechtoldt/tabellarius:<VERSION> python /tabellarius/tabellarius.py --confdir=/config

If you prefer running Tabellarius on arbitrary computers you should consider using `virtualenv <https://pypi.python.org/pypi/virtualenv>`_ with or without `virtualenvwrapper <https://pypi.python.org/pypi/virtualenvwrapper/>`_.
