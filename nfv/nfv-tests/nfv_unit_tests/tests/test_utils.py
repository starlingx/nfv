#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_unit_tests.tests import testcase
from nfv_vim.strategy._utils import parse_version


class TestParseVersion(testcase.NFVTestCase):
    """Unit tests for the parse_version helper."""

    def test_parse_version_returns_tuple(self):
        self.assertEqual(parse_version("26.10.0"), (26, 10, 0))

    def test_parse_version_handles_major_version(self):
        self.assertEqual(parse_version("26.09"), (26, 9))

    def test_parse_version_accepts_non_string_input(self):
        # The helper coerces its argument to a string before splitting.
        self.assertEqual(parse_version(26), (26,))

    def test_parse_version_orders_numerically_not_lexically(self):
        # A lexical comparison would wrongly treat 9.0.0 as greater than 11.0.0
        self.assertGreater(parse_version("11.0.0"), parse_version("9.0.0"))
        self.assertLess(parse_version("9.100.0"), parse_version("11.0.0"))

    def test_parse_version_raises_on_non_numeric_segment(self):
        # Non-numeric segments cannot be converted and raise ValueError
        self.assertRaises(ValueError, parse_version, "26.10.abc")
