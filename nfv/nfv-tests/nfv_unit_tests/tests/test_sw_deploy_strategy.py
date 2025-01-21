#
# Copyright (c) 2016-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from unittest import mock
import uuid

from nfv_common import strategy as common_strategy
from nfv_plugins.nfvi_plugins.openstack.usm import is_target_release_downgrade
from nfv_vim import nfvi
from nfv_vim.objects import HOST_PERSONALITY
from nfv_vim.objects import SW_UPDATE_ALARM_RESTRICTION
from nfv_vim.objects import SW_UPDATE_APPLY_TYPE
from nfv_vim.objects import SW_UPDATE_INSTANCE_ACTION
from nfv_vim.objects import SwUpgrade
from nfv_vim.strategy._strategy import SwUpgradeStrategy

from nfv_unit_tests.tests import sw_update_testcase


INITIAL_RELEASE = "3.2.1"
PATCH_RELEASE_UPGRADE = "3.2.2"
# Minor and Major are both major release upgrades
MINOR_RELEASE_UPGRADE = "4.0.1"
MAJOR_RELEASE_UPGRADE = "4.0.1"


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
@mock.patch.object(nfvi.objects.v1.upgrade, 'SW_VERSION', INITIAL_RELEASE)
class TestSwUpgradeStrategy(sw_update_testcase.SwUpdateStrategyTestCase):

    def create_sw_deploy_strategy(self,
            controller_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            storage_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            max_parallel_worker_hosts=10,
            alarm_restrictions=SW_UPDATE_ALARM_RESTRICTION.STRICT,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            release=MAJOR_RELEASE_UPGRADE,
            rollback=False,
            delete=False,
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
            delete=delete,
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
            delete=False,
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
            delete=delete,
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
            delete=False,
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
            delete=delete,
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

    def test_is_major_release(self):
        is_major_release = nfvi.objects.v1.is_major_release
        assert is_major_release(INITIAL_RELEASE, MAJOR_RELEASE_UPGRADE)
        assert is_major_release(INITIAL_RELEASE, MINOR_RELEASE_UPGRADE)
        assert not is_major_release(INITIAL_RELEASE, PATCH_RELEASE_UPGRADE)
        assert is_major_release("22.12", "24.09.1")
        assert is_major_release("22.12", "24.09.1")
        assert is_major_release("22.12", "24.09.1")
        assert is_major_release("22.12", "24.09")
        assert is_major_release("22.12.1", "24.09")
        assert is_major_release("24.03", "24.09.1")
        assert is_major_release("24.03", "24.09.1")
        assert not is_major_release("22.12", "22.12")
        assert not is_major_release("22.12", "22.12.1")
        assert not is_major_release("22.12.2", "22.12.1")

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
            {'name': 'query-upgrade'},
            {'name': 'sw-deploy-precheck'},
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
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        strategy._add_upgrade_start_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-upgrade-start',
                 'total_steps': 2,
                 'steps': [
                     {'name': 'start-upgrade',
                      'release': release},
                     {'name': 'query-alarms'},
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
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        strategy._add_upgrade_start_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-upgrade-start',
                 'total_steps': 2,
                 'steps': [
                     {'name': 'start-upgrade',
                      'release': release},
                     {'name': 'query-alarms'},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # pylint: disable=no-member
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
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        strategy._add_upgrade_start_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'sw-upgrade-start',
                 'total_steps': 2,
                 'steps': [
                     {'name': 'start-upgrade',
                      'release': release},
                     {'name': 'query-alarms'},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # pylint: disable=no-member
    def test_sw_deploy_strategy_start_on_controller_1_aiodx_major(self):
        """
        Test the sw_upgrade strategy start stages on controller-1:
        - dx
        - major release
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
                    'reboot_required': True,
                    'sw_version': MAJOR_RELEASE_UPGRADE,
                },
                None,
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
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'start-upgrade',
                      'release': release},
                     {'name': 'query-alarms'},
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
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
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
                     {'name': 'query-alarms'},
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
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
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
                     {'name': 'query-alarms'},
                  ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # pylint: disable=no-member
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
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
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
                     {'name': 'query-alarms'},
                 ]
                }
            ]
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # pylint: disable=no-member
    def test_sw_deploy_strategy_complete_on_controller_1_aiodx_major(self):
        """
        Test the sw_upgrade strategy complete stages on controller-1:
        - dx
        - major releasee
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
                    'reboot_required': True,
                    'sw_version': MAJOR_RELEASE_UPGRADE,
                },
                None,
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
                     {'name': 'swact-hosts',
                      'entity_names': ['controller-1']},
                     {'name': 'query-alarms'},
                     {'name': 'activate-upgrade',
                      'release': release},
                     {'name': 'complete-upgrade',
                      'release': release},
                     {'name': 'query-alarms'},
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
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
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
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
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
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
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
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
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

    def test_sw_deploy_strategy_aiosx_already_deploying(self):
        """
        Test the sw_deploy strategy when patch already deploying:
        - patch already deploying
        Verify:
        - Success
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                '13.01',
                {
                    'state': 'deploying',
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.INITIAL, strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.INITIAL, bpr.result

    def test_sw_deploy_strategy_aiosx_already_removing(self):
        """
        Test the sw_deploy strategy when patch already removing:
        - patch already removing
        Verify:
        - Success
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                '13.01',
                {
                    'state': 'removing',
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.INITIAL, strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.INITIAL, bpr.result

    def test_sw_deploy_strategy_aiosx_already_deploy_completed(self):
        """
        Test the sw_deploy strategy when patch already deploy completed:
        - patch deploy completed
        Verify:
        - Fail
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                '13.01',
                {'state': 'deploying'},
                {'state': 'completed'},
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        expected_reason = "Software deployment is already complete, pending delete"
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED, strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.FAILED, bpr.result
        assert bpr.result_reason == expected_reason, bpr.result_reason

    def test_sw_deploy_strategy_aiosx_already_deployed(self):
        """
        Test the sw_deploy strategy when patch already deploy completed:
        - patch deployed
        Verify:
        - Fail
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                '13.01',
                {'state': 'deployed'},
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        expected_reason = "no sw-deployments patches need to be applied"
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED, strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.FAILED, bpr.result
        assert bpr.result_reason == expected_reason, bpr.result_reason

    def test_sw_deploy_strategy_aiosx_already_deployed_downgrade_create(self):
        """
        Test the sw_deploy strategy when patch already deploy completed:
        - patch deployed
        Verify:
        - Fail
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                '13.01',
                {
                    'state': 'deployed',
                    'downgrade': True,
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.INITIAL, strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.INITIAL, bpr.result

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
                {
                    'state': 'commited',
                    'downgrade': True,
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.INITIAL, strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.INITIAL, bpr.result

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
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        expected_reason = "Software release does not exist or is unavailable"
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.FAILED
        assert bpr.result_reason == expected_reason, strategy.build_phase.result_reason

    def test_sw_deploy_strategy_aiosx_release_is_unavailable(self):
        """
        Test the sw_deploy strategy when patch is unavailable:
        - patch does not exist
        Verify:
        - Fail
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                '13.01',
                {'state': 'unavailable'},
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        expected_reason = "Software release does not exist or is unavailable"
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
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
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
                    'total_steps': 2,
                    'steps': [
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'query-alarms'},
                    ],
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                    ]
                },
                {
                    'name': 'sw-upgrade-complete',
                    'total_steps': 5,
                    'steps': [
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'query-alarms'},
                        {'name': 'activate-upgrade', 'release': release},
                        {'name': 'complete-upgrade', 'release': release},
                        {'name': 'query-alarms'},
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
                    'reboot_required': True,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
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
                    'total_steps': 2,
                    'steps': [
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'query-alarms'},
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
                        {'name': 'query-alarms'},
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
            delete=True,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 5,
            'stages': [
                {
                    'name': 'sw-upgrade-start',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'query-alarms'},
                    ],
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                    ]
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-1']},
                    ]
                },
                {
                    'name': 'sw-upgrade-complete',
                    'total_steps': 5,
                    'steps': [
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'query-alarms'},
                        {'name': 'activate-upgrade', 'release': release},
                        {'name': 'complete-upgrade', 'release': release},
                        {'name': 'query-alarms'},
                    ]
                },
                {
                    'name': 'sw-deploy-delete',
                    'total_steps': 1,
                    'steps': [
                        {'name': 'deploy-delete', 'release': release},
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
            delete=True,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'state': 'available',
                    'reboot_required': True,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 5,
            'stages': [
                {
                    'name': 'sw-upgrade-start',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'query-alarms'},
                    ],
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
                    'name': 'sw-upgrade-complete',
                    'total_steps': 4,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'activate-upgrade', 'release': release},
                        {'name': 'complete-upgrade', 'release': release},
                        {'name': 'query-alarms'},
                    ]
                },
                {
                    'name': 'sw-deploy-delete',
                    'total_steps': 1,
                    'steps': [
                        {'name': 'deploy-delete', 'release': release},
                    ]
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
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
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
                    'total_steps': 2,
                    'steps': [
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'query-alarms'},
                    ],
                },
                {
                    'name': 'sw-upgrade-controllers',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                    ]
                },
                {
                    'name': 'sw-upgrade-controllers',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-1']},
                    ]
                },
                {
                    'name': 'sw-upgrade-storage-hosts',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts',
                         'entity_names': ['storage-0', 'storage-1', 'storage-2']},
                    ]
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts',
                         'entity_names': ['compute-0', 'compute-1', 'compute-2']},
                    ]
                },
                {
                    'name': 'sw-upgrade-complete',
                    'total_steps': 5,
                    'steps': [
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'query-alarms'},
                        {'name': 'activate-upgrade', 'release': release},
                        {'name': 'complete-upgrade', 'release': release},
                        {'name': 'query-alarms'},
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
                    'reboot_required': True,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
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
                    'total_steps': 2,
                    'steps': [
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'query-alarms'},
                    ],
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
                        {'name': 'query-alarms'},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_standard_apply_phase_rr_major(self):
        """
        Test the sw_deploy strategy apply phase:
        - standard
        - rr
        - parallel storage
        - parallel workers
        - major release
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
                    'reboot_required': True,
                    'sw_version': MAJOR_RELEASE_UPGRADE,

                },
                None,
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
                        {'name': 'swact-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'query-alarms'},
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
                    'total_steps': 5,
                    'steps': [
                        {'name': 'swact-hosts',
                         'entity_names': ['controller-1']},
                        {'name': 'query-alarms'},
                        {'name': 'activate-upgrade', 'release': release},
                        {'name': 'complete-upgrade', 'release': release},
                        {'name': 'query-alarms'},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_complete(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - major
        - complete
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'release_id': MAJOR_RELEASE_UPGRADE,
                    'state': 'deploying',
                    'sw_version': MAJOR_RELEASE_UPGRADE,
                },
                {
                    'state': 'completed',
                    'reboot_required': True,
                    'from_release': INITIAL_RELEASE,
                    'to_release': MAJOR_RELEASE_UPGRADE,
                },
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        expected_reason = "Software rollback cannot be initiated by VIM after activation"
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED, strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.FAILED, bpr.result
        assert bpr.result_reason == expected_reason, bpr.result_reason

    def test_sw_deploy_strategy_aiosx_rollback_from_active_done(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - major
        - activate-deon
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'release_id': MAJOR_RELEASE_UPGRADE,
                    'state': 'deploying',
                    'sw_version': MAJOR_RELEASE_UPGRADE,
                },
                {
                    'state': 'activate-done',
                    'reboot_required': True,
                    'from_release': INITIAL_RELEASE,
                    'to_release': MAJOR_RELEASE_UPGRADE,
                },
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        expected_reason = "Software rollback cannot be initiated by VIM after activation"
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED, strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.FAILED, bpr.result
        assert bpr.result_reason == expected_reason, bpr.result_reason

    def test_sw_deploy_strategy_aiosx_rollback_from_activate_failed(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - major
        - activate-failed
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'release_id': MAJOR_RELEASE_UPGRADE,
                    'state': 'deploying',
                    'sw_version': MAJOR_RELEASE_UPGRADE,
                },
                {
                    'state': 'activate-failed',
                    'reboot_required': True,
                    'from_release': INITIAL_RELEASE,
                    'to_release': MAJOR_RELEASE_UPGRADE,
                },
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        expected_reason = "Software rollback cannot be initiated by VIM after activation"
        bpr = strategy.build_phase

        assert strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED, strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.FAILED, bpr.result
        assert bpr.result_reason == expected_reason, bpr.result_reason

    def test_sw_deploy_strategy_aiosx_rollback_from_start_done(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - major
        - start-done
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'release_id': MAJOR_RELEASE_UPGRADE,
                    'state': 'deploying',
                    'sw_version': MAJOR_RELEASE_UPGRADE,
                },
                {
                    'state': 'start-done',
                    'reboot_required': True,
                    'from_release': INITIAL_RELEASE,
                    'to_release': MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        'hostname': 'controller-0',
                        'host_state': 'pending',
                    },
                ],
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {
                    'name': 'sw-upgrade-rollback-start',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'sw-deploy-abort'},
                    ],
                },
                {
                    'name': 'sw-upgrade-rollback-complete',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'deploy-delete'},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_start_done_locked(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - major
        - start-done
        - c0 locked
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'release_id': MAJOR_RELEASE_UPGRADE,
                    'state': 'deploying',
                    'sw_version': MAJOR_RELEASE_UPGRADE,
                },
                {
                    'state': 'start-done',
                    'reboot_required': True,
                    'from_release': INITIAL_RELEASE,
                    'to_release': MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        'hostname': 'controller-0',
                        'host_state': 'pending',
                    },
                ],
            )
        )

        # Replace controller-0 with locked one
        self.create_host(
            'controller-0',
            aio=True,
            openstack_installed=False,
            admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED,
            oper_state=nfvi.objects.v1.HOST_OPER_STATE.DISABLED,
            avail_status=nfvi.objects.v1.HOST_AVAIL_STATUS.ONLINE)

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {
                    'name': 'sw-upgrade-rollback-start',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'sw-deploy-abort'},
                    ],
                },
                {
                    'name': 'sw-upgrade-rollback-complete',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'deploy-delete'},
                    ],
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 6,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'lock-hosts', 'entity_names': ['controller-0']},
                        {'name': 'sw-deploy-do-nothing', 'entity_names': ['controller-0']},
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'unlock-hosts'},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_host_rollback_deployed_unlocked(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - major
        - host-rollback-done
        - c0 unloacked
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'release_id': MAJOR_RELEASE_UPGRADE,
                    'state': 'deploying',
                    'sw_version': MAJOR_RELEASE_UPGRADE,
                },
                {
                    'state': 'host-rollback-done',
                    'reboot_required': True,
                    'from_release': INITIAL_RELEASE,
                    'to_release': MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        'hostname': 'controller-0',
                        'host_state': 'rollback-deployed',
                    },
                ],
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 2,
            'stages': [
                {
                    'name': 'sw-upgrade-rollback-start',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'sw-deploy-abort'},
                    ],
                },
                {
                    'name': 'sw-upgrade-rollback-complete',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'deploy-delete'},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_host_rollback_deployed_locked(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - major
        - host-rollback-done
        - c0 loacked
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'release_id': MAJOR_RELEASE_UPGRADE,
                    'state': 'deploying',
                    'sw_version': MAJOR_RELEASE_UPGRADE,
                },
                {
                    'state': 'host-rollback-done',
                    'reboot_required': True,
                    'from_release': INITIAL_RELEASE,
                    'to_release': MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        'hostname': 'controller-0',
                        'host_state': 'rollback-deployed',
                    },
                ],
            )
        )

        # Replace controller-0 with locked one
        self.create_host(
            'controller-0',
            aio=True,
            openstack_installed=False,
            admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED,
            oper_state=nfvi.objects.v1.HOST_OPER_STATE.DISABLED,
            avail_status=nfvi.objects.v1.HOST_AVAIL_STATUS.ONLINE)

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            'total_stages': 3,
            'stages': [
                {
                    'name': 'sw-upgrade-rollback-start',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'sw-deploy-abort'},
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
                        {'name': 'unlock-hosts'},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
                {
                    'name': 'sw-upgrade-rollback-complete',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'deploy-delete'},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_host_done(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - major
        - host-done
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'release_id': MAJOR_RELEASE_UPGRADE,
                    'state': 'deploying',
                    'sw_version': MAJOR_RELEASE_UPGRADE,
                },
                {
                    'state': 'host-done',
                    'reboot_required': True,
                    'from_release': INITIAL_RELEASE,
                    'to_release': MAJOR_RELEASE_UPGRADE,
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
                    'name': 'sw-upgrade-rollback-start',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'sw-deploy-abort'},
                        # {'name': 'sw-deploy-activate-rollback'},
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
                        {'name': 'unlock-hosts'},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
                {
                    'name': 'sw-upgrade-rollback-complete',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'deploy-delete'},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_host_failed(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - major
        - host-failed
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'release_id': MAJOR_RELEASE_UPGRADE,
                    'state': 'deploying',
                    'sw_version': MAJOR_RELEASE_UPGRADE,
                },
                {
                    'state': 'host-failed',
                    'reboot_required': True,
                    'from_release': INITIAL_RELEASE,
                    'to_release': MAJOR_RELEASE_UPGRADE,
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
                    'name': 'sw-upgrade-rollback-start',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'sw-deploy-abort'},
                        # {'name': 'sw-deploy-activate-rollback'},
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
                        {'name': 'unlock-hosts'},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
                {
                    'name': 'sw-upgrade-rollback-complete',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'deploy-delete'},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_host(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - major
        - host
        Verify:
        - Pass
        """

        release = '888.8'
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                {
                    'release_id': MAJOR_RELEASE_UPGRADE,
                    'state': 'deploying',
                    'sw_version': MAJOR_RELEASE_UPGRADE,
                },
                {
                    'state': 'host',
                    'reboot_required': True,
                    'from_release': INITIAL_RELEASE,
                    'to_release': MAJOR_RELEASE_UPGRADE,
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
                    'name': 'sw-upgrade-rollback-start',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'sw-deploy-abort'},
                        # {'name': 'sw-deploy-activate-rollback'},
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
                        {'name': 'unlock-hosts'},
                        {'name': 'wait-alarms-clear', 'timeout': 2400},
                    ]
                },
                {
                    'name': 'sw-upgrade-rollback-complete',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'deploy-delete'},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_downgrade(self):
        """
        Test the sw_deploy strategy apply phase:
        - aio-sx
        - major
        - host
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
                    'reboot_required': False,
                    'sw_version': PATCH_RELEASE_UPGRADE,
                },
                None,
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
                    'total_steps': 2,
                    'steps': [
                        {'name': 'start-upgrade', 'release': release},
                        {'name': 'query-alarms'},
                    ],
                },
                {
                    'name': 'sw-upgrade-worker-hosts',
                    'total_steps': 2,
                    'steps': [
                        {'name': 'query-alarms'},
                        {'name': 'upgrade-hosts', 'entity_names': ['controller-0']},
                    ]
                },
                {
                    'name': 'sw-upgrade-complete',
                    'total_steps': 5,
                    'steps': [
                        {'name': 'system-stabilize', 'timeout': 15},
                        {'name': 'query-alarms'},
                        {'name': 'activate-upgrade', 'release': release},
                        {'name': 'complete-upgrade', 'release': release},
                        {'name': 'query-alarms'},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_is_upgrade(self):
        """
        Test the sw_deploy strategy upgrade logic:
        - We should be able to upgrade to a deployed release
        Verify:
        - Pass
        """

        index = 1
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "available",  # Target
                "reboot_required": False,
            },
            {
                "state": "available",
                "reboot_required": False,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert upgrade
        assert not downgrade
        assert not vim_rr

    def test_sw_deploy_strategy_aiosx_is_upgrade_rr(self):
        """
        Test the sw_deploy strategy upgrade logic:
        - We should be able to upgrade to a deployed release
        - RR
        Verify:
        - Pass
        """

        index = 1
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "available",  # Target
                "reboot_required": True,
            },
            {
                "state": "available",
                "reboot_required": False,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert upgrade
        assert not downgrade
        assert vim_rr

    def test_sw_deploy_strategy_aiosx_is_upgrade_multiple(self):
        """
        Test the sw_deploy strategy upgrade logic:
        - We should be able to upgrade to a deployed release
        - Upgrade multiple releases at once
        Verify:
        - Pass
        """

        index = 2
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "available",
                "reboot_required": False,
            },
            {
                "state": "available",  # Target
                "reboot_required": False,
            },
            {
                "state": "available",
                "reboot_required": True,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert upgrade
        assert not downgrade
        assert not vim_rr

    def test_sw_deploy_strategy_aiosx_is_upgrade_multiple_rr_first(self):
        """
        Test the sw_deploy strategy upgrade logic:
        - We should be able to upgrade to a deployed release
        - Upgrade multiple releases at once
        - RR on the oldest release
        Verify:
        - Pass
        """

        index = 2
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "available",
                "reboot_required": True,
            },
            {
                "state": "available",  # Target
                "reboot_required": False,
            },
            {
                "state": "available",
                "reboot_required": True,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert upgrade
        assert not downgrade
        assert vim_rr

    def test_sw_deploy_strategy_aiosx_is_upgrade_multiple_rr_second(self):
        """
        Test the sw_deploy strategy upgrade logic:
        - We should be able to upgrade to a deployed release
        - Upgrade multiple releases at once
        - RR on the most recent release
        Verify:
        - Pass
        """

        index = 2
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "available",
                "reboot_required": False,
            },
            {
                "state": "available",  # Target
                "reboot_required": True,
            },
            {
                "state": "available",
                "reboot_required": True,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert upgrade
        assert not downgrade
        assert vim_rr

    def test_sw_deploy_strategy_aiosx_is_upgrade_deploying_complex(self):
        """
        Test the sw_deploy strategy upgrade logic:
        - We should be able to upgrade to a deployed release
        - Upgrade multiple releases at once
        - RR on the most recent release
        Verify:
        - Pass
        """

        index = 4
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "deployed",
                "reboot_required": False,
            },
            {
                "state": "deployed",
                "reboot_required": True,
            },
            {
                "state": "deploying",
                "reboot_required": False,
            },
            {
                "state": "deploying",  # Target
                "reboot_required": False,
            },
            {
                "state": "available",
                "reboot_required": True,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert upgrade
        assert not downgrade
        assert not vim_rr

    def test_sw_deploy_strategy_aiosx_is_upgrade_not_required(self):
        """
        Test the sw_deploy strategy upgrade logic:
        - Nothing to upgrade
        Verify:
        - Pass
        """

        index = 1
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "deployed",  # Target
            },
            {
                "state": "available",
                "reboot_required": False,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert not upgrade
        assert downgrade
        assert not vim_rr

    def test_sw_deploy_strategy_aiosx_is_upgrade_reenter(self):
        """
        Test the sw_deploy strategy upgrade logic:
        - Nothing to upgrade
        Verify:
        - Pass
        """

        index = 1
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "deploying",  # Target
                "reboot_required": False,
            },
            {
                "state": "available",
                "reboot_required": False,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert upgrade
        assert not downgrade
        assert not vim_rr

    def test_sw_deploy_strategy_aiosx_is_downgrade(self):
        """
        Test the sw_deploy strategy downgrade logic:
        - We should be able to downgrade to a deployed release
        Verify:
        - Pass
        """

        index = 1
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "deployed",  # Target
            },
            {
                "state": "deployed",
                "reboot_required": False,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert not upgrade
        assert downgrade
        assert not vim_rr

    def test_sw_deploy_strategy_aiosx_is_downgrade_rr(self):
        """
        Test the sw_deploy strategy downgrade logic:
        - We should be able to downgrade to a deployed release
        - RR
        Verify:
        - Pass
        """

        index = 1
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "deployed",  # Target
            },
            {
                "state": "deployed",
                "reboot_required": True,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert not upgrade
        assert downgrade
        assert vim_rr

    def test_sw_deploy_strategy_aiosx_is_downgrade_multiple(self):
        """
        Test the sw_deploy strategy downgrade logic:
        - We should be able to downgrade to a deployed release
        - Downgrade multiple releases at once
        Verify:
        - Pass
        """

        index = 1
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "deployed",  # Target
            },
            {
                "state": "deployed",
                "reboot_required": False,
            },
            {
                "state": "deployed",
                "reboot_required": False,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert not upgrade
        assert downgrade
        assert not vim_rr

    def test_sw_deploy_strategy_aiosx_is_downgrade_multiple_rr_first(self):
        """
        Test the sw_deploy strategy downgrade logic:
        - We should be able to downgrade to a deployed release
        - Downgrade multiple releases at once
        - RR on the oldest release
        Verify:
        - Pass
        """

        index = 1
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "deployed",  # Target
            },
            {
                "state": "deployed",
                "reboot_required": True,
            },
            {
                "state": "deployed",
                "reboot_required": False,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert not upgrade
        assert downgrade
        assert vim_rr

    def test_sw_deploy_strategy_aiosx_is_downgrade_multiple_rr_second(self):
        """
        Test the sw_deploy strategy downgrade logic:
        - We should be able to downgrade to a deployed release
        - Downgrade multiple releases at once
        - RR on the most recent release
        Verify:
        - Pass
        """

        index = 1
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "deployed",  # Target
            },
            {
                "state": "deployed",
                "reboot_required": False,
            },
            {
                "state": "deployed",
                "reboot_required": True,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert not upgrade
        assert downgrade
        assert vim_rr

    def test_sw_deploy_strategy_aiosx_is_downgrade_removing_complex(self):
        """
        Test the sw_deploy strategy downgrade logic:
        - We should be able to downgrade to a deployed release
        - Downgrade multiple releases at once
        - RR on the most recent release
        Verify:
        - Pass
        """

        index = 3
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "deployed",
            },
            {
                "state": "deployed",
                "reboot_required": True,
            },
            {
                "state": "removing",  # Target
                "reboot_required": False,
            },
            {
                "state": "removing",
                "reboot_required": False,
            },
            {
                "state": "available",
                "reboot_required": True,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert not upgrade
        assert downgrade
        assert not vim_rr

    def test_sw_deploy_strategy_aiosx_is_downgrade_not_required(self):
        """
        Test the sw_deploy strategy downgrade logic:
        - Nothing to downgrade
        Verify:
        - Pass
        """

        index = 1
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "deployed",  # Target
            },
            {
                "state": "available",
                "reboot_required": False,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert not upgrade
        assert downgrade
        assert not vim_rr

    def test_sw_deploy_strategy_aiosx_is_downgrade_reenter(self):
        """
        Test the sw_deploy strategy downgrade logic:
        - Nothing to downgrade
        Verify:
        - Pass
        """

        index = 1
        release_data = [
            {
                "state": "unavailable",
            },
            {
                "state": "deployed",  # Target
            },
            {
                "state": "removing",
                "reboot_required": False,
            },
        ]

        upgrade, downgrade, vim_rr = is_target_release_downgrade(index, release_data)
        assert not upgrade
        assert downgrade
        assert not vim_rr
