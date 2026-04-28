#
# Copyright (c) 2016-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from unittest import mock
import uuid

from nfv_common import strategy as common_strategy
from nfv_unit_tests.tests import sw_update_testcase
from nfv_vim import nfvi
from nfv_vim.nfvi.objects.v1 import KUBE_UPGRADE_STATE
from nfv_vim.nfvi.objects.v1 import KubeVersion
from nfv_vim.objects import HOST_PERSONALITY
from nfv_vim.objects import SW_UPDATE_ALARM_RESTRICTION
from nfv_vim.objects import SW_UPDATE_APPLY_TYPE
from nfv_vim.objects import SW_UPDATE_INSTANCE_ACTION
from nfv_vim.objects import SwUpgrade
from nfv_vim.strategy._strategy import SwUpgradeStrategy

INITIAL_RELEASE = "3.2.1"
PATCH_RELEASE_UPGRADE = "3.2.2"
# Minor and Major are both major release upgrades
MINOR_RELEASE_UPGRADE = "4.0.1"
MAJOR_RELEASE_UPGRADE = "4.0.1"

# Kubernetes version constants reused across combined strategy tests
_COMBINED_FROM_KUBE = "v1.29.2"
_COMBINED_TO_KUBE = "v1.30.6"

# The release-id and metapackages are not used in these test cases, because they were
# created before the componentization feature. Nevertheless, the upgrade object still
# requires a value for them.
MOCK_METAPACKAGES = ["distcloud", "k8s"]

# A minimal kube versions list: FROM is active, TO is available.
# Used to satisfy _build_kube_upgrade_stages version chain lookups.
_COMBINED_KUBE_VERSIONS_LIST = [
    KubeVersion(
        _COMBINED_FROM_KUBE,  # kube_version
        "active",  # state
        True,  # target
        [],  # upgrade_from
        [],  # downgrade_to
        [],  # applied_patches
        [],  # available_patches
    ),
    KubeVersion(
        _COMBINED_TO_KUBE,  # kube_version
        "available",  # state
        False,  # target
        [_COMBINED_FROM_KUBE],  # upgrade_from
        [],  # downgrade_to
        [],  # applied_patches
        [],  # available_patches
    ),
]

# A kube versions list where the target version is already active/upgraded.
_COMBINED_KUBE_VERSIONS_ALREADY_UPGRADED = [
    KubeVersion(
        _COMBINED_FROM_KUBE,
        "active",
        True,
        [],
        [],
        [],
        [],
    ),
    KubeVersion(
        _COMBINED_TO_KUBE,
        "active",  # already active = already upgraded
        True,
        [_COMBINED_FROM_KUBE],
        [],
        [],
        [],
    ),
]


def _make_nfvi_upgrade(release, state="available", reboot_required=True):
    """Helper: build an nfvi.objects.v1.Upgrade for combined strategy tests."""
    return nfvi.objects.v1.Upgrade(
        release,
        MOCK_METAPACKAGES,
        {
            "state": state,
            "reboot_required": reboot_required,
            "sw_version": MAJOR_RELEASE_UPGRADE,
        },
        None,
        None,
    )


def _make_nfvi_alarm(alarm_id="900.007"):
    """Helper: build a minimal nfvi Alarm object."""
    return nfvi.objects.v1.Alarm(
        alarm_uuid="fake-uuid",
        alarm_id=alarm_id,
        entity_instance_id="host=controller-0",
        severity="major",
        reason_text="test alarm",
        timestamp="2026-01-01T00:00:00",
        mgmt_affecting=True,
    )


# utility method for the formatting of unlock-hosts stage as dict
# workers default to 5 retries with 120 second delay between attempts
# std controllers and storage have 0 retries
def _unlock_hosts_stage_as_dict(host_names, retry_count=5, retry_delay=120):
    return {
        "name": "unlock-hosts",
        "entity_names": host_names,
        "retry_count": retry_count,
        "retry_delay": retry_delay,
        "timeout": 1800,
    }


class BaseSwUpgradeStrategy(sw_update_testcase.SwUpdateStrategyTestCase):
    def setUp(self):
        super().setUp()
        patchers = [
            mock.patch(
                "nfv_vim.event_log._instance._event_issue",
                sw_update_testcase.fake_event_issue,
            ),
            mock.patch(
                "nfv_vim.objects._sw_update.SwUpdate.save",
                sw_update_testcase.fake_save,
            ),
            mock.patch(
                "nfv_vim.objects._sw_update.timers.timers_create_timer",
                sw_update_testcase.fake_timer,
            ),
            mock.patch(
                "nfv_vim.nfvi.nfvi_compute_plugin_disabled",
                sw_update_testcase.fake_nfvi_compute_plugin_disabled,
            ),
            mock.patch.object(nfvi.objects.v1.upgrade, "SW_VERSION", INITIAL_RELEASE),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)

    def create_sw_deploy_strategy(
        self,
        controller_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
        storage_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
        worker_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
        max_parallel_worker_hosts=10,
        alarm_restrictions=SW_UPDATE_ALARM_RESTRICTION.STRICT,
        default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
        release=MAJOR_RELEASE_UPGRADE,
        rollback=False,
        delete=False,
        cleanup=False,
        snapshot=False,
        kube_upgrade_version=None,
        nfvi_upgrade=None,
        single_controller=False,
    ):
        """Create a software update strategy."""

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
            cleanup=cleanup,
            snapshot=snapshot,
            kube_upgrade_version=kube_upgrade_version,
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
        self.create_host("controller-0", aio=True, openstack_installed=openstack)

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
        self.create_host("controller-0", aio=True, openstack_installed=openstack)
        self.create_host("controller-1", aio=True, openstack_installed=openstack)

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
        self.create_host("controller-0", openstack_installed=openstack)
        self.create_host("controller-1", openstack_installed=openstack)
        self.create_host("compute-0")
        self.create_host("compute-1")
        self.create_host("compute-2")
        self.create_host("storage-0")
        self.create_host("storage-1")
        self.create_host("storage-2")

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


class TestSwUpgradeStrategy(BaseSwUpgradeStrategy):
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

    @mock.patch("nfv_common.strategy._strategy.Strategy._build")
    def test_sw_deploy_strategy_build_steps(self, fake_build):
        """Verify build phase steps and stages for sw deploy strategy creation."""

        # setup a minimal host environment
        self.create_host("controller-0", aio=True)

        update_obj = SwUpgrade()
        strategy = self.create_sw_deploy_strategy(single_controller=True)
        update_obj = SwUpgrade()
        strategy.sw_update_obj = update_obj

        strategy.build()

        # verify the build phase and steps
        build_phase = strategy.build_phase.as_dict()
        query_steps = [
            {"name": "query-alarms"},
            {"name": "query-upgrade"},
            {"name": "sw-deploy-precheck"},
        ]
        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-query",
                    "total_steps": len(query_steps),
                    "steps": query_steps,
                },
            ],
        }
        sw_update_testcase.validate_phase(build_phase, expected_results)

    #  ~~~ SW-DEPLOY Start ~~~

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_sw_deploy_strategy_start_on_controller_0_aiosx(self):
        """Test the sw_upgrade strategy start stage controller-0

        - sx
        Verify:
        - pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        strategy._add_upgrade_start_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-start",
                    "total_steps": 2,
                    "steps": [
                        {"name": "start-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                }
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_sw_deploy_strategy_start_on_controller_0__aiodx(self):
        """Test the sw_upgrade strategy start stages on controller-0:

        - dx
        Verify:
        - pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        strategy._add_upgrade_start_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-start",
                    "total_steps": 2,
                    "steps": [
                        {"name": "start-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                }
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # pylint: disable=no-member
    def test_sw_deploy_strategy_start_on_controller_1_aiodx(self):
        """Test the sw_upgrade strategy start stages on controller-1:

        - dx
        Verify:
        - pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        strategy._add_upgrade_start_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-start",
                    "total_steps": 2,
                    "steps": [
                        {"name": "start-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                }
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # pylint: disable=no-member
    def test_sw_deploy_strategy_start_on_controller_1_aiodx_major(self):
        """Test the sw_upgrade strategy start stages on controller-1:

        - dx
        - major release
        Verify:
        - pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": True,
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        strategy._add_upgrade_start_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "start-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                }
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    #  ~~~ SW-DEPLOY Complete ~~~

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_sw_deploy_strategy_complete_on_controller_0_aiosx(self):
        """Test the sw_upgrade strategy complete stage controller-0

        - sx
        Verify:
        - pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        strategy._add_upgrade_complete_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-complete",
                    "total_steps": 4,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "activate-upgrade", "release": release},
                        {"name": "complete-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                }
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_sw_deploy_strategy_complete_on_controller_0__aiodx(self):
        """Test the sw_upgrade strategy complete stages on controller-0:

        - dx
        Verify:
        - pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        strategy._add_upgrade_complete_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-complete",
                    "total_steps": 4,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "activate-upgrade", "release": release},
                        {"name": "complete-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                }
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # pylint: disable=no-member
    def test_sw_deploy_strategy_complete_on_controller_1_aiodx(self):
        """Test the sw_upgrade strategy complete stages on controller-1:

        - dx
        Verify:
        - pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        strategy._add_upgrade_complete_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-complete",
                    "total_steps": 4,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "activate-upgrade", "release": release},
                        {"name": "complete-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                }
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # pylint: disable=no-member
    def test_sw_deploy_strategy_complete_on_controller_1_aiodx_major(self):
        """Test the sw_upgrade strategy complete stages on controller-1:

        - dx
        - major releasee
        Verify:
        - pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": True,
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        strategy._add_upgrade_complete_stage()

        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-complete",
                    "total_steps": 5,
                    "steps": [
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "query-alarms"},
                        {"name": "activate-upgrade", "release": release},
                        {"name": "complete-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                }
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # ~~~ AIO-SX NRR ~~~

    def test_sw_deploy_strategy_aiosx_controllers_serial_nrr(self):
        """Test the sw_deploy strategy add controller strategy stages:

        - aio-sx host
        - serial apply
        - no reboot required
        - stop_start instances
        - no instances
        Verify:
        - Pass.
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy()

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts, reboot=False
        )

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_nrr(self):
        """Test the sw_deploy strategy add controller strategy stages:

        - aio-sx host
        - parallel apply
        - no reboot required
        - stop_start instances
        - no instances
        Verify:
        - Pass.
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts, reboot=False
        )

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_nrr_no_openstack(self):
        """Test the sw_deploy strategy add controller strategy stages:

        - aio-sx host
        - parallel apply
        - no reboot required
        - stop_start instances
        - no instances
        - no openstack
        Verify:
        - Pass.
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            openstack=False,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts, reboot=False
        )

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_nrr_instances_migrate(self):
        """Test the sw_deploy strategy add controller strategy stages:

        - aio-sx host
        - parallel apply
        - no reboot required
        - migrate instances
        - instances
        Verify:
        - Fail.
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            instances=[("small", "test_instance_0", "controller-0")],
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts, reboot=False
        )

        assert success is False
        assert reason == "cannot migrate instances in a single controller configuration"

        sw_update_testcase.validate_strategy_persists(strategy)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_nrr_instances_stop_start(
        self,
    ):
        """Test the sw_deploy strategy add controller strategy stages:

        - aio-sx host
        - parallel apply
        - no reboot required
        - stop_start instances
        - instances
        Verify:
        - Pass.
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            instances=[("small", "test_instance_0", "controller-0")],
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts, reboot=False
        )

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    # ~~~ AIO-SX RR ~~~

    def test_sw_deploy_strategy_aiosx_controllers_serial_rr(self):
        """Test the sw_deploy strategy add controller strategy stages:

        - aio-sx host
        - serial apply
        - reboot required
        - stop_start instances
        - no instances
        Verify:
        - Pass.
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy()

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts, reboot=True
        )

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["controller-0"],
                            "retry_count": 0,
                            "retry_delay": 120,
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_rr(self):
        """Test the sw_deploy strategy add controller strategy stages:

        - aio-sx host
        - parallel apply
        - reboot required
        - stop_start instances
        - no instances
        Verify:
        - Pass.
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts, reboot=True
        )

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["controller-0"],
                            "retry_count": 0,
                            "retry_delay": 120,
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_rr_no_openstack(self):
        """Test the sw_deploy strategy add controller strategy stages:

        - aio-sx host
        - parallel apply
        - reboot required
        - stop_start instances
        - no instances
        - no openstack
        Verify:
        - Pass.
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            openstack=False,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts, reboot=True
        )

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["controller-0"],
                            "retry_count": 0,
                            "retry_delay": 120,
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_rr_instances_migrate(self):
        """Test the sw_deploy strategy add controller strategy stages:

        - aio-sx host
        - parallel apply
        - reboot required
        - migrate instances
        - instances
        Verify:
        - Pass.
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            instances=[("small", "test_instance_0", "controller-0")],
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts, reboot=True
        )

        assert success is False
        assert reason == "cannot migrate instances in a single controller configuration"

        sw_update_testcase.validate_strategy_persists(strategy)

    def test_sw_deploy_strategy_aiosx_controllers_parallel_rr_instances_stop_start(
        self,
    ):
        """Test the sw_deploy strategy add controller strategy stages:

        - aio-sx host
        - parallel apply
        - reboot required
        - stop_start instances
        - instances
        Verify:
        - Pass.
        """

        controller_hosts, strategy = self._gen_aiosx_hosts_and_strategy(
            worker_apply_type=SW_UPDATE_APPLY_TYPE.PARALLEL,
            instances=[("small", "test_instance_0", "controller-0")],
        )

        success, reason = strategy._add_worker_strategy_stages(
            worker_hosts=controller_hosts, reboot=True
        )

        assert success is True, reason

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 8,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "stop-instances", "entity_names": ["test_instance_0"]},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["controller-0"],
                            "retry_count": 0,
                            "retry_delay": 120,
                        },
                        {
                            "name": "start-instances",
                            "entity_names": ["test_instance_0"],
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_already_deploying(self):
        """Test the sw_deploy strategy when patch already deploying:

        - patch already deploying
        Verify:
        - Success.
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                "13.01",
                MOCK_METAPACKAGES,
                {
                    "state": "deploying",
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        bpr = strategy.build_phase

        assert (
            strategy._state == common_strategy.STRATEGY_STATE.INITIAL
        ), strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.INITIAL, bpr.result

    def test_sw_deploy_strategy_aiosx_already_removing(self):
        """Test the sw_deploy strategy when patch already removing:

        - patch already removing
        Verify:
        - Success.
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                "13.01",
                MOCK_METAPACKAGES,
                {
                    "state": "removing",
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        bpr = strategy.build_phase

        assert (
            strategy._state == common_strategy.STRATEGY_STATE.INITIAL
        ), strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.INITIAL, bpr.result

    def test_sw_deploy_strategy_aiosx_already_deploy_completed(self):
        """Test the sw_deploy strategy when patch already deploy completed:

        - patch deploy completed
        Verify:
        - Fail.
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                "13.01",
                MOCK_METAPACKAGES,
                {"state": "deploying"},
                {"state": "completed"},
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        expected_reason = "Software deployment is already complete, pending delete"
        bpr = strategy.build_phase

        assert (
            strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED
        ), strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.FAILED, bpr.result
        assert bpr.result_reason == expected_reason, bpr.result_reason

    def test_sw_deploy_strategy_aiosx_already_deployed(self):
        """Test the sw_deploy strategy when patch already deploy completed:

        - patch deployed
        Verify:
        - Fail.
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                "13.01",
                MOCK_METAPACKAGES,
                {"state": "deployed"},
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        expected_reason = "no sw-deployments patches need to be applied"
        bpr = strategy.build_phase

        assert (
            strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED
        ), strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.FAILED, bpr.result
        assert bpr.result_reason == expected_reason, bpr.result_reason

    def test_sw_deploy_strategy_aiosx_already_deployed_downgrade_create(self):
        """Test the sw_deploy strategy when patch already deploy completed:

        - patch deployed
        Verify:
        - Fail.
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                "13.01",
                MOCK_METAPACKAGES,
                {
                    "state": "deployed",
                    "downgrade": True,
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        bpr = strategy.build_phase

        assert (
            strategy._state == common_strategy.STRATEGY_STATE.INITIAL
        ), strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.INITIAL, bpr.result

    def test_sw_deploy_strategy_aiosx_already_committed(self):
        """Test the sw_deploy strategy when patch already committed:

        - patch already committed
        Verify:
        - Fail.
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                "13.01",
                MOCK_METAPACKAGES,
                {
                    "state": "commited",
                    "downgrade": True,
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            )
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        bpr = strategy.build_phase

        assert (
            strategy._state == common_strategy.STRATEGY_STATE.INITIAL
        ), strategy._state
        assert bpr.result == common_strategy.STRATEGY_PHASE_RESULT.INITIAL, bpr.result

    def test_sw_deploy_strategy_aiosx_release_does_not_exist(self):
        """Test the sw_deploy strategy when patch does not exist:

        - patch does not exist
        Verify:
        - Fail.
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                "13.01", MOCK_METAPACKAGES, None, None, None
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
        """Test the sw_deploy strategy when patch is unavailable:

        - patch does not exist
        Verify:
        - Fail.
        """

        _, strategy = self._gen_aiosx_hosts_and_strategy(
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                "13.01",
                MOCK_METAPACKAGES,
                {"state": "unavailable"},
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
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - nrr
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 3,
            "stages": [
                {
                    "name": "sw-upgrade-start",
                    "total_steps": 2,
                    "steps": [
                        {"name": "start-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                    ],
                },
                {
                    "name": "sw-upgrade-complete",
                    "total_steps": 5,
                    "steps": [
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "query-alarms"},
                        {"name": "activate-upgrade", "release": release},
                        {"name": "complete-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_apply_phase_rr(self):
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - rr
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": True,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 3,
            "stages": [
                {
                    "name": "sw-upgrade-start",
                    "total_steps": 2,
                    "steps": [
                        {"name": "start-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["controller-0"],
                            "retry_count": 0,
                            "retry_delay": 120,
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-complete",
                    "total_steps": 4,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "activate-upgrade", "release": release},
                        {"name": "complete-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiodx_apply_phase_nrr(self):
        """Test the sw_deploy strategy apply phase:

        - aio-dx
        - nrr
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=release,
            delete=True,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 5,
            "stages": [
                {
                    "name": "sw-upgrade-start",
                    "total_steps": 2,
                    "steps": [
                        {"name": "start-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "upgrade-hosts", "entity_names": ["controller-1"]},
                    ],
                },
                {
                    "name": "sw-upgrade-complete",
                    "total_steps": 5,
                    "steps": [
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "query-alarms"},
                        {"name": "activate-upgrade", "release": release},
                        {"name": "complete-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
                {
                    "name": "sw-deploy-delete",
                    "total_steps": 1,
                    "steps": [
                        {"name": "deploy-delete", "release": release},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiodx_apply_phase_rr(self):
        """Test the sw_deploy strategy apply phase:

        - aio-dx
        - rr
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=release,
            delete=True,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": True,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 5,
            "stages": [
                {
                    "name": "sw-upgrade-start",
                    "total_steps": 2,
                    "steps": [
                        {"name": "start-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-0"]},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["controller-0"],
                            "retry_count": 0,
                            "retry_delay": 120,
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "lock-hosts", "entity_names": ["controller-1"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-1"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["controller-1"],
                            "retry_count": 0,
                            "retry_delay": 120,
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-complete",
                    "total_steps": 4,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "activate-upgrade", "release": release},
                        {"name": "complete-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
                {
                    "name": "sw-deploy-delete",
                    "total_steps": 1,
                    "steps": [
                        {"name": "deploy-delete", "release": release},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_standard_apply_phase_nrr(self):
        """Test the sw_deploy strategy apply phase:

        - standard
        - nrr
        - parallel storage
        - parallel workers
        Verify:
        - Pass.
        """

        release = "888.8"
        _, _, _, strategy = self._gen_standard_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 6,
            "stages": [
                {
                    "name": "sw-upgrade-start",
                    "total_steps": 2,
                    "steps": [
                        {"name": "start-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
                {
                    "name": "sw-upgrade-controllers",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                    ],
                },
                {
                    "name": "sw-upgrade-controllers",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "upgrade-hosts", "entity_names": ["controller-1"]},
                    ],
                },
                {
                    "name": "sw-upgrade-storage-hosts",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {
                            "name": "upgrade-hosts",
                            "entity_names": ["storage-0", "storage-1", "storage-2"],
                        },
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {
                            "name": "upgrade-hosts",
                            "entity_names": ["compute-0", "compute-1", "compute-2"],
                        },
                    ],
                },
                {
                    "name": "sw-upgrade-complete",
                    "total_steps": 5,
                    "steps": [
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "query-alarms"},
                        {"name": "activate-upgrade", "release": release},
                        {"name": "complete-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_standard_apply_phase_rr(self):
        """Test the sw_deploy strategy apply phase:

        - standard
        - rr
        - parallel storage
        - parallel workers
        Verify:
        - Pass.
        """

        release = "888.8"
        _, _, _, strategy = self._gen_standard_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": True,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 6,
            "stages": [
                {
                    "name": "sw-upgrade-start",
                    "total_steps": 2,
                    "steps": [
                        {"name": "start-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
                {
                    "name": "sw-upgrade-controllers",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-0"]},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["controller-0"],
                            "retry_count": 0,
                            "retry_delay": 120,
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-controllers",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "lock-hosts", "entity_names": ["controller-1"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-1"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["controller-1"],
                            "retry_count": 0,
                            "retry_delay": 120,
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-storage-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {
                            "name": "lock-hosts",
                            "entity_names": ["storage-0", "storage-1", "storage-2"],
                        },
                        {
                            "name": "upgrade-hosts",
                            "entity_names": ["storage-0", "storage-1", "storage-2"],
                        },
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["storage-0", "storage-1", "storage-2"],
                        },
                        {"name": "wait-data-sync", "timeout": 1800},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {
                            "name": "lock-hosts",
                            "entity_names": ["compute-0", "compute-1", "compute-2"],
                        },
                        {
                            "name": "upgrade-hosts",
                            "entity_names": ["compute-0", "compute-1", "compute-2"],
                        },
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["compute-0", "compute-1", "compute-2"],
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-complete",
                    "total_steps": 4,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "activate-upgrade", "release": release},
                        {"name": "complete-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_standard_apply_phase_rr_major(self):
        """Test the sw_deploy strategy apply phase:

        - standard
        - rr
        - parallel storage
        - parallel workers
        - major release
        Verify:
        - Pass.
        """

        release = "888.8"
        _, _, _, strategy = self._gen_standard_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": True,
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 6,
            "stages": [
                {
                    "name": "sw-upgrade-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "start-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
                {
                    "name": "sw-upgrade-controllers",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "lock-hosts", "entity_names": ["controller-1"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-1"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["controller-1"],
                            "retry_count": 0,
                            "retry_delay": 120,
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-controllers",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-0"]},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["controller-0"],
                            "retry_count": 0,
                            "retry_delay": 120,
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-storage-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {
                            "name": "lock-hosts",
                            "entity_names": ["storage-0", "storage-1", "storage-2"],
                        },
                        {
                            "name": "upgrade-hosts",
                            "entity_names": ["storage-0", "storage-1", "storage-2"],
                        },
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["storage-0", "storage-1", "storage-2"],
                        },
                        {"name": "wait-data-sync", "timeout": 1800},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {
                            "name": "lock-hosts",
                            "entity_names": ["compute-0", "compute-1", "compute-2"],
                        },
                        {
                            "name": "upgrade-hosts",
                            "entity_names": ["compute-0", "compute-1", "compute-2"],
                        },
                        {"name": "system-stabilize", "timeout": 15},
                        {
                            "name": "unlock-hosts",
                            "entity_names": ["compute-0", "compute-1", "compute-2"],
                        },
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-complete",
                    "total_steps": 5,
                    "steps": [
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "query-alarms"},
                        {"name": "activate-upgrade", "release": release},
                        {"name": "complete-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_complete(self):
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - major
        - complete
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "complete",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        "hostname": "controller-0",
                        "host_state": "deployed",
                    },
                ],
            ),
        )

        # Replace controller-0 with locked one
        self.create_host(
            "controller-0",
            aio=True,
            openstack_installed=False,
            admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED,
            oper_state=nfvi.objects.v1.HOST_OPER_STATE.DISABLED,
            avail_status=nfvi.objects.v1.HOST_AVAIL_STATUS.ONLINE,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 3,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts"},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_active_done(self):
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - major
        - activate-deon
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "activate-rollback-done",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        "hostname": "controller-0",
                        "host_state": "deployed",
                    },
                ],
            ),
        )

        # Replace controller-0 with locked one
        self.create_host(
            "controller-0",
            aio=True,
            openstack_installed=False,
            admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED,
            oper_state=nfvi.objects.v1.HOST_OPER_STATE.DISABLED,
            avail_status=nfvi.objects.v1.HOST_AVAIL_STATUS.ONLINE,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 3,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts"},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_activate_failed(self):
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - major
        - activate-failed
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "activate-rollback-failed",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        "hostname": "controller-0",
                        "host_state": "deployed",
                    },
                ],
            ),
        )

        # Replace controller-0 with locked one
        self.create_host(
            "controller-0",
            aio=True,
            openstack_installed=False,
            admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED,
            oper_state=nfvi.objects.v1.HOST_OPER_STATE.DISABLED,
            avail_status=nfvi.objects.v1.HOST_AVAIL_STATUS.ONLINE,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 3,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts"},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_start_done(self):
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - major
        - start-done
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "start-done",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        "hostname": "controller-0",
                        "host_state": "pending",
                    },
                ],
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 2,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_start_done_locked(self):
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - major
        - start-done
        - c0 locked
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "start-done",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        "hostname": "controller-0",
                        "host_state": "pending",
                    },
                ],
            ),
        )

        # Replace controller-0 with locked one
        self.create_host(
            "controller-0",
            aio=True,
            openstack_installed=False,
            admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED,
            oper_state=nfvi.objects.v1.HOST_OPER_STATE.DISABLED,
            avail_status=nfvi.objects.v1.HOST_AVAIL_STATUS.ONLINE,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 3,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "deploy-delete"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {
                            "name": "sw-deploy-do-nothing",
                            "entity_names": ["controller-0"],
                        },
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts"},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_host_rollback_deployed_unlocked(
        self,
    ):
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - major
        - host-rollback-done
        - c0 unloacked
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "host-rollback-done",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        "hostname": "controller-0",
                        "host_state": "rollback-deployed",
                    },
                ],
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 2,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_host_rollback_deployed_locked(self):
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - major
        - host-rollback-done
        - c0 loacked
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "host-rollback-done",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        "hostname": "controller-0",
                        "host_state": "rollback-deployed",
                    },
                ],
            ),
        )

        # Replace controller-0 with locked one
        self.create_host(
            "controller-0",
            aio=True,
            openstack_installed=False,
            admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED,
            oper_state=nfvi.objects.v1.HOST_OPER_STATE.DISABLED,
            avail_status=nfvi.objects.v1.HOST_AVAIL_STATUS.ONLINE,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 3,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts"},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_host_done(self):
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - major
        - host-done
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "host-done",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 3,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts"},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_host_failed(self):
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - major
        - host-failed
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "host-failed",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 3,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts"},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_rollback_from_host(self):
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - major
        - host
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "host",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 3,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 6,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts"},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_cleanup_build_fails_with_release(self):
        """cleanup cannot be combined with a release."""
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=MAJOR_RELEASE_UPGRADE,
            cleanup=True,
        )
        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build()

        assert strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED

    def test_sw_deploy_strategy_cleanup_build_fails_with_rollback(self):
        """cleanup cannot be combined with rollback."""
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            rollback=True,
            cleanup=True,
        )
        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build()

        assert strategy._state == common_strategy.STRATEGY_STATE.BUILD_FAILED

    def test_sw_deploy_strategy_cleanup_deploy_completed(self):
        """cleanup with a completed deployment: deploy-delete apply stage."""
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            cleanup=True,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                "888.8",
                MOCK_METAPACKAGES,
                {"state": "deploying"},
                {"state": "completed"},
                None,
            ),
        )
        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        with mock.patch("nfv_common.strategy._strategy.Strategy._build"):
            strategy.build()
        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        expected_build = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-query",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "query-upgrade"},
                        {"name": "query-kube-upgrade"},
                    ],
                },
            ],
        }
        expected_apply = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-deploy-delete",
                    "total_steps": 1,
                    "steps": [
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(
            strategy.build_phase.as_dict(), expected_build
        )
        sw_update_testcase.validate_phase(
            strategy.apply_phase.as_dict(), expected_apply
        )

    def test_sw_deploy_strategy_cleanup_system_deploy_active(self):
        """cleanup with an active software system deploy"""
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            cleanup=True,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                "888.8",
                MOCK_METAPACKAGES,
                {"state": "deploying"},
                None,
                None,
                system_deploy={"state": "active"},
            ),
        )
        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        with mock.patch("nfv_common.strategy._strategy.Strategy._build"):
            strategy.build()
        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        expected_build = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-query",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "query-upgrade"},
                        {"name": "query-kube-upgrade"},
                    ],
                },
            ],
        }
        expected_apply = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-system-deploy-delete",
                    "total_steps": 1,
                    "steps": [
                        {"name": "sw-system-deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(
            strategy.build_phase.as_dict(), expected_build
        )
        sw_update_testcase.validate_phase(
            strategy.apply_phase.as_dict(), expected_apply
        )

    def test_sw_deploy_strategy_cleanup_kube_upgrade_active_and_deploy_completed(
        self,
    ):
        """cleanup with active kube upgrade and completed deploy.

        Verify apply phase: kube-upgrade-complete, kube-post-application-update,
        kube-upgrade-cleanup, then deploy-delete.
        """
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            cleanup=True,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                "888.8",
                MOCK_METAPACKAGES,
                {"state": "deploying"},
                {"state": "completed"},
                None,
            ),
        )
        strategy.nfvi_kube_upgrade = nfvi.objects.v1.KubeUpgrade(
            state=KUBE_UPGRADE_STATE.KUBE_UPGRADE_COMPLETE,
            from_version="v1.29.0",
            to_version="v1.30.0",
        )
        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        expected_apply = {
            "total_stages": 4,
            "stages": [
                {
                    "name": "kube-upgrade-complete",
                    "total_steps": 1,
                    "steps": [{"name": "kube-upgrade-complete"}],
                },
                {
                    "name": "kube-post-application-update",
                    "total_steps": 1,
                    "steps": [{"name": "kube-post-application-update"}],
                },
                {
                    "name": "kube-upgrade-cleanup",
                    "total_steps": 1,
                    "steps": [{"name": "kube-upgrade-cleanup"}],
                },
                {
                    "name": "sw-deploy-delete",
                    "total_steps": 1,
                    "steps": [{"name": "deploy-delete"}],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(
            strategy.apply_phase.as_dict(), expected_apply
        )

    def test_sw_deploy_strategy_cleanup_all_three_conditions(self):
        """cleanup with all possible active stages

        Verify apply phase:
            kube-upgrade-complete chain
            deploy-delete
            system-deploy-delete.
        """
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=None,
            cleanup=True,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                "888.8",
                MOCK_METAPACKAGES,
                {"state": "deploying"},
                {"state": "completed"},
                None,
                system_deploy={"state": "active"},
            ),
        )
        strategy.nfvi_kube_upgrade = nfvi.objects.v1.KubeUpgrade(
            state=KUBE_UPGRADE_STATE.KUBE_UPGRADE_COMPLETE,
            from_version="v1.29.0",
            to_version="v1.30.0",
        )
        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        expected_apply = {
            "total_stages": 5,
            "stages": [
                {
                    "name": "kube-upgrade-complete",
                    "total_steps": 1,
                    "steps": [{"name": "kube-upgrade-complete"}],
                },
                {
                    "name": "kube-post-application-update",
                    "total_steps": 1,
                    "steps": [{"name": "kube-post-application-update"}],
                },
                {
                    "name": "kube-upgrade-cleanup",
                    "total_steps": 1,
                    "steps": [{"name": "kube-upgrade-cleanup"}],
                },
                {
                    "name": "sw-deploy-delete",
                    "total_steps": 1,
                    "steps": [{"name": "deploy-delete"}],
                },
                {
                    "name": "sw-system-deploy-delete",
                    "total_steps": 1,
                    "steps": [{"name": "sw-system-deploy-delete"}],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(
            strategy.apply_phase.as_dict(), expected_apply
        )

    def _send_precheck_callback(self, step, response):
        """Run the SwDeployPrecheckStep coroutine with the given response"""

        callback = step._sw_deploy_precheck_callback()

        try:
            callback.send(response)
        except StopIteration:
            pass

    def _create_precheck_step(self):
        from nfv_vim.strategy._strategy_steps import SwDeployPrecheckStep

        step = SwDeployPrecheckStep(release="12.0")
        step.stage = mock.MagicMock()
        return step

    def _create_response(
        self,
        completed,
        result_data,
        complete_data,
        error_message=None,
        upgrade_object_data=None,
    ):
        response = {
            "completed": completed,
            "result-data": result_data,
            "complete-data": complete_data,
        }

        if error_message:
            response["error-message"] = error_message

        # On the success path the precheck callback stores the upgrade object
        # built by USM from the precheck data into the strategy.
        if upgrade_object_data:
            response["upgrade-object-data"] = upgrade_object_data

        return response

    def _assert_response(
        self,
        step,
        expected_result=common_strategy.STRATEGY_STEP_RESULT.SUCCESS,
        expected_reason=None,
        error_response=None,
    ):
        result, reason = step.stage.step_complete.call_args[0]

        self.assertEqual(result, expected_result)
        self.assertEqual(reason, expected_reason)

        # No failure response should be reported on the success path.
        if expected_result == common_strategy.STRATEGY_STEP_RESULT.SUCCESS:
            step.phase.result_complete_response.assert_not_called()
        else:
            step.phase.result_complete_response.assert_called_once_with(error_response)

    def test_sw_deploy_precheck_callback_success(self):
        """Callback succeeds when completed=True and result-data=True"""

        step = self._create_precheck_step()
        upgrade_obj = nfvi.objects.v1.Upgrade(
            "13.0", MOCK_METAPACKAGES, None, None, None
        )
        response = self._create_response(
            True, True, {"info": "all healthy"}, upgrade_object_data=upgrade_obj
        )
        self._send_precheck_callback(step, response)

        # The callback stores the upgrade object returned by USM precheck.
        self.assertEqual(step.strategy.nfvi_upgrade, upgrade_obj)
        self._assert_response(step, expected_reason=response["complete-data"]["info"])

    def test_sw_deploy_precheck_callback_fails_when_result_data_is_false(self):
        """Callback fails when result-data=False (one or more metapackages unhealthy)"""

        step = self._create_precheck_step()
        response = self._create_response(True, False, {}, "pkg-A not healthy")
        self._send_precheck_callback(step, response)

        self._assert_response(
            step,
            common_strategy.STRATEGY_STEP_RESULT.FAILED,
            response["error-message"],
            response,
        )

    def test_sw_deploy_precheck_callback_fails_when_not_completed(self):
        """Callback fails when completed=False"""

        step = self._create_precheck_step()
        response = self._create_response(False, None, {}, "timeout")
        self._send_precheck_callback(step, response)

        self._assert_response(
            step,
            common_strategy.STRATEGY_STEP_RESULT.FAILED,
            response["error-message"],
            response,
        )

    def test_sw_deploy_precheck_callback_returns_unhealthy_metapackage_message(self):
        """Callback returns unhealthy metapackage"""

        step = self._create_precheck_step()
        response = self._create_response(False, False, {})
        self._send_precheck_callback(step, response)

        self._assert_response(
            step,
            common_strategy.STRATEGY_STEP_RESULT.FAILED,
            "One or more metapackages are not healthy",
            response,
        )

    def test_sw_deploy_precheck_callback_fails_with_default_message_when_not_completed(
        self,
    ):
        """Callback returns default unknown error message when completed=False"""

        step = self._create_precheck_step()
        response = self._create_response(False, True, {})
        self._send_precheck_callback(step, response)

        self._assert_response(
            step,
            common_strategy.STRATEGY_STEP_RESULT.FAILED,
            "Unknown error while trying software deploy precheck, check "
            "/var/log/nfv-vim.log or /var/log/software.log for more information.",
            response,
        )

    def _send_deploy_delete_callback(self, step, response):
        """Run the SwDeployDeleteStep coroutine with the given response"""

        callback = step._deploy_delete_callback()

        try:
            callback.send(response)
        except StopIteration:
            pass

    def _create_deploy_delete_step(self):
        from nfv_vim.strategy._strategy_steps import SwDeployDeleteStep

        step = SwDeployDeleteStep(release="12.0")
        step.stage = mock.MagicMock()
        return step

    def test_sw_deploy_delete_callback_success(self):
        """Callback succeeds when completed=True and no error is reported"""

        step = self._create_deploy_delete_step()
        response = self._create_response(
            True, {}, {"info": "Deploy deleted with success"}
        )
        self._send_deploy_delete_callback(step, response)

        self.assertNotIn("error", response["complete-data"])
        self._assert_response(step, expected_reason="Deploy deleted with success")

    def test_sw_deploy_delete_callback_success_strips_info(self):
        """Callback strips surrounding whitespace from the success info message"""

        step = self._create_deploy_delete_step()
        response = self._create_response(
            True, None, {"info": "  Deploy deleted with success  ", "error": ""}
        )
        self._send_deploy_delete_callback(step, response)

        self._assert_response(step, expected_reason="Deploy deleted with success")

    def test_sw_deploy_delete_callback_success_when_error_is_empty(self):
        """Callback succeeds when the error field is present but empty"""

        step = self._create_deploy_delete_step()
        response = self._create_response(
            True, None, {"info": "Deploy deleted with success", "error": ""}
        )
        self._send_deploy_delete_callback(step, response)

        self._assert_response(step, expected_reason="Deploy deleted with success")

    def test_sw_deploy_delete_callback_fails_when_completed_with_error(self):
        """Callback fails when completed=True but an error is reported.

        The failure reason must be the raw error value from complete-data and the
        full response must be forwarded to result_complete_response.
        """

        step = self._create_deploy_delete_step()
        response = self._create_response(
            True, None, {"info": "", "error": "Deploy delete failed"}
        )
        self._send_deploy_delete_callback(step, response)

        self._assert_response(
            step,
            common_strategy.STRATEGY_STEP_RESULT.FAILED,
            "Deploy delete failed",
            response,
        )

    def test_sw_deploy_delete_callback_error_strips_reason(self):
        """Callback strips surrounding whitespace from the error message"""

        step = self._create_deploy_delete_step()
        response = self._create_response(
            True, None, {"error": "  Deploy delete failed  "}
        )
        self._send_deploy_delete_callback(step, response)

        self._assert_response(
            step,
            common_strategy.STRATEGY_STEP_RESULT.FAILED,
            "Deploy delete failed",
            response,
        )

    def test_sw_deploy_delete_callback_fails_when_not_completed(self):
        """Callback fails with the error-message when completed=False"""

        step = self._create_deploy_delete_step()
        response = self._create_response(False, None, {}, "Delete timed out")
        self._send_deploy_delete_callback(step, response)

        self._assert_response(
            step,
            common_strategy.STRATEGY_STEP_RESULT.FAILED,
            "Delete timed out",
            response,
        )

    def test_sw_deploy_delete_callback_fails_with_default_message(self):
        """Callback returns the default message when completed=False and no error"""

        step = self._create_deploy_delete_step()
        response = self._create_response(False, None, {})
        self._send_deploy_delete_callback(step, response)

        self._assert_response(
            step,
            common_strategy.STRATEGY_STEP_RESULT.FAILED,
            "Unknown error while trying software deploy delete, "
            "check /var/log/nfv-vim.log or /var/log/software.log "
            "for more information.",
            response,
        )

    def test_sw_deploy_strategy_aiodx_rollback_host_rollback_deployed_unlocked_pending(
        self,
    ):
        """Test the sw_deploy strategy apply phase:

        - aio-dx
        - major
        - host-rollback-done
        - c0 locked
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "deploy-host-rollback",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        "hostname": "controller-0",
                        "host_state": "deploy-host-rollback-deployed",
                    },
                    {
                        "hostname": "controller-1",
                        "host_state": "deploy-host-rollback-pending",
                    },
                ],
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = expected_results = {
            "total_stages": 4,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-0"]},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts", "entity_names": ["controller-0"]},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "lock-hosts", "entity_names": ["controller-1"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-1"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts", "entity_names": ["controller-1"]},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiodx_rollback_from_host_rollback_deployed_unlocked(
        self,
    ):
        """Test the sw_deploy strategy apply phase:

        - aio-dx
        - major
        - host-rollback-done
        - c0 locked
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "host-rollback-done",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        "hostname": "controller-0",
                        "host_state": "rollback-deployed",
                    },
                    {
                        "hostname": "controller-1",
                        "host_state": "rollback-deployed",
                    },
                ],
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 2,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiodx_rollback_from_host_rollback_deployed_locked(self):
        """Test the sw_deploy strategy apply phase:

        - aio-dx
        - major
        - host-rollback-done
        - c0 locked
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "host-rollback-done",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                [
                    {
                        "hostname": "controller-0",
                        "host_state": "rollback-deployed",
                    },
                ],
            ),
        )

        self.create_host(
            "controller-0",
            aio=True,
            openstack_installed=False,
            admin_state=nfvi.objects.v1.HOST_ADMIN_STATE.LOCKED,
            oper_state=nfvi.objects.v1.HOST_OPER_STATE.DISABLED,
            avail_status=nfvi.objects.v1.HOST_AVAIL_STATUS.ONLINE,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 4,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-0"]},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts", "entity_names": ["controller-0"]},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "lock-hosts", "entity_names": ["controller-1"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-1"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts", "entity_names": ["controller-1"]},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiodx_rollback_from_host_done(self):
        """Test the sw_deploy strategy apply phase:

        - aio-dx
        - major
        - host-done
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "host-done",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 4,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-0"]},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts", "entity_names": ["controller-0"]},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "lock-hosts", "entity_names": ["controller-1"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-1"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts", "entity_names": ["controller-1"]},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiodx_rollback_from_host_failed(self):
        """Test the sw_deploy strategy apply phase:

        - aio-dx
        - major
        - host-failed
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "host-failed",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 4,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-0"]},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts", "entity_names": ["controller-0"]},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "lock-hosts", "entity_names": ["controller-1"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-1"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts", "entity_names": ["controller-1"]},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiodx_rollback_from_host(self):
        """Test the sw_deploy strategy rollback phase:

        - aio-dx
        - major
        - host
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiodx_hosts_and_strategy(
            release=None,
            rollback=True,
            delete=False,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "release_id": MAJOR_RELEASE_UPGRADE,
                    "state": "deploying",
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                {
                    "state": "host",
                    "reboot_required": True,
                    "from_release": INITIAL_RELEASE,
                    "to_release": MAJOR_RELEASE_UPGRADE,
                },
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 4,
            "stages": [
                {
                    "name": "sw-upgrade-rollback-start",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "sw-deploy-abort"},
                        {"name": "sw-deploy-activate-rollback"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-0"]},
                        {"name": "lock-hosts", "entity_names": ["controller-0"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts", "entity_names": ["controller-0"]},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 7,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "lock-hosts", "entity_names": ["controller-1"]},
                        {"name": "upgrade-hosts", "entity_names": ["controller-1"]},
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "unlock-hosts", "entity_names": ["controller-1"]},
                        {"name": "wait-alarms-clear", "timeout": 2400},
                    ],
                },
                {
                    "name": "sw-upgrade-rollback-complete",
                    "total_steps": 3,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "swact-hosts", "entity_names": ["controller-1"]},
                        {"name": "deploy-delete"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_deploy_strategy_aiosx_downgrade(self):
        """Test the sw_deploy strategy apply phase:

        - aio-sx
        - major
        - host
        Verify:
        - Pass.
        """

        release = "888.8"
        _, strategy = self._gen_aiosx_hosts_and_strategy(
            release=release,
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "available",
                    "reboot_required": False,
                    "sw_version": PATCH_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        apply_phase = strategy.apply_phase.as_dict()

        expected_results = {
            "total_stages": 3,
            "stages": [
                {
                    "name": "sw-upgrade-start",
                    "total_steps": 2,
                    "steps": [
                        {"name": "start-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
                {
                    "name": "sw-upgrade-worker-hosts",
                    "total_steps": 2,
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "upgrade-hosts", "entity_names": ["controller-0"]},
                    ],
                },
                {
                    "name": "sw-upgrade-complete",
                    "total_steps": 5,
                    "steps": [
                        {"name": "system-stabilize", "timeout": 15},
                        {"name": "query-alarms"},
                        {"name": "activate-upgrade", "release": release},
                        {"name": "complete-upgrade", "release": release},
                        {"name": "query-alarms"},
                    ],
                },
            ],
        }

        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def test_sw_upgrade_strategy_kube_version_normalization(self):
        """Test that kube_upgrade_version without 'v' prefix gets 'v' prepended.

        Verify:
        - "1.29.0" is stored as "v1.29.0"
        - "v1.29.0" is stored unchanged as "v1.29.0"
        """
        strategy_no_prefix = self.create_sw_deploy_strategy(
            kube_upgrade_version="1.29.0"
        )
        self.assertEqual("v1.29.0", strategy_no_prefix._kube_upgrade_version)

        strategy_with_prefix = self.create_sw_deploy_strategy(
            kube_upgrade_version="v1.29.0"
        )
        self.assertEqual("v1.29.0", strategy_with_prefix._kube_upgrade_version)

    def test_sw_upgrade_strategy_kube_upgrade_version_with_rollback_fails(self):
        """Test that setting both kube_upgrade_version and rollback=True fails build.

        Verify:
        - build() sets state to BUILD_FAILED
        - build_phase result is FAILED
        """
        self.create_host("controller-0", aio=True)

        strategy = self.create_sw_deploy_strategy(
            release=None,
            rollback=True,
            kube_upgrade_version="v1.29.0",
            delete=None,
        )

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj
        strategy.build()

        self.assertEqual(common_strategy.STRATEGY_STATE.BUILD_FAILED, strategy._state)
        self.assertEqual(
            common_strategy.STRATEGY_PHASE_RESULT.FAILED, strategy.build_phase.result
        )
        self.assertEqual(
            "Cannot set both kube_upgrade and rollback",
            strategy.build_phase.result_reason,
        )

    @mock.patch("nfv_common.strategy._strategy.Strategy._build")
    def test_sw_upgrade_strategy_build_query_includes_kube_steps(self, fake_build):
        """Test that build phase includes kube query steps when kube_upgrade_version set

        Verify:
        - QueryKubeVersionsStep, QueryKubeUpgradeStep, KubeUpgradeCleanupAbortedStep,
          and QueryKubeHostUpgradeStep are added to the build query stage.
        """
        self.create_host("controller-0", aio=True)

        fake_build.return_value = None

        strategy = self.create_sw_deploy_strategy(
            kube_upgrade_version="v1.29.0",
        )
        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj
        strategy.build()

        build_phase = strategy.build_phase.as_dict()
        expected_results = {
            "total_stages": 1,
            "stages": [
                {
                    "name": "sw-upgrade-query",
                    "steps": [
                        {"name": "query-alarms"},
                        {"name": "query-upgrade"},
                        {"name": "query-kube-versions"},
                        {"name": "query-kube-upgrade"},
                        {"name": "kube-upgrade-cleanup-aborted"},
                        {"name": "query-kube-host-upgrade"},
                        {"name": "sw-deploy-precheck"},
                    ],
                }
            ],
        }
        sw_update_testcase.validate_phase(build_phase, expected_results)

    def test_sw_upgrade_strategy_is_combined_strategy_by_kube_version(self):
        """Test _is_combined_strategy() reflects whether kube_upgrade_version is set.

        Verify:
        - When kube_upgrade_version is set: _is_combined_strategy() is truthy and
          the nfvi_kube_upgrade mixin attribute is initialized.
        - When kube_upgrade_version is None: _kube_upgrade_version is None,
          _is_combined_strategy() is falsy and the mixin attribute is not set.
        """
        strategy = self.create_sw_deploy_strategy(
            kube_upgrade_version="v1.29.0",
        )

        self.assertTrue(strategy._is_combined_strategy())
        self.assertTrue(hasattr(strategy, "_nfvi_kube_upgrade"))

        strategy = self.create_sw_deploy_strategy(
            kube_upgrade_version=None,
        )

        self.assertIsNone(strategy._kube_upgrade_version)
        self.assertFalse(strategy._is_combined_strategy())
        self.assertFalse(hasattr(strategy, "_nfvi_kube_upgrade"))

    def test_sw_upgrade_strategy_kube_upgrade_post_control_plane_state_fails(self):
        """Test build fails when kube upgrade is past the control plane phase.

        Verify:
        - build_complete sets state to BUILD_FAILED when nfvi_kube_upgrade is in
          a post-control-plane state (e.g. KUBE_UPGRADING_KUBELETS)
        """
        self.create_host("controller-0", aio=True)

        release = "starlingx-24.03.1"
        strategy = self.create_sw_deploy_strategy(
            kube_upgrade_version="v1.29.0",
            nfvi_upgrade=nfvi.objects.v1.Upgrade(
                release,
                MOCK_METAPACKAGES,
                {
                    "state": "deploying",
                    "reboot_required": True,
                    "sw_version": MAJOR_RELEASE_UPGRADE,
                },
                None,
                None,
            ),
        )

        strategy.nfvi_kube_upgrade = nfvi.objects.v1.KubeUpgrade(
            state=KUBE_UPGRADE_STATE.KUBE_UPGRADING_KUBELETS,
            from_version="v1.28.0",
            to_version="v1.29.0",
        )
        strategy.nfvi_kube_versions_list = []
        strategy.nfvi_kube_host_upgrade_list = []

        fake_upgrade_obj = SwUpgrade()
        strategy.sw_update_obj = fake_upgrade_obj
        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertEqual(common_strategy.STRATEGY_STATE.BUILD_FAILED, strategy._state)
        self.assertEqual(
            common_strategy.STRATEGY_PHASE_RESULT.FAILED, strategy.build_phase.result
        )
        expected_reason = (
            "Kubernetes upgrade is past the control plane "
            f"phase (state={KUBE_UPGRADE_STATE.KUBE_UPGRADING_KUBELETS}). "
            "Cannot proceed with sw-upgrade strategy."
        )
        self.assertEqual(expected_reason, strategy.build_phase.result_reason)


class TestSwUpgradeCombinedKubeStrategy(BaseSwUpgradeStrategy):
    """Tests for SwUpgradeStrategy with kube_upgrade_version set (combined strategy)."""

    RELEASE = "starlingx-24.03.1"
    KUBE_VER = _COMBINED_TO_KUBE

    def setUp(self):
        super().setUp()
        self.create_host("controller-0", aio=True)
        self.fake_upgrade_obj = SwUpgrade()
        self.strategy = self._create_combined_strategy()
        self.strategy.sw_update_obj = self.fake_upgrade_obj
        self.fake_upgrade_obj._strategy = self.strategy

    def _create_combined_strategy(
        self,
        kube_upgrade_version=None,
        nfvi_upgrade=None,
        nfvi_kube_upgrade=None,
        kube_versions_list=None,
        kube_hosts_list=None,
        single_controller=True,
        rollback=False,
        delete=False,
    ):
        """Create a SwUpgradeStrategy with kube_upgrade_version populated.

        Populates the mixin query results that would normally come from the
        build-phase query steps, so build_complete can be called directly.
        """
        if kube_upgrade_version is None:
            kube_upgrade_version = self.KUBE_VER

        strategy = SwUpgradeStrategy(
            uuid=str(uuid.uuid4()),
            controller_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            storage_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.IGNORE,
            max_parallel_worker_hosts=10,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            alarm_restrictions=SW_UPDATE_ALARM_RESTRICTION.STRICT,
            release=self.RELEASE,
            rollback=rollback,
            delete=delete,
            cleanup=False,
            snapshot=False,
            kube_upgrade_version=kube_upgrade_version,
            ignore_alarms=[],
            single_controller=single_controller,
        )

        if nfvi_upgrade is None:
            nfvi_upgrade = _make_nfvi_upgrade(self.RELEASE, state="available")
        strategy.nfvi_upgrade = nfvi_upgrade

        # Populate mixin fields that the build query steps would normally fill
        strategy.nfvi_kube_upgrade = nfvi_kube_upgrade
        strategy.nfvi_kube_versions_list = (
            kube_versions_list
            if kube_versions_list is not None
            else _COMBINED_KUBE_VERSIONS_LIST
        )
        strategy.nfvi_kube_host_upgrade_list = (
            kube_hosts_list if kube_hosts_list is not None else []
        )

        return strategy

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_no_existing_kube_upgrade_has_kube_stages_before_sw_deploy(self):
        """Test combined strategy with no existing kube upgrade.

        Verify:
        - apply phase begins with sw-system-deploy-init (kube_version injected)
        - kube upgrade stages follow: start, download-images, pre-app-update,
          networking, storage, first-control-plane
        - no kube-host-cordon stage (suppressed for combined strategy)
        - no kube-upgrade-kubelet stages (deferred to unlock after sw-deploy)
        - sw-deploy stages follow the kube stages
        """
        self.strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertFalse(self.strategy.is_build_failed())

        stage_names = [s.name for s in self.strategy.apply_phase.stages]

        # sw-system-deploy-init must be first
        self.assertEqual(stage_names[0], "sw-system-deploy-init")

        # kube upgrade stages must appear before sw-upgrade-start
        kube_start_idx = stage_names.index("kube-upgrade-start")
        sw_start_idx = stage_names.index("sw-upgrade-start")
        self.assertLess(kube_start_idx, sw_start_idx)

        # All expected kube control-plane stages must be present
        for expected in [
            "kube-upgrade-start",
            "kube-upgrade-download-images",
            "kube-pre-application-update",
            "kube-upgrade-networking",
            "kube-upgrade-storage",
            "kube-upgrade-first-control-plane %s" % self.KUBE_VER,
        ]:
            self.assertIn(expected, stage_names, "Missing stage: %s" % expected)

        self.assertNotIn("kube-host-cordon", stage_names)
        self.assertNotIn("kube-host-uncordon", stage_names)

        kubelet_stages = [s for s in stage_names if "kubelet" in s]
        self.assertEqual(
            [],
            kubelet_stages,
            "Kubelet stages should be deferred in combined strategy",
        )

        sw_update_testcase.validate_strategy_persists(self.strategy)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_duplex_builds_sequential_sw_then_kube(self):
        """Test combined strategy on duplex builds sequential phases.

        On duplex, --kube-upgrade runs full sw-deploy first, then full
        kube-upgrade (including control-planes for both controllers). Verify:
        - Build succeeds (no longer rejected)
        - sw-deploy stages come before kube-upgrade stages
        - No sw-system-deploy-init (simplex-only)
        - Both first and second control-plane stages present
        - No end stages without --delete (deferred to --cleanup)
        - No kube-host-cordon (simplex-only)
        """
        self.create_host("controller-1", aio=True)

        strategy = self._create_combined_strategy(single_controller=False)
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertFalse(strategy.is_build_failed())

        stage_names = [s.name for s in strategy.apply_phase.stages]

        # sw-deploy stages must come before kube-upgrade stages
        sw_start_idx = stage_names.index("sw-upgrade-start")
        sw_complete_idx = stage_names.index("sw-upgrade-complete")
        kube_start_idx = stage_names.index("kube-upgrade-start")
        self.assertLess(sw_start_idx, kube_start_idx)
        self.assertLess(sw_complete_idx, kube_start_idx)

        # kube-wait-upgrade-healthy must appear between sw-deploy and kube-upgrade
        self.assertIn("kube-wait-upgrade-healthy", stage_names)
        pods_ready_idx = stage_names.index("kube-wait-upgrade-healthy")
        self.assertLess(sw_complete_idx, pods_ready_idx)
        self.assertLess(pods_ready_idx, kube_start_idx)

        # No sw-system-deploy-init (duplex does not use it)
        self.assertNotIn("sw-system-deploy-init", stage_names)

        # kube-host-cordon is simplex-only
        self.assertNotIn("kube-host-cordon", stage_names)

        # Both control planes present (duplex)
        self.assertIn(
            "kube-upgrade-first-control-plane %s" % self.KUBE_VER, stage_names
        )
        self.assertIn(
            "kube-upgrade-second-control-plane %s" % self.KUBE_VER, stage_names
        )

        # End stages NOT present without --delete (deferred to --cleanup)
        self.assertNotIn("kube-upgrade-complete", stage_names)
        self.assertNotIn("kube-post-application-update", stage_names)
        self.assertNotIn("kube-upgrade-cleanup", stage_names)

        sw_update_testcase.validate_strategy_persists(strategy)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_resume_after_kube_upgrade_started_skips_start_stage(self):
        """Test combined strategy resumes correctly when kube upgrade already started.

        Verify:
        - kube-upgrade-start stage is skipped
        - resumes at kube-upgrade-download-images
        - sw-deploy stages still follow
        """
        nfvi_kube_upgrade = nfvi.objects.v1.KubeUpgrade(
            state=KUBE_UPGRADE_STATE.KUBE_UPGRADE_STARTED,
            from_version=_COMBINED_FROM_KUBE,
            to_version=_COMBINED_TO_KUBE,
        )

        strategy = self._create_combined_strategy(nfvi_kube_upgrade=nfvi_kube_upgrade)
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertFalse(strategy.is_build_failed())

        stage_names = [s.name for s in strategy.apply_phase.stages]

        self.assertNotIn("kube-upgrade-start", stage_names)
        self.assertIn("kube-upgrade-download-images", stage_names)
        self.assertIn("sw-upgrade-start", stage_names)

        sw_update_testcase.validate_strategy_persists(strategy)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_resume_after_kube_upgraded_first_master_skips_early_stages(self):
        """Test combined strategy resumes from KUBE_UPGRADED_FIRST_MASTER.

        Verify:
        - start, download-images, pre-app-update, networking, storage stages skipped
        - resumes at second-control-plane (simplex: skipped) or directly at sw-deploy
        - no kubelet stages
        """
        nfvi_kube_upgrade = nfvi.objects.v1.KubeUpgrade(
            state=KUBE_UPGRADE_STATE.KUBE_UPGRADED_FIRST_MASTER,
            from_version=_COMBINED_FROM_KUBE,
            to_version=_COMBINED_TO_KUBE,
        )

        strategy = self._create_combined_strategy(nfvi_kube_upgrade=nfvi_kube_upgrade)
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertFalse(strategy.is_build_failed())

        stage_names = [s.name for s in strategy.apply_phase.stages]

        # Early kube stages must be absent
        for skipped in [
            "kube-upgrade-start",
            "kube-upgrade-download-images",
            "kube-pre-application-update",
            "kube-upgrade-networking",
            "kube-upgrade-storage",
        ]:
            self.assertNotIn(skipped, stage_names)

        # sw-deploy stages must still be present
        self.assertIn("sw-upgrade-start", stage_names)
        # No kubelet stages
        self.assertFalse(any("kubelet" in s for s in stage_names))

        sw_update_testcase.validate_strategy_persists(strategy)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_post_control_plane_kube_state_fails_build(self):
        """Test BUILD_FAILED when kube upgrade is past the control-plane phase.

        Covers all states in POST_CONTROL_PLANE_STATES defined in
        _build_complete_normal. Each state must cause BUILD_FAILED with a
        reason that identifies the offending state.
        """
        post_control_plane_states = [
            KUBE_UPGRADE_STATE.KUBE_UPGRADING_KUBELETS,
            KUBE_UPGRADE_STATE.KUBE_HOST_UNCORDON,
            KUBE_UPGRADE_STATE.KUBE_HOST_UNCORDON_FAILED,
            KUBE_UPGRADE_STATE.KUBE_HOST_UNCORDON_COMPLETE,
            KUBE_UPGRADE_STATE.KUBE_UPGRADE_COMPLETE,
            KUBE_UPGRADE_STATE.KUBE_POST_UPDATING_APPS,
            KUBE_UPGRADE_STATE.KUBE_POST_UPDATING_APPS_FAILED,
            KUBE_UPGRADE_STATE.KUBE_POST_UPDATED_APPS,
        ]

        for state in post_control_plane_states:
            with self.subTest(state=state):
                nfvi_kube_upgrade = nfvi.objects.v1.KubeUpgrade(
                    state=state,
                    from_version=_COMBINED_FROM_KUBE,
                    to_version=_COMBINED_TO_KUBE,
                )

                strategy = self._create_combined_strategy(
                    nfvi_kube_upgrade=nfvi_kube_upgrade
                )
                strategy.sw_update_obj = self.fake_upgrade_obj

                strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

                self.assertEqual(
                    common_strategy.STRATEGY_STATE.BUILD_FAILED,
                    strategy._state,
                    "Expected BUILD_FAILED for state=%s" % state,
                )
                self.assertIn(
                    "past the control plane",
                    strategy.build_phase.result_reason,
                )
                self.assertIn(state, strategy.build_phase.result_reason)

                # Reset host table for next subTest iteration
                self._host_table.clear()
                self.create_host("controller-0", aio=True)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_active_alarms_fail_build(self):
        """Test BUILD_FAILED when active alarms are present.

        Verify:
        - _nfvi_alarms populated with a non-ignored alarm causes BUILD_FAILED
        - result_reason contains 'active alarms present' and the alarm id
        """
        # Inject an alarm that is NOT in the ignore list
        self.strategy._nfvi_alarms = [_make_nfvi_alarm(alarm_id="400.001")]

        self.strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertEqual(
            common_strategy.STRATEGY_STATE.BUILD_FAILED, self.strategy._state
        )
        self.assertIn("active alarms present", self.strategy.build_phase.result_reason)
        self.assertIn("400.001", self.strategy.build_phase.result_reason)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_kube_already_upgraded_fails_build(self):
        """Test BUILD_FAILED when the target kube version is already active.

        Verify:
        - nfvi_kube_upgrade is None (no upgrade in progress)
        - target version is already 'active' in kube_versions_list
        - result is BUILD_FAILED with reason 'Kubernetes is already upgraded to'
        """
        strategy = self._create_combined_strategy(
            nfvi_kube_upgrade=None,
            kube_versions_list=_COMBINED_KUBE_VERSIONS_ALREADY_UPGRADED,
        )
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertEqual(common_strategy.STRATEGY_STATE.BUILD_FAILED, strategy._state)
        self.assertIn(
            "Kubernetes is already upgraded to",
            strategy.build_phase.result_reason,
        )
        self.assertIn(self.KUBE_VER, strategy.build_phase.result_reason)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_invalid_kube_to_version_fails_build(self):
        """Test BUILD_FAILED when kube_upgrade_version is not in kube_versions_list.

        Verify:
        - kube_upgrade_version points to a version absent from nfvi_kube_versions_list
        - result is BUILD_FAILED with reason 'Invalid to_version value'
        """
        strategy = self._create_combined_strategy(
            kube_upgrade_version="v9.99.99",  # not in _COMBINED_KUBE_VERSIONS_LIST
        )
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertEqual(common_strategy.STRATEGY_STATE.BUILD_FAILED, strategy._state)
        self.assertIn("Invalid to_version value", strategy.build_phase.result_reason)
        self.assertIn("v9.99.99", strategy.build_phase.result_reason)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_kube_upgrade_invalid_resume_state_fails_build(self):
        """Test BUILD_FAILED when kube upgrade is in an unresumable state.

        Verify:
        - a kube upgrade state not present in RESUME_STATE causes BUILD_FAILED
        - result_reason contains 'Unable to resume kube upgrade from state'
        """
        # KUBE_UPGRADING_FIRST_MASTER is a transient in-progress state that
        # is not a key in RESUME_STATE (only the *_FAILED and *_DONE variants are)
        nfvi_kube_upgrade = nfvi.objects.v1.KubeUpgrade(
            state=KUBE_UPGRADE_STATE.KUBE_UPGRADING_FIRST_MASTER,
            from_version=_COMBINED_FROM_KUBE,
            to_version=_COMBINED_TO_KUBE,
        )

        strategy = self._create_combined_strategy(nfvi_kube_upgrade=nfvi_kube_upgrade)
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertEqual(common_strategy.STRATEGY_STATE.BUILD_FAILED, strategy._state)
        self.assertIn(
            "Unable to resume kube upgrade from state",
            strategy.build_phase.result_reason,
        )

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_delete_true_appends_kube_and_deploy_cleanup_stages(self):
        """Test that delete=True with kube_upgrade_version appends cleanup stages.

        Verify apply phase ends with, in order:
          kube-upgrade-complete → sw-deploy-delete → sw-system-deploy-delete
        """
        strategy = self._create_combined_strategy(delete=True)
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertFalse(strategy.is_build_failed())

        stage_names = [s.name for s in strategy.apply_phase.stages]

        self.assertIn("kube-upgrade-complete", stage_names)
        self.assertIn("sw-deploy-delete", stage_names)
        self.assertIn("sw-system-deploy-delete", stage_names)

        kube_complete_idx = stage_names.index("kube-upgrade-complete")
        sw_delete_idx = stage_names.index("sw-deploy-delete")
        sys_delete_idx = stage_names.index("sw-system-deploy-delete")

        self.assertLess(kube_complete_idx, sw_delete_idx)
        self.assertLess(sw_delete_idx, sys_delete_idx)

        sw_update_testcase.validate_strategy_persists(strategy)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_delete_false_omits_cleanup_stages(self):
        """Test that delete=False omits kube-upgrade-complete and deploy-delete stages.

        Verify:
        - kube-upgrade-complete is absent (only added when delete=True)
        - sw-deploy-delete is absent
        - sw-system-deploy-delete is absent
        """
        self.strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertFalse(self.strategy.is_build_failed())

        stage_names = [s.name for s in self.strategy.apply_phase.stages]

        self.assertNotIn("kube-upgrade-complete", stage_names)
        self.assertNotIn("sw-deploy-delete", stage_names)
        self.assertNotIn("sw-system-deploy-delete", stage_names)

        sw_update_testcase.validate_strategy_persists(self.strategy)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_duplex_delete_true_appends_deploy_cleanup_stages(self):
        """Test duplex combined + delete=True appends cleanup after kube stages.

        On duplex with --delete, _build_kube_upgrade_stages adds
        kube-upgrade-complete, kube-post-application-update, and
        kube-upgrade-cleanup exactly once, followed by sw-deploy-delete.
        sw-system-deploy-delete is NOT added (simplex-only).
        """
        self.create_host("controller-1", aio=True)

        strategy = self._create_combined_strategy(single_controller=False, delete=True)
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertFalse(strategy.is_build_failed())

        stage_names = [s.name for s in strategy.apply_phase.stages]

        # Full kube cleanup included via _build_kube_upgrade_stages
        self.assertIn("kube-upgrade-complete", stage_names)
        self.assertIn("kube-upgrade-cleanup", stage_names)

        # End stages must appear exactly once (no duplication)
        self.assertEqual(stage_names.count("kube-upgrade-complete"), 1)
        self.assertEqual(stage_names.count("kube-post-application-update"), 1)
        self.assertEqual(stage_names.count("kube-upgrade-cleanup"), 1)

        # sw-deploy-delete appended after kube cleanup
        self.assertIn("sw-deploy-delete", stage_names)

        # sw-system-deploy-delete is simplex-only
        self.assertNotIn("sw-system-deploy-delete", stage_names)

        kube_cleanup_idx = stage_names.index("kube-upgrade-cleanup")
        sw_delete_idx = stage_names.index("sw-deploy-delete")
        self.assertLess(kube_cleanup_idx, sw_delete_idx)

        sw_update_testcase.validate_strategy_persists(strategy)

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_combined_system_deploy_init_is_first_stage(self):
        """Test that sw-system-deploy-init is the very first apply stage.

        Verify:
        - stage name is 'sw-system-deploy-init'
        - it contains a single 'sw-system-deploy-init' step
        - it precedes all kube and sw-deploy stages
        """
        self.strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertFalse(self.strategy.is_build_failed())

        apply_phase = self.strategy.apply_phase.as_dict()
        first_stage = apply_phase["stages"][0]

        self.assertEqual("sw-system-deploy-init", first_stage["name"])
        self.assertEqual(1, first_stage["total_steps"])
        self.assertEqual("sw-system-deploy-init", first_stage["steps"][0]["name"])

        sw_update_testcase.validate_strategy_persists(self.strategy)

    def test_combined_rollback_with_kube_version_fails_at_build(self):
        """Test that rollback=True combined with kube_upgrade_version is rejected.

        The rejection happens in build() before build_complete is ever called.
        Verify:
        - strategy state is BUILD_FAILED immediately after build()
        - result_reason contains 'Cannot set both kube_upgrade and rollback'
        """
        strategy = self._create_combined_strategy(
            rollback=True,
            nfvi_upgrade=_make_nfvi_upgrade(self.RELEASE, state="deploying"),
        )
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build()

        self.assertEqual(common_strategy.STRATEGY_STATE.BUILD_FAILED, strategy._state)
        self.assertIn(
            "Cannot set both kube_upgrade and rollback",
            strategy.build_phase.result_reason,
        )

    def test_combined_is_combined_strategy_truthy_when_kube_version_set(self):
        """Test _is_combined_strategy() truthy on simplex with kube_version set.

        Verify:
        - _is_combined_strategy() returns a truthy value
        - kube mixin attribute _nfvi_kube_upgrade is initialized
        """
        strategy = self._create_combined_strategy(
            kube_upgrade_version="v1.30.6", single_controller=True
        )

        self.assertTrue(strategy._is_combined_strategy())
        self.assertTrue(hasattr(strategy, "_nfvi_kube_upgrade"))

    def test_combined_is_combined_strategy_falsy_on_duplex(self):
        """Test _is_combined_strategy() is falsy on duplex even with kube_version set.

        On duplex, the strategy runs sequential (not interleaved), so
        _is_combined_strategy() must return False.
        """
        self.create_host("controller-1", aio=True)

        strategy = self._create_combined_strategy(
            kube_upgrade_version="v1.30.6", single_controller=False
        )

        self.assertFalse(strategy._is_combined_strategy())

    def test_combined_is_combined_strategy_falsy_when_kube_version_none(self):
        """Test _is_combined_strategy() is falsy when kube_upgrade_version is None.

        Verify:
        - _kube_upgrade_version is None
        - _is_combined_strategy() returns a falsy value
        - kube mixin attribute _nfvi_kube_upgrade is NOT initialized
        """
        strategy = self.create_sw_deploy_strategy(
            single_controller=True,
            kube_upgrade_version=None,
        )

        self.assertIsNone(strategy._kube_upgrade_version)
        self.assertFalse(strategy._is_combined_strategy())
        self.assertFalse(hasattr(strategy, "_nfvi_kube_upgrade"))

    def test_is_kube_upgrade_active_false_without_strategy(self):
        """Test _is_kube_upgrade_active returns False when no strategy is attached."""
        fake_upgrade_obj = SwUpgrade()
        # _strategy is None by default after __init__
        self.assertFalse(fake_upgrade_obj._is_kube_upgrade_active())

    def test_is_kube_upgrade_active_false_without_kube_version(self):
        """Test _is_kube_upgrade_active returns False when no kube version is set.

        Covers the non-combined sw-deploy path where ``kube_to_version`` is
        None, so the helper short-circuits before inspecting the apply phase.
        """
        fake_upgrade_obj = SwUpgrade()
        fake_strategy = mock.MagicMock()
        fake_strategy.kube_to_version = None
        fake_upgrade_obj._strategy = fake_strategy

        self.assertFalse(fake_upgrade_obj._is_kube_upgrade_active())

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_is_kube_upgrade_active_matches_kube_stage_names(self):
        """Test _is_kube_upgrade_active agrees with stage names across apply phase.

        Regression test: previously this method compared ``stage.name`` against
        the sysinv KUBE_UPGRADE_STATE values (e.g. "upgrade-started"), which
        never overlap with strategy stage names ("kube-upgrade-start" etc.),
        so the helper always returned False once past its early guard. As a
        consequence the alarm/event context switch in
        ``SwUpgrade.alarm_type``/``event_id``/``nfvi_update`` was unreachable
        and a combined strategy raised the sw-upgrade alarm/event for every
        kube stage.

        This test drives the apply-phase cursor across every stage of a
        combined strategy and asserts the helper returns True iff the stage
        belongs to the kube-upgrade workflow.
        """
        self.strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(self.strategy.is_build_failed())

        apply_phase = self.strategy.apply_phase
        self.assertGreater(len(apply_phase.stages), 0)

        for index, stage in enumerate(apply_phase.stages):
            # current_stage is a read-only property backed by _current_stage;
            # poking the private attribute is the pragmatic way to drive the
            # cursor in a unit test without executing the strategy.
            apply_phase._current_stage = index
            active = self.fake_upgrade_obj._is_kube_upgrade_active()

            # A kube-upgrade stage starts with "kube-" but is not part of the
            # kube-rootca-update strategy (which has its own alarm/event ids).
            is_kube_upgrade_stage = stage.name.startswith(
                "kube-"
            ) and not stage.name.startswith("kube-rootca-")

            self.assertEqual(
                is_kube_upgrade_stage,
                bool(active),
                "_is_kube_upgrade_active() returned %s for stage '%s', "
                "expected %s" % (bool(active), stage.name, is_kube_upgrade_stage),
            )

    def test_is_kube_upgrade_active_false_when_apply_phase_finished(self):
        """Test _is_kube_upgrade_active returns False past the last stage.

        Covers the boundary where ``apply_phase.current_stage`` has been
        advanced past the final stage (e.g. between strategy completion and
        teardown).
        """
        self.strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(self.strategy.is_build_failed())

        # Simulate the apply phase having advanced past the final stage.
        self.strategy.apply_phase._current_stage = len(self.strategy.apply_phase.stages)

        self.assertFalse(self.fake_upgrade_obj._is_kube_upgrade_active())

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_is_abortable_false_during_kube_stages_on_duplex(self):
        """Test is_abortable returns False during kube upgrade stages on duplex.

        On duplex combined strategy, abort must be blocked when the current
        stage is a kube upgrade stage (matching KUBE_STAGE_PREFIXES).
        """
        self.create_host("controller-1", aio=True)

        strategy = self._create_combined_strategy(single_controller=False)
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(strategy.is_build_failed())

        # Set strategy to applying state
        strategy._state = common_strategy.STRATEGY_STATE.APPLYING

        # Find a kube stage and set it as current
        from nfv_vim.strategy._strategy_stages import KUBE_STAGE_PREFIXES

        for index, stage in enumerate(strategy.apply_phase.stages):
            if any(
                stage.name.startswith(prefix.value) for prefix in KUBE_STAGE_PREFIXES
            ):
                strategy.apply_phase._current_stage = index
                self.assertFalse(
                    strategy.is_abortable(),
                    "Expected is_abortable()=False during kube stage '%s'" % stage.name,
                )
                return

        self.fail("No kube upgrade stage found in apply phase")

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_is_abortable_true_during_sw_deploy_stages_on_duplex(self):
        """Test is_abortable returns True during sw-deploy stages on duplex.

        Even on duplex combined strategy, abort should remain allowed during
        the sw-deploy portion of the strategy.
        """
        self.create_host("controller-1", aio=True)

        strategy = self._create_combined_strategy(single_controller=False)
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(strategy.is_build_failed())

        # Set strategy to applying state
        strategy._state = common_strategy.STRATEGY_STATE.APPLYING

        # Find a non-kube stage (sw-deploy stage) and set it as current
        from nfv_vim.strategy._strategy_stages import KUBE_STAGE_PREFIXES

        for index, stage in enumerate(strategy.apply_phase.stages):
            if not any(
                stage.name.startswith(prefix.value) for prefix in KUBE_STAGE_PREFIXES
            ):
                strategy.apply_phase._current_stage = index
                self.assertTrue(
                    strategy.is_abortable(),
                    "Expected is_abortable()=True during sw-deploy stage '%s'"
                    % stage.name,
                )
                return

        self.fail("No sw-deploy stage found in apply phase")

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_is_abortable_true_during_kube_stages_on_simplex(self):
        """Test is_abortable delegates to parent on simplex combined strategy.

        Simplex systems should not block abort during kube stages because
        the restriction only applies to duplex.
        """
        strategy = self._create_combined_strategy(single_controller=True)
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(strategy.is_build_failed())

        # Set strategy to applying state
        strategy._state = common_strategy.STRATEGY_STATE.APPLYING

        # Find a kube stage and set it as current
        from nfv_vim.strategy._strategy_stages import KUBE_STAGE_PREFIXES

        for index, stage in enumerate(strategy.apply_phase.stages):
            if any(
                stage.name.startswith(prefix.value) for prefix in KUBE_STAGE_PREFIXES
            ):
                strategy.apply_phase._current_stage = index
                self.assertTrue(
                    strategy.is_abortable(),
                    "Expected is_abortable()=True on simplex during kube stage '%s'"
                    % stage.name,
                )
                return

        self.fail("No kube upgrade stage found in apply phase")

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_is_abortable_true_on_duplex_without_kube_version(self):
        """Test is_abortable delegates to parent on non-combined duplex strategy.

        When kube_upgrade_version is not set, the is_abortable override
        should not interfere and just delegate to the parent class.
        """
        self.create_host("controller-1", aio=True)

        strategy = self.create_sw_deploy_strategy(
            single_controller=False,
            kube_upgrade_version=None,
        )
        strategy.sw_update_obj = self.fake_upgrade_obj
        strategy.nfvi_upgrade = _make_nfvi_upgrade(
            MAJOR_RELEASE_UPGRADE, state="available"
        )

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(strategy.is_build_failed())

        # Set strategy to applying state
        strategy._state = common_strategy.STRATEGY_STATE.APPLYING
        strategy.apply_phase._current_stage = 0

        self.assertTrue(
            strategy.is_abortable(),
            "Expected is_abortable()=True on duplex without kube_upgrade_version",
        )

    @mock.patch(
        "nfv_vim.strategy._strategy.get_local_host_name",
        sw_update_testcase.fake_host_name_controller_0,
    )
    def test_is_abortable_all_kube_stages_blocked_on_duplex(self):
        """Test every kube upgrade stage is non-abortable on duplex combined.

        Drives the apply-phase cursor across all stages and asserts that
        is_abortable() returns False for every kube stage and True for
        every non-kube stage.
        """
        self.create_host("controller-1", aio=True)

        strategy = self._create_combined_strategy(single_controller=False, delete=True)
        strategy.sw_update_obj = self.fake_upgrade_obj

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")
        self.assertFalse(strategy.is_build_failed())

        # Set strategy to applying state
        strategy._state = common_strategy.STRATEGY_STATE.APPLYING

        from nfv_vim.strategy._strategy_stages import KUBE_STAGE_PREFIXES

        for index, stage in enumerate(strategy.apply_phase.stages):
            strategy.apply_phase._current_stage = index
            is_kube_stage = any(
                stage.name.startswith(prefix.value) for prefix in KUBE_STAGE_PREFIXES
            )

            if is_kube_stage:
                self.assertFalse(
                    strategy.is_abortable(),
                    "Expected is_abortable()=False for kube stage '%s'" % stage.name,
                )
            else:
                self.assertTrue(
                    strategy.is_abortable(),
                    "Expected is_abortable()=True for non-kube stage '%s'" % stage.name,
                )


@mock.patch(
    "nfv_vim.event_log._instance._event_issue", sw_update_testcase.fake_event_issue
)
@mock.patch("nfv_vim.objects._sw_update.SwUpdate.save", sw_update_testcase.fake_save)
@mock.patch(
    "nfv_vim.objects._sw_update.timers.timers_create_timer",
    sw_update_testcase.fake_timer,
)
@mock.patch(
    "nfv_vim.nfvi.nfvi_compute_plugin_disabled",
    sw_update_testcase.fake_nfvi_compute_plugin_disabled,
)
class TestWaitKubernetesUpgradeHealthy(sw_update_testcase.SwUpdateStrategyTestCase):
    """Unit tests for the WaitKubernetesUpgradeHealthy."""

    def setUp(self):
        super().setUp()
        from nfv_vim.strategy.steps.kube_upgrade_steps import (
            WaitKubernetesUpgradeHealthy,
        )

        self.step = WaitKubernetesUpgradeHealthy(
            timeout_in_secs=180, first_query_delay_in_secs=20
        )
        self.mock_stage = mock.MagicMock()
        self.step.stage = self.mock_stage

    def _send_callback(self, response):
        """Drive the coroutine callback with the given response."""

        callback = self.step._query_health_callback()
        try:
            callback.send(response)
        except StopIteration:
            pass

    def test_health_no_failures_completes_step_successfully(self):
        """Step completes with SUCCESS when health data has no failures."""

        self._send_callback(
            {
                "completed": True,
                "result-data": {"System Health": {"All hosts are provisioned": ["OK"]}},
            }
        )

        self.mock_stage.step_complete.assert_called_once_with(
            common_strategy.STRATEGY_STEP_RESULT.SUCCESS, ""
        )

    def test_query_failure_fails_step(self):
        """Step fails when the query itself fails."""

        self._send_callback({"completed": False, "reason": "connection error"})

        self.mock_stage.step_complete.assert_called_once_with(
            common_strategy.STRATEGY_STEP_RESULT.FAILED, "connection error"
        )

    def test_handle_event_triggers_query_after_delay(self):
        """HOST_AUDIT triggers query after first_query_delay_in_secs."""

        from nfv_common import timers
        from nfv_vim.strategy._strategy_defs import STRATEGY_EVENT

        with mock.patch.object(
            timers, "get_monotonic_timestamp_in_ms", return_value=1000
        ):
            self.step.handle_event(STRATEGY_EVENT.HOST_AUDIT)

        with mock.patch.object(
            timers, "get_monotonic_timestamp_in_ms", return_value=22000
        ):
            with mock.patch("nfv_vim.nfvi.nfvi_get_kube_upgrade_health") as mock_query:
                self.step.handle_event(STRATEGY_EVENT.HOST_AUDIT)
                mock_query.assert_called_once()

    def test_handle_event_does_not_trigger_query_before_delay(self):
        """HOST_AUDIT does not trigger query before first_query_delay_in_secs."""

        from nfv_common import timers
        from nfv_vim.strategy._strategy_defs import STRATEGY_EVENT

        with mock.patch.object(
            timers, "get_monotonic_timestamp_in_ms", return_value=1000
        ):
            self.step.handle_event(STRATEGY_EVENT.HOST_AUDIT)

        with mock.patch.object(
            timers, "get_monotonic_timestamp_in_ms", return_value=11000
        ):
            with mock.patch("nfv_vim.nfvi.nfvi_get_kube_upgrade_health") as mock_query:
                self.step.handle_event(STRATEGY_EVENT.HOST_AUDIT)
                mock_query.assert_not_called()

    def test_from_dict_roundtrip(self):
        """Step can be serialized and deserialized without data loss."""

        from nfv_vim.strategy.steps.kube_upgrade_steps import (
            WaitKubernetesUpgradeHealthy,
        )

        data = self.step.as_dict()
        new_step = object.__new__(WaitKubernetesUpgradeHealthy)
        new_step.from_dict(data)

        self.assertEqual(new_step._first_query_delay_in_secs, 20)
        self.assertEqual(new_step._wait_time, 0)
        self.assertFalse(new_step._query_inprogress)

    def test_timeout_returns_descriptive_reason(self):
        """Timeout provides a meaningful error message."""

        result, reason = self.step.timeout()
        self.assertEqual(result, common_strategy.STRATEGY_STEP_RESULT.TIMED_OUT)
        self.assertIn("did not become healthy", reason)

    def test_missing_result_data_fails_step(self):
        """Step fails when response is completed but result-data is missing."""

        self._send_callback({"completed": True})

        self.mock_stage.step_complete.assert_called_once_with(
            common_strategy.STRATEGY_STEP_RESULT.FAILED,
            "Kubernetes upgrade health check missing result-data",
        )

    def test_query_failure_with_empty_reason_uses_default_message(self):
        """Step fails with a descriptive message when reason is empty."""

        self._send_callback({"completed": False, "reason": ""})

        self.mock_stage.step_complete.assert_called_once_with(
            common_strategy.STRATEGY_STEP_RESULT.FAILED,
            "Unknown error while trying kubernetes upgrade health check, "
            "check /var/log/nfv-vim.log for more information.",
        )

    def test_query_failure_with_no_reason_uses_default_message(self):
        """Step fails with a descriptive message when reason key is absent."""

        self._send_callback({"completed": False})

        self.mock_stage.step_complete.assert_called_once_with(
            common_strategy.STRATEGY_STEP_RESULT.FAILED,
            "Unknown error while trying kubernetes upgrade health check, "
            "check /var/log/nfv-vim.log for more information.",
        )
