#
# Copyright (c) 2020-2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import mock
import uuid

from nfv_common import strategy as common_strategy
from nfv_vim import nfvi

from nfv_vim.nfvi.objects.v1 import HostSwPatch
from nfv_vim.nfvi.objects.v1 import KUBE_UPGRADE_STATE
from nfv_vim.nfvi.objects.v1 import KubeVersion
from nfv_vim.nfvi.objects.v1 import SwPatch
from nfv_vim.objects import KubeUpgrade
from nfv_vim.objects import SW_UPDATE_ALARM_RESTRICTION
from nfv_vim.objects import SW_UPDATE_APPLY_TYPE
from nfv_vim.objects import SW_UPDATE_INSTANCE_ACTION
from nfv_vim.strategy._strategy import KubeUpgradeStrategy

from . import sw_update_testcase  # noqa: H304


FROM_KUBE_VERSION = '1.2.3'
TO_KUBE_VERSION = '1.2.4'

FAKE_LOAD = '12.01'

KUBE_PATCH_1 = 'KUBE.1'  # the control plane patch
KUBE_PATCH_2 = 'KUBE.2'  # the kubelet patch


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
            to_version=TO_KUBE_VERSION,
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
            {'name': 'query-kube-host-upgrade'},
            {'name': 'query-sw-patches'},
            {'name': 'query-sw-patch-hosts'},
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
    FAKE_PATCH_HOSTS_LIST = [
        HostSwPatch('controller-0',  # name
                    'controller',  # personality
                    FAKE_LOAD,  # sw_version
                    False,  # requires reboot
                    False,  # patch_current
                    'idle',   # state
                    False,    # patch_failed
                    False),   # interim_state
    ]
    FAKE_KUBE_HOST_UPGRADES_LIST = []

    def setUp(self):
        super(SimplexKubeUpgradeMixin, self).setUp()

    def is_simplex(self):
        return True

    def is_duplex(self):
        return False


class DuplexKubeUpgradeMixin(object):
    FAKE_PATCH_HOSTS_LIST = [
        HostSwPatch('controller-0', 'controller', FAKE_LOAD,
                    False, False, 'idle', False, False),
        HostSwPatch('controller-1', 'controller', FAKE_LOAD,
                    False, False, 'idle', False, False),
    ]
    FAKE_KUBE_HOST_UPGRADES_LIST = []

    def setUp(self):
        super(DuplexKubeUpgradeMixin, self).setUp()

    def is_simplex(self):
        return False

    def is_duplex(self):
        return True


class KubePatchMixin(object):
    """This Mixin represents the patches for a kube upgrade in proper state"""

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
            TO_KUBE_VERSION,  # kube_version
            'available',  # state
            False,  # target
            [FROM_KUBE_VERSION],  # upgrade_from
            [],  # downgrade_to
            [KUBE_PATCH_1],  # applied_patches
            [KUBE_PATCH_2]  # available_patches
        )
    ]

    FAKE_PATCHES_LIST = [
        SwPatch(KUBE_PATCH_1, FAKE_LOAD, 'Applied', 'Applied'),
        SwPatch(KUBE_PATCH_2, FAKE_LOAD, 'Available', 'Available'),
    ]

    def setUp(self):
        super(KubePatchMixin, self).setUp()

    def _kube_upgrade_patch_storage_stage(self, host_list, reboot):
        steps = [
            {'name': 'query-alarms', },
            {'name': 'sw-patch-hosts',
             'entity_type': 'hosts',
             'entity_names': host_list,
            },
            {'name': 'system-stabilize',
             'timeout': 30,
            },
        ]
        return {
            'name': 'sw-patch-storage-hosts',
            'total_steps': len(steps),
            'steps': steps,
        }

    def _kube_upgrade_patch_worker_stage(self, host_list, reboot):
        steps = [
            {'name': 'query-alarms', },
            {'name': 'sw-patch-hosts',
             'entity_type': 'hosts',
             'entity_names': host_list,
            },
            {'name': 'system-stabilize',
             'timeout': 30,
            },
        ]
        return {
            'name': 'sw-patch-worker-hosts',
            'total_steps': len(steps),
            'steps': steps,
        }

    def _kube_upgrade_patch_controller_stage(self, host_list, reboot):
        steps = [
            {'name': 'query-alarms', },
            {'name': 'sw-patch-hosts',
             'entity_type': 'hosts',
             'entity_names': host_list,
            },
            {'name': 'system-stabilize',
             'timeout': 30,
            },
        ]
        return {
            'name': 'sw-patch-controllers',
            'total_steps': len(steps),
            'steps': steps,
        }

    def _kube_upgrade_patch_stage(self,
                                  std_controller_list=None,
                                  worker_list=None,
                                  storage_list=None):
        """hosts are patched in the following order
           controllers, storage, then workers
        """
        patch_stages = []
        patch_stage = {
            'name': 'kube-upgrade-patch',
            'total_steps': 1,
            'steps': [{'name': 'apply-patches',
                       'entity_type': 'patches',
                       'entity_names': ['KUBE.2']},
                     ],
        }
        patch_stages.append(patch_stage)

        for host_name in std_controller_list:
            patch_stages.append(
                self._kube_upgrade_patch_controller_stage([host_name], False))
        if storage_list:
            for sub_list in storage_list:
                patch_stages.append(
                    self._kube_upgrade_patch_storage_stage(sub_list, False))
        if worker_list:
            for sub_list in worker_list:
                patch_stages.append(
                    self._kube_upgrade_patch_worker_stage(sub_list, False))
        return patch_stages


class ApplyStageMixin(object):
    """This Mixin will not work unless combined with other mixins.
    PatchMixin - to provide the setup patches and kube versions
    HostMixin - to provide the patch hosts and kube host upgrade states
    """

    # override any of these prior to calling setup in classes that use mixin
    alarm_restrictions = SW_UPDATE_ALARM_RESTRICTION.STRICT
    max_parallel_worker_hosts = 10
    controller_apply_type = SW_UPDATE_APPLY_TYPE.SERIAL
    storage_apply_type = SW_UPDATE_APPLY_TYPE.SERIAL
    worker_apply_type = SW_UPDATE_APPLY_TYPE.SERIAL
    default_instance_action = SW_UPDATE_INSTANCE_ACTION.STOP_START

    def setUp(self):
        super(ApplyStageMixin, self).setUp()

    def _create_kube_upgrade_obj(self,
                                 state,
                                 from_version=FROM_KUBE_VERSION,
                                 to_version=TO_KUBE_VERSION):
        """
        Create a kube upgrade db object
        """
        return nfvi.objects.v1.KubeUpgrade(state=state,
                                           from_version=from_version,
                                           to_version=to_version)

    def _create_built_kube_upgrade_strategy(self,
                                            sw_update_obj,
                                            to_version=TO_KUBE_VERSION,
                                            single_controller=False,
                                            kube_upgrade=None,
                                            alarms_list=None,
                                            patch_list=None,
                                            patch_hosts_list=None,
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
        if patch_list is None:
            patch_list = self.FAKE_PATCHES_LIST
        strategy.nfvi_sw_patches = patch_list

        if patch_hosts_list is None:
            patch_hosts_list = self.FAKE_PATCH_HOSTS_LIST
        strategy.nfvi_sw_patch_hosts = patch_hosts_list

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
                 'success_state': 'upgrade-started'},
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

    def _kube_upgrade_first_control_plane_stage(self):
        return {
            'name': 'kube-upgrade-first-control-plane',
            'total_steps': 1,
            'steps': [
                {'name': 'kube-host-upgrade-control-plane',
                 'success_state': 'upgraded-first-master',
                 'fail_state': 'upgrading-first-master-failed'},
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

    def _kube_upgrade_second_control_plane_stage(self):
        """This stage only executes on a duplex system"""
        return {
            'name': 'kube-upgrade-second-control-plane',
            'total_steps': 1,
            'steps': [
                {'name': 'kube-host-upgrade-control-plane',
                 'success_state': 'upgraded-second-master',
                 'fail_state': 'upgrading-second-master-failed'},
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

    def _kube_upgrade_kubelet_controller_stage(self, host, do_lock=True):
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
        return {
            'name': 'kube-upgrade-kubelets-controllers',
            'total_steps': len(steps),
            'steps': steps,
        }

    def _kube_upgrade_kubelet_worker_stage(self,
                                           hosts,
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

        return {
            'name': 'kube-upgrade-kubelets-workers',
            'total_steps': len(steps),
            'steps': steps,
        }

    def _kube_upgrade_kubelet_stages(self,
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
                    self.is_duplex()))  # lock is duplex only
        for host_name in aio_controller_list:
            kubelet_stages.append(
                self._kube_upgrade_kubelet_worker_stage(
                    [host_name],
                    do_lock=self.is_duplex(),  # lock is duplex only
                    do_swact=self.is_duplex()))  # swact only if we lock
        for sub_list in worker_list:
            # kubelet workers are lock but not controllers, so no swact
            kubelet_stages.append(
                self._kube_upgrade_kubelet_worker_stage(sub_list, True, False))
        return kubelet_stages

    def validate_apply_phase(self, single_controller, kube_upgrade, stages):
        # sw_update_obj is a weak ref. it must be defined here
        update_obj = KubeUpgrade()

        # create a strategy for a system with no existing kube_upgrade
        strategy = self._create_built_kube_upgrade_strategy(
            update_obj,
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
                         patch_worker_list=None,
                         worker_list=None,
                         storage_list=None,
                         add_start=True,
                         add_download=True,
                         add_first_plane=True,
                         add_networking=True,
                         add_second_plane=True,
                         add_patches=True,
                         add_kubelets=True,
                         add_complete=True,
                         add_cleanup=True):
        """The order of the host_list determines the patch and kubelets"""
        stages = []
        if add_start:
            stages.append(self._kube_upgrade_start_stage())
        if add_download:
            stages.append(self._kube_upgrade_download_images_stage())
        if add_networking:
            stages.append(self._kube_upgrade_networking_stage())
        if add_first_plane:
            stages.append(self._kube_upgrade_first_control_plane_stage())
        if add_second_plane:
            stages.append(self._kube_upgrade_second_control_plane_stage())
        if add_patches:
            # patches are not processed like kubelets.
            # AIO controllers are processed with the worker list
            stages.extend(self._kube_upgrade_patch_stage(
                std_controller_list=std_controller_list,
                worker_list=patch_worker_list,
                storage_list=storage_list))
        if add_kubelets:
            # there are no kubelets on storage
            stages.extend(self._kube_upgrade_kubelet_stages(std_controller_list,
                                                            aio_controller_list,
                                                            worker_list))
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
            patch_worker_list=self.patch_worker_list,
            worker_list=self.worker_list,
            storage_list=self.storage_list,
            add_second_plane=self.is_duplex())
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_upgrade_started(self):
        """
        Test the kube_upgrade strategy creation when the upgrade was created
        already (upgrade-started)
        The 'start stage should be skipped and the upgrade resumes at the
        'downloading images' stage
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADE_STARTED)
        # explicity bypass the start stage
        stages = self.build_stage_list(
            std_controller_list=self.std_controller_list,
            aio_controller_list=self.aio_controller_list,
            patch_worker_list=self.patch_worker_list,
            worker_list=self.worker_list,
            storage_list=self.storage_list,
            add_start=False,
            add_second_plane=self.is_duplex())
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_upgrade_complete(self):
        """
        Test the kube_upgrade strategy creation when the upgrade had previously
        stopped after upgrade-completed.
        It is expected to resume at the cleanup stage
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADE_COMPLETE)
        # not using build_stage_list utility since the list of stages is small
        stages = [
            self._kube_upgrade_cleanup_stage(),
        ]
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestSimplexApplyStrategy(sw_update_testcase.SwUpdateStrategyTestCase,
                               KubePatchMixin,
                               ApplyStageMixin,
                               SimplexKubeUpgradeMixin):
    def setUp(self):
        super(TestSimplexApplyStrategy, self).setUp()
        self.create_host('controller-0', aio=True)
        # AIO will be patched in the worker list
        self.std_controller_list = []
        self.patch_worker_list = [['controller-0']]  # nested list
        # AIO kubelet phase does not process controller with the workers
        self.aio_controller_list = ['controller-0']
        self.worker_list = []
        self.storage_list = []

    def test_resume_after_download_images_failed(self):
        """
        Test the kube_upgrade strategy creation when the upgrade had previously
        stopped with 'downloading-images-failed'
        It is expected to resume at the 'downloading images' stage
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADE_DOWNLOADING_IMAGES_FAILED)
        stages = [
            self._kube_upgrade_download_images_stage(),
            self._kube_upgrade_networking_stage(),
            self._kube_upgrade_first_control_plane_stage(),
        ]
        stages.extend(
            self._kube_upgrade_patch_stage(
                std_controller_list=self.std_controller_list,
                worker_list=self.patch_worker_list,
                storage_list=self.storage_list))
        stages.extend(
           self._kube_upgrade_kubelet_stages(self.std_controller_list,
                                             self.aio_controller_list,
                                             self.worker_list))
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
            KUBE_UPGRADE_STATE.KUBE_UPGRADE_DOWNLOADED_IMAGES)
        stages = [
            self._kube_upgrade_networking_stage(),
            self._kube_upgrade_first_control_plane_stage(),
        ]
        stages.extend(
            self._kube_upgrade_patch_stage(
                std_controller_list=self.std_controller_list,
                worker_list=self.patch_worker_list,
                storage_list=self.storage_list))
        stages.extend(
           self._kube_upgrade_kubelet_stages(self.std_controller_list,
                                             self.aio_controller_list,
                                             self.worker_list))
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
            KUBE_UPGRADE_STATE.KUBE_UPGRADING_FIRST_MASTER_FAILED)
        stages = [
            self._kube_upgrade_first_control_plane_stage(),
        ]
        stages.extend(
            self._kube_upgrade_patch_stage(
                std_controller_list=self.std_controller_list,
                worker_list=self.patch_worker_list,
                storage_list=self.storage_list))
        stages.extend(
           self._kube_upgrade_kubelet_stages(self.std_controller_list,
                                             self.aio_controller_list,
                                             self.worker_list))
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
            KUBE_UPGRADE_STATE.KUBE_UPGRADED_FIRST_MASTER)
        stages = []
        stages.extend(
            self._kube_upgrade_patch_stage(
                std_controller_list=self.std_controller_list,
                worker_list=self.patch_worker_list,
                storage_list=self.storage_list))
        stages.extend(
           self._kube_upgrade_kubelet_stages(self.std_controller_list,
                                             self.aio_controller_list,
                                             self.worker_list))
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
            KUBE_UPGRADE_STATE.KUBE_UPGRADING_NETWORKING_FAILED)
        stages = [
            self._kube_upgrade_networking_stage(),
            self._kube_upgrade_first_control_plane_stage(),
        ]
        stages.extend(
            self._kube_upgrade_patch_stage(
                std_controller_list=self.std_controller_list,
                worker_list=self.patch_worker_list,
                storage_list=self.storage_list))
        stages.extend(
           self._kube_upgrade_kubelet_stages(self.std_controller_list,
                                             self.aio_controller_list,
                                             self.worker_list))
        stages.extend([
            self._kube_upgrade_complete_stage(),
            self._kube_upgrade_cleanup_stage(),
        ])
        self.validate_apply_phase(self.is_simplex(), kube_upgrade, stages)

    def test_resume_after_networking_succeeded(self):
        """
        Test the kube_upgrade strategy creation when there is only a simplex
        and the upgrade had previously stopped after successful networking.
        It is expected to resume at the patch stage
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADED_NETWORKING)
        stages = [
            self._kube_upgrade_first_control_plane_stage(),
        ]
        stages.extend(
            self._kube_upgrade_patch_stage(
                std_controller_list=self.std_controller_list,
                worker_list=self.patch_worker_list,
                storage_list=self.storage_list))
        stages.extend(
           self._kube_upgrade_kubelet_stages(self.std_controller_list,
                                             self.aio_controller_list,
                                             self.worker_list))
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
        the stages should skip over it to the patch stage.
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADED_SECOND_MASTER)
        stages = []
        stages.extend(
            self._kube_upgrade_patch_stage(
                std_controller_list=self.std_controller_list,
                worker_list=self.patch_worker_list,
                storage_list=self.storage_list))
        stages.extend(
           self._kube_upgrade_kubelet_stages(self.std_controller_list,
                                             self.aio_controller_list,
                                             self.worker_list))
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
        There should never be a second control plane state in a simplex, so
        the stages should skip over it to the patch stage.
        """
        kube_upgrade = self._create_kube_upgrade_obj(
            KUBE_UPGRADE_STATE.KUBE_UPGRADING_SECOND_MASTER_FAILED)
        stages = []
        stages.extend(
            self._kube_upgrade_patch_stage(
                std_controller_list=self.std_controller_list,
                worker_list=self.patch_worker_list,
                storage_list=self.storage_list))
        stages.extend(
           self._kube_upgrade_kubelet_stages(self.std_controller_list,
                                             self.aio_controller_list,
                                             self.worker_list))
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
class TestDuplexApplyStrategy(sw_update_testcase.SwUpdateStrategyTestCase,
                              KubePatchMixin,
                              ApplyStageMixin,
                              DuplexKubeUpgradeMixin):
    def setUp(self):
        super(TestDuplexApplyStrategy, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        # AIO will be patched in the worker list
        # AIO kubelet phase does not process controller with the workers
        self.std_controller_list = []
        self.aio_controller_list = ['controller-1', 'controller-0']
        self.patch_worker_list = [['controller-0'], ['controller-1']]
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
                              KubePatchMixin,
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
        self.patch_worker_list = [['controller-0'], ['controller-1'], ['compute-0']]
        self.aio_controller_list = ['controller-1', 'controller-0']
        self.worker_list = [['compute-0']]  # A nested list
        self.storage_list = []
        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('compute-0',  # name
                        'worker',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state


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
        KubePatchMixin,
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
        self.patch_worker_list = [['controller-0'], ['controller-1'], ['compute-0'], ['compute-1']]
        self.worker_list = [['compute-0'], ['compute-1']]  # nested serial list
        self.storage_list = []

        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('compute-0',  # name
                        'worker',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state
        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('compute-1',  # name
                        'worker',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state


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
        KubePatchMixin,
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
        self.patch_worker_list = [['controller-0'], ['controller-1'], ['compute-0', 'compute-1']]
        self.worker_list = [['compute-0', 'compute-1']]  # nested parallel list
        self.storage_list = []
        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('compute-0',  # name
                        'worker',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state
        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('compute-1',  # name
                        'worker',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state


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
        KubePatchMixin,
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
        self.patch_worker_list = [['controller-0'], ['controller-1']]
        self.worker_list = []
        self.storage_list = [['storage-0'], ['storage-1']]  # serial
        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('storage-0',  # name
                        'storage',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state
        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('storage-1',  # name
                        'storage',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state


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
        KubePatchMixin,
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
        self.patch_worker_list = [['controller-0'], ['controller-1']]
        self.worker_list = []
        self.storage_list = [['storage-0', 'storage-1']]  # parallel
        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('storage-0',  # name
                        'storage',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state
        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('storage-1',  # name
                        'storage',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state


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
        KubePatchMixin,
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
        self.patch_worker_list = [['compute-0'], ['compute-1']]
        self.worker_list = [['compute-0'], ['compute-1']]
        self.storage_list = [['storage-0'], ['storage-1']]
        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('storage-0',  # name
                        'storage',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state
        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('storage-1',  # name
                        'storage',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state
        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('compute-0',  # name
                        'worker',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state
        self.FAKE_PATCH_HOSTS_LIST.append(
            HostSwPatch('compute-1',  # name
                        'worker',  # personality
                        FAKE_LOAD,  # sw_version
                        False,  # requires reboot
                        False,  # patch_current
                        'idle',  # state
                        False,  # patch_failed
                        False))  # interim_state
