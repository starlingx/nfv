#
# Copyright (c) 2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import pickle

from nfv_plugins.nfvi_plugins.openstack.exceptions import NotFound
from nfv_plugins.nfvi_plugins.openstack.exceptions import OpenStackException
from nfv_plugins.nfvi_plugins.openstack.exceptions import OpenStackRestAPIException

from nfv_unit_tests.tests import testcase


class TestPickleableExceptions(testcase.NFVTestCase):
    """Unit tests that verify pickleable exceptions"""

    def setUp(self):
        """Setup for testing."""
        super(TestPickleableExceptions, self).setUp()

    def tearDown(self):
        """Cleanup testing setup."""
        super(TestPickleableExceptions, self).tearDown()

    def _do_pickling_test(self, ex):
        data = pickle.dumps(ex)
        obj = pickle.loads(data)
        self.assertEqual(obj.__reduce__(), ex.__reduce__())

    def test_pickling_not_found(self):
        ex = NotFound("message")
        self._do_pickling_test(ex)

    def test_pickling_openstack_exception(self):
        ex = OpenStackException("method",
                                "url",
                                "headers",
                                "body",
                                "message",
                                "reason")
        self._do_pickling_test(ex)

    def test_pickling_openstack_rest_api_exception(self):
        ex = OpenStackRestAPIException("method",
                                       "url",
                                       "headers",
                                       "body",
                                       "status_code",
                                       "message",
                                       "reason",
                                       "response_headers",
                                       "response_body",
                                       "response_reason")
        self._do_pickling_test(ex)
