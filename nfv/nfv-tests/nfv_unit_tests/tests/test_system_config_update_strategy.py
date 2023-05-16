#
# Copyright (c) 2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from unittest import mock
import uuid

from nfv_common import strategy as common_strategy
from nfv_vim import nfvi

from nfv_vim.objects import SW_UPDATE_ALARM_RESTRICTION
from nfv_vim.objects import SW_UPDATE_APPLY_TYPE
from nfv_vim.objects import SW_UPDATE_INSTANCE_ACTION
from nfv_vim.objects import SystemConfigUpdate
from nfv_vim.strategy._strategy import SystemConfigUpdateStrategy

from nfv_unit_tests.tests import sw_update_testcase


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestSystemConfigUpdateStrategy(sw_update_testcase.SwUpdateStrategyTestCase):

    def _create_system_config_update_strategy(self,
            sw_update_obj,
            controller_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            storage_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            max_parallel_worker_hosts=10,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            alarm_restrictions=SW_UPDATE_ALARM_RESTRICTION.STRICT,
            single_controller=False,
            nfvi_system_config_update_hosts=None):
        """
        Create a system config update strategy
        """
        strategy = SystemConfigUpdateStrategy(
                uuid=str(uuid.uuid4()),
                controller_apply_type=controller_apply_type,
                storage_apply_type=storage_apply_type,
                worker_apply_type=worker_apply_type,
                max_parallel_worker_hosts=max_parallel_worker_hosts,
                default_instance_action=default_instance_action,
                alarm_restrictions=alarm_restrictions,
                single_controller=single_controller,
                ignore_alarms=[])

        strategy.sw_update_obj = sw_update_obj
        strategy.nfvi_system_config_update_hosts = nfvi_system_config_update_hosts
        return strategy

    @mock.patch('nfv_common.strategy._strategy.Strategy._build')
    def test_system_config_update_strategy_build_steps(self, fake_build):
        """
        Verify build phases, etc.. for system config update strategy creation.
        """
        # setup a minimal host environment
        self.create_host('controller-0', aio=True)

        # construct the strategy. the update_obj MUST be declared here and not
        # in the create method, because it is a weakref and will be cleaned up
        # when it goes out of scope.
        update_obj = SystemConfigUpdate()
        strategy = self._create_system_config_update_strategy(update_obj)
        # The 'build' constructs a strategy that includes multiple queries
        # the results of those queries are not used until build_complete
        # mock away '_build', which invokes the build steps and their api calls
        fake_build.return_value = None
        strategy.build()

        # verify the build phase and steps
        build_phase = strategy.build_phase.as_dict()

        query_steps = [
            {'name': 'query-alarms'},
            {'name': 'query-system-config-update-hosts'},
        ]
        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'system-config-update-query',
                 'total_steps': len(query_steps),
                 'steps': query_steps,
                },
            ],
        }
        sw_update_testcase.validate_phase(build_phase, expected_results)

    def temp_log(self, txt):
        with open('./tbd.txt', 'a') as f:
            f.write(txt + "\n")

    @mock.patch('nfv_common.strategy._strategy.Strategy._build')
    def test_apply_system_config_update_strategy_simplex(self, fake_build):

        self.create_host('controller-0', aio=True)

        update_obj = SystemConfigUpdate()
        nfvi_system_config_update_hosts = list()
        controller_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-0', 'lock_required')
        nfvi_system_config_update_hosts.append(controller_0_resource)

        strategy = self._create_system_config_update_strategy(
            update_obj,
            single_controller=True,
            nfvi_system_config_update_hosts=nfvi_system_config_update_hosts)

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(strategy.is_build_failed())
        self.assertEqual(strategy.build_phase.result_reason, "")

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {
                    'name': "system-config-update-worker-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 1800},
                    ]
                },
            ]
        }
        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_common.strategy._strategy.Strategy._build')
    def test_apply_system_config_update_strategy_duplex(self, fake_build):

        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)

        update_obj = SystemConfigUpdate()
        nfvi_system_config_update_hosts = list()
        controller_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-0', 'lock_required')
        controller_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-1', 'lock_required')
        nfvi_system_config_update_hosts.append(controller_0_resource)
        nfvi_system_config_update_hosts.append(controller_1_resource)

        strategy = self._create_system_config_update_strategy(
            update_obj,
            nfvi_system_config_update_hosts=nfvi_system_config_update_hosts)

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(strategy.is_build_failed())
        self.assertEqual(strategy.build_phase.result_reason, "")

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {
                    'name': "system-config-update-worker-hosts",
                    'total_steps': 7,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'swact-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'lock-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-worker-hosts",
                    'total_steps': 7,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'swact-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'lock-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 1800},
                    ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_common.strategy._strategy.Strategy._build')
    def test_apply_system_config_update_strategy_standard_serial(self, fake_build):

        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('compute-0')
        self.create_host('compute-1')

        update_obj = SystemConfigUpdate()
        nfvi_system_config_update_hosts = list()
        controller_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-0', 'lock_required')
        controller_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-1', 'lock_required')
        compute_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'compute-0', 'lock_required')
        compute_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'compute-1', 'lock_required')
        storage_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'storage-0', 'lock_required')
        storage_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'storage-1', 'lock_required')
        nfvi_system_config_update_hosts.append(controller_0_resource)
        nfvi_system_config_update_hosts.append(controller_1_resource)
        nfvi_system_config_update_hosts.append(compute_0_resource)
        nfvi_system_config_update_hosts.append(compute_1_resource)
        nfvi_system_config_update_hosts.append(storage_0_resource)
        nfvi_system_config_update_hosts.append(storage_1_resource)

        strategy = self._create_system_config_update_strategy(
            update_obj,
            nfvi_system_config_update_hosts=nfvi_system_config_update_hosts)

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(strategy.is_build_failed())
        self.assertEqual(strategy.build_phase.result_reason, "")

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 6,
            'stages': [
                {
                    'name': "system-config-update-controllers",
                    'total_steps': 7,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'swact-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'lock-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-controllers",
                    'total_steps': 7,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'swact-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'lock-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-storage-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['storage-0']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['storage-0']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['storage-0']},
                        {'name': 'wait-data-sync',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-storage-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'wait-data-sync',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-worker-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['compute-0']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['compute-0']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['compute-0']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 600},
                    ]
                },
                {
                    'name': "system-config-update-worker-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['compute-1']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['compute-1']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['compute-1']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 600},
                    ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_common.strategy._strategy.Strategy._build')
    def test_apply_system_config_update_strategy_standard_parallel_worker(self, fake_build):

        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('compute-0')
        self.create_host('compute-1')

        update_obj = SystemConfigUpdate()
        nfvi_system_config_update_hosts = list()
        controller_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-0', 'lock_required')
        controller_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-1', 'lock_required')
        compute_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'compute-0', 'lock_required')
        compute_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'compute-1', 'lock_required')
        storage_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'storage-0', 'lock_required')
        storage_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'storage-1', 'lock_required')
        nfvi_system_config_update_hosts.append(controller_0_resource)
        nfvi_system_config_update_hosts.append(controller_1_resource)
        nfvi_system_config_update_hosts.append(compute_0_resource)
        nfvi_system_config_update_hosts.append(compute_1_resource)
        nfvi_system_config_update_hosts.append(storage_0_resource)
        nfvi_system_config_update_hosts.append(storage_1_resource)

        strategy = self._create_system_config_update_strategy(
            update_obj,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            nfvi_system_config_update_hosts=nfvi_system_config_update_hosts)

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(strategy.is_build_failed())
        self.assertEqual(strategy.build_phase.result_reason, "")

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 5,
            'stages': [
                {
                    'name': "system-config-update-controllers",
                    'total_steps': 7,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'swact-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'lock-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-controllers",
                    'total_steps': 7,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'swact-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'lock-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-storage-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['storage-0']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['storage-0']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['storage-0']},
                        {'name': 'wait-data-sync',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-storage-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'wait-data-sync',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-worker-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['compute-0', 'compute-1']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['compute-0', 'compute-1']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['compute-0', 'compute-1']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 600},
                    ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_common.strategy._strategy.Strategy._build')
    def test_apply_system_config_update_strategy_host_not_required(self, fake_build):

        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('compute-0')
        self.create_host('compute-1')

        update_obj = SystemConfigUpdate()
        nfvi_system_config_update_hosts = list()
        controller_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-0', 'lock_required')
        controller_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-1', 'not_required')
        compute_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'compute-0', 'lock_required')
        compute_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'compute-1', 'not_required')
        storage_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'storage-0', 'not_required')
        storage_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'storage-1', 'lock_required')
        nfvi_system_config_update_hosts.append(controller_0_resource)
        nfvi_system_config_update_hosts.append(controller_1_resource)
        nfvi_system_config_update_hosts.append(compute_0_resource)
        nfvi_system_config_update_hosts.append(compute_1_resource)
        nfvi_system_config_update_hosts.append(storage_0_resource)
        nfvi_system_config_update_hosts.append(storage_1_resource)

        strategy = self._create_system_config_update_strategy(
            update_obj,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            nfvi_system_config_update_hosts=nfvi_system_config_update_hosts)

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(strategy.is_build_failed())
        self.assertEqual(strategy.build_phase.result_reason, "")

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {
                    'name': "system-config-update-controllers",
                    'total_steps': 7,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'swact-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'lock-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-storage-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'wait-data-sync',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-worker-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['compute-0']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['compute-0']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['compute-0']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 600},
                    ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_common.strategy._strategy.Strategy._build')
    def test_apply_system_config_update_strategy_controller_ignore(self, fake_build):

        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('compute-0')
        self.create_host('compute-1')

        update_obj = SystemConfigUpdate()
        nfvi_system_config_update_hosts = list()
        controller_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-0', 'lock_required')
        controller_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-1', 'not_required')
        compute_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'compute-0', 'lock_required')
        compute_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'compute-1', 'not_required')
        storage_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'storage-0', 'not_required')
        storage_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'storage-1', 'lock_required')
        nfvi_system_config_update_hosts.append(controller_0_resource)
        nfvi_system_config_update_hosts.append(controller_1_resource)
        nfvi_system_config_update_hosts.append(compute_0_resource)
        nfvi_system_config_update_hosts.append(compute_1_resource)
        nfvi_system_config_update_hosts.append(storage_0_resource)
        nfvi_system_config_update_hosts.append(storage_1_resource)

        strategy = self._create_system_config_update_strategy(
            update_obj,
            controller_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            nfvi_system_config_update_hosts=nfvi_system_config_update_hosts)

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(strategy.is_build_failed())
        self.assertEqual(strategy.build_phase.result_reason, "")

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {
                    'name': "system-config-update-storage-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'wait-data-sync',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-worker-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['compute-0']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['compute-0']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['compute-0']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 600},
                    ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_common.strategy._strategy.Strategy._build')
    def test_apply_system_config_update_strategy_worker_ignore(self, fake_build):

        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('compute-0')
        self.create_host('compute-1')

        update_obj = SystemConfigUpdate()
        nfvi_system_config_update_hosts = list()
        controller_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-0', 'lock_required')
        controller_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'controller-1', 'not_required')
        compute_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'compute-0', 'lock_required')
        compute_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'compute-1', 'not_required')
        storage_0_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'storage-0', 'not_required')
        storage_1_resource = nfvi.objects.v1.HostSystemConfigUpdate(
            'storage-1', 'lock_required')
        nfvi_system_config_update_hosts.append(controller_0_resource)
        nfvi_system_config_update_hosts.append(controller_1_resource)
        nfvi_system_config_update_hosts.append(compute_0_resource)
        nfvi_system_config_update_hosts.append(compute_1_resource)
        nfvi_system_config_update_hosts.append(storage_0_resource)
        nfvi_system_config_update_hosts.append(storage_1_resource)

        strategy = self._create_system_config_update_strategy(
            update_obj,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            nfvi_system_config_update_hosts=nfvi_system_config_update_hosts)

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(strategy.is_build_failed())
        self.assertEqual(strategy.build_phase.result_reason, "")

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {
                    'name': "system-config-update-controllers",
                    'total_steps': 7,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'swact-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'lock-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0']},
                        {'name': 'wait-alarms-clear',
                         'timeout': 1800},
                    ]
                },
                {
                    'name': "system-config-update-storage-hosts",
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'system-config-update-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'system-stabilize',
                         'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['storage-1']},
                        {'name': 'wait-data-sync',
                         'timeout': 1800},
                    ]
                },
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)
