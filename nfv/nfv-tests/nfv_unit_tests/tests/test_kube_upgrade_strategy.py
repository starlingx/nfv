#
# Copyright (c) 2020-2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from unittest import mock
import uuid

from nfv_common import strategy as common_strategy
from nfv_vim import nfvi

from nfv_vim.nfvi.objects.v1 import KUBE_UPGRADE_STATE
from nfv_vim.nfvi.objects.v1 import KubeVersion
from nfv_vim.objects import KubeUpgrade
from nfv_vim.objects import SW_UPDATE_ALARM_RESTRICTION
from nfv_vim.objects import SW_UPDATE_APPLY_TYPE
from nfv_vim.objects import SW_UPDATE_INSTANCE_ACTION
from nfv_vim.strategy._strategy import KubeUpgradeStrategy

from nfv_unit_tests.tests import sw_update_testcase


FROM_KUBE_VERSION = '1.2.3'
MID_KUBE_VERSION = '1.2.4'
HIGH_KUBE_VERSION = '1.2.5'
DEFAULT_TO_VERSION = MID_KUBE_VERSION
FAKE_LOAD = '12.01'


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestBuildStrategy(sw_update_testcase.SwUpdateStrategyTestCase):

    def _create_kube_upgrade_strategy(self,
            sw_update_obj,
            controller_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            storage_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            max_parallel_worker_hosts=10,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            alarm_restrictions=SW_UPDATE_ALARM_RESTRICTION.STRICT,
            to_version=MID_KUBE_VERSION,
            single_controller=False,
            nfvi_kube_upgrade=None):
        """
        Create a kube upgrade strategy
        """
        strategy = KubeUpgradeStrategy(
            uuid=str(uuid.uuid4()),
            controller_apply_type=controller_apply_type,
            storage_apply_type=storage_apply_type,
            worker_apply_type=worker_apply_type,
            max_parallel_worker_hosts=max_parallel_worker_hosts,
            default_instance_action=default_instance_action,
            alarm_restrictions=alarm_restrictions,
            ignore_alarms=[],
            to_version=to_version,
            single_controller=single_controller
        )
        strategy.sw_update_obj = sw_update_obj  # this is a weakref
        strategy.nfvi_kube_upgrade = nfvi_kube_upgrade
        return strategy

    @mock.patch('nfv_common.strategy._strategy.Strategy._build')
    def test_kube_upgrade_strategy_build_steps(self, fake_build):
        """
        Verify build phase steps and stages for kube_upgrade strategy creation.
        """
        # setup a minimal host environment
        self.create_host('controller-0', aio=True)

        # construct the strategy. the update_obj MUST be declared here and not
        # in the create method, because it is a weakref and will be cleaned up
        # when it goes out of scope.
        update_obj = KubeUpgrade()
        strategy = self._create_kube_upgrade_strategy(update_obj)
        # The 'build' constructs a strategy that includes multiple queries
        # the results of those queries are not used until build_complete
        # mock away '_build', which invokes the build steps and their api calls
        fake_build.return_value = None
        strategy.build()

        # verify the build phase and steps
        build_phase = strategy.build_phase.as_dict()
        query_steps = [
            {'name': 'query-alarms'},
            {'name': 'query-kube-versions'},
            {'name': 'query-kube-upgrade'},
            {'name': 'kube-upgrade-cleanup-aborted'},
            {'name': 'query-kube-host-upgrade'},
        ]
        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'kube-upgrade-query',
                 'total_steps': len(query_steps),
                 'steps': query_steps,
                },
            ],
        }
        sw_update_testcase.validate_phase(build_phase, expected_results)


class SimplexKubeUpgradeMixin(object):
    FAKE_KUBE_HOST_UPGRADES_LIST = []

    # simplex sets the versions as available
    FAKE_KUBE_VERSIONS_LIST = [
        KubeVersion(
            FROM_KUBE_VERSION,  # kube_version
            'active',  # state
            True,  # target
            [],  # upgrade_from
            [],  # downgrade_to
            [],  # applied_patches
            []   # available_patches
        ),
        KubeVersion(
            MID_KUBE_VERSION,  # kube_version
            'available',  # state
            False,  # target
            [FROM_KUBE_VERSION],  # upgrade_from
            [],  # downgrade_to
            [],  # applied_patches
            []  # available_patches
        ),
        KubeVersion(
            HIGH_KUBE_VERSION,  # kube_version
            'available',  # state
            False,  # target
            [MID_KUBE_VERSION],  # upgrade_from
            [],  # downgrade_to
            [],  # applied_patches
            []  # available_patches
        ),
    ]

    def setUp(self):
        super(SimplexKubeUpgradeMixin, self).setUp()

    def is_simplex(self):
        return True

    def is_duplex(self):
        return False


class DuplexKubeUpgradeMixin(object):
    FAKE_KUBE_HOST_UPGRADES_LIST = []

    # duplex sets only one version as available
    FAKE_KUBE_VERSIONS_LIST = [
        KubeVersion(
            FROM_KUBE_VERSION,  # kube_version
            'active',  # state
            True,  # target
            [],  # upgrade_from
            [],  # downgrade_to
            [],  # applied_patches
            []   # available_patches
        ),
        KubeVersion(
            MID_KUBE_VERSION,  # kube_version
            'available',  # state
            False,  # target
            [FROM_KUBE_VERSION],  # upgrade_from
            [],  # downgrade_to
            [],  # applied_patches
            []  # available_patches
        ),
        KubeVersion(
            HIGH_KUBE_VERSION,  # kube_version
            'unavailable',  # state
            False,  # target
            [MID_KUBE_VERSION],  # upgrade_from
            [],  # downgrade_to
            [],  # applied_patches
            []  # available_patches
        ),
    ]

    def setUp(self):
        super(DuplexKubeUpgradeMixin, self).setUp()

    def is_simplex(self):
        return False

    def is_duplex(self):
        return True


class ApplyStageMixin(object):
    """This Mixin will not work unless combined with other mixins.
    HostMixin - to provide the kube host upgrade states
    """

    # override any of these prior to calling setup in classes that use mixin
    alarm_restrictions = SW_UPDATE_ALARM_RESTRICTION.STRICT
    max_parallel_worker_hosts = 10
    controller_apply_type = SW_UPDATE_APPLY_TYPE.SERIAL
    storage_apply_type = SW_UPDATE_APPLY_TYPE.SERIAL
    worker_apply_type = SW_UPDATE_APPLY_TYPE.SERIAL
    default_instance_action = SW_UPDATE_INSTANCE_ACTION.STOP_START

    # for multi-kube upgrade: 'to' and 'kube_versions' should be updated
    default_from_version = FROM_KUBE_VERSION
    default_to_version = MID_KUBE_VERSION
    # steps when performing control plane and kubelet upversion
    kube_versions = [MID_KUBE_VERSION, ]

    def setUp(self):
        super(ApplyStageMixin, self).setUp()

    def _create_kube_upgrade_obj(self, state, from_version, to_version):
        """Create a kube upgrade db object"""
        return nfvi.objects.v1.KubeUpgrade(state=state,
                                           from_version=from_version,
                                           to_version=to_version)

    def _create_built_kube_upgrade_strategy(self,
                                            sw_update_obj,
                                            to_version,
                                            single_controller=False,
                                            kube_upgrade=None,
                                            alarms_list=None,
                                            kube_versions_list=None,
                                            kube_hosts_list=None):
        """
        Create a kube upgrade strategy
        populate the API query results from the build steps
        """
        strategy = KubeUpgradeStrategy(
            uuid=str(uuid.uuid4()),
            controller_apply_type=self.controller_apply_type,
            storage_apply_type=self.storage_apply_type,
            worker_apply_type=self.worker_apply_type,
            max_parallel_worker_hosts=self.max_parallel_worker_hosts,
            default_instance_action=self.default_instance_action,
            alarm_restrictions=self.alarm_restrictions,
            ignore_alarms=[],
            to_version=to_version,
            single_controller=single_controller
        )
        strategy.sw_update_obj = sw_update_obj  # warning: this is a weakref
        strategy.nfvi_kube_upgrade = kube_upgrade

        # If any of the input lists are None, replace with defaults
        # this is done to prevent passing a list as a default

        if kube_versions_list is None:
            kube_versions_list = self.FAKE_KUBE_VERSIONS_LIST
        strategy.nfvi_kube_versions_list = kube_versions_list

        if kube_hosts_list is None:
            kube_hosts_list = self.FAKE_KUBE_HOST_UPGRADES_LIST
        strategy.nfvi_kube_host_upgrade_list = kube_hosts_list

        return strategy

    def _kube_upgrade_start_stage(self):
        return {
            'name': 'kube-upgrade-start',
            'total_steps': 1,
            'steps': [
                {'name': 'kube-upgrade-start',
                 'success_state': 'upgrade-started',
                 'fail_state': 'upgrade-starting-failed'},
            ],
        }

    def _kube_upgrade_download_images_stage(self):
        return {
            'name': 'kube-upgrade-download-images',
            'total_steps': 1,
            'steps': [
                {'name': 'kube-upgrade-download-images',
                 'success_state': 'downloaded-images',
                 'fail_state': 'downloading-images-failed'},
            ],
        }

    def _kube_host_cordon_stage(self, ver="N/A"):
        return {
            'name': 'kube-host-cordon',
            'total_steps': 1,
            'steps': [
                {'name': 'kube-host-cordon',
                 'success_state': 'cordon-complete',
                 'fail_state': 'cordon-failed'},
            ],
        }

    def _kube_host_uncordon_stage(self, ver="N/A"):
        return {
            'name': 'kube-host-uncordon',
            'total_steps': 1,
            'steps': [
                {'name': 'kube-host-uncordon',
                 'success_state': 'uncordon-complete',
                 'fail_state': 'uncordon-failed'},
            ],
        }

    def _kube_upgrade_first_control_plane_stage(self, ver):
        return {
            'name': 'kube-upgrade-first-control-plane %s' % ver,
            'total_steps': 1,
            'steps': [
                {'name': 'kube-host-upgrade-control-plane',
                 'success_state': 'upgraded-first-master',
                 'fail_state': 'upgrading-first-master-failed'},
            ],
        }

    def _kube_upgrade_second_control_plane_stage(self, ver):
        """This stage only executes on a duplex system"""
        return {
            'name': 'kube-upgrade-second-control-plane %s' % ver,
            'total_steps': 1,
            'steps': [
                {'name': 'kube-host-upgrade-control-plane',
                 'success_state': 'upgraded-second-master',
                 'fail_state': 'upgrading-second-master-failed'},
            ],
        }

    def _kube_upgrade_networking_stage(self):
        return {
            'name': 'kube-upgrade-networking',
            'total_steps': 1,
            'steps': [
                {'name': 'kube-upgrade-networking',
                 'success_state': 'upgraded-networking',
                 'fail_state': 'upgrading-networking-failed'},
            ],
        }

    def _kube_upgrade_storage_stage(self):
        return {
            'name': 'kube-upgrade-storage',
            'total_steps': 1,
            'steps': [
                {'name': 'kube-upgrade-storage',
                 'success_state': 'upgraded-storage',
                 'fail_state': 'upgrading-storage-failed'},
            ],
        }

    def _kube_upgrade_complete_stage(self):
        return {
            'name': 'kube-upgrade-complete',
            'total_steps': 1,
            'steps': [
                {'name': 'kube-upgrade-complete',
                 'success_state': 'upgrade-complete'},
            ],
        }

    def _kube_upgrade_cleanup_stage(self):
        return {
            'name': 'kube-upgrade-cleanup',
            'total_steps': 1,
            'steps': [
                {'name': 'kube-upgrade-cleanup'},
            ],
        }

    def _kube_upgrade_kubelet_controller_stage(self, host, ver, do_lock=True):
        """duplex needs to swact/lock/unlock whereas simplex does not"""
        if do_lock:
            steps = [
                {'name': 'query-alarms'},
                {'name': 'swact-hosts',
                 'entity_names': [host],
                 'entity_type': 'hosts', },
                {'name': 'lock-hosts',
                 'entity_names': [host],
                 'entity_type': 'hosts', },
                {'name': 'kube-host-upgrade-kubelet',
                 'entity_names': [host],
                 'entity_type': 'hosts', },
                {'name': 'system-stabilize', },
                {'name': 'unlock-hosts',
                 'entity_names': [host],
                 'entity_type': 'hosts', },
                {'name': 'wait-alarms-clear', },
            ]
        else:
            steps = [
                {'name': 'query-alarms'},
                {'name': 'kube-host-upgrade-kubelet',
                 'entity_names': [host],
                 'entity_type': 'hosts', },
                {'name': 'system-stabilize', },
            ]
        stage_name = "kube-upgrade-kubelet %s" % ver
        return {
            'name': stage_name,
            'total_steps': len(steps),
            'steps': steps,
        }

    def _kube_upgrade_kubelet_worker_stage(self,
                                           hosts,
                                           ver,
                                           do_lock=True,
                                           do_swact=False):
        steps = [{'name': 'query-alarms', }]
        if do_lock:
            if do_swact:  # only check for swacts if we are locking
                steps.append({'name': 'swact-hosts',
                              'entity_names': hosts,
                              'entity_type': 'hosts', })
            steps.append({'name': 'lock-hosts',
                          'entity_names': hosts,
                          'entity_type': 'hosts', })
        steps.append({'name': 'kube-host-upgrade-kubelet',
                      'entity_names': hosts,
                      'entity_type': 'hosts', })
        steps.append({'name': 'system-stabilize', })
        if do_lock:
            steps.append({'name': 'unlock-hosts',
                          'entity_names': hosts,
                           'entity_type': 'hosts', })
            steps.append({'name': 'wait-alarms-clear', })

        stage_name = "kube-upgrade-kubelet %s" % ver
        return {
            'name': stage_name,
            'total_steps': len(steps),
            'steps': steps,
        }

    def _kube_upgrade_kubelet_stages(self,
                                     ver,
                                     std_controller_list,
                                     aio_controller_list,
                                     worker_list):
        """This section will change as more host types are supported"""
        if worker_list is None:
            worker_list = []
        kubelet_stages = []
        for host_name in std_controller_list:
            kubelet_stages.append(
                self._kube_upgrade_kubelet_controller_stage(
                    host_name,
                    ver,
                    self.is_duplex()))  # lock is duplex only
        for host_name in aio_controller_list:
            kubelet_stages.append(
                self._kube_upgrade_kubelet_worker_stage(
                    [host_name],
                    ver,
                    do_lock=self.is_duplex(),  # lock is duplex only
                    do_swact=self.is_duplex()))  # swact only if we lock
        for sub_list in worker_list:
            # kubelet workers are lock but not controllers, so no swact
            kubelet_stages.append(
                self._kube_upgrade_kubelet_worker_stage(sub_list, ver, True, False))
        return kubelet_stages

    def validate_apply_phase(self, single_controller, kube_upgrade, stages):
        # sw_update_obj is a weak ref. it must be defined here
        update_obj = KubeUpgrade()

        # create a strategy for a system with no existing kube_upgrade
        strategy = self._create_built_kube_upgrade_strategy(
            update_obj,
            self.default_to_version,
            single_controller=single_controller,
            kube_upgrade=kube_upgrade)

        strategy.build_complete(common_strategy.STRATEGY_RESULT.SUCCESS, "")

        self.assertFalse(strategy.is_build_failed())
        self.assertEqual(strategy.build_phase.result_reason, "")

        apply_phase = strategy.apply_phase.as_dict()
        expected_results = {
            'total_stages': len(stages),
            'stages': stages
        }
        sw_update_testcase.validate_strategy_persists(strategy)
        sw_update_testcase.validate_phase(apply_phase, expected_results)

    def build_stage_list(self,
                         std_controller_list=None,
                         aio_controller_list=None,
                         worker_list=None,
                         storage_list=None,
                         add_start=True,
                         add_download=True,
                         add_networking=True,
                         add_storage=True,
                         add_cordon=True,
                         add_first_control_plane=True,
                         add_second_control_plane=True,
                         add_kubelets=True,
                         add_uncordon=True,
                         add_complete=True,
                         add_cleanup=True):
        """The order of the host_list determines the kubelets"""
        # We never add a second control plane on a simplex
        if self.is_simplex():
            add_second_control_plane = False
        # we do not support cordon and uncordon in duplex
        if self.is_duplex():
            add_cordon = False
            add_uncordon = False
        stages = []
        if add_start:
            stages.append(self._kube_upgrade_start_stage())
        if add_download:
            stages.append(self._kube_upgrade_download_images_stage())
        if add_networking:
            stages.append(self._kube_upgrade_networking_stage())
        if add_storage:
            stages.append(self._kube_upgrade_storage_stage())
        if add_cordon:
            stages.append(self._kube_host_cordon_stage())
        for ver in self.kube_versions:
            if add_first_control_plane:
                stages.append(self._kube_upgrade_first_control_plane_stage(ver))
            if add_second_control_plane:
                stages.append(self._kube_upgrade_second_control_plane_stage(ver))
            if add_kubelets:
                # there are no kubelets on storage
                stages.extend(self._kube_upgrade_kubelet_stages(ver,
                                                                std_controller_list,
                                                                aio_controller_list,
                                                                worker_list))
        if add_uncordon:
            stages.append(self._kube_host_uncordon_stage())
        if add_complete:
            stages.append(self._kube_upgrade_complete_stage())
        if add_cleanup:
            stages.append(self._kube_upgrade_cleanup_stage())
        return stages

    def test_no_existing_upgrade(self):
        """
        Test the kube_upgrade strategy creation for the hosts when there is
        no existing kube upgrade exists.
        A duplex env will have more steps than a simplex environment
        """
        kube_upgrade = None
        # default stage list includes all , however second plane is duplex only
        stages = self.build_stage_list(
            std_controller_list=self.std_controller_list,
            aio_controller_list=self.aio_controller_list,
            worker_list=self.worker_list,
            storage_list=self.storage_list)
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_upgrade_started(self):
        """
        Test the kube_upgrade strategy creation when the upgrade was created
        already (upgrade-started)
        The 'start stage should be skipped and the upgrade resumes at the
        'downloading images' stage
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADE_STARTED,
            self.default_from_version,
            self.default_to_version)
        # explicity bypass the start stage
        stages = self.build_stage_list(
            std_controller_list=self.std_controller_list,
            aio_controller_list=self.aio_controller_list,
            worker_list=self.worker_list,
            storage_list=self.storage_list,
            add_start=False)
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_upgrade_complete(self):
        """
        Test the kube_upgrade strategy creation when the upgrade had previously
        stopped after upgrade-completed.
        It is expected to resume at the cleanup stage
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADE_COMPLETE,
            self.default_from_version,
            self.default_to_version)
        # not using build_stage_list utility since the list of stages is small
        stages = [
            self._kube_upgrade_cleanup_stage(),
        ]
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)


class MultiApplyStageMixin(ApplyStageMixin):
    default_to_version = HIGH_KUBE_VERSION
    kube_versions = [MID_KUBE_VERSION, HIGH_KUBE_VERSION, ]

    def setUp(self):
        super(MultiApplyStageMixin, self).setUp()


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestSimplexApplyStrategy(sw_update_testcase.SwUpdateStrategyTestCase,
                               ApplyStageMixin,
                               SimplexKubeUpgradeMixin):
    def setUp(self):
        super(TestSimplexApplyStrategy, self).setUp()
        self.create_host('controller-0', aio=True)
        # AIO will be patched in the worker list
        self.std_controller_list = []
        # AIO kubelet phase does not process controller with the workers
        self.aio_controller_list = ['controller-0']
        self.worker_list = []
        self.storage_list = []

    def test_resume_after_starting_failed(self):
        """
        Test the kube_upgrade strategy creation when the upgrade had previously
        stopped with 'upgrade-starting-failed'
        It is expected to resume at the 'upgrade-starting' stage
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADE_STARTING_FAILED,
            self.default_from_version,
            self.default_to_version)
        stages = [
            self._kube_upgrade_start_stage(),
            self._kube_upgrade_download_images_stage(),
            self._kube_upgrade_networking_stage(),
            self._kube_upgrade_storage_stage(),
        ]
        if self.is_simplex():
            stages.append(self._kube_host_cordon_stage())
        for ver in self.kube_versions:
            stages.append(self._kube_upgrade_first_control_plane_stage(ver))
            stages.extend(self._kube_upgrade_kubelet_stages(
                ver,
                self.std_controller_list,
                self.aio_controller_list,
                self.worker_list))
        if self.is_simplex():
            stages.append(self._kube_host_uncordon_stage())
        stages.extend([
            self._kube_upgrade_complete_stage(),
            self._kube_upgrade_cleanup_stage(),
        ])
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_download_images_failed(self):
        """
        Test the kube_upgrade strategy creation when the upgrade had previously
        stopped with 'downloading-images-failed'
        It is expected to resume at the 'downloading images' stage
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADE_DOWNLOADING_IMAGES_FAILED,
            self.default_from_version,
            self.default_to_version)
        stages = [
            self._kube_upgrade_download_images_stage(),
            self._kube_upgrade_networking_stage(),
            self._kube_upgrade_storage_stage(),
        ]
        if self.is_simplex():
            stages.append(self._kube_host_cordon_stage())
        for ver in self.kube_versions:
            stages.append(self._kube_upgrade_first_control_plane_stage(ver))
            stages.extend(self._kube_upgrade_kubelet_stages(
                ver,
                self.std_controller_list,
                self.aio_controller_list,
                self.worker_list))
        if self.is_simplex():
            stages.append(self._kube_host_uncordon_stage())
        stages.extend([
            self._kube_upgrade_complete_stage(),
            self._kube_upgrade_cleanup_stage(),
        ])
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_download_images_succeeded(self):
        """
        Test the kube_upgrade strategy creation when the upgrade had previously
        stopped with 'downloaded-images'
        It is expected to resume at the 'first control plane' stage.
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADE_DOWNLOADED_IMAGES,
            self.default_from_version,
            self.default_to_version)
        stages = [
            self._kube_upgrade_networking_stage(),
            self._kube_upgrade_storage_stage(),
        ]
        if self.is_simplex():
            stages.append(self._kube_host_cordon_stage())
        for ver in self.kube_versions:
            stages.append(self._kube_upgrade_first_control_plane_stage(
                ver))
            stages.extend(self._kube_upgrade_kubelet_stages(
                ver,
                self.std_controller_list,
                self.aio_controller_list,
                self.worker_list))
        if self.is_simplex():
            stages.append(self._kube_host_uncordon_stage())
        stages.extend([
            self._kube_upgrade_complete_stage(),
            self._kube_upgrade_cleanup_stage(),
        ])
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_first_control_plane_failed(self):
        """
        Test the kube_upgrade strategy creation when there is only a simplex
        and the upgrade had previously failed during the first control plane.
        It is expected to resume and retry the 'first control plane' stage
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADING_FIRST_MASTER_FAILED,
            self.default_from_version,
            self.default_to_version)
        stages = []
        for ver in self.kube_versions:
            stages.append(self._kube_upgrade_first_control_plane_stage(
                ver))
            stages.extend(self._kube_upgrade_kubelet_stages(
                ver,
                self.std_controller_list,
                self.aio_controller_list,
                self.worker_list))
        if self.is_simplex():
            stages.append(self._kube_host_uncordon_stage())
        stages.extend([
            self._kube_upgrade_complete_stage(),
            self._kube_upgrade_cleanup_stage(),
        ])
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_first_control_plane_succeeded(self):
        """
        Test the kube_upgrade strategy creation when there is only a simplex
        and the upgrade had previously stopped after the first control plane.
        It is expected to resume at the second control plane stage in duplex
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADED_FIRST_MASTER,
            self.default_from_version,
            self.default_to_version)
        stages = []
        for ver in self.kube_versions:
            stages.extend(self._kube_upgrade_kubelet_stages(
                ver,
                self.std_controller_list,
                self.aio_controller_list,
                self.worker_list))
        if self.is_simplex():
            stages.append(self._kube_host_uncordon_stage())
        stages.extend([
            self._kube_upgrade_complete_stage(),
            self._kube_upgrade_cleanup_stage(),
        ])
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_networking_failed(self):
        """
        Test the kube_upgrade strategy creation when there is only a simplex
        and the upgrade had previously failed during networking.
        It is expected to retry and resume at the networking stage
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADING_NETWORKING_FAILED,
            self.default_from_version,
            self.default_to_version)
        stages = [
            self._kube_upgrade_networking_stage(),
            self._kube_upgrade_storage_stage()
        ]
        if self.is_simplex():
            stages.append(self._kube_host_cordon_stage())
        for ver in self.kube_versions:
            stages.append(self._kube_upgrade_first_control_plane_stage(
                ver))
            stages.extend(self._kube_upgrade_kubelet_stages(
                ver,
                self.std_controller_list,
                self.aio_controller_list,
                self.worker_list))
        if self.is_simplex():
            stages.append(self._kube_host_uncordon_stage())
        stages.extend([
            self._kube_upgrade_complete_stage(),
            self._kube_upgrade_cleanup_stage(),
        ])
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_networking_succeeded(self):
        """
        Test the kube_upgrade strategy creation when there is only a simplex
        and the upgrade had previously stopped after successful networking.
        It is expected to resume at the storage stage
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADED_NETWORKING,
            self.default_from_version,
            self.default_to_version)
        stages = [
            self._kube_upgrade_storage_stage()
        ]
        if self.is_simplex():
            stages.append(self._kube_host_cordon_stage())
        for ver in self.kube_versions:
            stages.append(self._kube_upgrade_first_control_plane_stage(
                ver))
            stages.extend(self._kube_upgrade_kubelet_stages(
                ver,
                self.std_controller_list,
                self.aio_controller_list,
                self.worker_list))
        if self.is_simplex():
            stages.append(self._kube_host_uncordon_stage())
        stages.extend([
            self._kube_upgrade_complete_stage(),
            self._kube_upgrade_cleanup_stage(),
        ])
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_storage_failed(self):
        """
        Test the kube_upgrade strategy creation when there is only a simplex
        and the upgrade had previously failed during storage.
        It is expected to retry and resume at the storage stage
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADING_STORAGE_FAILED,
            self.default_from_version,
            self.default_to_version)
        stages = [
            self._kube_upgrade_storage_stage(),
        ]
        if self.is_simplex():
            stages.append(self._kube_host_cordon_stage())
        for ver in self.kube_versions:
            stages.append(self._kube_upgrade_first_control_plane_stage(
                ver))
            stages.extend(self._kube_upgrade_kubelet_stages(
                ver,
                self.std_controller_list,
                self.aio_controller_list,
                self.worker_list))
        if self.is_simplex():
            stages.append(self._kube_host_uncordon_stage())
        stages.extend([
            self._kube_upgrade_complete_stage(),
            self._kube_upgrade_cleanup_stage(),
        ])
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_storage_succeeded(self):
        """
        Test the kube_upgrade strategy creation when there is only a simplex
        and the upgrade had previously stopped after successful storage.
        It is expected to resume at the first control plane
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADED_STORAGE,
            self.default_from_version,
            self.default_to_version)
        stages = []
        if self.is_simplex():
            stages.append(self._kube_host_cordon_stage())
        for ver in self.kube_versions:
            stages.append(self._kube_upgrade_first_control_plane_stage(
                ver))
            stages.extend(self._kube_upgrade_kubelet_stages(
                ver,
                self.std_controller_list,
                self.aio_controller_list,
                self.worker_list))
        if self.is_simplex():
            stages.append(self._kube_host_uncordon_stage())
        stages.extend([
            self._kube_upgrade_complete_stage(),
            self._kube_upgrade_cleanup_stage(),
        ])
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_invalid_second_master_state(self):
        """
        Test the kube_upgrade strategy creation when there is only a simplex
        and the upgrade had previously stopped after a second control plane
        state is encountered.
        There should never be a second control plane state in a simplex, so
        the stages should skip over it to the kubelet stage.
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADED_SECOND_MASTER,
            self.default_from_version,
            self.default_to_version)
        stages = []
        for ver in self.kube_versions:
            stages.extend(self._kube_upgrade_kubelet_stages(
                ver,
                self.std_controller_list,
                self.aio_controller_list,
                self.worker_list))
        if self.is_simplex():
            stages.append(self._kube_host_uncordon_stage())
        stages.extend([
            self._kube_upgrade_complete_stage(),
            self._kube_upgrade_cleanup_stage(),
        ])
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_invalid_second_master_fail_state(self):
        """
        Test the kube_upgrade strategy creation when there is only a simplex
        and the upgrade had previously stopped after a second control plane
        failure state is encountered.
        There should never be a second control plane state in a simplex
        so the logic should just proceed to the kubelets
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADING_SECOND_MASTER_FAILED,
            self.default_from_version,
            self.default_to_version)
        stages = []
        for ver in self.kube_versions:
            stages.extend(self._kube_upgrade_kubelet_stages(
                ver,
                self.std_controller_list,
                self.aio_controller_list,
                self.worker_list))
        if self.is_simplex():
            stages.append(self._kube_host_uncordon_stage())
        stages.extend([
            self._kube_upgrade_complete_stage(),
            self._kube_upgrade_cleanup_stage(),
        ])
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestSimplexMultiApplyStrategy(sw_update_testcase.SwUpdateStrategyTestCase,
                                    MultiApplyStageMixin,
                                    SimplexKubeUpgradeMixin):
    """This test class can be updated to resume from partial control plane"""

    def setUp(self):
        super(TestSimplexMultiApplyStrategy, self).setUp()
        self.create_host('controller-0', aio=True)
        # AIO kubelet phase does not process controller with the workers
        self.std_controller_list = []
        self.aio_controller_list = ['controller-0', ]
        self.worker_list = []
        self.storage_list = []


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestDuplexApplyStrategy(sw_update_testcase.SwUpdateStrategyTestCase,
                              ApplyStageMixin,
                              DuplexKubeUpgradeMixin):
    def setUp(self):
        super(TestDuplexApplyStrategy, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        # AIO kubelet phase does not process controller with the workers
        self.std_controller_list = []
        self.aio_controller_list = ['controller-1', 'controller-0']
        self.worker_list = []
        self.storage_list = []


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestDuplexPlusApplyStrategy(sw_update_testcase.SwUpdateStrategyTestCase,
                              ApplyStageMixin,
                              DuplexKubeUpgradeMixin):
    def setUp(self):
        super(TestDuplexPlusApplyStrategy, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.create_host('compute-0')  # creates a worker

        # AIO will be patched in the worker list
        # AIO kubelet phase does not process controller with the workers
        self.std_controller_list = []
        self.aio_controller_list = ['controller-1', 'controller-0']
        self.worker_list = [['compute-0']]  # A nested list
        self.storage_list = []


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestDuplexPlusApplyStrategyTwoWorkers(
        sw_update_testcase.SwUpdateStrategyTestCase,
        ApplyStageMixin,
        DuplexKubeUpgradeMixin):

    def setUp(self):
        super(TestDuplexPlusApplyStrategyTwoWorkers, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.create_host('compute-0')  # creates a worker
        self.create_host('compute-1')  # creates a worker
        # AIO will be patched in the worker list
        # AIO kubelet phase does not process controller with the workers
        self.std_controller_list = []
        self.aio_controller_list = ['controller-1', 'controller-0']
        self.worker_list = [['compute-0'], ['compute-1']]  # nested serial list
        self.storage_list = []


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestDuplexPlusApplyStrategyTwoWorkersParallel(
        sw_update_testcase.SwUpdateStrategyTestCase,
        ApplyStageMixin,
        DuplexKubeUpgradeMixin):

    def setUp(self):
        # override the strategy values before calling setup of the superclass
        self.worker_apply_type = SW_UPDATE_APPLY_TYPE.PARALLEL
        super(TestDuplexPlusApplyStrategyTwoWorkersParallel, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.create_host('compute-0')  # creates a worker
        self.create_host('compute-1')  # creates a worker
        # AIO will be patched in the worker list
        # AIO kubelet phase does not process controller with the workers
        self.std_controller_list = []
        self.aio_controller_list = ['controller-1', 'controller-0']
        self.worker_list = [['compute-0', 'compute-1']]  # nested parallel list
        self.storage_list = []


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestDuplexPlusApplyStrategyTwoStorage(
        sw_update_testcase.SwUpdateStrategyTestCase,
        ApplyStageMixin,
        DuplexKubeUpgradeMixin):

    def setUp(self):
        super(TestDuplexPlusApplyStrategyTwoStorage, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.create_host('storage-0')
        self.create_host('storage-1')
        # AIO will be patched in the worker list
        # AIO kubelet phase does not process controller with the workers
        self.std_controller_list = []
        self.aio_controller_list = ['controller-1', 'controller-0']
        self.worker_list = []
        self.storage_list = [['storage-0'], ['storage-1']]  # serial


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestDuplexPlusApplyStrategyTwoStorageParallel(
        sw_update_testcase.SwUpdateStrategyTestCase,
        ApplyStageMixin,
        DuplexKubeUpgradeMixin):

    def setUp(self):
        # override the strategy values before calling setup of the superclass
        self.storage_apply_type = SW_UPDATE_APPLY_TYPE.PARALLEL
        super(TestDuplexPlusApplyStrategyTwoStorageParallel, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.create_host('storage-0')
        self.create_host('storage-1')
        # AIO will be patched in the worker list
        # AIO kubelet phase does not process controller with the workers
        self.std_controller_list = []
        self.aio_controller_list = ['controller-1', 'controller-0']
        self.worker_list = []
        self.storage_list = [['storage-0', 'storage-1']]  # parallel


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestStandardTwoWorkerTwoStorage(
        sw_update_testcase.SwUpdateStrategyTestCase,
        ApplyStageMixin,
        DuplexKubeUpgradeMixin):

    def setUp(self):
        super(TestStandardTwoWorkerTwoStorage, self).setUp()
        # This is not AIO, so the stages are a little different
        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.std_controller_list = ['controller-1', 'controller-0']
        self.aio_controller_list = []
        self.worker_list = [['compute-0'], ['compute-1']]
        self.storage_list = [['storage-0'], ['storage-1']]
