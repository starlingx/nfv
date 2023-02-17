#
# Copyright (c) 2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import os

from nfv_common import debug
from nfv_common.debug._debug_defs import DEBUG_LEVEL
from nfv_common.debug._debug_module import Debug

from nfv_unit_tests.tests import testcase


class TestDebugConfig(testcase.NFVTestCase):

    def setUp(self):
        """Setup for testing."""
        super(TestDebugConfig, self).setUp()

    def tearDown(self):
        """Cleanup testing setup."""
        super(TestDebugConfig, self).tearDown()

    def test_create_debug_config(self):
        # Debug is a singleton.  Its default value is VERBOSE
        self.assertEqual(Debug()._debug_level, DEBUG_LEVEL.VERBOSE)

        # Parse a debug.ini and see if it changes
        dirname = os.path.dirname(__file__)
        debug_ini = os.path.join(dirname, '../../../nfv-vim/nfv_vim/debug.ini')
        CONF = dict()
        CONF['debug'] = dict()
        CONF['debug']['config_file'] = debug_ini
        debug.debug_initialize(CONF['debug'])

        config = debug.debug_get_config()
        # assert that the debug CONF was populated
        self.assertEqual(CONF['debug']['config_file'], config.get('config_file'))

        # assert that the _debug_level has changed
        self.assertNotEqual(Debug()._debug_level, DEBUG_LEVEL.VERBOSE)

        # locally modify the debug_level
        Debug()._debug_level = DEBUG_LEVEL.VERBOSE
        self.assertEqual(Debug()._debug_level, DEBUG_LEVEL.VERBOSE)

        # call reload_config to undo the local modification
        debug.debug_reload_config()
        self.assertNotEqual(Debug()._debug_level, DEBUG_LEVEL.VERBOSE)
