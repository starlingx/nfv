#
# Copyright (c) 2015-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import copy
import six
import weakref

from nfv_common import debug
from nfv_common.helpers import Constant
from nfv_common.helpers import Constants
from nfv_common.helpers import get_local_host_name
from nfv_common.helpers import Singleton
from nfv_common import strategy
from nfv_vim.nfvi.objects.v1 import KUBE_ROOTCA_UPDATE_STATE
from nfv_vim.objects import HOST_GROUP_POLICY
from nfv_vim.objects import HOST_NAME
from nfv_vim.objects import HOST_PERSONALITY
from nfv_vim.objects import HOST_SERVICES
from nfv_vim.objects import INSTANCE_GROUP_POLICY
from nfv_vim.objects import SW_UPDATE_APPLY_TYPE
from nfv_vim.objects import SW_UPDATE_INSTANCE_ACTION

DLOG = debug.debug_get_logger('nfv_vim.strategy')


@six.add_metaclass(Singleton)
class StrategyNames(Constants):
    """
    Strategy Names
    """
    SW_PATCH = Constant('sw-patch')
    SW_UPGRADE = Constant('sw-upgrade')
    FW_UPDATE = Constant('fw-update')
    KUBE_ROOTCA_UPDATE = Constant('kube-rootca-update')
    KUBE_UPGRADE = Constant('kube-upgrade')
    SYSYTEM_CONFIG_UPDATE = Constant('system-config-update')


# Constant Instantiation
STRATEGY_NAME = StrategyNames()

# SystemStabilize timeout constants:
# After a reboot patch is applied, we need to wait for maintenance to detect
# that the host is patch current
MTCE_DELAY = 15
# a no-reboot patch can stabilize in 30 seconds
NO_REBOOT_DELAY = 30

# constants used by the patching API for state and repo state
PATCH_REPO_STATE_APPLIED = 'Applied'
PATCH_STATE_APPLIED = 'Applied'
WAIT_ALARM_TIMEOUT = 2400


###################################################################
#
# The Software Update Strategy ; Base Class
#
###################################################################
class SwUpdateStrategy(strategy.Strategy):
    """
    Software Update - Strategy
    """
    def __init__(self, uuid, strategy_name, controller_apply_type,
                 storage_apply_type,
                 swift_apply_type, worker_apply_type,
                 max_parallel_worker_hosts, default_instance_action,
                 alarm_restrictions,
                 ignore_alarms):
        super(SwUpdateStrategy, self).__init__(uuid, strategy_name)
        self._controller_apply_type = controller_apply_type
        self._storage_apply_type = storage_apply_type
        self._swift_apply_type = swift_apply_type
        self._worker_apply_type = worker_apply_type
        self._max_parallel_worker_hosts = max_parallel_worker_hosts
        self._default_instance_action = default_instance_action
        self._alarm_restrictions = alarm_restrictions
        self._sw_update_obj_reference = None

        # The ignore_alarms is a list that needs to get a copy
        # to avoid inadvertently modifying the input list by
        # subclass service strategies.
        self._ignore_alarms = copy.copy(ignore_alarms)
        self._nfvi_alarms = list()

    @property
    def sw_update_obj(self):
        """
        Returns the software update object this strategy is a part of
        """
        return self._sw_update_obj_reference()

    @sw_update_obj.setter
    def sw_update_obj(self, sw_update_obj_value):
        """
        Set the software update object this strategy is a part of
        """
        self._sw_update_obj_reference = weakref.ref(sw_update_obj_value)

    @property
    def nfvi_alarms(self):
        """
        Returns the alarms raised in the NFVI layer
        """
        return self._nfvi_alarms

    @nfvi_alarms.setter
    def nfvi_alarms(self, nfvi_alarms):
        """
        Save the alarms raised in the NFVI Layer
        """
        self._nfvi_alarms = nfvi_alarms

    def save(self):
        """
        Save the software update strategy object information
        """
        if self.sw_update_obj is not None:
            self.sw_update_obj.save()

    def build(self):
        """
        Build the strategy (expected to be overridden by child class)
        """
        super(SwUpdateStrategy, self).build()

    def _create_storage_host_lists(self, storage_hosts):
        """
        Create host lists for updating storage hosts
        """
        from nfv_vim import tables

        if SW_UPDATE_APPLY_TYPE.IGNORE != self._storage_apply_type:
            host_table = tables.tables_get_host_table()

            for host in storage_hosts:
                if HOST_PERSONALITY.STORAGE not in host.personality:
                    DLOG.error("Host inventory personality storage mismatch "
                               "detected for host %s." % host.name)
                    reason = 'host inventory personality storage mismatch detected'
                    return None, reason

            if 2 > host_table.total_by_personality(HOST_PERSONALITY.STORAGE):
                DLOG.warn("Not enough storage hosts to apply software updates.")
                reason = 'not enough storage hosts to apply software updates'
                return None, reason

        host_lists = list()

        if SW_UPDATE_APPLY_TYPE.SERIAL == self._storage_apply_type:
            for host in storage_hosts:
                host_lists.append([host])

        elif SW_UPDATE_APPLY_TYPE.PARALLEL == self._storage_apply_type:
            policy = HOST_GROUP_POLICY.STORAGE_REPLICATION
            host_group_table = tables.tables_get_host_group_table()

            for host in storage_hosts:
                # find the first list that can add this host
                # else create a new list
                for host_list in host_lists:
                    for peer_host in host_list:
                        if host_group_table.same_group(policy, host.name,
                                                       peer_host.name):
                            break
                    else:
                        host_list.append(host)
                        break
                else:
                    host_lists.append([host])
        else:
            DLOG.verbose("Storage apply type set to ignore.")

        return host_lists, ''

    def _create_worker_host_lists(self, worker_hosts, reboot):
        """
        Create host lists for updating worker hosts
        """
        from nfv_vim import tables

        def has_policy_conflict(peer_host):
            for instance in instance_table.on_host(host.name):
                for peer_instance in instance_table.on_host(peer_host.name):
                    for policy in policies:
                        if instance_group_table.same_group(policy, instance.uuid,
                                                           peer_instance.uuid):
                            return True
            DLOG.debug("No instance group policy conflict between host %s and "
                       "host %s." % (host.name, peer_host.name))
            return False

        def calculate_host_aggregate_limits():
            """
            Calculate limit for each host aggregate
            """
            # Use the ratio of the max parallel worker hosts to the total
            # number of worker hosts to limit the number of hosts in each
            # aggregate that will be updated at the same time. If there
            # are multiple aggregates, that will help us select hosts
            # from more than one aggregate for each stage.
            host_table = tables.tables_get_host_table()
            num_worker_hosts = host_table.total_by_personality(
                HOST_PERSONALITY.WORKER)
            # Limit the ratio to half the worker hosts in an aggregate
            aggregate_ratio = min(
                float(self._max_parallel_worker_hosts) / num_worker_hosts,
                0.5)

            for host_aggregate in host_aggregate_table:
                aggregate_count = len(
                    host_aggregate_table[host_aggregate].host_names)
                if aggregate_count == 1:
                    # only one host in this aggregate
                    host_aggregate_limit[host_aggregate] = 1
                else:
                    # multiple hosts in the aggregate - use the ratio,
                    # rounding down, but no lower than 1.
                    host_aggregate_limit[host_aggregate] = max(
                        1, int(aggregate_count * aggregate_ratio))

        def aggregate_limit_reached():
            """
            Determine whether adding this host to a host_list would exceed
            the number of hosts to be updated in the same aggregate
            Note: This isn't efficient, because we will be calling the
            host_aggregate_table.get_by_host many times, which will traverse
            all the aggregates each time. It would be more efficient to
            create a dictionary mapping host names to a list of aggregates
            for that host. We could do this once and then use it to more
            quickly calculate the host_aggregate_count here.
            """

            # count the number of hosts from the current host_list in each aggregate
            host_aggregate_count = {}
            for existing_host in host_list:
                for aggregate in host_aggregate_table.get_by_host(
                        existing_host.name):
                    if aggregate.name in host_aggregate_count:
                        host_aggregate_count[aggregate.name] += 1
                    else:
                        host_aggregate_count[aggregate.name] = 1

            # now check whether adding the current host will exceed the limit
            # for any aggregate
            for aggregate in host_aggregate_table.get_by_host(host.name):
                if aggregate.name in host_aggregate_count:
                    if host_aggregate_count[aggregate.name] == \
                            host_aggregate_limit[aggregate.name]:
                        return True

            DLOG.debug("No host aggregate limit reached for host %s." % (host.name))
            return False

        instance_table = tables.tables_get_instance_table()
        instance_group_table = tables.tables_get_instance_group_table()

        if SW_UPDATE_APPLY_TYPE.IGNORE != self._worker_apply_type:
            for host in worker_hosts:
                if HOST_PERSONALITY.WORKER not in host.personality:
                    DLOG.error("Host inventory personality worker mismatch "
                               "detected for host %s." % host.name)
                    reason = 'host inventory personality worker mismatch detected'
                    return None, reason

            # Do not allow reboots if there are locked instances that
            # that are members of an instance group. This could result in a
            # service disruption when the remaining instances are stopped or
            # migrated.
            if reboot:
                for instance in list(instance_table.values()):
                    if instance.is_locked():
                        for instance_group in instance_group_table.get_by_instance(
                                instance.uuid):
                            DLOG.warn(
                                "Instance %s in group %s must not be shut down"
                                % (instance.name, instance_group.name))
                            reason = (
                                'instance %s in group %s must not be shut down'
                                % (instance.name, instance_group.name))
                            return None, reason

        host_lists = list()

        if SW_UPDATE_APPLY_TYPE.SERIAL == self._worker_apply_type:
            # handle controller hosts first
            for host in worker_hosts:
                if HOST_PERSONALITY.CONTROLLER in host.personality:
                    host_lists.append([host])

            # handle the workers with no instances next
            host_with_instances_lists = list()
            for host in worker_hosts:
                if HOST_PERSONALITY.CONTROLLER not in host.personality:
                    if not instance_table.exist_on_host(host.name):
                        host_lists.append([host])
                    else:
                        host_with_instances_lists.append([host])

            # then add workers with instances
            if host_with_instances_lists:
                host_lists += host_with_instances_lists

        elif SW_UPDATE_APPLY_TYPE.PARALLEL == self._worker_apply_type:
            policies = [INSTANCE_GROUP_POLICY.ANTI_AFFINITY,
                        INSTANCE_GROUP_POLICY.ANTI_AFFINITY_BEST_EFFORT]

            host_aggregate_table = tables.tables_get_host_aggregate_table()
            host_aggregate_limit = {}
            calculate_host_aggregate_limits()
            controller_list = list()
            host_lists.append([])  # start with empty list of workers

            for host in worker_hosts:
                if HOST_PERSONALITY.CONTROLLER in host.personality:
                    # have to swact the controller so put it in its own list
                    controller_list.append([host])
                    continue
                elif not reboot:
                    # parallel no-reboot can group all workers together
                    host_lists[0].append(host)
                    continue
                elif not instance_table.exist_on_host(host.name):
                    # group the workers with no instances together
                    host_lists[0].append(host)
                    continue

                # find the first list that can add this host else create a new list
                for idx in range(1, len(host_lists), 1):
                    host_list = host_lists[idx]
                    if len(host_list) >= self._max_parallel_worker_hosts:
                        # this list is full - don't add the host
                        continue

                    for peer_host in host_list:
                        if has_policy_conflict(peer_host):
                            # don't add host to the current list
                            break
                    else:
                        if aggregate_limit_reached():
                            # don't add host to the current list
                            continue

                        # add host to the current list
                        host_list.append(host)
                        break
                else:
                    # create a new list with this host
                    host_lists.append([host])

            if controller_list:
                # handle controller hosts first
                host_lists = controller_list + host_lists

        else:
            DLOG.verbose("Worker apply type set to ignore.")

        # Drop empty lists and enforce a maximum number of hosts to be updated
        # at once (only required list of workers with no instances, as we
        # enforced the limit for worker hosts with instances above).
        sized_host_lists = list()
        for host_list in host_lists:
            # drop empty host lists
            if not host_list:
                continue

            if self._max_parallel_worker_hosts < len(host_list):
                start = 0
                end = self._max_parallel_worker_hosts
                while start < len(host_list):
                    sized_host_lists.append(host_list[start:end])
                    start = end
                    end += self._max_parallel_worker_hosts
            else:
                sized_host_lists.append(host_list)

        return sized_host_lists, ''

    def build_complete(self, result, result_reason):
        """
        Strategy Build Complete
        """
        result, result_reason = \
            super(SwUpdateStrategy, self).build_complete(result, result_reason)
        return result, result_reason

    def apply(self, stage_id):
        """
        Apply the strategy
        """
        success, reason = super(SwUpdateStrategy, self).apply(stage_id)
        return success, reason

    def apply_complete(self, result, result_reason):
        """
        Strategy Apply Complete
        """
        result, result_reason = \
            super(SwUpdateStrategy, self).apply_complete(result, result_reason)

        DLOG.info("Apply Complete Callback, result=%s, reason=%s."
                  % (result, result_reason))

        if result in [strategy.STRATEGY_RESULT.SUCCESS,
                      strategy.STRATEGY_RESULT.DEGRADED]:
            self.sw_update_obj.strategy_apply_complete(True, '')
        else:
            self.sw_update_obj.strategy_apply_complete(
                False, self.apply_phase.result_reason)

    def abort(self, stage_id):
        """
        Abort the strategy
        """
        success, reason = super(SwUpdateStrategy, self).abort(stage_id)
        return success, reason

    def abort_complete(self, result, result_reason):
        """
        Strategy Abort Complete
        """
        result, result_reason = \
            super(SwUpdateStrategy, self).abort_complete(result, result_reason)

        DLOG.info("Abort Complete Callback, result=%s, reason=%s."
                  % (result, result_reason))

        if result in [strategy.STRATEGY_RESULT.SUCCESS,
                      strategy.STRATEGY_RESULT.DEGRADED]:
            self.sw_update_obj.strategy_abort_complete(True, '')
        else:
            self.sw_update_obj.strategy_abort_complete(
                False, self.abort_phase.result_reason)

    def report_build_failure(self, reason):
        """
        Report a build failure for the strategy

        todo(yuxing): report all build failure use this method
        """
        DLOG.warn("Strategy Build Failed: %s" % reason)
        self._state = strategy.STRATEGY_STATE.BUILD_FAILED
        self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
        self.build_phase.result_reason = reason
        self.sw_update_obj.strategy_build_complete(
            False,
            self.build_phase.result_reason)
        self.save()

    def from_dict(self, data, build_phase=None, apply_phase=None, abort_phase=None):
        """
        Initializes a software update strategy object using the given dictionary
        """
        from nfv_vim import nfvi

        super(SwUpdateStrategy, self).from_dict(data, build_phase, apply_phase,
                                                abort_phase)
        self._controller_apply_type = data['controller_apply_type']
        self._storage_apply_type = data['storage_apply_type']
        self._swift_apply_type = data['swift_apply_type']
        self._worker_apply_type = data['worker_apply_type']
        self._max_parallel_worker_hosts = data['max_parallel_worker_hosts']
        self._default_instance_action = data['default_instance_action']
        self._alarm_restrictions = data['alarm_restrictions']
        self._ignore_alarms = data['ignore_alarms']

        nfvi_alarms = list()
        for alarm_data in data['nfvi_alarms_data']:
            alarm = nfvi.objects.v1.Alarm(
                alarm_data['alarm_uuid'], alarm_data['alarm_id'],
                alarm_data['entity_instance_id'], alarm_data['severity'],
                alarm_data['reason_text'], alarm_data['timestamp'],
                alarm_data['mgmt_affecting'])
            nfvi_alarms.append(alarm)
        self._nfvi_alarms = nfvi_alarms

        return self

    def as_dict(self):
        """
        Represent the software update strategy as a dictionary
        """
        data = super(SwUpdateStrategy, self).as_dict()
        data['controller_apply_type'] = self._controller_apply_type
        data['storage_apply_type'] = self._storage_apply_type
        data['swift_apply_type'] = self._swift_apply_type
        data['worker_apply_type'] = self._worker_apply_type
        data['max_parallel_worker_hosts'] = self._max_parallel_worker_hosts
        data['default_instance_action'] = self._default_instance_action
        data['alarm_restrictions'] = self._alarm_restrictions
        data['ignore_alarms'] = self._ignore_alarms

        nfvi_alarms_data = list()
        for alarm in self._nfvi_alarms:
            nfvi_alarms_data.append(alarm.as_dict())
        data['nfvi_alarms_data'] = nfvi_alarms_data

        return data


###################################################################
#
# Mixins used by various Strategies
#
###################################################################
class QueryMixinBase(object):
    """
    QueryMixinBase stubs the query mixin classes.

    Query steps require fields on the strategy to populate and store results
    each query step should have a mixin to simplify using it for a strategy.

    The methods here do not call super, and stop the method invocation chain.
    """

    def initialize_mixin(self):
        pass

    def mixin_from_dict(self, data):
        pass

    def mixin_as_dict(self, data):
        pass


class QuerySwPatchesMixin(QueryMixinBase):
    """This mixin is used through the QuerySwPatchesStep class"""

    def initialize_mixin(self):
        super(QuerySwPatchesMixin, self).initialize_mixin()
        self._nfvi_sw_patches = list()

    @property
    def nfvi_sw_patches(self):
        """
        Returns the software patches from the NFVI layer
        """
        return self._nfvi_sw_patches

    @nfvi_sw_patches.setter
    def nfvi_sw_patches(self, nfvi_sw_patches):
        """
        Save the software patches from the NFVI Layer
        """
        self._nfvi_sw_patches = nfvi_sw_patches

    def mixin_from_dict(self, data):
        """
        Extracts this mixin data from a dictionary
        """
        super(QuerySwPatchesMixin, self).mixin_from_dict(data)

        from nfv_vim import nfvi

        mixin_data = list()
        for sw_patch_data in data['nfvi_sw_patches_data']:
            sw_patch = nfvi.objects.v1.SwPatch(
                sw_patch_data['name'],
                sw_patch_data['sw_version'],
                sw_patch_data['repo_state'],
                sw_patch_data['patch_state'])
            mixin_data.append(sw_patch)
        self._nfvi_sw_patches = mixin_data

    def mixin_as_dict(self, data):
        """
        Updates the dictionary with this mixin data
        """
        super(QuerySwPatchesMixin, self).mixin_as_dict(data)
        mixin_data = list()
        for sw_patch in self._nfvi_sw_patches:
            mixin_data.append(sw_patch.as_dict())
        data['nfvi_sw_patches_data'] = mixin_data


class QuerySwPatchHostsMixin(QueryMixinBase):
    """This mixin is used through the QuerySwPatchHostsStep class"""

    def initialize_mixin(self):
        super(QuerySwPatchHostsMixin, self).initialize_mixin()
        self._nfvi_sw_patch_hosts = list()

    @property
    def nfvi_sw_patch_hosts(self):
        """
        Returns the software patch hosts from the NFVI layer
        """
        return self._nfvi_sw_patch_hosts

    @nfvi_sw_patch_hosts.setter
    def nfvi_sw_patch_hosts(self, nfvi_sw_patch_hosts):
        """
        Save the software patch hosts from the NFVI Layer
        """
        self._nfvi_sw_patch_hosts = nfvi_sw_patch_hosts

    def mixin_from_dict(self, data):
        """
        Extracts this mixin data from a dictionary
        """
        super(QuerySwPatchHostsMixin, self).mixin_from_dict(data)

        from nfv_vim import nfvi

        mixin_data = list()
        for host_data in data['nfvi_sw_patch_hosts_data']:
            host = nfvi.objects.v1.HostSwPatch(
                host_data['name'], host_data['personality'],
                host_data['sw_version'], host_data['requires_reboot'],
                host_data['patch_current'], host_data['state'],
                host_data['patch_failed'], host_data['interim_state'])
            mixin_data.append(host)
        self._nfvi_sw_patch_hosts = mixin_data

    def mixin_as_dict(self, data):
        """
        Updates the dictionary with this mixin data
        """
        super(QuerySwPatchHostsMixin, self).mixin_as_dict(data)
        mixin_data = list()
        for host in self._nfvi_sw_patch_hosts:
            mixin_data.append(host.as_dict())
        data['nfvi_sw_patch_hosts_data'] = mixin_data


class QueryKubeRootcaHostUpdatesMixin(QueryMixinBase):
    """This mixin is used through the QueryKubeRootcaHostUpdatesStep class"""

    def initialize_mixin(self):
        super(QueryKubeRootcaHostUpdatesMixin, self).initialize_mixin()
        self._nfvi_kube_rootca_host_update_list = list()

    @property
    def nfvi_kube_rootca_host_update_list(self):
        """
        Returns the kube rootca host update list from the NFVI layer
        """
        return self._nfvi_kube_rootca_host_update_list

    @nfvi_kube_rootca_host_update_list.setter
    def nfvi_kube_rootca_host_update_list(self, new_list):
        """
        Save the kube rootca host update list from the NFVI Layer
        """
        self._nfvi_kube_rootca_host_update_list = new_list

    def mixin_from_dict(self, data):
        """
        Extracts this mixin data from a dictionary
        """
        super(QueryKubeRootcaHostUpdatesMixin, self).mixin_from_dict(data)

        from nfv_vim import nfvi

        mixin_data = list()
        for list_data in data['nfvi_kube_rootca_host_update_list_data']:
            new_object = nfvi.objects.v1.KubeRootcaHostUpdate(
                list_data['host_id'],
                list_data['hostname'],
                list_data['target_rootca_cert'],
                list_data['effective_rootca_cert'],
                list_data['state'],
                list_data['created_at'],
                list_data['updated_at'])
            mixin_data.append(new_object)
        self._nfvi_kube_rootca_host_update_list = mixin_data

    def mixin_as_dict(self, data):
        """
        Updates the dictionary with this mixin data
        """
        super(QueryKubeRootcaHostUpdatesMixin, self).mixin_as_dict(data)
        mixin_data = list()
        for list_entry in self._nfvi_kube_rootca_host_update_list:
            mixin_data.append(list_entry.as_dict())
        data['nfvi_kube_rootca_host_update_list_data'] = mixin_data


class QueryKubeRootcaUpdatesMixin(QueryMixinBase):
    """This mixin is used through the QueryKubeRootcaUpdatesStep class"""

    def initialize_mixin(self):
        super(QueryKubeRootcaUpdatesMixin, self).initialize_mixin()
        self._nfvi_kube_rootca_update = None

    @property
    def nfvi_kube_rootca_update(self):
        """
        Returns the kube rootca update from the NFVI layer
        """
        return self._nfvi_kube_rootca_update

    @nfvi_kube_rootca_update.setter
    def nfvi_kube_rootca_update(self, nfvi_kube_rootca_update):
        """
        Save the kube rootca update from the NFVI Layer
        """
        self._nfvi_kube_rootca_update = nfvi_kube_rootca_update

    def mixin_from_dict(self, data):
        """
        Extracts this mixin data from a dictionary
        """
        super(QueryKubeRootcaUpdatesMixin, self).mixin_from_dict(data)

        from nfv_vim import nfvi

        mixin_data = data['nfvi_kube_rootca_update_data']
        if mixin_data:
            self._nfvi_kube_rootca_update = nfvi.objects.v1.KubeRootcaUpdate(
                mixin_data['state'])
        else:
            self._nfvi_kube_rootca_update = None

    def mixin_as_dict(self, data):
        """
        Updates the dictionary with this mixin data
        """
        super(QueryKubeRootcaUpdatesMixin, self).mixin_as_dict(data)
        mixin_data = None
        if self._nfvi_kube_rootca_update:
            mixin_data = self._nfvi_kube_rootca_update.as_dict()
        data['nfvi_kube_rootca_update_data'] = mixin_data


class QueryKubeUpgradesMixin(QueryMixinBase):
    """This mixin is used through the QueryKubeUpgradesStep class"""

    def initialize_mixin(self):
        super(QueryKubeUpgradesMixin, self).initialize_mixin()
        self._nfvi_kube_upgrade = None

    @property
    def nfvi_kube_upgrade(self):
        """
        Returns the kube upgrade from the NFVI layer
        """
        return self._nfvi_kube_upgrade

    @nfvi_kube_upgrade.setter
    def nfvi_kube_upgrade(self, nfvi_kube_upgrade):
        """
        Save the kube upgrade from the NFVI Layer
        """
        self._nfvi_kube_upgrade = nfvi_kube_upgrade

    def mixin_from_dict(self, data):
        """
        Extracts this mixin data from a dictionary
        """
        super(QueryKubeUpgradesMixin, self).mixin_from_dict(data)

        from nfv_vim import nfvi

        mixin_data = data['nfvi_kube_upgrade_data']
        if mixin_data:
            self._nfvi_kube_upgrade = nfvi.objects.v1.KubeUpgrade(
                mixin_data['state'],
                mixin_data['from_version'],
                mixin_data['to_version'])
        else:
            self._nfvi_kube_upgrade = None

    def mixin_as_dict(self, data):
        """
        Updates the dictionary with this mixin data
        """
        super(QueryKubeUpgradesMixin, self).mixin_as_dict(data)
        mixin_data = None
        if self._nfvi_kube_upgrade:
            mixin_data = self._nfvi_kube_upgrade.as_dict()
        data['nfvi_kube_upgrade_data'] = mixin_data


class QueryKubeHostUpgradesMixin(QueryMixinBase):
    """This mixin is used through the QueryKubeHostUpgradesStep class"""

    def initialize_mixin(self):
        super(QueryKubeHostUpgradesMixin, self).initialize_mixin()
        self._nfvi_kube_host_upgrade_list = list()

    @property
    def nfvi_kube_host_upgrade_list(self):
        """
        Returns the kube host upgrade list from the NFVI layer
        """
        return self._nfvi_kube_host_upgrade_list

    @nfvi_kube_host_upgrade_list.setter
    def nfvi_kube_host_upgrade_list(self, nfvi_kube_host_upgrade_list):
        """
        Save the kube host upgrade list from the NFVI Layer
        """
        self._nfvi_kube_host_upgrade_list = nfvi_kube_host_upgrade_list

    def mixin_from_dict(self, data):
        """
        Extracts this mixin data from a dictionary
        """
        super(QueryKubeHostUpgradesMixin, self).mixin_from_dict(data)

        from nfv_vim import nfvi

        mixin_data = list()
        for kube_host_upgrade_data in data['nfvi_kube_host_upgrade_list_data']:
            kube_host_upgrade = nfvi.objects.v1.KubeHostUpgrade(
                kube_host_upgrade_data['host_id'],
                kube_host_upgrade_data['host_uuid'],
                kube_host_upgrade_data['target_version'],
                kube_host_upgrade_data['control_plane_version'],
                kube_host_upgrade_data['kubelet_version'],
                kube_host_upgrade_data['status'])
            mixin_data.append(kube_host_upgrade)
        self._nfvi_kube_host_upgrade_list = mixin_data

    def mixin_as_dict(self, data):
        """
        Updates the dictionary with this mixin data
        """
        super(QueryKubeHostUpgradesMixin, self).mixin_as_dict(data)
        mixin_data = list()
        for kube_host_upgrade in self._nfvi_kube_host_upgrade_list:
            mixin_data.append(kube_host_upgrade.as_dict())
        data['nfvi_kube_host_upgrade_list_data'] = mixin_data


class QueryKubeVersionsMixin(QueryMixinBase):
    """This mixin is used through the QueryKubeVersionsStep class"""

    def initialize_mixin(self):
        super(QueryKubeVersionsMixin, self).initialize_mixin()
        self._nfvi_kube_versions_list = list()

    @property
    def nfvi_kube_versions_list(self):
        """
        Returns the kube versions list from the NFVI layer
        """
        return self._nfvi_kube_versions_list

    @nfvi_kube_versions_list.setter
    def nfvi_kube_versions_list(self, nfvi_kube_versions_list):
        """
        Save the kube versions list from the NFVI Layer
        """
        self._nfvi_kube_versions_list = nfvi_kube_versions_list

    def mixin_from_dict(self, data):
        """
        Extracts this mixin data from a dictionary
        """
        super(QueryKubeVersionsMixin, self).mixin_from_dict(data)

        from nfv_vim import nfvi

        mixin_data = list()
        for data_item in data['nfvi_kube_versions_list_data']:
            mixin_object = nfvi.objects.v1.KubeVersion(
                data_item['kube_version'],
                data_item['state'],
                data_item['target'],
                data_item['upgrade_from'],
                data_item['downgrade_to'],
                data_item['applied_patches'],
                data_item['available_patches'])
            mixin_data.append(mixin_object)
        self._nfvi_kube_versions_list = mixin_data

    def mixin_as_dict(self, data):
        """
        Updates the dictionary with this mixin data
        """
        super(QueryKubeVersionsMixin, self).mixin_as_dict(data)
        mixin_data = list()
        for mixin_obj in self._nfvi_kube_versions_list:
            mixin_data.append(mixin_obj.as_dict())
        data['nfvi_kube_versions_list_data'] = mixin_data


class QuerySystemConfigUpdateHostsMixin(QueryMixinBase):
    """This mixin is used through the QuerySystemConfigUpdateHostsMixin class"""

    def initialize_mixin(self):
        super(QuerySystemConfigUpdateHostsMixin, self).initialize_mixin()
        self._nfvi_system_config_update_hosts = list()

    @property
    def nfvi_system_config_update_hosts(self):
        """
        Returns the System Config Update hosts from the NFVI layer
        """
        return self._nfvi_system_config_update_hosts

    @nfvi_system_config_update_hosts.setter
    def nfvi_system_config_update_hosts(self, nfvi_system_config_update_hosts):
        """
        Save the System Config Update hosts from the NFVI Layer
        """
        self._nfvi_system_config_update_hosts = nfvi_system_config_update_hosts

    def mixin_from_dict(self, data):
        """
        Extracts this mixin data from a dictionary
        """
        super(QuerySystemConfigUpdateHostsMixin, self).mixin_from_dict(data)

        from nfv_vim import nfvi

        mixin_data = list()
        for host_data in data['nfvi_system_config_update_hosts_data']:
            host = nfvi.objects.v1.HostSystemConfigUpdate(
                host_data['name'],
                host_data['unlock_request'])
            mixin_data.append(host)
        self._nfvi_system_config_update_hosts = mixin_data

    def mixin_as_dict(self, data):
        """
        Updates the dictionary with this mixin data
        """
        super(QuerySystemConfigUpdateHostsMixin, self).mixin_as_dict(data)
        mixin_data = list()
        for host in self._nfvi_system_config_update_hosts:
            mixin_data.append(host.as_dict())
        data['nfvi_system_config_update_hosts_data'] = mixin_data


class UpdateControllerHostsMixin(object):

    def _add_update_controller_strategy_stages(self,
                                               controllers,
                                               reboot,
                                               strategy_stage_name,
                                               host_action_step,
                                               extra_args=None):
        """
        Add controller software stages for a controller list to a strategy
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        if SW_UPDATE_APPLY_TYPE.IGNORE != self._controller_apply_type:
            host_table = tables.tables_get_host_table()

            for host in controllers:
                if HOST_PERSONALITY.CONTROLLER not in host.personality:
                    DLOG.error("Host inventory personality controller mismatch "
                               "detected for host %s." % host.name)
                    reason = ('host inventory personality controller mismatch '
                              'detected')
                    return False, reason

            if (not self._single_controller and
                    2 > host_table.total_by_personality(
                    HOST_PERSONALITY.CONTROLLER)):
                DLOG.warn("Not enough controllers to apply software update.")
                reason = 'not enough controllers to apply software update'
                return False, reason

        if self._controller_apply_type == SW_UPDATE_APPLY_TYPE.SERIAL:
            local_host = None
            local_host_name = get_local_host_name()

            for host in controllers:
                if HOST_PERSONALITY.WORKER not in host.personality:
                    if local_host_name == host.name:
                        local_host = host
                    else:
                        host_list = [host]
                        stage = strategy.StrategyStage(strategy_stage_name)
                        stage.add_step(strategy.QueryAlarmsStep(
                            True, ignore_alarms=self._ignore_alarms,
                            ignore_alarms_conditional=self._ignore_alarms_conditional))
                        if reboot:
                            stage.add_step(strategy.SwactHostsStep(host_list))
                            stage.add_step(strategy.LockHostsStep(host_list))
                        # Add the action step for these hosts (patch, etc..)
                        if extra_args is None:
                            stage.add_step(host_action_step(host_list))
                        else:
                            stage.add_step(host_action_step(host_list, extra_args))
                        if reboot:
                            # Cannot unlock right away after certain actions
                            # like SwPatchHostsStep
                            stage.add_step(strategy.SystemStabilizeStep(
                                timeout_in_secs=MTCE_DELAY))
                            stage.add_step(strategy.UnlockHostsStep(host_list))
                            # After controller node(s) are unlocked, we need extra time to
                            # allow the OSDs to go back in sync and the storage related
                            # alarms to clear. Note: not all controller nodes will have
                            # OSDs configured, but the alarms should clear quickly in
                            # that case so this will not delay the update strategy.
                            stage.add_step(strategy.WaitAlarmsClearStep(
                                           timeout_in_secs=WAIT_ALARM_TIMEOUT,
                                           ignore_alarms=self._ignore_alarms,
                                           ignore_alarms_conditional=self._ignore_alarms_conditional))
                        else:
                            # Less time required if host is not rebooting
                            stage.add_step(strategy.SystemStabilizeStep(
                                           timeout_in_secs=NO_REBOOT_DELAY))
                        self.apply_phase.add_stage(stage)

            if local_host is not None:
                host_list = [local_host]
                stage = strategy.StrategyStage(strategy_stage_name)
                stage.add_step(strategy.QueryAlarmsStep(
                    True, ignore_alarms=self._ignore_alarms,
                    ignore_alarms_conditional=self._ignore_alarms_conditional))
                if reboot:
                    stage.add_step(strategy.SwactHostsStep(host_list))
                    stage.add_step(strategy.LockHostsStep(host_list))
                # Add the action step for the local_hosts (patch, etc..)
                if extra_args is None:
                    stage.add_step(host_action_step(host_list))
                else:
                    stage.add_step(host_action_step(host_list, extra_args))
                if reboot:
                    # Cannot unlock right away after certain actions
                    # like SwPatchHostsStep
                    stage.add_step(strategy.SystemStabilizeStep(
                                   timeout_in_secs=MTCE_DELAY))
                    stage.add_step(strategy.UnlockHostsStep(host_list))
                    # After controller node(s) are unlocked, we need extra time to
                    # allow the OSDs to go back in sync and the storage related
                    # alarms to clear. Note: not all controller nodes will have
                    # OSDs configured, but the alarms should clear quickly in
                    # that case so this will not delay the update strategy.
                    stage.add_step(strategy.WaitAlarmsClearStep(
                                   timeout_in_secs=WAIT_ALARM_TIMEOUT,
                                   ignore_alarms=self._ignore_alarms,
                                   ignore_alarms_conditional=self._ignore_alarms_conditional))
                else:
                    # Less time required if host is not rebooting
                    stage.add_step(strategy.SystemStabilizeStep(
                                   timeout_in_secs=NO_REBOOT_DELAY))

                self.apply_phase.add_stage(stage)

        elif self._controller_apply_type == SW_UPDATE_APPLY_TYPE.PARALLEL:
            DLOG.warn("Parallel apply type cannot be used for controllers.")
            reason = 'parallel apply type not allowed for controllers'
            return False, reason
        else:
            DLOG.verbose("Controller apply type set to ignore.")

        return True, ''


class PatchControllerHostsMixin(UpdateControllerHostsMixin):
    def _add_controller_strategy_stages(self, controllers, reboot):
        from nfv_vim import strategy
        return self._add_update_controller_strategy_stages(
            controllers,
            reboot,
            strategy.STRATEGY_STAGE_NAME.SW_PATCH_CONTROLLERS,
            strategy.SwPatchHostsStep)


class SwDeployControllerHostsMixin(UpdateControllerHostsMixin):
    def _add_controller_strategy_stages(self, controllers, reboot):
        from nfv_vim import strategy
        return self._add_update_controller_strategy_stages(
            controllers,
            reboot,
            strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_CONTROLLERS,
            strategy.UpgradeHostsStep)


class UpdateSystemConfigControllerHostsMixin(UpdateControllerHostsMixin):
    def _add_system_config_controller_strategy_stages(self, controllers):
        """
        Add controller system config update stages to a strategy
        """
        from nfv_vim import strategy
        return self._add_update_controller_strategy_stages(
            controllers,
            True,
            strategy.STRATEGY_STAGE_NAME.SYSTEM_CONFIG_UPDATE_CONTROLLERS,
            strategy.SystemConfigUpdateHostsStep)


class UpgradeKubeletControllerHostsMixin(UpdateControllerHostsMixin):
    def _add_kubelet_controller_strategy_stages(self, controllers, to_version, reboot, stage_name):
        from nfv_vim import strategy
        return self._add_update_controller_strategy_stages(
            controllers,
            reboot,
            stage_name,
            strategy.KubeHostUpgradeKubeletStep,
            extra_args=to_version)


class UpdateStorageHostsMixin(object):
    """
    Adds the ability to add steps for storage hosts to a strategy.

    This mixin can only be used classes that subclass or mixin with:
    - SwUpdateStrategy: - provides _create_storage_host_lists
    """

    def _add_update_storage_strategy_stages(self,
                                            storage_hosts,
                                            reboot,
                                            strategy_stage_name,
                                            host_action_step):
        """
        Add storage update stages to a strategy
        The strategy_stage_name is the type of stage (patch, kube, etc..)
        The host_action_step is the step to invoke once hosts are locked, etc..
        """
        from nfv_vim import strategy

        host_lists, reason = self._create_storage_host_lists(storage_hosts)
        if host_lists is None:
            return False, reason

        for host_list in host_lists:
            stage = strategy.StrategyStage(strategy_stage_name)
            stage.add_step(strategy.QueryAlarmsStep(
                True, ignore_alarms=self._ignore_alarms,
                ignore_alarms_conditional=self._ignore_alarms_conditional))
            if reboot:
                stage.add_step(strategy.LockHostsStep(host_list))
            # Add the action step for these hosts (patch, etc..)
            stage.add_step(host_action_step(host_list))
            if reboot:
                # Cannot unlock right away after the host action
                stage.add_step(strategy.SystemStabilizeStep(
                               timeout_in_secs=MTCE_DELAY))
                stage.add_step(strategy.UnlockHostsStep(host_list))
                # After storage node(s) are unlocked, we need extra time to
                # allow the OSDs to go back in sync and the storage related
                # alarms to clear.
                stage.add_step(strategy.WaitDataSyncStep(
                    timeout_in_secs=30 * 60,
                    ignore_alarms=self._ignore_alarms))
            else:
                stage.add_step(strategy.SystemStabilizeStep(
                               timeout_in_secs=NO_REBOOT_DELAY))
            self.apply_phase.add_stage(stage)
        return True, ''


class PatchStorageHostsMixin(UpdateStorageHostsMixin):
    def _add_storage_strategy_stages(self, storage_hosts, reboot):
        """
        Add storage software patch stages to a strategy
        """
        from nfv_vim import strategy
        return self._add_update_storage_strategy_stages(
            storage_hosts,
            reboot,
            strategy.STRATEGY_STAGE_NAME.SW_PATCH_STORAGE_HOSTS,
            strategy.SwPatchHostsStep)


class SwDeployStorageHostsMixin(UpdateStorageHostsMixin):
    def _add_storage_strategy_stages(self, storage_hosts, reboot):
        """
        Add storage software patch stages to a strategy
        """
        from nfv_vim import strategy
        return self._add_update_storage_strategy_stages(
            storage_hosts,
            reboot,
            strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_STORAGE_HOSTS,
            strategy.UpgradeHostsStep)


class UpdateSystemConfigStorageHostsMixin(UpdateStorageHostsMixin):
    def _add_system_config_storage_strategy_stages(self, storage_hosts):
        """
        Add storage system config update stages to a strategy
        """
        from nfv_vim import strategy
        return self._add_update_storage_strategy_stages(
            storage_hosts,
            True,
            strategy.STRATEGY_STAGE_NAME.SYSTEM_CONFIG_UPDATE_STORAGE_HOSTS,
            strategy.SystemConfigUpdateHostsStep)


class UpdateWorkerHostsMixin(object):
    """
    Adds the ability to add update steps for worker hosts to a strategy.

    This includes adding swact, lock etc.. if the update step requires reboot.

    This mixin can only be used classes that subclass or mixin with:
    - SwUpdateStrategy: - provides _create_worker_host_lists
    - the strategy must have attributes:
       '_single_controller'
       '_worker_apply_type'
       '_default_instance_action'
       '_ignore_alarms'
    """

    def _add_update_worker_strategy_stages(self,
                                           worker_hosts,
                                           reboot,
                                           strategy_stage_name,
                                           host_action_step,
                                           extra_args=None):
        """
        Add worker update stages to a strategy
        The strategy_stage_name is the type of stage (patch, kube, etc..)
        The host_action_step is the step to invoke once hosts are locked, etc..
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        if SW_UPDATE_APPLY_TYPE.IGNORE != self._worker_apply_type:
            # When using a single controller/worker host that is running
            # OpenStack, only allow the stop/start instance action.
            if self._single_controller:
                for host in worker_hosts:
                    if host.openstack_compute and \
                            HOST_PERSONALITY.CONTROLLER in host.personality and \
                            SW_UPDATE_INSTANCE_ACTION.STOP_START != \
                            self._default_instance_action:
                        DLOG.error("Cannot migrate instances in a single "
                                   "controller configuration")
                        reason = 'cannot migrate instances in a single ' \
                                 'controller configuration'
                        return False, reason

        host_lists, reason = self._create_worker_host_lists(worker_hosts,
                                                            reboot)
        if host_lists is None:
            return False, reason

        instance_table = tables.tables_get_instance_table()

        for host_list in host_lists:
            instance_list = list()
            openstack_hosts = list()

            for host in host_list:
                if host.host_service_configured(HOST_SERVICES.COMPUTE):
                    openstack_hosts.append(host)
                for instance in instance_table.on_host(host.name):
                    # Do not take action (migrate or stop-start) on an instance
                    # if it is locked (i.e. stopped).
                    if not instance.is_locked():
                        instance_list.append(instance)

            hosts_to_lock = list()
            hosts_to_reboot = list()
            if reboot:
                hosts_to_lock = [x for x in host_list if not x.is_locked()]
                hosts_to_reboot = [x for x in host_list if x.is_locked()]

            stage = strategy.StrategyStage(strategy_stage_name)

            stage.add_step(strategy.QueryAlarmsStep(
                True, ignore_alarms=self._ignore_alarms,
                ignore_alarms_conditional=self._ignore_alarms_conditional))

            if reboot:
                if 1 == len(host_list):
                    if HOST_PERSONALITY.CONTROLLER in host_list[0].personality:
                        if not self._single_controller:
                            # Swact controller before locking
                            stage.add_step(strategy.SwactHostsStep(host_list))

                # Migrate or stop instances as necessary
                if SW_UPDATE_INSTANCE_ACTION.MIGRATE == self._default_instance_action:
                    # TODO(jkraitbe): Should probably be:
                    #   if len(openstack_hosts) and len(instance_list)
                    if len(openstack_hosts):
                        if SW_UPDATE_APPLY_TYPE.PARALLEL == self._worker_apply_type:
                            # Disable host services before migrating to ensure
                            # instances do not migrate to worker hosts in the
                            # same set of hosts.
                            stage.add_step(strategy.DisableHostServicesStep(
                                openstack_hosts, HOST_SERVICES.COMPUTE))
                            # TODO(ksmith)
                            # When support is added for orchestration on
                            # non-OpenStack worker nodes, support for disabling
                            # kubernetes services will have to be added.
                        stage.add_step(strategy.MigrateInstancesFromHostStep(
                            openstack_hosts, instance_list))
                elif len(instance_list):
                    stage.add_step(strategy.StopInstancesStep(instance_list))

                if hosts_to_lock:
                    wait_until_disabled = True
                    if 1 == len(hosts_to_lock):
                        if HOST_PERSONALITY.CONTROLLER in \
                                hosts_to_lock[0].personality:
                            if self._single_controller:
                                # A single controller will not go disabled when
                                # it is locked.
                                wait_until_disabled = False
                    # Lock hosts
                    stage.add_step(strategy.LockHostsStep(
                        hosts_to_lock, wait_until_disabled=wait_until_disabled))

            # Add the action step for these hosts (patch, etc..)
            if extra_args is None:
                stage.add_step(host_action_step(host_list))
            else:
                stage.add_step(host_action_step(host_list, extra_args))

            if reboot:
                # Cannot unlock right away after the action step
                stage.add_step(strategy.SystemStabilizeStep(
                               timeout_in_secs=MTCE_DELAY))
                if hosts_to_lock:
                    # Unlock hosts that were locked
                    stage.add_step(strategy.UnlockHostsStep(hosts_to_lock))
                if hosts_to_reboot:
                    # Reboot hosts that were already locked
                    stage.add_step(strategy.RebootHostsStep(hosts_to_reboot))

                if len(instance_list):
                    # Start any instances that were stopped
                    if SW_UPDATE_INSTANCE_ACTION.MIGRATE != self._default_instance_action:
                        stage.add_step(strategy.StartInstancesStep(instance_list))
                # After controller node(s) are unlocked, we need extra time to
                # allow the OSDs to go back in sync and the storage related
                # alarms to clear. Note: not all controller nodes will have
                # OSDs configured, but the alarms should clear quickly in
                # that case so this will not delay the update strategy.
                if any([HOST_PERSONALITY.CONTROLLER in host.personality
                        for host in hosts_to_lock + hosts_to_reboot]):
                    # Multiple personality nodes that need to wait for OSDs to sync:
                    stage.add_step(strategy.WaitAlarmsClearStep(
                                   timeout_in_secs=WAIT_ALARM_TIMEOUT,
                                   ignore_alarms=self._ignore_alarms,
                                   ignore_alarms_conditional=self._ignore_alarms_conditional))
                else:
                    if any([host.openstack_control or host.openstack_compute
                            for host in hosts_to_lock + hosts_to_reboot]):
                        # Hosts with openstack that just need to wait for services to start up:
                        stage.add_step(strategy.WaitAlarmsClearStep(
                                timeout_in_secs=10 * 60,
                                ignore_alarms=self._ignore_alarms))
                    else:
                        # Worker host wihout multiple personalities or openstack:
                        stage.add_step(strategy.SystemStabilizeStep())
            else:
                # Less time required if host is not rebooting:
                stage.add_step(strategy.SystemStabilizeStep(
                               timeout_in_secs=NO_REBOOT_DELAY))
            self.apply_phase.add_stage(stage)
        return True, ''


class PatchWorkerHostsMixin(UpdateWorkerHostsMixin):
    def _add_worker_strategy_stages(self, worker_hosts, reboot):
        from nfv_vim import strategy
        return self._add_update_worker_strategy_stages(
            worker_hosts,
            reboot,
            strategy.STRATEGY_STAGE_NAME.SW_PATCH_WORKER_HOSTS,
            strategy.SwPatchHostsStep)


class SwDeployWorkerHostsMixin(UpdateWorkerHostsMixin):
    def _add_worker_strategy_stages(self, worker_hosts, reboot):
        from nfv_vim import strategy
        return self._add_update_worker_strategy_stages(
            worker_hosts,
            reboot,
            strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_WORKER_HOSTS,
            strategy.UpgradeHostsStep)


class UpgradeKubeletWorkerHostsMixin(UpdateWorkerHostsMixin):
    def _add_kubelet_worker_strategy_stages(self, worker_hosts, to_version, reboot, stage_name):
        from nfv_vim import strategy
        return self._add_update_worker_strategy_stages(
            worker_hosts,
            reboot,
            stage_name,
            strategy.KubeHostUpgradeKubeletStep,
            extra_args=to_version)


class UpdateSystemConfigWorkerHostsMixin(UpdateWorkerHostsMixin):
    def _add_system_config_worker_strategy_stages(self, worker_hosts):
        """
        Add worker system config update stages to a strategy
        """
        from nfv_vim import strategy
        return self._add_update_worker_strategy_stages(
            worker_hosts,
            True,
            strategy.STRATEGY_STAGE_NAME.SYSTEM_CONFIG_UPDATE_WORKER_HOSTS,
            strategy.SystemConfigUpdateHostsStep)


###################################################################
#
# The Software Patch Strategy
#
###################################################################
class SwPatchStrategy(SwUpdateStrategy,
                      QuerySwPatchesMixin,
                      QuerySwPatchHostsMixin,
                      PatchControllerHostsMixin,
                      PatchStorageHostsMixin,
                      PatchWorkerHostsMixin):
    """
    Software Patch - Strategy
    """
    def __init__(self, uuid, controller_apply_type, storage_apply_type,
                 swift_apply_type, worker_apply_type,
                 max_parallel_worker_hosts, default_instance_action,
                 alarm_restrictions,
                 ignore_alarms,
                 single_controller):
        super(SwPatchStrategy, self).__init__(
            uuid,
            STRATEGY_NAME.SW_PATCH,
            controller_apply_type,
            storage_apply_type,
            swift_apply_type,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            ignore_alarms)

        # The following alarms will not prevent a software patch operation
        IGNORE_ALARMS = ['900.001',  # Patch in progress
                         '900.005',  # Upgrade in progress
                         '900.101',  # Software patch auto apply in progress
                         '200.001',  # Maintenance host lock alarm
                         '700.004',  # VM stopped
                         '280.002',  # Subcloud resource out-of-sync
                         '100.119',  # PTP alarm for SyncE
                         '900.701',  # Node tainted
                         ]
        IGNORE_ALARMS_CONDITIONAL = {'750.006': 1800}
        self._ignore_alarms += IGNORE_ALARMS
        self._single_controller = single_controller

        # This is to ignore the stale alarm(currently 750.006 is ignored).
        self._ignore_alarms_conditional = IGNORE_ALARMS_CONDITIONAL

        # initialize the variables required by the mixins
        # ie: self._nfvi_sw_patches, self._nfvi_sw_patch_hosts
        self.initialize_mixin()

    def build(self):
        """
        Build the strategy
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.SW_PATCH_QUERY)
        stage.add_step(
            strategy.QueryAlarmsStep(ignore_alarms=self._ignore_alarms,
            ignore_alarms_conditional=self._ignore_alarms_conditional))
        stage.add_step(strategy.QuerySwPatchesStep())
        stage.add_step(strategy.QuerySwPatchHostsStep())
        self.build_phase.add_stage(stage)
        super(SwPatchStrategy, self).build()

    def _add_swift_strategy_stages(self, swift_hosts, reboot):
        """
        Add swift software patch strategy stages
        todo(abailey): remove this if swift hosts are not supported
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        if SW_UPDATE_APPLY_TYPE.IGNORE != self._swift_apply_type:
            host_table = tables.tables_get_host_table()

            for host in swift_hosts:
                if HOST_PERSONALITY.SWIFT not in host.personality:
                    DLOG.error("Host inventory personality swift mismatch "
                               "detected for host %s." % host.name)
                    reason = 'host inventory personality swift mismatch detected'
                    return False, reason

            if 2 > host_table.total_by_personality(HOST_PERSONALITY.SWIFT):
                DLOG.warn("Not enough swift hosts to apply software patches.")
                reason = 'not enough swift hosts to apply software patches'
                return False, reason

        if self._swift_apply_type in [SW_UPDATE_APPLY_TYPE.SERIAL,
                                      SW_UPDATE_APPLY_TYPE.PARALLEL]:
            for host in swift_hosts:
                host_list = [host]
                stage = strategy.StrategyStage(
                    strategy.STRATEGY_STAGE_NAME.SW_PATCH_SWIFT_HOSTS)
                stage.add_step(strategy.QueryAlarmsStep(
                    True, ignore_alarms=self._ignore_alarms))
                if reboot:
                    stage.add_step(strategy.LockHostsStep(host_list))
                stage.add_step(strategy.SwPatchHostsStep(host_list))
                if reboot:
                    # Cannot unlock right away after SwPatchHostsStep
                    stage.add_step(strategy.SystemStabilizeStep(
                                   timeout_in_secs=MTCE_DELAY))
                    stage.add_step(strategy.UnlockHostsStep(host_list))
                    stage.add_step(strategy.SystemStabilizeStep())
                else:
                    stage.add_step(strategy.SystemStabilizeStep(
                                   timeout_in_secs=NO_REBOOT_DELAY))
                self.apply_phase.add_stage(stage)
        else:
            DLOG.verbose("Swift apply type set to ignore.")

        return True, ''

    def build_complete(self, result, result_reason):
        """
        Strategy Build Complete
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        result, result_reason = \
            super(SwPatchStrategy, self).build_complete(result, result_reason)

        DLOG.info("Build Complete Callback, result=%s, reason=%s."
                  % (result, result_reason))

        if result in [strategy.STRATEGY_RESULT.SUCCESS,
                      strategy.STRATEGY_RESULT.DEGRADED]:

            host_table = tables.tables_get_host_table()

            if not self.nfvi_sw_patches:
                DLOG.warn("No software patches found.")
                self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
                self.build_phase.result_reason = 'no software patches found'
                self.sw_update_obj.strategy_build_complete(
                    False, self.build_phase.result_reason)
                self.save()
                return

            if self._nfvi_alarms:
                DLOG.warn("Active alarms found, can't apply software patches.")
                self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
                self.build_phase.result_reason = 'active alarms present'
                self.sw_update_obj.strategy_build_complete(
                    False, self.build_phase.result_reason)
                self.save()
                return

            for host in list(host_table.values()):
                if HOST_PERSONALITY.WORKER in host.personality and \
                        HOST_PERSONALITY.CONTROLLER not in host.personality:
                    # Allow patch orchestration when worker hosts are available,
                    # locked or powered down.
                    if not ((host.is_unlocked() and host.is_enabled() and
                             host.is_available()) or
                            (host.is_locked() and host.is_disabled() and
                             host.is_offline()) or
                            (host.is_locked() and host.is_disabled() and
                             host.is_online())):
                        DLOG.warn(
                            "All worker hosts must be unlocked-enabled-available, "
                            "locked-disabled-online or locked-disabled-offline, "
                            "can't apply software patches.")
                        self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                        self.build_phase.result = \
                            strategy.STRATEGY_PHASE_RESULT.FAILED
                        self.build_phase.result_reason = (
                            'all worker hosts must be unlocked-enabled-available, '
                            'locked-disabled-online or locked-disabled-offline')
                        self.sw_update_obj.strategy_build_complete(
                            False, self.build_phase.result_reason)
                        self.save()
                        return
                else:
                    # Only allow patch orchestration when all controller,
                    # storage and swift hosts are available. It is not safe to
                    # automate patch application when we do not have full
                    # redundancy.
                    if not (host.is_unlocked() and host.is_enabled() and
                            host.is_available()):
                        DLOG.warn(
                            "All %s hosts must be unlocked-enabled-available, "
                            "can't apply software patches." % host.personality)
                        self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                        self.build_phase.result = \
                            strategy.STRATEGY_PHASE_RESULT.FAILED
                        self.build_phase.result_reason = (
                            'all %s hosts must be unlocked-enabled-available' %
                            host.personality)
                        self.sw_update_obj.strategy_build_complete(
                            False, self.build_phase.result_reason)
                        self.save()
                        return

            controllers = list()
            controllers_no_reboot = list()
            storage_hosts = list()
            storage_hosts_no_reboot = list()
            swift_hosts = list()
            swift_hosts_no_reboot = list()
            worker_hosts = list()
            worker_hosts_no_reboot = list()

            for sw_patch_host in self.nfvi_sw_patch_hosts:
                host = host_table.get(sw_patch_host.name, None)
                if host is None:
                    DLOG.error("Host inventory mismatch detected for host %s."
                               % sw_patch_host.name)
                    self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                    self.build_phase.result = \
                        strategy.STRATEGY_PHASE_RESULT.FAILED
                    self.build_phase.result_reason = \
                        'host inventory mismatch detected'
                    self.sw_update_obj.strategy_build_complete(
                        False, self.build_phase.result_reason)
                    self.save()
                    return

                if sw_patch_host.interim_state:
                    # A patch operation has been done recently and we don't
                    # have an up-to-date state for this host.
                    DLOG.warn("Host %s is in pending patch current state."
                              % sw_patch_host.name)
                    self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                    self.build_phase.result = \
                        strategy.STRATEGY_PHASE_RESULT.FAILED
                    self.build_phase.result_reason = (
                        'at least one host is in pending patch current state')
                    self.sw_update_obj.strategy_build_complete(
                        False, self.build_phase.result_reason)
                    self.save()
                    return

                if sw_patch_host.patch_current:
                    # No need to patch this host
                    continue

                if HOST_PERSONALITY.CONTROLLER in sw_patch_host.personality:
                    if sw_patch_host.requires_reboot:
                        controllers.append(host)
                    else:
                        controllers_no_reboot.append(host)

                elif HOST_PERSONALITY.STORAGE in sw_patch_host.personality:
                    if sw_patch_host.requires_reboot:
                        storage_hosts.append(host)
                    else:
                        storage_hosts_no_reboot.append(host)

                elif HOST_PERSONALITY.SWIFT in sw_patch_host.personality:
                    if sw_patch_host.requires_reboot:
                        swift_hosts.append(host)
                    else:
                        swift_hosts_no_reboot.append(host)

                # Separate if check to handle AIO where host has multiple
                # personality disorder.
                if HOST_PERSONALITY.WORKER in sw_patch_host.personality:
                    # Ignore worker hosts that are powered down
                    if not host.is_offline():
                        if sw_patch_host.requires_reboot:
                            worker_hosts.append(host)
                        else:
                            worker_hosts_no_reboot.append(host)

            STRATEGY_CREATION_COMMANDS = [
                (self._add_controller_strategy_stages,
                 controllers_no_reboot, False),
                (self._add_controller_strategy_stages,
                 controllers, True),
                (self._add_storage_strategy_stages,
                 storage_hosts_no_reboot, False),
                (self._add_storage_strategy_stages,
                 storage_hosts, True),
                (self._add_swift_strategy_stages,
                 swift_hosts_no_reboot, False),
                (self._add_swift_strategy_stages,
                 swift_hosts, True),
                (self._add_worker_strategy_stages,
                 worker_hosts_no_reboot, False),
                (self._add_worker_strategy_stages,
                 worker_hosts, True)
            ]

            for add_strategy_stages_function, host_list, reboot in \
                    STRATEGY_CREATION_COMMANDS:
                if host_list:
                    success, reason = add_strategy_stages_function(
                        host_list, reboot)
                    if not success:
                        self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                        self.build_phase.result = \
                            strategy.STRATEGY_PHASE_RESULT.FAILED
                        self.build_phase.result_reason = reason
                        self.sw_update_obj.strategy_build_complete(
                            False, self.build_phase.result_reason)
                        self.save()
                        return

            if 0 == len(self.apply_phase.stages):
                DLOG.warn("No software patches need to be applied.")
                self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
                self.build_phase.result_reason = ('no software patches need to be '
                                                  'applied')
                self.sw_update_obj.strategy_build_complete(
                    False, self.build_phase.result_reason)
                self.save()
                return
        else:
            self.sw_update_obj.strategy_build_complete(
                False, self.build_phase.result_reason)

        self.sw_update_obj.strategy_build_complete(True, '')
        self.save()

    def from_dict(self, data, build_phase=None, apply_phase=None, abort_phase=None):
        """
        Initializes a software patch strategy object using the given dictionary
        """
        super(SwPatchStrategy, self).from_dict(data, build_phase, apply_phase,
                                               abort_phase)

        self._single_controller = data['single_controller']

        # get the fields associated with the mixins:
        # ie: self._nfvi_sw_patch_hosts
        self.mixin_from_dict(data)
        return self

    def as_dict(self):
        """
        Represent the software patch strategy as a dictionary
        """
        data = super(SwPatchStrategy, self).as_dict()

        data['single_controller'] = self._single_controller

        # store mixin data to the data structure
        # ie: self._nfvi_sw_patch_hosts
        self.mixin_as_dict(data)
        return data


###################################################################
#
# The Software Upgrade Strategy
#
###################################################################
class SwUpgradeStrategy(
    SwUpdateStrategy,
    SwDeployControllerHostsMixin,
    SwDeployStorageHostsMixin,
    SwDeployWorkerHostsMixin,
):
    """
    Software Upgrade - Strategy
    """
    def __init__(self, uuid,
                 controller_apply_type, storage_apply_type, worker_apply_type,
                 max_parallel_worker_hosts, default_instance_action,
                 alarm_restrictions, release, rollback,
                 ignore_alarms, single_controller):
        super(SwUpgradeStrategy, self).__init__(
            uuid,
            STRATEGY_NAME.SW_UPGRADE,
            controller_apply_type,
            storage_apply_type,
            SW_UPDATE_APPLY_TYPE.IGNORE,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            ignore_alarms)

        self._release = release
        self._rollback = rollback

        # The following alarms will not prevent a software upgrade operation
        IGNORE_ALARMS = ['900.005',  # Upgrade in progress
                         '900.201',  # Software upgrade auto apply in progress
                         '750.006',  # Configuration change requires reapply of cert-manager
                         '100.119',  # PTP alarm for SyncE
                         '900.701',  # Node tainted
                         '900.231',  # Software deployment data is out of sync
                         ]
        self._ignore_alarms += IGNORE_ALARMS
        self._single_controller = single_controller
        self._nfvi_upgrade = None
        self._ignore_alarms_conditional = None

    @property
    def nfvi_upgrade(self):
        """
        Returns the upgrade from the NFVI layer
        """
        return self._nfvi_upgrade

    @nfvi_upgrade.setter
    def nfvi_upgrade(self, nfvi_upgrade):
        """
        Save the upgrade from the NFVI Layer
        """
        self._nfvi_upgrade = nfvi_upgrade

    def _build_normal(self):
        from nfv_vim import strategy

        stage = strategy.StrategyStage(strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_QUERY)
        stage.add_step(strategy.QueryAlarmsStep(ignore_alarms=self._ignore_alarms))
        stage.add_step(strategy.QueryUpgradeStep(release=self._release))
        stage.add_step(strategy.SwDeployPrecheckStep(release=self._release))
        self.build_phase.add_stage(stage)
        super(SwUpgradeStrategy, self).build()

    def _build_rollback(self):
        reason = "Rollback not supported yet."
        DLOG.warn(reason)
        self._state = strategy.STRATEGY_STATE.BUILD_FAILED
        self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
        self.build_phase.result_reason = reason
        self.sw_update_obj.strategy_build_complete(
            False, self.build_phase.result_reason)
        self.save()
        super(SwUpgradeStrategy, self).build()

    def build(self):
        """
        Build the strategy
        """

        if self._release is None and not self._rollback:
            reason = "Release or rollback must be set"
            DLOG.error(reason)
            self._state = strategy.STRATEGY_STATE.BUILD_FAILED
            self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
            self.build_phase.result_reason = reason
            self.sw_update_obj.strategy_build_complete(
                False, self.build_phase.result_reason)
            self.save()
            super(SwUpgradeStrategy, self).build()

        elif self._release is not None and self._rollback:
            reason = "Cannot set both release and rollback"
            DLOG.error(reason)
            self._state = strategy.STRATEGY_STATE.BUILD_FAILED
            self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
            self.build_phase.result_reason = reason
            self.sw_update_obj.strategy_build_complete(
                False, self.build_phase.result_reason)
            self.save()
            super(SwUpgradeStrategy, self).build()

        elif self._rollback:
            return self._build_rollback()

        else:
            return self._build_normal()

    def _swact_fix(self, stage, controller_name):
        """Add a SWACT to a stage on DX systems

        Currently, certain steps during sw-deploy must be done on a specific controller.
        Here we insert arbitrary SWACTs to meet those requirements.
        """

        if self._single_controller or not self.nfvi_upgrade.major_release:
            return

        from nfv_vim import strategy
        from nfv_vim import tables

        host_table = tables.tables_get_host_table()
        for host in host_table.get_by_personality(HOST_PERSONALITY.CONTROLLER):
            if controller_name == host.name:
                stage.add_step(strategy.SwactHostsStep([host]))
                break

    def _add_upgrade_start_stage(self):
        """
        Add upgrade start strategy stage
        """

        from nfv_vim import strategy

        stage = strategy.StrategyStage(strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_START)

        # If the release is not available the deployment is already started
        if self.nfvi_upgrade.is_available:
            stage.add_step(strategy.QueryAlarmsStep(True, ignore_alarms=self._ignore_alarms))
            # sw-deploy start for major releases must be done on controller-0
            self._swact_fix(stage, HOST_NAME.CONTROLLER_1)
            stage.add_step(strategy.UpgradeStartStep(release=self._release))
        else:
            DLOG.info("Software deployment already inprogress, skipping start")

        stage.add_step(strategy.SystemStabilizeStep(timeout_in_secs=MTCE_DELAY))
        self.apply_phase.add_stage(stage)

    def _add_upgrade_complete_stage(self):
        """
        Add upgrade complete strategy stage
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_COMPLETE)
        stage.add_step(strategy.QueryAlarmsStep(ignore_alarms=self._ignore_alarms))
        self._swact_fix(stage, HOST_NAME.CONTROLLER_1)
        stage.add_step(strategy.UpgradeActivateStep(release=self._release))
        stage.add_step(strategy.UpgradeCompleteStep(release=self._release))
        stage.add_step(strategy.SystemStabilizeStep())
        self.apply_phase.add_stage(stage)

    def _build_complete_normal(self, result, result_reason):
        from nfv_vim import strategy
        from nfv_vim import tables

        result, result_reason = \
            super(SwUpgradeStrategy, self).build_complete(result, result_reason)

        DLOG.info("Build Complete Callback, result=%s, reason=%s."
                  % (result, result_reason))

        if result in [strategy.STRATEGY_RESULT.SUCCESS,
                      strategy.STRATEGY_RESULT.DEGRADED]:
            if not self.nfvi_upgrade.release_info:
                reason = "Software release does not exist."
                DLOG.warn(reason)
                self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
                self.build_phase.result_reason = reason
                self.sw_update_obj.strategy_build_complete(
                    False, self.build_phase.result_reason)
                self.save()
                return

            if self.nfvi_upgrade.is_deployed or self.nfvi_upgrade.is_committed:
                reason = "Software release is already deployed or committed."
                DLOG.warn(reason)
                self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                self.build_phase.result = \
                    strategy.STRATEGY_PHASE_RESULT.FAILED
                self.build_phase.result_reason = reason
                self.sw_update_obj.strategy_build_complete(
                    False, self.build_phase.result_reason)
                self.save()
                return

            if self._nfvi_alarms:
                DLOG.warn("Active alarms found, can't apply sw-deployment.")
                self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
                self.build_phase.result_reason = 'active alarms present'
                self.sw_update_obj.strategy_build_complete(
                    False, self.build_phase.result_reason)
                self.save()
                return

            host_table = tables.tables_get_host_table()

            for host in list(host_table.values()):
                # All hosts must be unlock/enabled/available
                if not (host.is_unlocked() and host.is_enabled() and host.is_available()):
                    DLOG.warn(
                        "All hosts must be unlocked-enabled-available, "
                        "can't apply sw-deployment: %s" % host.name)
                    self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                    self.build_phase.result = \
                        strategy.STRATEGY_PHASE_RESULT.FAILED
                    self.build_phase.result_reason = (
                        'all %s hosts must be unlocked-enabled-available' %
                        host.personality)
                    self.sw_update_obj.strategy_build_complete(
                        False, self.build_phase.result_reason)
                    self.save()
                    return

            reboot_required = self.nfvi_upgrade.reboot_required
            controller_strategy = self._add_controller_strategy_stages
            controllers_hosts = list()
            storage_hosts = list()
            worker_hosts = list()

            self._add_upgrade_start_stage()

            for host in host_table.values():
                if HOST_PERSONALITY.CONTROLLER in host.personality:
                    controllers_hosts.append(host)
                    if HOST_PERSONALITY.WORKER in host.personality:
                        # We need to use this strategy on AIO type
                        controller_strategy = self._add_worker_strategy_stages

                elif HOST_PERSONALITY.STORAGE in host.personality:
                    storage_hosts.append(host)

                elif HOST_PERSONALITY.WORKER in host.personality:
                    worker_hosts.append(host)

                else:
                    DLOG.error(f"Unsupported personality for host {host.name}.")
                    self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                    self.build_phase.result = \
                        strategy.STRATEGY_PHASE_RESULT.FAILED
                    self.build_phase.result_reason = \
                        'Unsupported personality for host'
                    self.sw_update_obj.strategy_build_complete(
                        False, self.build_phase.result_reason)
                    self.save()
                    return

            if not self._single_controller and self.nfvi_upgrade.major_release:
                # Reverse controller hosts so controller-1 is first
                controllers_hosts = sorted(
                    controllers_hosts,
                    key=lambda x: x.name == HOST_NAME.CONTROLLER_0,
                )

            strategy_pairs = [
                (controller_strategy, controllers_hosts),
                (self._add_storage_strategy_stages, storage_hosts),
                (self._add_worker_strategy_stages, worker_hosts)
            ]

            for stage_func, host_list in strategy_pairs:
                if host_list:
                    success, reason = stage_func(host_list, reboot_required)
                    if not success:
                        self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                        self.build_phase.result = \
                            strategy.STRATEGY_PHASE_RESULT.FAILED
                        self.build_phase.result_reason = reason
                        self.sw_update_obj.strategy_build_complete(
                            False, self.build_phase.result_reason)
                        self.save()
                        return

            self._add_upgrade_complete_stage()

            if 0 == len(self.apply_phase.stages):
                DLOG.warn("No sw-deployments need to be applied.")
                self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
                self.build_phase.result_reason = ('no sw-deployments patches need to be '
                                                  'applied')
                self.sw_update_obj.strategy_build_complete(
                    False, self.build_phase.result_reason)
                self.save()
                return
        else:
            self.sw_update_obj.strategy_build_complete(
                False, self.build_phase.result_reason)

        self.sw_update_obj.strategy_build_complete(True, '')
        self.save()

    def _build_complete_rollback(self, result, result_reason):
        reason = "Rollback not supported yet."
        DLOG.warn(reason)
        self._state = strategy.STRATEGY_STATE.BUILD_FAILED
        self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
        self.build_phase.result_reason = reason
        self.sw_update_obj.strategy_build_complete(
            False, self.build_phase.result_reason)
        self.save()

    def build_complete(self, result, result_reason):
        """
        Strategy Build Complete
        """
        if self._rollback:
            return self._build_complete_rollback(result, result_reason)

        return self._build_complete_normal(result, result_reason)

    def from_dict(self, data, build_phase=None, apply_phase=None, abort_phase=None):
        """
        Initializes a software upgrade strategy object using the given dictionary
        """
        from nfv_vim import nfvi

        super(SwUpgradeStrategy, self).from_dict(data, build_phase, apply_phase,
                                                 abort_phase)
        self._single_controller = data['single_controller']
        self._release = data['release']
        self._rollback = data['rollback']
        nfvi_upgrade_data = data['nfvi_upgrade_data']
        if nfvi_upgrade_data:
            self._nfvi_upgrade = nfvi.objects.v1.Upgrade(
                nfvi_upgrade_data['release'],
                nfvi_upgrade_data['release_info'],
                nfvi_upgrade_data['deploy_info'],
                nfvi_upgrade_data['hosts_info'])
        else:
            self._nfvi_upgrade = None

        return self

    def as_dict(self):
        """
        Represent the software upgrade strategy as a dictionary
        """
        data = super(SwUpgradeStrategy, self).as_dict()
        data['single_controller'] = self._single_controller
        data['release'] = self._release
        data['rollback'] = self._rollback
        if self._nfvi_upgrade:
            nfvi_upgrade_data = self._nfvi_upgrade.as_dict()
        else:
            nfvi_upgrade_data = None
        data['nfvi_upgrade_data'] = nfvi_upgrade_data

        return data


###################################################################
#
# The System Config Update Strategy
#
###################################################################
class SystemConfigUpdateStrategy(SwUpdateStrategy,
                                 QuerySystemConfigUpdateHostsMixin,
                                 UpdateSystemConfigControllerHostsMixin,
                                 UpdateSystemConfigStorageHostsMixin,
                                 UpdateSystemConfigWorkerHostsMixin):
    """
    System Config Update - Strategy
    """
    def __init__(self, uuid, controller_apply_type, storage_apply_type,
                 worker_apply_type, max_parallel_worker_hosts,
                 default_instance_action, alarm_restrictions,
                 ignore_alarms, single_controller):
        super(SystemConfigUpdateStrategy, self).__init__(
            uuid,
            STRATEGY_NAME.SYSYTEM_CONFIG_UPDATE,
            controller_apply_type,
            storage_apply_type,
            SW_UPDATE_APPLY_TYPE.IGNORE,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            ignore_alarms)

        # The following alarms will not prevent a system config update operation
        IGNORE_ALARMS = ['100.103',  # Memory threshold exceeded
                         '100.119',  # PTP alarm for SyncE
                         '200.001',  # Locked Host
                         '250.001',  # System Config out of date
                         '260.001',  # Unreconciled resource
                         '260.002',  # Unsynchronized resource
                         '280.001',  # Subcloud resource off-line
                         '280.002',  # Subcloud resource out-of-sync
                         '280.003',  # Subcloud backup failed
                         '500.200',  # Certificate expiring soon
                         '700.004',  # VM stopped
                         '750.006',  # Configuration change requires reapply of an application
                         '900.010',  # System Config Update in progress
                         '900.601',  # System Config Update Auto Apply in progress
                         '900.701',  # Node tainted
                         ]
        self._ignore_alarms += IGNORE_ALARMS
        self._single_controller = single_controller
        self._ignore_alarms_conditional = None
        # initialize the variables required by the mixins
        self.initialize_mixin()

    def build(self):
        """
        Build the strategy
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.SYSTEM_CONFIG_UPDATE_QUERY)
        stage.add_step(strategy.QueryAlarmsStep(
            ignore_alarms=self._ignore_alarms))
        stage.add_step(strategy.QuerySystemConfigUpdateHostsStep())
        self.build_phase.add_stage(stage)
        super(SystemConfigUpdateStrategy, self).build()

    def build_complete(self, result, result_reason):
        """
        Strategy Build Complete
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        result, result_reason = \
            super(SystemConfigUpdateStrategy, self).build_complete(result, result_reason)

        DLOG.info("Build Complete Callback, result=%s, reason=%s."
                  % (result, result_reason))

        if result in [strategy.STRATEGY_RESULT.SUCCESS,
                      strategy.STRATEGY_RESULT.DEGRADED]:

            if self._nfvi_alarms:
                alarm_id_set = set()
                for alarm_data in self._nfvi_alarms:
                    alarm_id_set.add(alarm_data['alarm_id'])
                alarm_id_list = ", ".join(sorted(alarm_id_set))
                DLOG.warn("System config update: Active alarms present [ %s ]"
                          % alarm_id_list)
                self.report_build_failure("active alarms present [ %s ]"
                                          % alarm_id_list)

                return

            host_table = tables.tables_get_host_table()
            for host in list(host_table.values()):
                if HOST_PERSONALITY.WORKER in host.personality and \
                        HOST_PERSONALITY.CONTROLLER not in host.personality:
                    # Allow system config update orchestration when worker
                    # hosts are available, locked or powered down.
                    if not ((host.is_unlocked() and host.is_enabled() and
                             host.is_available()) or
                            (host.is_locked() and host.is_disabled() and
                             host.is_offline()) or
                            (host.is_locked() and host.is_disabled() and
                             host.is_online())):
                        self.report_build_failure(
                            "all worker hosts must be unlocked-enabled-available, "
                            "locked-disabled-online or locked-disabled-offline")
                        return
                else:
                    # Only allow system config update orchestration when all
                    # controller and storage hosts are available. The config
                    # update wil be blocked when we do not have full redundancy.
                    if not (host.is_unlocked() and host.is_enabled() and
                            host.is_available()):
                        self.report_build_failure(
                            "all %s hosts must be unlocked-enabled-available, "
                            % host.personality)
                        return

            controller_hosts = list()
            storage_hosts = list()
            worker_hosts = list()
            host_list = list(host_table.values())

            for host_resource in self.nfvi_system_config_update_hosts:
                for host in host_list:
                    if host_resource.name == host.name:
                        if HOST_PERSONALITY.CONTROLLER in host.personality and \
                                host_resource.unlock_request != 'not_required':
                            controller_hosts.append(host)

                        elif HOST_PERSONALITY.STORAGE in host.personality and \
                                host_resource.unlock_request != 'not_required':
                            storage_hosts.append(host)

                        if HOST_PERSONALITY.WORKER in host.personality and \
                                host_resource.unlock_request != 'not_required':
                            worker_hosts.append(host)

                        host_list.remove(host)
                        break

            STRATEGY_CREATION_COMMANDS = [
                (self._add_system_config_controller_strategy_stages,
                 controller_hosts),
                (self._add_system_config_storage_strategy_stages,
                 storage_hosts),
                (self._add_system_config_worker_strategy_stages,
                 worker_hosts)
            ]

            for add_strategy_stages_function, host_list in \
                    STRATEGY_CREATION_COMMANDS:
                if host_list:
                    success, reason = add_strategy_stages_function(host_list)
                    if not success:
                        self.report_build_failure(reason)
                        return

            if 0 == len(self.apply_phase.stages):
                self.report_build_failure(
                    "no system config updates need to be applied")
                return
        else:
            self.sw_update_obj.strategy_build_complete(  # pylint: disable=no-member
                False, self.build_phase.result_reason)

        self.sw_update_obj.strategy_build_complete(True, '')  # pylint: disable=no-member
        self.save()

    def from_dict(self, data, build_phase=None, apply_phase=None, abort_phase=None):
        """
        Initializes a system config update strategy object using the given
        dictionary
        """
        super(SystemConfigUpdateStrategy, self).from_dict(
            data, build_phase, apply_phase, abort_phase)
        self._single_controller = data['single_controller']

        self.mixin_from_dict(data)
        return self

    def as_dict(self):
        """
        Represent the software upgrade strategy as a dictionary
        """
        data = super(SystemConfigUpdateStrategy, self).as_dict()
        data['single_controller'] = self._single_controller

        self.mixin_as_dict(data)
        return data


###################################################################
#
# The Firmware Update Strategy
#
###################################################################
class FwUpdateStrategy(SwUpdateStrategy):
    """
    Firmware Update - Strategy - FPGA
    """
    def __init__(self, uuid, controller_apply_type, storage_apply_type,
                 worker_apply_type, max_parallel_worker_hosts,
                 default_instance_action,
                 alarm_restrictions, ignore_alarms,
                 single_controller):
        super(FwUpdateStrategy, self).__init__(
            uuid,
            STRATEGY_NAME.FW_UPDATE,
            controller_apply_type,
            storage_apply_type,
            SW_UPDATE_APPLY_TYPE.IGNORE,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            ignore_alarms)

        # The following alarms will not prevent a firmware update operation
        IGNORE_ALARMS = ['700.004',  # VM stopped
                         '280.002',  # Subcloud resource out-of-sync
                         '900.006',  # Device Image Update in progress
                         '900.301',  # Fw Update Auto Apply in progress
                         '200.001',  # Locked Host
                         '100.119',  # PTP alarm for SyncE
                         '900.701',  # Node tainted
                         ]

        self._ignore_alarms += IGNORE_ALARMS
        self._single_controller = single_controller

        self._fail_on_alarms = True

        # list of hostnames that need update
        self._fw_update_hosts = list()

    @property
    def fw_update_hosts(self):
        """
        Returns a list of hostnames that require firmware update
        """
        return self._fw_update_hosts

    @fw_update_hosts.setter
    def fw_update_hosts(self, fw_update_hosts):
        """
        Save a list of hostnames that require firmware update
        """
        self._fw_update_hosts = fw_update_hosts

    def build(self):
        """
        Build the strategy
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.FW_UPDATE_HOSTS_QUERY)

        # Firmware update is only supported for hosts that support
        # the worker function.
        if self._worker_apply_type == SW_UPDATE_APPLY_TYPE.IGNORE:
            msg = "apply type is 'ignore' ; must be '%s' or '%s'" % \
                  (SW_UPDATE_APPLY_TYPE.SERIAL,
                   SW_UPDATE_APPLY_TYPE.PARALLEL)
            DLOG.warn("Worker %s" % msg)
            self._state = strategy.STRATEGY_STATE.BUILD_FAILED
            self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
            self.build_phase.result_reason = "Worker " + msg
            self.sw_update_obj.strategy_build_complete(  # pylint: disable=no-member
                False, self.build_phase.result_reason)
            self.save()
            return

        stage.add_step(strategy.QueryAlarmsStep(
            self._fail_on_alarms,
            ignore_alarms=self._ignore_alarms))

        # using existing vim host inventory add a step for each host
        host_table = tables.tables_get_host_table()
        for host in list(host_table.values()):
            if HOST_PERSONALITY.WORKER in host.personality:
                if host.is_unlocked() and host.is_enabled():
                    stage.add_step(strategy.QueryFwUpdateHostStep(host))

        self.build_phase.add_stage(stage)
        super(FwUpdateStrategy, self).build()

    def _add_worker_strategy_stages(self, worker_hosts, reboot):
        """
        Add worker firmware update strategy stages
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        hostnames = ''
        for host in worker_hosts:
            hostnames += host.name + ' '
        DLOG.info("Worker hosts that require firmware update: %s " % hostnames)

        # When using a single controller/worker host that is running
        # OpenStack, only allow the stop/start instance action.
        if self._single_controller:
            for host in worker_hosts:
                if host.openstack_compute and \
                        HOST_PERSONALITY.CONTROLLER in host.personality and \
                        SW_UPDATE_INSTANCE_ACTION.STOP_START != \
                        self._default_instance_action:
                    DLOG.error("Cannot migrate instances in a single "
                               "controller configuration")
                    reason = 'cannot migrate instances in a single ' \
                             'controller configuration'
                    return False, reason

        # Returns a list of 'host update lists' based on serial vs parallel
        # update specification and the overall host pool and various aspects
        # of the hosts in that pool ; i.e. personality, instances, etc.
        host_lists, reason = self._create_worker_host_lists(worker_hosts, reboot)
        if host_lists is None:
            DLOG.info("failed to create worker host lists")
            return False, reason

        instance_table = tables.tables_get_instance_table()

        # Loop over the host aggregate lists creating back to back steps
        # that will update all the worker hosts in the order dictated
        # by the strategy.
        for host_list in host_lists:

            # Start the Update Worker Hosts Stage ; the stage that includes all
            # the steps to update all the worker hosts found to need firmware update.
            stage = strategy.StrategyStage(strategy.STRATEGY_STAGE_NAME.FW_UPDATE_WORKER_HOSTS)

            # build a list of unlocked instances
            instance_list = list()
            for host in host_list:
                for instance in instance_table.on_host(host.name):
                    # Do not take action (migrate or stop-start) on
                    # an instance if it is locked (i.e. stopped).
                    if not instance.is_locked():
                        instance_list.append(instance)

            # Handle alarms that show up after create but before apply.
            stage.add_step(strategy.QueryAlarmsStep(
                self._fail_on_alarms,
                ignore_alarms=self._ignore_alarms))

            # Issue Firmware Update for hosts in host_list
            stage.add_step(strategy.FwUpdateHostsStep(host_list))

            # Handle reboot-required option with host lock/unlock.
            if reboot:
                if 1 == len(host_list):
                    if HOST_PERSONALITY.CONTROLLER in host_list[0].personality:
                        if not self._single_controller:
                            # Handle upgrade of both controllers
                            # in AIO DX Swact controller before locking.
                            # If this is not the active controller then it has no effect
                            stage.add_step(strategy.SwactHostsStep(host_list))

                # Handle instance migration
                if len(instance_list):
                    # Migrate or stop instances as necessary
                    if SW_UPDATE_INSTANCE_ACTION.MIGRATE == \
                            self._default_instance_action:
                        if SW_UPDATE_APPLY_TYPE.PARALLEL == \
                                self._worker_apply_type:
                            # Disable host services before migrating to ensure
                            # instances do not migrate to worker hosts in the
                            # same set of hosts.
                            if host_list[0].host_service_configured(
                                    HOST_SERVICES.COMPUTE):
                                stage.add_step(strategy.DisableHostServicesStep(
                                    host_list, HOST_SERVICES.COMPUTE))
                            # TODO(ksmith)
                            # When support is added for orchestration on
                            # non-OpenStack worker nodes, support for disabling
                            # kubernetes services will have to be added.
                        stage.add_step(strategy.MigrateInstancesStep(
                            instance_list))
                    else:
                        stage.add_step(strategy.StopInstancesStep(
                            instance_list))

                wait_until_disabled = True
                if 1 == len(host_list):
                    if HOST_PERSONALITY.CONTROLLER in \
                            host_list[0].personality:
                        if self._single_controller:
                            # Handle upgrade of AIO SX
                            # A single controller will not go disabled when
                            # it is locked.
                            wait_until_disabled = False

                # Lock hosts
                stage.add_step(strategy.LockHostsStep(host_list, wait_until_disabled=wait_until_disabled))

                # Wait for system to stabilize
                stage.add_step(strategy.SystemStabilizeStep(timeout_in_secs=MTCE_DELAY))

                # Unlock hosts
                stage.add_step(strategy.UnlockHostsStep(host_list))

                if 0 != len(instance_list):
                    # Start any instances that were stopped
                    if SW_UPDATE_INSTANCE_ACTION.MIGRATE != \
                            self._default_instance_action:
                        stage.add_step(strategy.StartInstancesStep(
                            instance_list))

                stage.add_step(strategy.SystemStabilizeStep())
            else:
                # Less time required if host is not rebooting
                stage.add_step(strategy.SystemStabilizeStep(
                               timeout_in_secs=NO_REBOOT_DELAY))

            self.apply_phase.add_stage(stage)

        return True, ''

    def build_complete(self, result, result_reason):
        """
        Strategy Build Complete
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        result, result_reason = \
            super(FwUpdateStrategy, self).build_complete(result, result_reason)

        DLOG.verbose("Build Complete Callback, result=%s, reason=%s." %
                    (result, result_reason))

        if result in [strategy.STRATEGY_RESULT.SUCCESS,
                      strategy.STRATEGY_RESULT.DEGRADED]:

            if self._nfvi_alarms:
                # Fail create strategy if unignored alarms present
                DLOG.warn("Active alarms found, can't update firmware.")
                alarm_id_list = ""
                for alarm_data in self._nfvi_alarms:
                    if alarm_id_list:
                        alarm_id_list += ', '
                    alarm_id_list += alarm_data['alarm_id']
                DLOG.warn("... active alarms: %s" % alarm_id_list)
                self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
                self.build_phase.result_reason = 'active alarms present ; '
                self.build_phase.result_reason += alarm_id_list
                self.sw_update_obj.strategy_build_complete(  # pylint: disable=no-member
                    False, self.build_phase.result_reason)
                self.save()
                return

            # Fail if no hosts require firmware upgrade.
            if len(self._fw_update_hosts) == 0:
                self.build_phase.result_reason = "no firmware update required"
                DLOG.warn(self.build_phase.result_reason)
                self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
                self.sw_update_obj.strategy_build_complete(  # pylint: disable=no-member
                    False, self.build_phase.result_reason)
                self.save()
                return

            worker_hosts = list()
            host_table = tables.tables_get_host_table()
            for host in list(host_table.values()):
                if host.name in self._fw_update_hosts:
                    worker_hosts.append(host)

            STRATEGY_CREATION_COMMANDS = [
                (self._add_worker_strategy_stages,
                 worker_hosts, True)]

            for add_strategy_stages_function, host_list, reboot in \
                    STRATEGY_CREATION_COMMANDS:
                if host_list:
                    success, reason = add_strategy_stages_function(
                        host_list, reboot)
                    if not success:
                        self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                        self.build_phase.result = \
                            strategy.STRATEGY_PHASE_RESULT.FAILED
                        self.build_phase.result_reason = reason
                        self.sw_update_obj.strategy_build_complete(  # pylint: disable=no-member
                            False, self.build_phase.result_reason)
                        self.save()
                        return
        else:
            self.sw_update_obj.strategy_build_complete(  # pylint: disable=no-member
                False, self.build_phase.result_reason)

        self.sw_update_obj.strategy_build_complete(True, '')  # pylint: disable=no-member
        self.save()

    def from_dict(self,
                  data,
                  build_phase=None,
                  apply_phase=None,
                  abort_phase=None):
        """
        Load firmware update strategy object from dict data.
        """
        from nfv_vim import nfvi

        super(FwUpdateStrategy, self).from_dict(
            data, build_phase, apply_phase, abort_phase)

        self._single_controller = data['single_controller']

        # Load nfvi alarm data
        nfvi_alarms = list()
        nfvi_alarms_data = data.get('nfvi_alarms_data')
        if nfvi_alarms_data:
            for alarm_data in data['nfvi_alarms_data']:
                alarm = nfvi.objects.v1.Alarm(
                    alarm_data['alarm_uuid'], alarm_data['alarm_id'],
                    alarm_data['entity_instance_id'], alarm_data['severity'],
                    alarm_data['reason_text'], alarm_data['timestamp'],
                    alarm_data['mgmt_affecting'])
                nfvi_alarms.append(alarm)
            self._nfvi_alarms = nfvi_alarms
        return self

    def as_dict(self):
        """
        Return firmware update strategy nfvi data object as dictionary.
        """
        data = super(FwUpdateStrategy, self).as_dict()

        data['single_controller'] = self._single_controller

        #  Save nfvi alarm info to data
        if self._nfvi_alarms:
            nfvi_alarms_data = list()
            for alarm in self._nfvi_alarms:
                nfvi_alarms_data.append(alarm.as_dict())
            data['nfvi_alarms_data'] = nfvi_alarms_data
        return data


###################################################################
#
# The Kubernetes RootCa Update Strategy
#
###################################################################
class KubeRootcaUpdateStrategy(SwUpdateStrategy,
                               QueryKubeRootcaUpdatesMixin,
                               QueryKubeRootcaHostUpdatesMixin):
    """
    Kubernetes RootCa Update - Strategy
    """
    def __init__(self,
                 uuid,
                 controller_apply_type,
                 storage_apply_type,
                 worker_apply_type,
                 max_parallel_worker_hosts,
                 default_instance_action,
                 alarm_restrictions,
                 ignore_alarms,
                 single_controller,
                 expiry_date,
                 subject,
                 cert_file):
        super(KubeRootcaUpdateStrategy, self).__init__(
            uuid,
            STRATEGY_NAME.KUBE_ROOTCA_UPDATE,
            controller_apply_type,
            storage_apply_type,
            SW_UPDATE_APPLY_TYPE.IGNORE,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            ignore_alarms)

        # The following alarms will NOT prevent a kube rootca update operation
        # todo(abailey): remove memory alarm from this list if possible
        IGNORE_ALARMS = [
            '100.103',  # Memory threshold exceeded
            '100.119',  # PTP alarm for SyncE
            '200.001',  # Locked Host
            '280.001',  # Subcloud resource off-line
            '280.002',  # Subcloud resource out-of-sync
            '500.200',  # Certificate expiring soon
            '500.210',  # Certificate expired
            '700.004',  # VM stopped
            '750.006',  # Configuration change requires reapply of cert-manager
            '900.008',  # Kubernetes rootca update in progress
            '900.009',  # Kubernetes rootca update aborted
            '900.501',  # Kubernetes rootca update auto-apply inprogress
            '900.701',  # Node tainted
        ]
        # self._ignore_alarms is declared in parent class
        self._ignore_alarms += IGNORE_ALARMS

        # the following attributes need to be handled in from_dict/as_dict
        self._single_controller = single_controller
        self._expiry_date = expiry_date
        self._subject = subject
        self._cert_file = cert_file

        # initialize the variables required by the mixins
        self.initialize_mixin()

    def build(self):
        """Build the strategy"""
        from nfv_vim import strategy

        # Initial stage is a query of existing kube rootca update
        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_ROOTCA_UPDATE_QUERY)
        stage.add_step(strategy.QueryAlarmsStep(
            ignore_alarms=self._ignore_alarms))
        # these query steps are paired with mixins that process their results
        stage.add_step(strategy.QueryKubeRootcaUpdateStep())
        stage.add_step(strategy.QueryKubeRootcaHostUpdatesStep())
        self.build_phase.add_stage(stage)
        super(KubeRootcaUpdateStrategy, self).build()

    def _add_kube_rootca_update_start_stage(self):
        """
        Add kube-rootca-update start strategy stage
        This stage only occurs when no kube rootca update has been initiated.
        """
        from nfv_vim import strategy
        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_ROOTCA_UPDATE_START)
        stage.add_step(strategy.KubeRootcaUpdateStartStep())
        self.apply_phase.add_stage(stage)
        # Proceed to the next stage
        self._add_kube_rootca_update_cert_stage()

    def _add_kube_rootca_update_cert_stage(self):
        """
        Add kube-rootca-update cert strategy stage
        This stage either uploads an existing cert, or generates one.
        The upload option requires the path for the file to upload.
        The generate option supports a expiry_date and subject  option.
        This stage is skipped if a previous update has already performed this
        activity.
        """
        from nfv_vim import strategy
        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_ROOTCA_UPDATE_CERT)
        # if there is an existing cert file, upload it
        if self._cert_file:
            stage.add_step(
                strategy.KubeRootcaUpdateUploadCertStep(self._cert_file))
        else:
            stage.add_step(
                strategy.KubeRootcaUpdateGenerateCertStep(self._expiry_date,
                                                          self._subject))
        self.apply_phase.add_stage(stage)
        # Proceed to the next stage
        self._add_kube_rootca_hosts_trustbothcas_stage()

    def _determine_kube_rootca_host_lists(self, success_state):
        """
        Utility method to get host lists (list of lists) for a rootca update
        Storage hosts are excluded
        """
        from nfv_vim import tables
        host_table = tables.tables_get_host_table()

        hosts_to_update = list()

        rootca_host_map = dict()
        if self.nfvi_kube_rootca_host_update_list:
            for k_host in self.nfvi_kube_rootca_host_update_list:
                rootca_host_map[k_host.hostname] = k_host.state

        for host in host_table.values():
            # if we do not have the host in the map or its state does not match
            # then we need to process it
            if rootca_host_map.get(host.name) != success_state:
                if HOST_PERSONALITY.CONTROLLER in host.personality:
                    hosts_to_update.append(host)
                elif HOST_PERSONALITY.WORKER in host.personality:
                    hosts_to_update.append(host)
                else:
                    DLOG.info("Skipping host: %s of personality: %s"
                              % (host.name, host.personality))
            else:
                DLOG.info("Skipping up to date host: %s (%s)"
                          % (host.name, success_state))

        host_lists = list()
        if hosts_to_update:
            # sort the hosts by name, to provide predicability
            sorted_hosts = sorted(hosts_to_update, key=lambda host: host.name)
            for host in sorted_hosts:
                host_lists.append([host])
        return host_lists

    def _add_kube_rootca_hosts_trustbothcas_stage(self):
        """
        Add kube-rootca-update host trustbothcas strategy stages
        This stage is performed on the hosts
        """
        host_lists = self._determine_kube_rootca_host_lists(
            KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATED_HOST_TRUSTBOTHCAS)
        if host_lists:
            from nfv_vim import strategy
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.KUBE_ROOTCA_UPDATE_HOSTS_TRUSTBOTHCAS)
            for hosts in host_lists:
                stage.add_step(
                    strategy.KubeRootcaUpdateHostTrustBothcasStep(hosts))
            # todo(abailey) consider adding a host query
            self.apply_phase.add_stage(stage)
        # Proceed to the next stage
        self._add_kube_rootca_update_pods_trustbothcas_stage()

    def _add_kube_rootca_update_pods_trustbothcas_stage(self):
        """
        Add kube-rootca-update 'pods' trustbothcas strategy stage
        This stage is performed on the pods.
        """
        from nfv_vim import strategy
        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_ROOTCA_UPDATE_PODS_TRUSTBOTHCAS)
        stage.add_step(strategy.KubeRootcaUpdatePodsTrustBothcasStep())
        self.apply_phase.add_stage(stage)
        # Proceed to the next stage
        self._add_kube_rootca_hosts_update_certs_stage()

    def _add_kube_rootca_hosts_update_certs_stage(self):
        """
        Add kube-rootca-update host update certs strategy stages
        This stage is performed on the hosts
        """
        host_lists = self._determine_kube_rootca_host_lists(
            KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATED_HOST_UPDATECERTS)
        if host_lists:
            from nfv_vim import strategy
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.KUBE_ROOTCA_UPDATE_HOSTS_UPDATECERTS)
            for hosts in host_lists:
                stage.add_step(
                    strategy.KubeRootcaUpdateHostUpdateCertsStep(hosts))
            self.apply_phase.add_stage(stage)
        # Proceed to the next stage
        self._add_kube_rootca_hosts_trustnewca_stage()

    def _add_kube_rootca_hosts_trustnewca_stage(self):
        """
        Add kube-rootca-update host trustnewca strategy stages
        This stage is performed on the hosts
        """
        host_lists = self._determine_kube_rootca_host_lists(
            KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATED_HOST_TRUSTNEWCA)
        if host_lists:
            from nfv_vim import strategy
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.KUBE_ROOTCA_UPDATE_HOSTS_TRUSTNEWCA)
            for hosts in host_lists:
                stage.add_step(
                    strategy.KubeRootcaUpdateHostTrustNewcaStep(hosts))
            self.apply_phase.add_stage(stage)
        # Proceed to the next stage
        self._add_kube_rootca_update_pods_trustnewca_stage()

    def _add_kube_rootca_update_pods_trustnewca_stage(self):
        """
        Add kube-rootca-update 'pods' trustnewca strategy stage
        This stage is performed on the pods.
        """
        from nfv_vim import strategy
        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_ROOTCA_UPDATE_PODS_TRUSTNEWCA)
        stage.add_step(strategy.KubeRootcaUpdatePodsTrustNewcaStep())
        self.apply_phase.add_stage(stage)
        # Proceed to the next stage
        self._add_kube_rootca_update_complete_stage()

    def _add_kube_rootca_update_complete_stage(self):
        """
        Add kube rootca update complete strategy stage
        This stage occurs after all kube rootca are updated
        """
        from nfv_vim import strategy
        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_ROOTCA_UPDATE_COMPLETE)
        stage.add_step(strategy.KubeRootcaUpdateCompleteStep())
        self.apply_phase.add_stage(stage)
        # There is no next stage. this is the final stage of the strategy

    def build_complete(self, result, result_reason):
        """
        Strategy Build Complete
        """
        from nfv_vim import nfvi
        from nfv_vim import strategy

        RESUME_STATE = {
            # update was aborted, this means it needs to be recreated
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATE_ABORTED:
                self._add_kube_rootca_update_start_stage,
            # after update-started -> generate or upload cert
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATE_STARTED:
                self._add_kube_rootca_update_cert_stage,

            # after generated or uploaded, host trustbothcas stage
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATE_CERT_GENERATED:
                self._add_kube_rootca_hosts_trustbothcas_stage,
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATE_CERT_UPLOADED:
                self._add_kube_rootca_hosts_trustbothcas_stage,

            # handle interruption updating hosts trustbothcas -> retry
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATING_HOST_TRUSTBOTHCAS:
                self._add_kube_rootca_hosts_trustbothcas_stage,
            # handle failure updating hosts trustbothcas -> retry
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATING_HOST_TRUSTBOTHCAS_FAILED:
                self._add_kube_rootca_hosts_trustbothcas_stage,
            # handle success updating hosts trustbothcas -> pods trustbothcas
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATED_HOST_TRUSTBOTHCAS:
                self._add_kube_rootca_update_pods_trustbothcas_stage,

            # handle interruption updating the pods for trust both ca -> retry
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATING_PODS_TRUSTBOTHCAS:
                self._add_kube_rootca_update_pods_trustbothcas_stage,
            # handle failure updating the pods for trust both ca -> retry)
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATING_PODS_TRUSTBOTHCAS_FAILED:
                self._add_kube_rootca_update_pods_trustbothcas_stage,
            # handle success updating pods trust both ca - > update certs
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATED_PODS_TRUSTBOTHCAS:
                self._add_kube_rootca_hosts_update_certs_stage,

            # handle interruption updating the certs for hosts -> retry
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATING_HOST_UPDATECERTS:
                self._add_kube_rootca_hosts_update_certs_stage,
            # handle failure updating the certs for hosts -> retry
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATING_HOST_UPDATECERTS_FAILED:
                self._add_kube_rootca_hosts_update_certs_stage,
            # handle success updating the certs for hosts -> hosts trust new ca
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATED_HOST_UPDATECERTS:
                self._add_kube_rootca_hosts_trustnewca_stage,

            # handle interruption updating hosts trust new ca -> retry
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATING_HOST_TRUSTNEWCA:
                self._add_kube_rootca_hosts_trustnewca_stage,
            # handle failure updating hosts trust new ca -> retry
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATING_HOST_TRUSTNEWCA_FAILED:
                self._add_kube_rootca_hosts_trustnewca_stage,
            # handle success updating hosts trust new ca -> pods trust new ca
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATED_HOST_TRUSTNEWCA:
                self._add_kube_rootca_update_pods_trustnewca_stage,

            # handle interruption updating the pods for trust new ca -> retry
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATING_PODS_TRUSTNEWCA:
                self._add_kube_rootca_update_pods_trustnewca_stage,
            # handle failure updating the pods for trust new ca -> retry)
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATING_PODS_TRUSTNEWCA_FAILED:
                self._add_kube_rootca_update_pods_trustnewca_stage,
            # handle success while updating pods trust new ca - > complete
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATED_PODS_TRUSTNEWCA:
                self._add_kube_rootca_update_complete_stage,

            # update is completed, usually this gets deleted.
            nfvi.objects.v1.KUBE_ROOTCA_UPDATE_STATE.KUBE_ROOTCA_UPDATE_COMPLETED:
                self._add_kube_rootca_update_complete_stage,
        }

        result, result_reason = \
            super(KubeRootcaUpdateStrategy, self).build_complete(result,
                                                                 result_reason)

        DLOG.verbose("Build Complete Callback, result=%s, reason=%s."
                     % (result, result_reason))

        if result in [strategy.STRATEGY_RESULT.SUCCESS,
                      strategy.STRATEGY_RESULT.DEGRADED]:

            if self._nfvi_alarms:
                # Fail create strategy if unignored alarms present
                # add the alarm ids to the result reason.
                # eliminate duplicates  using a set, and sort the list
                alarm_id_set = set()
                for alarm_data in self._nfvi_alarms:
                    alarm_id_set.add(alarm_data['alarm_id'])
                alarm_id_list = ", ".join(sorted(alarm_id_set))

                DLOG.warn("kube rootca update: Active alarms present [ %s ]"
                          % alarm_id_list)
                self.report_build_failure("active alarms present [ %s ]"
                                          % alarm_id_list)
                return

            if self.nfvi_kube_rootca_update is None:
                # Start kube rootca update at the first stage
                self._add_kube_rootca_update_start_stage()
            else:
                # Determine which stage to resume at
                current_state = self.nfvi_kube_rootca_update.state
                resume_from_stage = RESUME_STATE.get(current_state)
                if resume_from_stage is None:
                    self.report_build_failure(
                        "Unable to resume kube rootca update from state: %s"
                        % current_state)
                    return
                else:
                    # Invoke the method that resumes the build from the stage
                    resume_from_stage()
        else:
            # build did not succeed. set failed.
            self.report_build_failure(result_reason)
            return

        # successful build
        self.sw_update_obj.strategy_build_complete(True, '')
        self.save()

    def from_dict(self, data, build_phase=None, apply_phase=None,
                  abort_phase=None):
        """
        Initializes a kube rootca update strategy object from a dictionary
        """
        super(KubeRootcaUpdateStrategy, self).from_dict(data,
                                                        build_phase,
                                                        apply_phase,
                                                        abort_phase)
        self._single_controller = data['single_controller']
        self._expiry_date = data.get('expiry_date')
        self._subject = data.get('subject')
        self._cert_file = data.get('cert_file')
        self.mixin_from_dict(data)
        return self

    def as_dict(self):
        """
        Represent the kube rootca update strategy as a dictionary
        """
        data = super(KubeRootcaUpdateStrategy, self).as_dict()
        data['single_controller'] = self._single_controller
        data['expiry_date'] = self._expiry_date
        data['subject'] = self._subject
        data['cert_file'] = self._cert_file
        self.mixin_as_dict(data)
        return data


###################################################################
#
# The Kubernetes Upgrade Strategy
#
###################################################################
class KubeUpgradeStrategy(SwUpdateStrategy,
                          QueryKubeUpgradesMixin,
                          QueryKubeHostUpgradesMixin,
                          QueryKubeVersionsMixin,
                          UpgradeKubeletControllerHostsMixin,
                          UpgradeKubeletWorkerHostsMixin):
    """
    Kubernetes Upgrade - Strategy
    """
    def __init__(self,
                 uuid,
                 controller_apply_type,
                 storage_apply_type,
                 worker_apply_type,
                 max_parallel_worker_hosts,
                 default_instance_action,
                 alarm_restrictions,
                 ignore_alarms,
                 to_version,
                 single_controller):
        super(KubeUpgradeStrategy, self).__init__(
            uuid,
            STRATEGY_NAME.KUBE_UPGRADE,
            controller_apply_type,
            storage_apply_type,
            SW_UPDATE_APPLY_TYPE.IGNORE,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            ignore_alarms)

        # The following alarms will NOT prevent a kube upgrade operation
        # Note: if an alarm is critical (ex: memory), it will still block the
        # kube upgrade due to the host being degraded.
        # todo(abailey): remove memory alarm from this list if possible
        IGNORE_ALARMS = [
            '100.103',  # Memory threshold exceeded
            '100.119',  # PTP alarm for SyncE
            '200.001',  # Locked Host
            '280.001',  # Subcloud resource off-line
            '280.002',  # Subcloud resource out-of-sync
            '700.004',  # VM stopped
            '750.006',  # Configuration change requires reapply of cert-manager
            '900.007',  # Kube Upgrade in progress
            '900.401',  # kube-upgrade-auto-apply-inprogress
            '900.701',  # Node tainted
        ]
        # self._ignore_alarms is declared in parent class
        self._ignore_alarms += IGNORE_ALARMS
        self._ignore_alarms_conditional = None
        # to_version and single_controller MUST be serialized
        self._to_version = to_version
        self._single_controller = single_controller

        # initialize the variables required by the mixins
        self.initialize_mixin()

    @property
    def to_version(self):
        """
        Returns the read only kube upgrade 'to_version' for this strategy
        """
        return self._to_version

    def build(self):
        """
        Build the strategy
        """
        from nfv_vim import strategy

        # Initial stage is a query of existing kube upgrade
        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_QUERY)

        # these query steps are paired with mixins that process their results
        stage.add_step(strategy.QueryAlarmsStep(
            ignore_alarms=self._ignore_alarms))
        stage.add_step(strategy.QueryKubeVersionsStep())
        stage.add_step(strategy.QueryKubeUpgradeStep())
        # cleanup kube upgrade if 'upgrade-aborted'
        stage.add_step(strategy.KubeUpgradeCleanupAbortedStep())

        # query hosts last, after any aborted upgrade is cleaned up
        stage.add_step(strategy.QueryKubeHostUpgradeStep())

        self.build_phase.add_stage(stage)
        super(KubeUpgradeStrategy, self).build()

    def _get_kube_version_steps(self, target_version, kube_list):
        """Returns an ordered list for a multi-version kubernetes upgrade

        Returns an ordered list of kubernetes versions to complete the upgrade
         If the target is already the active version, the list will be empty
        Raises an exception if the kubernetes chain is broken
        """
        # convert the kube_list into a dictionary indexed by version
        kube_dict = {}
        for kube in kube_list:
            kube_dict[kube['kube_version']] = kube

        # Populate the kube_sequence
        # Start with the target version and traverse based on the
        # 'upgrade_from' field.
        # The loop ends when we reach the active/partial version
        # The loop always inserts at the 'front' of the kube_sequence
        kube_sequence = []
        ver = target_version
        loop_count = 0
        while True:
            # We should never encounter a version that is not in the dict
            kube = kube_dict.get(ver)
            if kube is None:
                # We do not raise an exception. if the lowest version is
                # 'partial' its 'upgrade_from' will not exist in the dict,
                # so we can stop iterating
                break

            # We do not add the 'active' version to the front of the list
            # since it will not be updated
            if kube['state'] == 'active':
                # active means we are at the end of the sequence
                break

            # Add to the kube_sequence if it is any state other than 'active'
            kube_sequence.insert(0, ver)

            # 'partial' means we have started updating that version
            # There can be two partial states if the control plane
            # was updated, but the kubelet was not, so add  only the first
            if kube['state'] == 'partial':
                # if its partial there is no need for another loop
                break

            # 'upgrade_from' value is a list of versions however the
            # list should only ever be a single entry so we get the first
            # value and allow an exception to  be raised if the list is empty
            # todo(abailey): if the list contains more than one entry the
            # algorithm may not work, since it may not converge at the active version.
            ver = kube['upgrade_from'][0]

            # go around the loop again...

            # We should NEVER get into an infinite loop, but if the kube-version entries
            # in sysinv are malformed, we do not want to spin forever
            loop_count += 1
            if loop_count > 10:
                raise Exception("Invalid kubernetes dependency chain detected")

        return kube_sequence

    def _kubelet_map(self):
        """Map the host kubelet versions by the host uuid.
           Leave the kubelet version empty, if the status is not None,
           since that means the kubelet may not be running the version
           indicated.  ie: upgrading-kubelet-failed
           """
        from nfv_vim import nfvi

        kubelet_map = dict()
        for host in self.nfvi_kube_host_upgrade_list:
            # host status can be None if the activity has not been started,
            # or has been completed, in both cases the host version is correct.
            # for the other three states (upgrading, upgraded, failed) only
            # the upgraded state indicates the accurate kubelet version
            if host.status is None \
            or host.status == nfvi.objects.v1.KUBE_HOST_UPGRADE_STATE.KUBE_HOST_UPGRADED_KUBELET:
                kubelet_map[host.host_uuid] = host.kubelet_version
        return kubelet_map

    def _add_kube_upgrade_start_stage(self):
        """
        Add upgrade start strategy stage
        This stage only occurs when no kube upgrade has been initiated.
        """
        from nfv_vim import strategy
        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_START)
        stage.add_step(strategy.KubeUpgradeStartStep(self._to_version,
                                                     force=True))
        self.apply_phase.add_stage(stage)
        # Add the stage that comes after the kube upgrade start stage
        self._add_kube_upgrade_download_images_stage()

    def _add_kube_upgrade_download_images_stage(self):
        """
        Add downloading images stage
        This stage only occurs when kube upgrade has been started.
        It then proceeds to the next stage
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_DOWNLOAD_IMAGES)
        stage.add_step(strategy.KubeUpgradeDownloadImagesStep())
        self.apply_phase.add_stage(stage)
        # Next stage after download images is pre application update
        self._add_kube_pre_application_update_stage()

    def _add_kube_pre_application_update_stage(self):
        """
        Add kube pre application update stage.
        This stage only occurs after download images
        It then proceeds to the next stage
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_PRE_APPLICATION_UPDATE)
        stage.add_step(strategy.KubePreApplicationUpdateStep())
        self.apply_phase.add_stage(stage)

        # Next stage after pre application update is upgrade networking
        self._add_kube_upgrade_networking_stage()

    def _add_kube_upgrade_networking_stage(self):
        """
        Add kube upgrade networking stage.
        This stage only occurs after download images
        It then proceeds to the next stage
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_NETWORKING)
        stage.add_step(strategy.KubeUpgradeNetworkingStep())
        self.apply_phase.add_stage(stage)

        # Next stage after networking is upgrade storage
        self._add_kube_upgrade_storage_stage()

    def _add_kube_upgrade_storage_stage(self):
        """
        Add kube upgrade storage stage.
        This stage only occurs after upgrade networking
        It then proceeds to the next stage
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_STORAGE)
        stage.add_step(strategy.KubeUpgradeStorageStep())
        self.apply_phase.add_stage(stage)

        # Next stage after networking is cordon
        self._add_kube_host_cordon_stage()

    def _add_kube_host_cordon_stage(self):
        """Add host cordon stage for a host"""
        # simplex only

        from nfv_vim import nfvi
        from nfv_vim import strategy

        first_host = self.get_first_host()
        second_host = self.get_second_host()
        is_simplex = second_host is None
        if is_simplex:
            # todo(abailey): add rollback support to trigger uncordon
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.KUBE_HOST_CORDON)
            stage.add_step(strategy.KubeHostCordonStep(
                first_host,
                self._to_version,
                False,  # force
                nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_HOST_CORDON_COMPLETE,
                nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_HOST_CORDON_FAILED)
            )
            self.apply_phase.add_stage(stage)
        self._add_kube_update_stages()

    def _add_kube_update_stages(self):
        """Stages for control plane, kubelet and cordon"""
        # Algorithm
        # -------------------------
        # Simplex:
        # - loop over kube versions
        #   - control plane
        #   - kubelet
        # -------------------------
        # Duplex:
        # - loop over kube versions
        #   - first control plane
        #   - second control plane
        #   - kubelets
        # -------------------------
        from nfv_vim import nfvi
        from nfv_vim import strategy

        first_host = self.get_first_host()
        second_host = self.get_second_host()
        ver_list = self._get_kube_version_steps(self._to_version,
                                                self._nfvi_kube_versions_list)

        prev_state = None
        if self.nfvi_kube_upgrade is not None:
            prev_state = self.nfvi_kube_upgrade.state

        skip_first = False
        skip_second = False
        if prev_state in [nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_FIRST_MASTER,
                          nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_SECOND_MASTER,
                          nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_SECOND_MASTER_FAILED]:
            # we have already proceeded past first control plane
            skip_first = True
        elif prev_state in [nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_SECOND_MASTER,
                            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_KUBELETS]:
            # we have already proceeded past first control plane and second control plane
            skip_first = True
            skip_second = True

        for kube_ver in ver_list:
            DLOG.info("Examining %s " % kube_ver)

            # first control plane
            if skip_first:
                # skip only occurs on the first loop
                skip_first = False
            else:
                self._add_kube_upgrade_first_control_plane_stage(first_host, kube_ver)

            # second control plane
            if skip_second:
                skip_second = False
            else:
                self._add_kube_upgrade_second_control_plane_stage(second_host, kube_ver)

            # kubelets
            self._add_kube_upgrade_kubelets_stage(kube_ver)
            # kubelets can 'fail' the build. Return abruptly if it does
            # todo(abailey): change this once all lock/unlock are removed from kubelet
            if self._state == strategy.STRATEGY_STATE.BUILD_FAILED:
                return

        self._add_kube_host_uncordon_stage()

    def _add_kube_host_uncordon_stage(self):
        """Add host uncordon stage for a host"""
        # simplex only

        from nfv_vim import nfvi
        from nfv_vim import strategy

        first_host = self.get_first_host()
        second_host = self.get_second_host()
        is_simplex = second_host is None
        if is_simplex:
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.KUBE_HOST_UNCORDON)
            stage.add_step(strategy.KubeHostUncordonStep(
                first_host,
                self._to_version,
                False,  # force
                nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_HOST_UNCORDON_COMPLETE,
                nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_HOST_UNCORDON_FAILED)
            )
            self.apply_phase.add_stage(stage)
        # after this loop is kube upgrade complete stage
        self._add_kube_upgrade_complete_stage()

    def _add_kube_upgrade_first_control_plane_stage(self, first_host, kube_ver):
        """Add first controller control plane kube upgrade stage"""
        from nfv_vim import nfvi
        from nfv_vim import strategy

        stage_name = "%s %s" % (strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_FIRST_CONTROL_PLANE, kube_ver)
        stage = strategy.StrategyStage(stage_name)
        first_host = self.get_first_host()
        # force argument is ignored by control plane API
        force = True
        stage.add_step(strategy.KubeHostUpgradeControlPlaneStep(
            first_host,
            kube_ver,
            force,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_FIRST_MASTER,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_FIRST_MASTER_FAILED)
        )
        self.apply_phase.add_stage(stage)
        return True

    def _add_kube_upgrade_second_control_plane_stage(self, second_host, kube_ver):
        """
        Add second control plane kube upgrade stage
        This stage only occurs after networking and if this is a duplex.
        It then proceeds to the next stage
        """
        from nfv_vim import nfvi
        from nfv_vim import strategy

        if second_host is not None:
            # force argument is ignored by control plane API
            force = True
            stage_name = "%s %s" % (strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_SECOND_CONTROL_PLANE, kube_ver)
            stage = strategy.StrategyStage(stage_name)
            stage.add_step(strategy.KubeHostUpgradeControlPlaneStep(
                second_host,
                kube_ver,
                force,
                nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_SECOND_MASTER,
                nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_SECOND_MASTER_FAILED)
            )
            self.apply_phase.add_stage(stage)
            return True
        return False

    def _add_kube_upgrade_kubelets_stage(self, kube_ver):
        # todo(abailey): This can be completely redone when lock
        # and unlock are completely obsoleted

        from nfv_vim import tables

        host_table = tables.tables_get_host_table()

        # controller_0 and controller_1 are lists of no more than 1
        # if the controller is AIO it is added to the workers list
        # otherwise it is the std list
        controller_0_std = list()
        controller_1_std = list()
        controller_0_workers = list()
        controller_1_workers = list()
        worker_hosts = list()
        kubelet_map = self._kubelet_map()

        # Skip hosts that the kubelet is already the correct version
        # group the hosts by their type (controller, storage, worker)
        # place each controller in a separate list
        # there are no kubelets running on storage nodes
        for host in list(host_table.values()):
            if kubelet_map.get(host.uuid) == self._to_version:
                DLOG.info("Host %s kubelet already up to date" % host.name)
                continue
            if kubelet_map.get(host.uuid) == kube_ver:
                DLOG.info("Host %s kubelet already at interim version" % host.name)
                continue
            if HOST_PERSONALITY.CONTROLLER in host.personality:
                if HOST_NAME.CONTROLLER_0 == host.name:
                    if HOST_PERSONALITY.WORKER in host.personality:
                        controller_0_workers.append(host)
                    else:
                        controller_0_std.append(host)
                elif HOST_NAME.CONTROLLER_1 == host.name:
                    if HOST_PERSONALITY.WORKER in host.personality:
                        controller_1_workers.append(host)
                    else:
                        controller_1_std.append(host)
                else:
                    DLOG.warn("Unsupported controller name %s" % host.name)
            elif HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
            else:
                DLOG.info("No kubelet stage required for host %s" % host.name)

        # kubelet order is: controller-1, controller-0 then workers
        # storage nodes can be skipped
        # we only include 'reboot' in a duplex env (includes workers)
        reboot_default = not self._single_controller  # We do NOT reboot an AIO-SX host
        HOST_STAGES = [
            (self._add_kubelet_controller_strategy_stages,
             controller_1_std,
             reboot_default),
            (self._add_kubelet_controller_strategy_stages,
             controller_0_std,
             reboot_default),
            (self._add_kubelet_worker_strategy_stages,
             controller_1_workers,
             reboot_default),
            (self._add_kubelet_worker_strategy_stages,
             controller_0_workers,
             reboot_default),
            (self._add_kubelet_worker_strategy_stages,
             worker_hosts,
             reboot_default)
        ]
        stage_name = "kube-upgrade-kubelet %s" % kube_ver
        for add_kubelet_stages_function, host_list, reboot in HOST_STAGES:
            if host_list:
                sorted_host_list = sorted(host_list,
                                          key=lambda host: host.name)
                success, reason = add_kubelet_stages_function(sorted_host_list,
                                                              kube_ver,
                                                              reboot,
                                                              stage_name)
                # todo(abailey): We need revisit if this can never fail
                if not success:
                    self.report_build_failure(reason)
                    return

    def _add_kube_upgrade_complete_stage(self):
        """
        Add kube upgrade complete strategy stage
        This stage occurs after all kubelets are upgraded
        """
        from nfv_vim import strategy
        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_COMPLETE)
        stage.add_step(strategy.KubeUpgradeCompleteStep())
        self.apply_phase.add_stage(stage)
        # Next stage after upgrade complete is post application update
        self._add_kube_post_application_update_stage()

    def _add_kube_post_application_update_stage(self):
        """
        Add kube post application update stage.
        This stage occurs after the upgrade is completed
        It then proceeds to the next stage
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_POST_APPLICATION_UPDATE)
        stage.add_step(strategy.KubePostApplicationUpdateStep())
        self.apply_phase.add_stage(stage)

        # Next stage after post application update is upgrade cleanup
        self._add_kube_upgrade_cleanup_stage()

    def _add_kube_upgrade_cleanup_stage(self):
        """
        kube upgrade cleanup stage deletes the kube upgrade.
        This stage occurs after the post application update stage
        """
        from nfv_vim import strategy
        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_CLEANUP)
        stage.add_step(strategy.KubeUpgradeCleanupStep())
        self.apply_phase.add_stage(stage)

    def get_first_host(self):
        """
        This corresponds to the first host that should be updated.
        In simplex env, first host: controller-0. In duplex env: controller-1
        """
        from nfv_vim import tables

        controller_0_host = None
        controller_1_host = None
        host_table = tables.tables_get_host_table()
        for host in host_table.get_by_personality(HOST_PERSONALITY.CONTROLLER):
            if HOST_NAME.CONTROLLER_0 == host.name:
                controller_0_host = host
            if HOST_NAME.CONTROLLER_1 == host.name:
                controller_1_host = host
        if controller_1_host is None:
            # simplex
            return controller_0_host
        else:
            # duplex
            return controller_1_host

    def get_second_host(self):
        """
        This corresponds to the second host that should be updated.
        In simplex env, second host: None. In duplex env: controller-0
        """
        from nfv_vim import tables
        controller_0_host = None
        controller_1_host = None
        host_table = tables.tables_get_host_table()
        for host in host_table.get_by_personality(HOST_PERSONALITY.CONTROLLER):
            if HOST_NAME.CONTROLLER_0 == host.name:
                controller_0_host = host
            if HOST_NAME.CONTROLLER_1 == host.name:
                controller_1_host = host
        if controller_1_host is None:
            # simplex
            return None
        else:
            # duplex
            return controller_0_host

    def build_complete(self, result, result_reason):
        """
        Strategy Build Complete
        """
        from nfv_vim import nfvi
        from nfv_vim import strategy

        # Note: there are no resume states for actions that are still running
        # ie:  KUBE_UPGRADE_DOWNLOADING_IMAGES
        RESUME_STATE = {
            # after upgrade-started -> download images
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_STARTED:
                self._add_kube_upgrade_download_images_stage,

            # if downloading images failed, resume at downloading images
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_DOWNLOADING_IMAGES_FAILED:
                self._add_kube_upgrade_download_images_stage,

            # After downloading images -> pre update applications
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_DOWNLOADED_IMAGES:
                self._add_kube_pre_application_update_stage,

            # if pre updating apps failed, resume at pre updating apps
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_PRE_UPDATING_APPS_FAILED:
                self._add_kube_pre_application_update_stage,

            # After pre updating apps -> upgrade networking
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_PRE_UPDATED_APPS:
                self._add_kube_upgrade_networking_stage,

            # if networking state failed, resync at networking state
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_NETWORKING_FAILED:
                self._add_kube_upgrade_networking_stage,

            # After networking -> upgrade storage
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_NETWORKING:
                self._add_kube_upgrade_storage_stage,

            # if storage state failed, resync at storage state
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_STORAGE_FAILED:
                self._add_kube_upgrade_storage_stage,

            # After storage -> cordon
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_STORAGE:
                self._add_kube_host_cordon_stage,

            # If the state is cordon-failed, resume at cordon stage
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_HOST_CORDON_FAILED:
                self._add_kube_host_cordon_stage,

            # If the state is cordon-complete, resume at update stages
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_HOST_CORDON_COMPLETE:
                self._add_kube_update_stages,

            # if upgrading first control plane failed, resume there
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_FIRST_MASTER_FAILED:
                self._add_kube_update_stages,

            # After first control plane -> upgrade second control plane
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_FIRST_MASTER:
                self._add_kube_update_stages,

            # Re-attempt second control plane
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_SECOND_MASTER_FAILED:
                self._add_kube_update_stages,

            # After second control plane , do kubelets
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_SECOND_MASTER:
                self._add_kube_update_stages,

            # kubelets transition to 'uncordon after they are done
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_KUBELETS:
                self._add_kube_update_stages,

            # If the state is uncordon-failed, resume at uncordon stage
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_HOST_UNCORDON_FAILED:
                self._add_kube_host_uncordon_stage,

            # If the state is uncordon-complete, resume at complete stage
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_HOST_UNCORDON_COMPLETE:
                self._add_kube_upgrade_complete_stage,

            # upgrade is completed, post update apps
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_COMPLETE:
                self._add_kube_post_application_update_stage,

            # If post updating apps failed, resume at post application update stage
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_POST_UPDATING_APPS_FAILED:
                self._add_kube_post_application_update_stage,

            # After post updating apps, delete the upgrade
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_POST_UPDATED_APPS:
                self._add_kube_upgrade_cleanup_stage,
        }

        result, result_reason = \
            super(KubeUpgradeStrategy, self).build_complete(result,
                                                            result_reason)

        DLOG.verbose("Build Complete Callback, result=%s, reason=%s."
                     % (result, result_reason))

        if result in [strategy.STRATEGY_RESULT.SUCCESS,
                      strategy.STRATEGY_RESULT.DEGRADED]:

            matching_version_upgraded = False
            for kube_version_object in self._nfvi_kube_versions_list:
                if kube_version_object['kube_version'] == self._to_version:
                    # found a matching version.  check if already upgraded
                    matching_version_upgraded = (kube_version_object['target']
                        and kube_version_object['state'] == 'active')
                    break
            else:
                # the for loop above did not find a matching kube version
                DLOG.warn("Invalid to_version(%s) for the kube upgrade"
                          % self._to_version)
                self.report_build_failure("Invalid to_version value: '%s'"
                                          % self._to_version)
                return

            if self._nfvi_alarms:
                # Fail create strategy if unignored alarms present
                # add the alarm ids to the result reason.
                # eliminate duplicates  using a set, and sort the list
                alarm_id_set = set()
                for alarm_data in self._nfvi_alarms:
                    alarm_id_set.add(alarm_data['alarm_id'])
                alarm_id_list = ", ".join(sorted(alarm_id_set))

                DLOG.warn("Cannot upgrade kube: Active alarms present [ %s ]"
                          % alarm_id_list)
                self.report_build_failure("active alarms present [ %s ]"
                                          % alarm_id_list)
                return

            if self.nfvi_kube_upgrade is None:
                # We only reject creating a new kube upgrade for an already
                # upgraded version if no kube_upgrade exists
                if matching_version_upgraded:
                    self.report_build_failure(
                        "Kubernetes is already upgraded to: %s"
                        % self._to_version)
                    return
                    # Do NOT start a kube upgrade if none exists AND the
                    # to_version is already active
                # Start upgrade which adds all stages
                self._add_kube_upgrade_start_stage()
            else:
                # Determine which stage to resume at
                # this is complicated due to the 'loop'
                current_state = self.nfvi_kube_upgrade.state
                resume_from_stage = RESUME_STATE.get(current_state)
                if resume_from_stage is None:
                    self.report_build_failure(
                        "Unable to resume kube upgrade from state: %s"
                        % current_state)
                    return
                else:
                    # Invoke the method that resumes the build from the stage
                    resume_from_stage()

        else:
            # build did not succeed. set failed.
            self.report_build_failure(result_reason)
            return

        # successful build
        self.sw_update_obj.strategy_build_complete(True, '')
        self.save()

    def from_dict(self, data, build_phase=None, apply_phase=None,
                  abort_phase=None):
        """
        Initializes a kube upgrade strategy object using the given dictionary
        """
        super(KubeUpgradeStrategy, self).from_dict(data,
                                                   build_phase,
                                                   apply_phase,
                                                   abort_phase)
        self._to_version = data['to_version']
        self._single_controller = data['single_controller']
        self.mixin_from_dict(data)
        return self

    def as_dict(self):
        """
        Represent the kube upgrade strategy as a dictionary
        """
        data = super(KubeUpgradeStrategy, self).as_dict()
        data['to_version'] = self._to_version
        data['single_controller'] = self._single_controller
        self.mixin_as_dict(data)
        return data


def strategy_rebuild_from_dict(data):
    """
    Returns the strategy object initialized using the given dictionary
    """
    from nfv_vim.strategy._strategy_phases import strategy_phase_rebuild_from_dict  # noqa: F401

    if not data:
        return None

    build_phase = strategy_phase_rebuild_from_dict(data['build_phase'])
    apply_phase = strategy_phase_rebuild_from_dict(data['apply_phase'])
    abort_phase = strategy_phase_rebuild_from_dict(data['abort_phase'])

    if STRATEGY_NAME.SW_PATCH == data['name']:
        strategy_obj = object.__new__(SwPatchStrategy)
    elif STRATEGY_NAME.SW_UPGRADE == data['name']:
        strategy_obj = object.__new__(SwUpgradeStrategy)
    elif STRATEGY_NAME.SYSYTEM_CONFIG_UPDATE == data['name']:
        strategy_obj = object.__new__(SystemConfigUpdateStrategy)
    elif STRATEGY_NAME.FW_UPDATE == data['name']:
        strategy_obj = object.__new__(FwUpdateStrategy)
    elif STRATEGY_NAME.KUBE_ROOTCA_UPDATE == data['name']:
        strategy_obj = object.__new__(KubeRootcaUpdateStrategy)
    elif STRATEGY_NAME.KUBE_UPGRADE == data['name']:
        strategy_obj = object.__new__(KubeUpgradeStrategy)
    else:
        strategy_obj = object.__new__(strategy.StrategyStage)

    strategy_obj.from_dict(data, build_phase, apply_phase, abort_phase)
    return strategy_obj
