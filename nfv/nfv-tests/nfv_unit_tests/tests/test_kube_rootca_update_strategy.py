#
# Copyright (c) 2020-2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import mock
import uuid

from nfv_common import strategy as common_strategy
from nfv_vim import nfvi

from nfv_vim.nfvi.objects.v1 import KUBE_ROOTCA_UPDATE_STATE
from nfv_vim.objects import KubeRootcaUpdate
from nfv_vim.objects import SW_UPDATE_ALARM_RESTRICTION
from nfv_vim.objects import SW_UPDATE_APPLY_TYPE
from nfv_vim.objects import SW_UPDATE_INSTANCE_ACTION
from nfv_vim.strategy._strategy import KubeRootcaUpdateStrategy

from . import sw_update_testcase  # noqa: H304


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestBuildStrategy(sw_update_testcase.SwUpdateStrategyTestCase):

    def _create_kube_rootca_update_strategy(self,
            sw_update_obj,
            controller_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            storage_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            worker_apply_type=SW_UPDATE_APPLY_TYPE.SERIAL,
            max_parallel_worker_hosts=10,
            default_instance_action=SW_UPDATE_INSTANCE_ACTION.STOP_START,
            alarm_restrictions=SW_UPDATE_ALARM_RESTRICTION.STRICT,
            single_controller=False,
            expiry_date=None,
            subject=None,
            cert_file=None,
            nfvi_kube_rootca_update=None):
        """
        Create a kube rootca update strategy
        """
        strategy = KubeRootcaUpdateStrategy(
            uuid=str(uuid.uuid4()),
            controller_apply_type=controller_apply_type,
            storage_apply_type=storage_apply_type,
            worker_apply_type=worker_apply_type,
            max_parallel_worker_hosts=max_parallel_worker_hosts,
            default_instance_action=default_instance_action,
            alarm_restrictions=alarm_restrictions,
            ignore_alarms=[],
            single_controller=single_controller,
            expiry_date=expiry_date,
            subject=subject,
            cert_file=cert_file
        )
        strategy.sw_update_obj = sw_update_obj  # this is a weakref
        strategy.nfvi_kube_rootca_update = nfvi_kube_rootca_update
        return strategy

    @mock.patch('nfv_common.strategy._strategy.Strategy._build')
    def test_kube_rootca_update_strategy_build_steps(self, fake_build):
        """
        Verify build phases, etc.. for kube_rootca_update strategy creation.
        """
        # setup a minimal host environment
        self.create_host('controller-0', aio=True)

        # construct the strategy. the update_obj MUST be declared here and not
        # in the create method, because it is a weakref and will be cleaned up
        # when it goes out of scope.
        update_obj = KubeRootcaUpdate()
        strategy = self._create_kube_rootca_update_strategy(update_obj)
        # The 'build' constructs a strategy that includes multiple queries
        # the results of those queries are not used until build_complete
        # mock away '_build', which invokes the build steps and their api calls
        fake_build.return_value = None
        strategy.build()

        # verify the build phase and steps
        build_phase = strategy.build_phase.as_dict()

        query_steps = [
            {'name': 'query-alarms'},
            {'name': 'query-kube-rootca-update'},
            {'name': 'query-kube-rootca-host-updates'},
        ]
        expected_results = {
            'total_stages': 1,
            'stages': [
                {'name': 'kube-rootca-update-query',
                 'total_steps': len(query_steps),
                 'steps': query_steps,
                },
            ],
        }
        sw_update_testcase.validate_phase(build_phase, expected_results)


# These Mixins must be defined on the test class BEFORE the testcase superclass
# since one of the testtools base classes does not call 'super' for setUp
# and tearDown
class HostListMixin(object):

    def setUp(self):
        self._hosts = []
        super(HostListMixin, self).setUp()

    def tearDown(self):
        super(HostListMixin, self).tearDown()
        self._hosts = []

    def sort_hosts(self):
        """sort_hosts requires mixing with SwUpdateStrategyTestCase"""
        self._hosts = []
        for host_name in list(self._host_table):
            if 'storage' not in host_name:
                self._hosts.append(host_name)

    def hosts(self):
        return sorted(self._hosts)


class SimplexMixin(HostListMixin):

    def setUp(self):
        super(SimplexMixin, self).setUp()

    def is_simplex(self):
        return True

    def is_duplex(self):
        return False


class DuplexMixin(HostListMixin):

    def setUp(self):
        super(DuplexMixin, self).setUp()

    def is_simplex(self):
        return False

    def is_duplex(self):
        return True


class ApplyStageMixin(object):
    """This Mixin will not work unless combined with other mixins.  """

    # override any of these prior to calling setup in classes that use mixin
    alarm_restrictions = SW_UPDATE_ALARM_RESTRICTION.STRICT
    max_parallel_worker_hosts = 10
    controller_apply_type = SW_UPDATE_APPLY_TYPE.SERIAL
    storage_apply_type = SW_UPDATE_APPLY_TYPE.SERIAL
    worker_apply_type = SW_UPDATE_APPLY_TYPE.SERIAL
    default_instance_action = SW_UPDATE_INSTANCE_ACTION.STOP_START

    def setUp(self):
        super(ApplyStageMixin, self).setUp()

    def _create_kube_rootca_update_obj(self, state):
        """
        Create a kube rootca update db object
        """
        return nfvi.objects.v1.KubeRootcaUpdate(state=state)

    def _create_built_kube_rootca_update_strategy(self,
                                            sw_update_obj,
                                            single_controller=False,
                                            kube_rootca_update=None,
                                            alarms_list=None,
                                            expiry_date=None,
                                            subject=None,
                                            cert_file=None):
        """
        Create a kube rootca update strategy
        populate the API query results from the build steps
        """
        strategy = KubeRootcaUpdateStrategy(
            uuid=str(uuid.uuid4()),
            controller_apply_type=self.controller_apply_type,
            storage_apply_type=self.storage_apply_type,
            worker_apply_type=self.worker_apply_type,
            max_parallel_worker_hosts=self.max_parallel_worker_hosts,
            default_instance_action=self.default_instance_action,
            alarm_restrictions=self.alarm_restrictions,
            ignore_alarms=[],
            single_controller=single_controller,
            expiry_date=expiry_date,
            subject=subject,
            cert_file=cert_file
        )
        strategy.sw_update_obj = sw_update_obj  # warning: this is a weakref
        strategy.nfvi_kube_rootca_update = kube_rootca_update

        # If any of the input lists are None, replace with defaults
        # this is done to prevent passing a list as a default

        return strategy

    def _kube_rootca_update_start_stage(self):
        return {
            'name': 'kube-rootca-update-start',
            'total_steps': 1,
            'steps': [
                {'name': 'kube-rootca-update-start',
                 'success_state': 'update-started'},
            ],
        }

    def _kube_rootca_update_cert_stage(self, upload=None):
        if upload is not None:
            step = {
                'name': 'kube-rootca-update-upload-cert',
            }
        else:
            step = {
                'name': 'kube-rootca-update-generate-cert',
            }
        return {
            'name': 'kube-rootca-update-cert',
            'total_steps': 1,
            'steps': [step, ],
        }

    def _kube_rootca_update_host_trustbothcas_stage(self, host_list, reboot):
        steps = []
        for host in host_list:
            steps.append(
                {'name': 'kube-rootca-update-host-trustbothcas',
                 'entity_type': 'hosts',
                 'entity_names': [host, ],
                 'success_state': 'updated-host-trust-both-cas',
                 'fail_state': 'updating-host-trust-both-cas-failed',
                })
        return {
            'name': 'kube-rootca-update-hosts-trustbothcas',
            'total_steps': len(steps),
            'steps': steps,
        }

    def _kube_rootca_update_pods_trustbothcas_stage(self):
        steps = [
            {'name': 'kube-rootca-update-pods-trustbothcas',
             'success_state': 'updated-pods-trust-both-cas',
             'fail_state': 'updating-pods-trust-both-cas-failed',
            },
        ]
        return {
            'name': 'kube-rootca-update-pods-trustbothcas',
            'total_steps': len(steps),
            'steps': steps,
        }

    def _kube_rootca_update_host_trustnewca_stage(self, host_list, reboot):
        steps = []
        for host in host_list:
            steps.append(
                {'name': 'kube-rootca-update-host-trustnewca',
                 'entity_type': 'hosts',
                 'entity_names': [host, ],
                 'success_state': 'updated-host-trust-new-ca',
                 'fail_state': 'updating-host-trust-new-ca-failed',
                })
        return {
            'name': 'kube-rootca-update-hosts-trustnewca',
            'total_steps': len(steps),
            'steps': steps,
        }

    def _kube_rootca_update_pods_trustnewca_stage(self):
        steps = [
            {'name': 'kube-rootca-update-pods-trustnewca',
             'success_state': 'updated-pods-trust-new-ca',
             'fail_state': 'updating-pods-trust-new-ca-failed',
            },
        ]
        return {
            'name': 'kube-rootca-update-pods-trustnewca',
            'total_steps': len(steps),
            'steps': steps,
        }

    def _kube_rootca_update_host_updatecerts_stage(self, host_list, reboot):
        steps = []
        for host in host_list:
            steps.append(
                {'name': 'kube-rootca-update-host-update-certs',
                 'entity_type': 'hosts',
                 'entity_names': [host, ],
                 'success_state': 'updated-host-update-certs',
                 'fail_state': 'updating-host-update-certs-failed',
                })
        return {
            'name': 'kube-rootca-update-hosts-updatecerts',
            'total_steps': len(steps),
            'steps': steps,
        }

    def _kube_rootca_update_host_stages(self,
                                        stage_method,
                                        host_list):
        stages = []
        if host_list:
            stages.append(stage_method(host_list, False))
        return stages

    def _kube_rootca_update_host_trustbothcas_stages(self, host_list=None):
        return self._kube_rootca_update_host_stages(
            self._kube_rootca_update_host_trustbothcas_stage,
            host_list)

    def _kube_rootca_update_host_trustnewca_stages(self, host_list=None):
        return self._kube_rootca_update_host_stages(
            self._kube_rootca_update_host_trustnewca_stage,
            host_list)

    def _kube_rootca_update_host_updatecerts_stages(self, host_list=None):
        return self._kube_rootca_update_host_stages(
            self._kube_rootca_update_host_updatecerts_stage,
            host_list)

    def _kube_rootca_update_complete_stage(self):
        return {
            'name': 'kube-rootca-update-complete',
            'total_steps': 1,
            'steps': [
                {'name': 'kube-rootca-update-complete',
                 'success_state': 'update-completed'},
            ],
        }

    def validate_apply_phase(self, single_controller, kube_rootca_update, stages):
        # sw_update_obj is a weak ref. it must be defined here
        update_obj = KubeRootcaUpdate()

        # create a strategy for a system with no existing kube_rootca_update
        strategy = self._create_built_kube_rootca_update_strategy(
            update_obj,
            single_controller=single_controller,
            kube_rootca_update=kube_rootca_update)

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
                         add_start=True,
                         add_cert=True,
                         add_host_trustboth=True,
                         add_pods_trustboth=True,
                         add_host_updatecerts=True,
                         add_host_trustnew=True,
                         add_pods_trustnew=True,
                         add_complete=True):
        """The order of the host_list determines the patch and kubelets"""
        stages = []
        if add_start:
            stages.append(self._kube_rootca_update_start_stage())

        if add_cert:
            # todo(abailey): add support for upload vs generate
            stages.append(self._kube_rootca_update_cert_stage(upload=None))

        if add_host_trustboth:
            stages.extend(
                self._kube_rootca_update_host_trustbothcas_stages(self.hosts())
            )

        if add_pods_trustboth:
            stages.append(self._kube_rootca_update_pods_trustbothcas_stage())

        if add_host_updatecerts:
            stages.extend(
                self._kube_rootca_update_host_updatecerts_stages(self.hosts())
            )
        if add_host_trustnew:
            stages.extend(
                self._kube_rootca_update_host_trustnewca_stages(self.hosts())
            )
        if add_pods_trustnew:
            stages.append(self._kube_rootca_update_pods_trustnewca_stage())

        if add_complete:
            stages.append(self._kube_rootca_update_complete_stage())

        return stages

    def test_no_existing_update(self):
        """
        Test the kube_rootca_update strategy creation for the hosts when there is
        no existing kube rootca update exists.
        A duplex env will have more steps than a simplex environment
        """
        kube_rootca_update = None
        # default stage list includes all , however second plane is duplex only
        stages = self.build_stage_list()
        self.validate_apply_phase(self.is_simplex(), kube_rootca_update, stages)

    def test_resume_after_update_started(self):
        """
        Test the kube_rootca_update strategy creation when the update was created
        already (update-started)
        The 'start stage should be skipped and the upgdate resumes at the
        next stage
        """
        kube_rootca_update = self._create_kube_rootca_update_obj(
            KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATE_STARTED)
        # explicity bypass the start stage
        stages = self.build_stage_list(add_start=False)
        self.validate_apply_phase(self.is_simplex(), kube_rootca_update, stages)

    def test_resume_after_update_complete(self):
        """
        Test the kube_rootca_update strategy creation when the update had previously
        stopped after update-completed.
        It is expected to resume at the complete stage
        """
        kube_rootca_update = self._create_kube_rootca_update_obj(
            KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATE_COMPLETED)
        # not using build_stage_list utility since the list of stages is small
        stages = [
            self._kube_rootca_update_complete_stage(),
        ]
        self.validate_apply_phase(self.is_simplex(), kube_rootca_update, stages)


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestSimplexApplyStrategy(ApplyStageMixin,
                               SimplexMixin,
                               sw_update_testcase.SwUpdateStrategyTestCase):
    def setUp(self):
        super(TestSimplexApplyStrategy, self).setUp()
        self.create_host('controller-0', aio=True)
        self.sort_hosts()


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestDuplexApplyStrategy(ApplyStageMixin,
                              DuplexMixin,
                              sw_update_testcase.SwUpdateStrategyTestCase):
    def setUp(self):
        super(TestDuplexApplyStrategy, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.sort_hosts()


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestDuplexPlusApplyStrategy(ApplyStageMixin,
                                  DuplexMixin,
                                  sw_update_testcase.SwUpdateStrategyTestCase):
    def setUp(self):
        super(TestDuplexPlusApplyStrategy, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.create_host('compute-0')  # creates a worker
        self.sort_hosts()


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestDuplexPlusApplyStrategyTwoWorkers(
        ApplyStageMixin,
        DuplexMixin,
        sw_update_testcase.SwUpdateStrategyTestCase):

    def setUp(self):
        super(TestDuplexPlusApplyStrategyTwoWorkers, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.create_host('compute-0')  # creates a worker
        self.create_host('compute-1')  # creates a worker
        self.sort_hosts()


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestDuplexPlusApplyStrategyTwoWorkersParallel(
        ApplyStageMixin,
        DuplexMixin,
        sw_update_testcase.SwUpdateStrategyTestCase):

    def setUp(self):
        # override the strategy values before calling setup of the superclass
        self.worker_apply_type = SW_UPDATE_APPLY_TYPE.PARALLEL
        super(TestDuplexPlusApplyStrategyTwoWorkersParallel, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.create_host('compute-0')  # creates a worker
        self.create_host('compute-1')  # creates a worker
        self.sort_hosts()


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestDuplexPlusApplyStrategyTwoStorage(
        ApplyStageMixin,
        DuplexMixin,
        sw_update_testcase.SwUpdateStrategyTestCase):

    def setUp(self):
        super(TestDuplexPlusApplyStrategyTwoStorage, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.sort_hosts()


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestDuplexPlusApplyStrategyTwoStorageParallel(
        ApplyStageMixin,
        DuplexMixin,
        sw_update_testcase.SwUpdateStrategyTestCase):

    def setUp(self):
        # override the strategy values before calling setup of the superclass
        self.storage_apply_type = SW_UPDATE_APPLY_TYPE.PARALLEL
        super(TestDuplexPlusApplyStrategyTwoStorageParallel, self).setUp()
        self.create_host('controller-0', aio=True)
        self.create_host('controller-1', aio=True)
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.sort_hosts()


@mock.patch('nfv_vim.event_log._instance._event_issue',
            sw_update_testcase.fake_event_issue)
@mock.patch('nfv_vim.objects._sw_update.SwUpdate.save',
            sw_update_testcase.fake_save)
@mock.patch('nfv_vim.objects._sw_update.timers.timers_create_timer',
            sw_update_testcase.fake_timer)
@mock.patch('nfv_vim.nfvi.nfvi_compute_plugin_disabled',
            sw_update_testcase.fake_nfvi_compute_plugin_disabled)
class TestStandardTwoWorkerTwoStorage(
        ApplyStageMixin,
        DuplexMixin,
        sw_update_testcase.SwUpdateStrategyTestCase):

    def setUp(self):
        super(TestStandardTwoWorkerTwoStorage, self).setUp()
        # This is not AIO, so the stages are a little different
        self.create_host('controller-0')
        self.create_host('controller-1')
        self.create_host('storage-0')
        self.create_host('storage-1')
        self.create_host('compute-0')
        self.create_host('compute-1')
        self.sort_hosts()
