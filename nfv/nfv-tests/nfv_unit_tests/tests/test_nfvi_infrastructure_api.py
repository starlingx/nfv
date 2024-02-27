#
# Copyright (c) 2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import sys
import uuid

from nfv_vim.nfvi.objects.v1 import HOST_AVAIL_STATUS
from nfv_vim.nfvi.objects.v1 import HOST_LABEL_KEYS
from nfv_vim.nfvi.objects.v1 import HOST_LABEL_VALUES
from nfv_vim.nfvi.objects.v1 import HOST_OPER_STATE

from nfv_unit_tests.tests import testcase
from unittest import mock
sys.modules['fm_core'] = mock.Mock()
from nfv_plugins.nfvi_plugins.nfvi_infrastructure_api import host_state  # noqa: H306,E402  pylint: disable=C0413
from nfv_plugins.nfvi_plugins.nfvi_infrastructure_api import NFVIInfrastructureAPI  # noqa: H306,E402  pylint: disable=C0413

# todo(abailey): use already existing constants
CONTROLLER_PERSONALITY = 'controller'
WORKER_PERSONALITY = 'worker'
CONTROLLER_SUBFUNCTION = 'controller'
WORKER_SUBFUNCTION = 'worker'
ADMIN_STATE_UNLOCKED = "unlocked"


class TestNFVIInfrastructureAPI(testcase.NFVTestCase):

    def setUp(self):
        """Setup for testing."""
        super(TestNFVIInfrastructureAPI, self).setUp()

    def tearDown(self):
        """Cleanup testing setup."""
        super(TestNFVIInfrastructureAPI, self).tearDown()

    def test_create(self):
        """Test that the plugin_api can be created"""
        plugin_api = NFVIInfrastructureAPI()
        self.assertIsNotNone(plugin_api)
        # test the getter methods
        self.assertEqual(plugin_api.name, NFVIInfrastructureAPI._name)
        self.assertEqual(plugin_api.version, NFVIInfrastructureAPI._version)
        self.assertEqual(plugin_api.provider, NFVIInfrastructureAPI._provider)
        self.assertEqual(plugin_api.signature, NFVIInfrastructureAPI._signature)

    def test_static_host_supports_kubernetes(self):
        """Test that the _host_supports_kubernetes static method"""
        # personality is a string list.
        aio_personality = ['controller', 'worker', ]
        controller_personality = ['controller', ]
        storage_personality = ['storage', ]
        worker_personality = ['worker', ]
        # aio / controller / worker support kubernetes
        self.assertTrue(NFVIInfrastructureAPI._host_supports_kubernetes(aio_personality))
        self.assertTrue(NFVIInfrastructureAPI._host_supports_kubernetes(controller_personality))
        self.assertTrue(NFVIInfrastructureAPI._host_supports_kubernetes(worker_personality))
        # storage does not support kubernetes
        self.assertFalse(NFVIInfrastructureAPI._host_supports_kubernetes(storage_personality))

    def test_static_get_host_labels(self):
        """Test the static _get_host_labels

        Extracts from a list of label_key:label_value
         - openstack_compute
         - openstack_control
         - remote_storage
        defaults: False, False, False
        """
        OS_COMPUTE = HOST_LABEL_KEYS.OS_COMPUTE_NODE
        OS_CONTROL = HOST_LABEL_KEYS.OS_CONTROL_PLANE
        REMOTE_STORAGE = HOST_LABEL_KEYS.REMOTE_STORAGE
        LABEL_ENABLED = HOST_LABEL_VALUES.ENABLED
        LABEL_KEY = 'label_key'
        LABEL_VALUE = 'label_value'

        # todo(abailey): Fix _get_host_labels KeyError caused by
        # missing 'label_key' or 'label_value'

        # todo(abailey): Fix _get_host_labels KeyError caused by the commented out test
        # ie: 'label_key' without 'label_value'
        # test_data = [{LABEL_KEY: 'junk'}]
        # self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (False, False, False))
        # test_data = [{LABEL_VALUE: 'junk'}]
        # self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (False, False, False))

        test_data = [{LABEL_KEY: 'junk', LABEL_VALUE: 'junk'}]
        self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (False, False, False))
        test_data = [{LABEL_KEY: 'junk', LABEL_VALUE: LABEL_ENABLED}]
        self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (False, False, False))

        # test that OS_COMPUTE (first boolean) works when properly populated
        # todo(abailey): Fix _get_host_labels KeyError caused by the commented out test
        # test_data = [{LABEL_KEY: OS_COMPUTE}]
        # self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (False, False, False))
        test_data = [{LABEL_KEY: OS_COMPUTE, LABEL_VALUE: 'junk'}]
        self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (False, False, False))
        test_data = [{LABEL_KEY: OS_COMPUTE, LABEL_VALUE: LABEL_ENABLED}]
        self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (True, False, False))

        # test that OS_CONTROL (second boolean) works when properly populated
        # todo(abailey): Fix _get_host_labels KeyError caused by the commented out test
        # test_data = [{LABEL_KEY: OS_CONTROL}]
        # self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (False, False, False))
        test_data = [{LABEL_KEY: OS_CONTROL, LABEL_VALUE: 'junk'}]
        self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (False, False, False))
        test_data = [{LABEL_KEY: OS_CONTROL, LABEL_VALUE: LABEL_ENABLED}]
        self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (False, True, False))

        # test that REMOTE_STORAGE (third boolean) works when properly populated
        # todo(abailey): Fix _get_host_labels KeyError caused by the commented out test
        # test_data = [{LABEL_KEY: REMOTE_STORAGE}]
        # self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (False, False, False))
        test_data = [{LABEL_KEY: REMOTE_STORAGE, LABEL_VALUE: 'junk'}]
        self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (False, False, False))
        test_data = [{LABEL_KEY: REMOTE_STORAGE, LABEL_VALUE: LABEL_ENABLED}]
        self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (False, False, True))

        # that all three work..
        test_data = [
          {LABEL_KEY: OS_COMPUTE, LABEL_VALUE: LABEL_ENABLED},
          {LABEL_KEY: OS_CONTROL, LABEL_VALUE: LABEL_ENABLED},
          {LABEL_KEY: REMOTE_STORAGE, LABEL_VALUE: LABEL_ENABLED}
        ]
        self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (True, True, True))
        # that all three work and order not important
        test_data = [
          {LABEL_KEY: REMOTE_STORAGE, LABEL_VALUE: LABEL_ENABLED},
          {LABEL_KEY: OS_COMPUTE, LABEL_VALUE: LABEL_ENABLED},
          {LABEL_KEY: OS_CONTROL, LABEL_VALUE: LABEL_ENABLED}
        ]
        self.assertEqual(NFVIInfrastructureAPI._get_host_labels(test_data), (True, True, True))


class TestNFVIInfrastructureHostState(testcase.NFVTestCase):

    def get_host_state_args(self):
        return {
            "host_uuid": uuid.uuid4,
            "host_name": "controller-0",
            "host_personality": CONTROLLER_PERSONALITY,
            "host_sub_functions": [CONTROLLER_SUBFUNCTION,
                                   WORKER_SUBFUNCTION, ],
            "host_admin_state": ADMIN_STATE_UNLOCKED,
            "host_oper_state": HOST_OPER_STATE.ENABLED,
            "host_avail_status": HOST_AVAIL_STATUS.AVAILABLE,
            "sub_function_oper_state": HOST_OPER_STATE.ENABLED,
            "sub_function_avail_status": HOST_AVAIL_STATUS.AVAILABLE,
            "data_port_oper_state": HOST_OPER_STATE.ENABLED,
            "data_port_avail_status": HOST_AVAIL_STATUS.AVAILABLE,
            "data_port_fault_handling_enabled": False
        }

    def test_host_state_aio_sx(self):
        """Tests get_host_state defaults"""
        # unlocked / enabled / available

        args = self.get_host_state_args()
        admin_state, oper_state, avail_status, nfvi_data \
            = host_state(**args)
        self.assertEqual(admin_state, ADMIN_STATE_UNLOCKED)
        self.assertEqual(oper_state, HOST_OPER_STATE.ENABLED)
        self.assertEqual(avail_status, HOST_AVAIL_STATUS.AVAILABLE)

    def test_host_state_aio_sx_disabled(self):
        """Tests get_host_state host disabled"""
        # unlocked / disabled / available

        args = self.get_host_state_args()
        # override the default host oper state as disabled
        args["host_oper_state"] = HOST_OPER_STATE.DISABLED
        admin_state, oper_state, avail_status, nfvi_data \
            = host_state(**args)
        self.assertEqual(admin_state, ADMIN_STATE_UNLOCKED)
        self.assertEqual(oper_state, HOST_OPER_STATE.DISABLED)
        self.assertEqual(avail_status, HOST_AVAIL_STATUS.AVAILABLE)

    def test_host_state_aio_sx_missing_fields(self):
        """Tests get_host_state host missing some fields

        Set sub function operation state: None
        Set sub function avail status: None
        Set data port fields: None

        This may not be a valid scenario...
        """
        # unlocked / None / None

        args = self.get_host_state_args()
        # override the default host oper state as disabled
        args["sub_function_oper_state"] = None
        args["sub_function_avail_status"] = None
        args["data_port_oper_state"] = None

        admin_state, oper_state, avail_status, nfvi_data \
            = host_state(**args)
        self.assertEqual(admin_state, ADMIN_STATE_UNLOCKED)
        self.assertIsNone(oper_state)
        self.assertIsNone(avail_status)

    def test_host_state_worker(self):
        """Tests get_host_state for a worker"""
        # unlocked / enabled / available

        args = self.get_host_state_args()
        args["host_name"] = "worker-0"
        args["host_personality"] = WORKER_PERSONALITY
        args["host_sub_functions"] = [WORKER_SUBFUNCTION, ]
        args["data_port_fault_handling_enabled"] = True

        admin_state, oper_state, avail_status, nfvi_data \
            = host_state(**args)
        self.assertEqual(admin_state, ADMIN_STATE_UNLOCKED)
        self.assertEqual(oper_state, HOST_OPER_STATE.ENABLED)
        self.assertEqual(avail_status, HOST_AVAIL_STATUS.AVAILABLE)

    def test_host_state_worker_unknown(self):
        """Tests get_host_state for a worker with unknown states"""
        # unlocked / unknown / unknown

        args = self.get_host_state_args()
        args["host_name"] = "worker-0"
        args["host_personality"] = WORKER_PERSONALITY
        args["host_sub_functions"] = [WORKER_SUBFUNCTION, ]
        args["data_port_fault_handling_enabled"] = True
        args["data_port_oper_state"] = None

        admin_state, oper_state, avail_status, nfvi_data \
            = host_state(**args)
        self.assertEqual(admin_state, ADMIN_STATE_UNLOCKED)
        self.assertEqual(oper_state, HOST_OPER_STATE.UNKNOWN)
        self.assertEqual(avail_status, HOST_AVAIL_STATUS.UNKNOWN)

    def test_host_state_worker_failed(self):
        """Tests get_host_state for a failed worker"""
        # unlocked / enabled / failed

        args = self.get_host_state_args()
        args["host_name"] = "worker-0"
        args["host_personality"] = WORKER_PERSONALITY
        args["host_sub_functions"] = [WORKER_SUBFUNCTION, ]
        args["data_port_fault_handling_enabled"] = True
        args["data_port_avail_status"] = HOST_AVAIL_STATUS.OFFLINE

        admin_state, oper_state, avail_status, nfvi_data \
            = host_state(**args)
        self.assertEqual(admin_state, ADMIN_STATE_UNLOCKED)
        self.assertEqual(oper_state, HOST_OPER_STATE.ENABLED)
        self.assertEqual(avail_status, HOST_AVAIL_STATUS.FAILED_COMPONENT)

    def test_host_state_controller(self):
        """Tests get_host_state for a std controller"""
        # unlocked / enabled / available

        args = self.get_host_state_args()
        args["host_personality"] = CONTROLLER_PERSONALITY
        args["host_sub_functions"] = [CONTROLLER_SUBFUNCTION, ]

        admin_state, oper_state, avail_status, nfvi_data \
            = host_state(**args)
        self.assertEqual(admin_state, ADMIN_STATE_UNLOCKED)
        self.assertEqual(oper_state, HOST_OPER_STATE.ENABLED)
        self.assertEqual(avail_status, HOST_AVAIL_STATUS.AVAILABLE)
