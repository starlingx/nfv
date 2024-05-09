#
# Copyright (c) 2016-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from unittest import mock
import uuid

from nfv_common import strategy as common_strategy
from nfv_vim import nfvi

from nfv_vim.objects import HOST_PERSONALITY
from nfv_vim.objects import SW_UPDATE_ALARM_RESTRICTION
from nfv_vim.objects import SW_UPDATE_APPLY_TYPE
from nfv_vim.objects import SW_UPDATE_INSTANCE_ACTION
from nfv_vim.objects import SwUpgrade
from nfv_vim.strategy._strategy import SwUpgradeStrategy

from nfv_unit_tests.tests import sw_update_testcase


# utility method for the formatting of unlock-hosts stage as dict
# workers default to 5 retries with 120 second delay between attempts
# std controllers and storage have 0 retries
def _unlock_hosts_stage_as_dict(host_names, retry_count=5, retry_delay=120):
    return {
        'name': 'unlock-hosts',
        'entity_names': host_names,
        'retry_count': retry_count,
        'retry_delay': retry_delay,
        'timeout': 1800,
    }


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestSwUpgradeStrategy(sw_update_testcase.SwUpdateStrategyTestCase):

    def create_sw_deploy_strategy(self,
            controller_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            storage_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            max_parallel_worker_hosts=10,
            alarm_restrictions=SW_UPDATE_ALARM_RESTRICTION.STRICT,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            release="123.1",
            rollback=False,
            nfvi_upgrade=None,
            single_controller=False
    ):
        """
        Create a software update strategy
        """
        strategy = SwUpgradeStrategy(
            uuid=str(uuid.uuid4()),
            controller_apply_type=controller_apply_type,
            storage_apply_type=storage_apply_type,
            worker_apply_type=worker_apply_type,
            max_parallel_worker_hosts=max_parallel_worker_hosts,
            default_instance_action=default_instance_action,
            alarm_restrictions=alarm_restrictions,
            release=release,
            rollback=rollback,
            ignore_alarms=[],
            single_controller=single_controller,
        )
        strategy.nfvi_upgrade = nfvi_upgrade
        return strategy

    def _gen_aiosx_hosts_and_strategy(
            self,
            openstack=True,
            # aio-sx must be stop_start
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            instances=None,
            rollback=False,
            **kwargs,
    ):
        self.create_host('controller-0', aio=True, openstack_installed=openstack)

        controller_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                controller_hosts.append(host)

        for args in instances or []:
            self.create_instance(*args)

        strategy = self.create_sw_deploy_strategy(
            single_controller=True,
            default_instance_action=default_instance_action,
            worker_apply_type=worker_apply_type,
            rollback=rollback,
            **kwargs,
        )

        return controller_hosts, strategy

    def _gen_aiodx_hosts_and_strategy(
            self,
            openstack=True,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            instances=None,
            rollback=False,
            **kwargs,
    ):
        self.create_host('controller-0', aio=True, openstack_installed=openstack)
        self.create_host('controller-1', aio=True, openstack_installed=openstack)

        controller_hosts = []
        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                controller_hosts.append(host)

        for args in instances or []:
            self.create_instance(*args)

        strategy = self.create_sw_deploy_strategy(
            default_instance_action=default_instance_action,
            worker_apply_type=worker_apply_type,
            rollback=rollback,
            **kwargs,
        )

        return controller_hosts, strategy

    def _gen_standard_hosts_and_strategy(
            self,
            openstack=True,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            controller_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            storage_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            instances=None,
            **kwargs,
    ):
        self.create_host('controller-0', openstack_installed=openstack)
        self.create_host('controller-1', openstack_installed=openstack)
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('compute-2')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('storage-2')

        controller_hosts = []
        storage_hosts = []
        worker_hosts = []

        for host in list(self._host_table.values()):
            if HOST_PERSONALITY.CONTROLLER in host.personality:
                controller_hosts.append(host)

            elif HOST_PERSONALITY.STORAGE in host.personality:
                storage_hosts.append(host)

            elif HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)

        for args in instances or []:
            self.create_instance(*args)

        strategy = self.create_sw_deploy_strategy(
            default_instance_action=default_instance_action,
            controller_apply_type=controller_apply_type,
            worker_apply_type=worker_apply_type,
            storage_apply_type=storage_apply_type,
            **kwargs,
        )

        return controller_hosts, storage_hosts, worker_hosts, strategy

    @mock.patch('nfv_common.strategy._strategy.Strategy._build')
    def test_sw_deploy_strategy_build_steps(self, fake_build):
        """
        Verify build phase steps and stages for sw deploy strategy creation.
        """
        # setup a minimal host environment
        self.create_host('controller-0', aio=True)

        update_obj = SwUpgrade()
        strategy = self.create_sw_deploy_strategy(
            single_controller=True)
        update_obj = SwUpgrade()
        strategy.sw_update_obj = update_obj

        strategy.build()

        # verify the build phase and steps
        build_phase = strategy.build_phase.as_dict()
        query_steps = [
            {'name': 'query-alarms'},
            {'name': 'sw-deploy-precheck'},
            {'name': 'query-upgrade'},
        ]
        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-upgrade-query',
                 'total_steps': len(query_steps),
                 'steps': query_steps,
                },
            ],
        }
        sw_update_testcase.validate_phase(build_phase, expected_results)

    #  ~~~ SW-DEPLOY Start ~~~

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_0)
    def test_sw_deploy_strategy_start_on_controller_0_aiosx(self):
        """
        Test the sw_upgrade strategy start stage controller-0
        - sx
        Verify:
        - pass
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'N',
                },
                None,
            )
        )

        strategy._add_upgrade_start_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-upgrade-start',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'start-upgrade',
                      'release': release},
                     {'name': 'system-stabilize',
                      'timeout': 60},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_0)
    def test_sw_deploy_strategy_start_on_controller_0__aiodx(self):
        """
        Test the sw_upgrade strategy start stages on controller-0:
        - dx
        Verify:
        - pass
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'N',
                },
                None,
            )
        )

        strategy._add_upgrade_start_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-upgrade-start',
                 'total_steps': 3,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'start-upgrade',
                      'release': release},
                     {'name': 'system-stabilize',
                      'timeout': 60},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # pylint: disable=no-member
    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_flipper('controller-1', 'controller-0', n=2))
    def test_sw_deploy_strategy_start_on_controller_1_aiodx(self):
        """
        Test the sw_upgrade strategy start stages on controller-1:
        - dx
        Verify:
        - pass
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'N',
                },
                None,
            )
        )

        strategy._add_upgrade_start_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-upgrade-start',
                 'total_steps': 5,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'start-upgrade',
                      'release': release},
                     {'name': 'system-stabilize',
                      'timeout': 60},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-0']},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    #  ~~~ SW-DEPLOY Complete ~~~

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_0)
    def test_sw_deploy_strategy_complete_on_controller_0_aiosx(self):
        """
        Test the sw_upgrade strategy complete stage controller-0
        - sx
        Verify:
        - pass
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'N',
                },
                None,
            )
        )

        strategy._add_upgrade_complete_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-upgrade-complete',
                 'total_steps': 4,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'activate-upgrade',
                      'release': release},
                     {'name': 'complete-upgrade',
                      'release': release},
                     {'name': 'system-stabilize',
                      'timeout': 60},
                  ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_controller_0)
    def test_sw_deploy_strategy_complete_on_controller_0__aiodx(self):
        """
        Test the sw_upgrade strategy complete stages on controller-0:
        - dx
        Verify:
        - pass
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'N',
                },
                None,
            )
        )

        strategy._add_upgrade_complete_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-upgrade-complete',
                 'total_steps': 4,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'activate-upgrade',
                      'release': release},
                     {'name': 'complete-upgrade',
                      'release': release},
                     {'name': 'system-stabilize',
                      'timeout': 60},
                  ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # pylint: disable=no-member
    @mock.patch('nfv_vim.strategy._strategy.get_local_host_name',
                sw_update_testcase.fake_host_name_flipper('controller-1', 'controller-0', n=2))
    def test_sw_deploy_strategy_complete_on_controller_1_aiodx(self):
        """
        Test the sw_upgrade strategy complete stages on controller-1:
        - dx
        Verify:
        - pass
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'N',
                },
                None,
            )
        )

        strategy._add_upgrade_complete_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-upgrade-complete',
                 'total_steps': 5,
                 'steps': [
                     {'name': 'query-alarms'},
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'activate-upgrade',
                      'release': release},
                     {'name': 'complete-upgrade',
                      'release': release},
                     {'name': 'system-stabilize',
                      'timeout': 60},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # ~~~ AIO-SX NRR ~~~

    def test_sw_deploy_strategy_aiosx_controllers_serial_nrr(self):
        """
        Test the sw_deploy strategy add controller strategy stages:
        - aio-sx host
        - serial apply
        - no reboot required
        - stop_start instances
        - no instances
        Verify:
        - Pass
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy()

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts,
            reboot=False)

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            'total_stages': 1,
            'stages': [
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 30},
                    ]
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_nrr(self):
        """
        Test the sw_deploy strategy add controller strategy stages:
        - aio-sx host
        - parallel apply
        - no reboot required
        - stop_start instances
        - no instances
        Verify:
        - Pass
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts,
            reboot=False)

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            'total_stages': 1,
            'stages': [
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 30},
                    ]
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_nrr_no_openstack(self):
        """
        Test the sw_deploy strategy add controller strategy stages:
        - aio-sx host
        - parallel apply
        - no reboot required
        - stop_start instances
        - no instances
        - no openstack
        Verify:
        - Pass
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            openstack=False,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts,
            reboot=False)

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            'total_stages': 1,
            'stages': [
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 30},
                    ]
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_nrr_instances_migrate(self):
        """
        Test the sw_deploy strategy add controller strategy stages:
        - aio-sx host
        - parallel apply
        - no reboot required
        - migrate instances
        - instances
        Verify:
        - Fail
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            instances=[('small', 'test_instance_0', 'controller-0')],
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts,
            reboot=False)

        assert success is False
        assert reason == 'cannot migrate instances in a single controller configuration'

        sw_update_testcase.validate_strategy_persists(strategy)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_nrr_instances_stop_start(self):
        """
        Test the sw_deploy strategy add controller strategy stages:
        - aio-sx host
        - parallel apply
        - no reboot required
        - stop_start instances
        - instances
        Verify:
        - Pass
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            instances=[('small', 'test_instance_0', 'controller-0')],
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts,
            reboot=False)

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            'total_stages': 1,
            'stages': [
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 30},
                    ]
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # ~~~ AIO-SX RR ~~~

    def test_sw_deploy_strategy_aiosx_controllers_serial_rr(self):
        """
        Test the sw_deploy strategy add controller strategy stages:
        - aio-sx host
        - serial apply
        - reboot required
        - stop_start instances
        - no instances
        Verify:
        - Pass
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy()

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts,
            reboot=True)

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            'total_stages': 1,
            'stages': [
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts', 'entity_names': ['controller-0']},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0'], 'retry_count': 0, 'retry_delay': 120},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_rr(self):
        """
        Test the sw_deploy strategy add controller strategy stages:
        - aio-sx host
        - parallel apply
        - reboot required
        - stop_start instances
        - no instances
        Verify:
        - Pass
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts,
            reboot=True)

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            'total_stages': 1,
            'stages': [
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts', 'entity_names': ['controller-0']},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0'], 'retry_count': 0, 'retry_delay': 120},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_rr_no_openstack(self):
        """
        Test the sw_deploy strategy add controller strategy stages:
        - aio-sx host
        - parallel apply
        - reboot required
        - stop_start instances
        - no instances
        - no openstack
        Verify:
        - Pass
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            openstack=False,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts,
            reboot=True)

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            'total_stages': 1,
            'stages': [
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts', 'entity_names': ['controller-0']},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0'], 'retry_count': 0, 'retry_delay': 120},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_rr_instances_migrate(self):
        """
        Test the sw_deploy strategy add controller strategy stages:
        - aio-sx host
        - parallel apply
        - reboot required
        - migrate instances
        - instances
        Verify:
        - Pass
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            instances=[('small', 'test_instance_0', 'controller-0')],
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts,
            reboot=True)

        assert success is False
        assert reason == 'cannot migrate instances in a single controller configuration'

        sw_update_testcase.validate_strategy_persists(strategy)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_rr_instances_stop_start(self):
        """
        Test the sw_deploy strategy add controller strategy stages:
        - aio-sx host
        - parallel apply
        - reboot required
        - stop_start instances
        - instances
        Verify:
        - Pass
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            instances=[('small', 'test_instance_0', 'controller-0')],
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts,
            reboot=True)

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            'total_stages': 1,
            'stages': [
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 8,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'stop-instances', 'entity_names': ['test_instance_0']},
                        {'name': 'lock-hosts', 'entity_names': ['controller-0']},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0'], 'retry_count': 0, 'retry_delay': 120},
                        {'name': 'start-instances', 'entity_names': ['test_instance_0']},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_already_deployed(self):
        """
        Test the sw_deploy strategy when patch already deployed:
        - patch already committed
        Verify:
        - Fail
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                '13.01',
                {'state': 'deployed'},
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        expected_reason = "Software release is already deployed or committed."
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.FAILED
        assert bpr.result_reason == expected_reason, strategy.build_phase.result_reason

    def test_sw_deploy_strategy_aiosx_already_committed(self):
        """
        Test the sw_deploy strategy when patch already committed:
        - patch already committed
        Verify:
        - Fail
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                '13.01',
                {'state': 'committed'},
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        expected_reason = "Software release is already deployed or committed."
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.FAILED
        assert bpr.result_reason == expected_reason, strategy.build_phase.result_reason

    def test_sw_deploy_strategy_aiosx_release_does_not_exist(self):
        """
        Test the sw_deploy strategy when patch does not exist:
        - patch does not exist
        Verify:
        - Fail
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                '13.01',
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        expected_reason = "Software release does not exist."
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.FAILED
        assert bpr.result_reason == expected_reason, strategy.build_phase.result_reason

# ~~~~~~ Full Apply Phase ~~~~~~~

    def test_sw_deploy_strategy_aiosx_apply_phase_nrr(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - nrr
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'N',
                },
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {
                    'name': 'sw-upgrade-start',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ],
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 30},
                    ]
                },
                {
                    'name': 'sw-upgrade-complete',
                    'total_steps': 4,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'activate-upgrade', 'release': release},
                        {'name': 'complete-upgrade', 'release': release},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_apply_phase_rr(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - rr
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'Y',
                },
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {
                    'name': 'sw-upgrade-start',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ],
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts', 'entity_names': ['controller-0']},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0'], 'retry_count': 0, 'retry_delay': 120},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
                {
                    'name': 'sw-upgrade-complete',
                    'total_steps': 4,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'activate-upgrade', 'release': release},
                        {'name': 'complete-upgrade', 'release': release},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiodx_apply_phase_nrr(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-dx
        - nrr
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'N',
                },
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {
                    'name': 'sw-upgrade-start',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ],
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-1']},
                        {'name': 'system-stabilize', 'timeout': 30},
                    ]
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 30},
                    ]
                },
                {
                    'name': 'sw-upgrade-complete',
                    'total_steps': 4,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'activate-upgrade', 'release': release},
                        {'name': 'complete-upgrade', 'release': release},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiodx_apply_phase_rr(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-dx
        - rr
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'Y',
                },
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 4,
            'stages': [
                {
                    'name': 'sw-upgrade-start',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ],
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 7,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'swact-hosts', 'entity_names': ['controller-1']},
                        {'name': 'lock-hosts', 'entity_names': ['controller-1']},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-1']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-1'], 'retry_count': 0, 'retry_delay': 120},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 7,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'swact-hosts', 'entity_names': ['controller-0']},
                        {'name': 'lock-hosts', 'entity_names': ['controller-0']},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0'], 'retry_count': 0, 'retry_delay': 120},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
                {
                    'name': 'sw-upgrade-complete',
                    'total_steps': 4,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'activate-upgrade', 'release': release},
                        {'name': 'complete-upgrade', 'release': release},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_standard_apply_phase_nrr(self):
        """
        Test the sw_deploy strategy apply phase:
        - standard
        - nrr
        - parallel storage
        - parallel workers
        Verify:
        - Pass
        """

        release = '888.8'
        _, _, _, strategy = self._gen_standard_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'N',
                },
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 6,
            'stages': [
                {
                    'name': 'sw-upgrade-start',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ],
                },
                {
                    'name': 'sw-upgrade-controllers',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-1']},
                        {'name': 'system-stabilize', 'timeout': 30},
                    ]
                },
                {
                    'name': 'sw-upgrade-controllers',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 30},
                    ]
                },
                {
                    'name': 'sw-upgrade-storage-hosts',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts',
                         'entity_names': ['storage-0', 'storage-1', 'storage-2']},
                        {'name': 'system-stabilize', 'timeout': 30},
                    ]
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts',
                         'entity_names': ['compute-0', 'compute-1', 'compute-2']},
                        {'name': 'system-stabilize', 'timeout': 30},
                    ]
                },
                {
                    'name': 'sw-upgrade-complete',
                    'total_steps': 4,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'activate-upgrade', 'release': release},
                        {'name': 'complete-upgrade', 'release': release},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_standard_apply_phase_rr(self):
        """
        Test the sw_deploy strategy apply phase:
        - standard
        - rr
        - parallel storage
        - parallel workers
        Verify:
        - Pass
        """

        release = '888.8'
        _, _, _, strategy = self._gen_standard_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': 'Y',
                },
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 6,
            'stages': [
                {
                    'name': 'sw-upgrade-start',
                    'total_steps': 3,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ],
                },
                {
                    'name': 'sw-upgrade-controllers',
                    'total_steps': 7,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'swact-hosts', 'entity_names': ['controller-1']},
                        {'name': 'lock-hosts', 'entity_names': ['controller-1']},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-1']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-1'], 'retry_count': 0, 'retry_delay': 120},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
                {
                    'name': 'sw-upgrade-controllers',
                    'total_steps': 7,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'swact-hosts', 'entity_names': ['controller-0']},
                        {'name': 'lock-hosts', 'entity_names': ['controller-0']},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['controller-0'], 'retry_count': 0, 'retry_delay': 120},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
                {
                    'name': 'sw-upgrade-storage-hosts',
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['storage-0', 'storage-1', 'storage-2']},
                        {'name': 'upgrade-hosts',
                         'entity_names': ['storage-0', 'storage-1', 'storage-2']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['storage-0', 'storage-1', 'storage-2']},
                        {'name': 'wait-data-sync', 'timeout': 1800},
                    ]
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts',
                         'entity_names': ['compute-0', 'compute-1', 'compute-2']},
                        {'name': 'upgrade-hosts',
                         'entity_names': ['compute-0', 'compute-1', 'compute-2']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts',
                         'entity_names': ['compute-0', 'compute-1', 'compute-2']},
                        {'name': 'wait-alarms-clear', 'timeout': 600},
                    ]
                },
                {
                    'name': 'sw-upgrade-complete',
                    'total_steps': 4,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'activate-upgrade', 'release': release},
                        {'name': 'complete-upgrade', 'release': release},
                        {'name': 'system-stabilize', 'timeout': 60},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)
