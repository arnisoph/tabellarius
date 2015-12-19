# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import sys
import unittest

sys.path.insert(0, './tabellarius')


class TabellariusTest(unittest.TestCase):
    class LoggerDummy:
        def isEnabledFor(self, *arg):
            return True

        def debug(self, *arg):
            print(*arg)

        info = debug
        critical = debug
        error = debug

    logger = LoggerDummy()


if __name__ == "__main__":
    unittest.main()
