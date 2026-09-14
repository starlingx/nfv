#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import testtools

from nfv_vim.api.controllers.v1.orchestration.sw_update._sw_update_defs import (
    FlexibleList,
    FlexibleListType,
)


class TestFlexibleListType(testtools.TestCase):
    def setUp(self):
        super().setUp()
        self.ftype = FlexibleListType()

    def test_singleton_instance(self):
        """FlexibleList should be a FlexibleListType instance."""
        self.assertIsInstance(FlexibleList, FlexibleListType)

    def test_basetype_is_str(self):
        """basetype must be str so WSME passes raw JSON values through."""
        self.assertEqual(self.ftype.basetype, str)

    def test_frombasetype_string_to_list(self):
        """A scalar string should be normalized to a single-element list."""
        result = self.ftype.frombasetype("starlingx-26.10.0")
        self.assertEqual(result, ["starlingx-26.10.0"])

    def test_frombasetype_list_passthrough(self):
        """A list should pass through unchanged."""
        result = self.ftype.frombasetype(["starlingx-26.10.0"])
        self.assertEqual(result, ["starlingx-26.10.0"])

    def test_frombasetype_multi_item_list(self):
        """A multi-item list should pass through unchanged."""
        items = ["starlingx-26.10.0", "starlingx-26.10.1"]
        result = self.ftype.frombasetype(items)
        self.assertEqual(result, items)

    def test_frombasetype_empty_list(self):
        """An empty list should pass through unchanged."""
        result = self.ftype.frombasetype([])
        self.assertEqual(result, [])

    def test_frombasetype_none(self):
        """None should be normalized to an empty list."""
        result = self.ftype.frombasetype(None)
        self.assertEqual(result, [])

    def test_frombasetype_invalid_type(self):
        """Non-string non-list types should raise ValueError."""
        self.assertRaises(ValueError, self.ftype.frombasetype, 123)

    def test_tobasetype_list(self):
        """tobasetype should return the list as-is."""
        value = ["starlingx-26.10.0"]
        result = self.ftype.tobasetype(value)
        self.assertEqual(result, value)

    def test_tobasetype_none(self):
        """tobasetype should return empty list for None."""
        result = self.ftype.tobasetype(None)
        self.assertEqual(result, [])

    def test_validate_valid_list(self):
        """A list of strings should pass validation."""
        value = ["starlingx-26.10.0", "starlingx-26.10.1"]
        result = self.ftype.validate(value)
        self.assertEqual(result, value)

    def test_validate_empty_list(self):
        """An empty list should pass validation."""
        result = self.ftype.validate([])
        self.assertEqual(result, [])

    def test_validate_none(self):
        """None should be validated as an empty list."""
        result = self.ftype.validate(None)
        self.assertEqual(result, [])

    def test_validate_non_list_rejected(self):
        """Non-list values should fail validation."""
        self.assertRaises(ValueError, self.ftype.validate, "not-a-list")

    def test_validate_non_string_items_rejected(self):
        """List items that aren't strings should fail validation."""
        self.assertRaises(ValueError, self.ftype.validate, [123])

    def test_wsme_fromjson_string_input(self):
        """End-to-end test: WSME fromjson with a string should yield a list."""
        from wsme.rest.json import fromjson

        result = fromjson(FlexibleList, "starlingx-26.10.0")
        self.assertEqual(result, ["starlingx-26.10.0"])

    def test_wsme_fromjson_list_input(self):
        """End-to-end test: WSME fromjson with a list should yield a list."""
        from wsme.rest.json import fromjson

        result = fromjson(FlexibleList, ["starlingx-26.10.0"])
        self.assertEqual(result, ["starlingx-26.10.0"])

    def test_wsme_fromjson_none_input(self):
        """End-to-end test: WSME fromjson with None should return None."""
        from wsme.rest.json import fromjson

        result = fromjson(FlexibleList, None)
        self.assertIsNone(result)
