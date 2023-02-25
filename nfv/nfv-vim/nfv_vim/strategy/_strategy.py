#
# Copyright (c) 2015-2021 Wind River Systems, Inc.
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
from nfv_vim.nfvi.objects.v1 import UPGRADE_STATE
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
            aggregate_ratio = \
                float(self._max_parallel_worker_hosts) / num_worker_hosts
            # Limit the ratio to half the worker hosts in an aggregate
            if aggregate_ratio > 0.5:
                aggregate_ratio = 0.5

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


class UpdateControllerHostsMixin(object):

    def _add_update_controller_strategy_stages(self,
                                               controllers,
                                               reboot,
                                               strategy_stage_name,
                                               host_action_step):
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
                            True, ignore_alarms=self._ignore_alarms))
                        if reboot:
                            stage.add_step(strategy.SwactHostsStep(host_list))
                            stage.add_step(strategy.LockHostsStep(host_list))
                        # Add the action step for these hosts (patch, etc..)
                        stage.add_step(host_action_step(host_list))
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
                                           timeout_in_secs=30 * 60,
                                           ignore_alarms=self._ignore_alarms))
                        else:
                            # Less time required if host is not rebooting
                            stage.add_step(strategy.SystemStabilizeStep(
                                           timeout_in_secs=NO_REBOOT_DELAY))
                        self.apply_phase.add_stage(stage)

            if local_host is not None:
                host_list = [local_host]
                stage = strategy.StrategyStage(strategy_stage_name)
                stage.add_step(strategy.QueryAlarmsStep(
                    True, ignore_alarms=self._ignore_alarms))
                if reboot:
                    stage.add_step(strategy.SwactHostsStep(host_list))
                    stage.add_step(strategy.LockHostsStep(host_list))
                # Add the action step for the local_hosts (patch, etc..)
                stage.add_step(host_action_step(host_list))
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
                                   timeout_in_secs=30 * 60,
                                   ignore_alarms=self._ignore_alarms))
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


class UpgradeKubeletControllerHostsMixin(UpdateControllerHostsMixin):
    def _add_kubelet_controller_strategy_stages(self, controllers, reboot):
        from nfv_vim import strategy
        return self._add_update_controller_strategy_stages(
            controllers,
            reboot,
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_KUBELETS_CONTROLLERS,
            strategy.KubeHostUpgradeKubeletStep)


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
                True, ignore_alarms=self._ignore_alarms))
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
                                           host_action_step):
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
                True, ignore_alarms=self._ignore_alarms))

            if reboot:
                if 1 == len(host_list):
                    if HOST_PERSONALITY.CONTROLLER in host_list[0].personality:
                        if not self._single_controller:
                            # Swact controller before locking
                            stage.add_step(strategy.SwactHostsStep(host_list))

                # Migrate or stop instances as necessary
                if SW_UPDATE_INSTANCE_ACTION.MIGRATE == self._default_instance_action:
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
            stage.add_step(host_action_step(host_list))

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
                                   timeout_in_secs=30 * 60,
                                   ignore_alarms=self._ignore_alarms))
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


class UpgradeKubeletWorkerHostsMixin(UpdateWorkerHostsMixin):
    def _add_kubelet_worker_strategy_stages(self, worker_hosts, reboot):
        from nfv_vim import strategy
        return self._add_update_worker_strategy_stages(
            worker_hosts,
            reboot,
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_KUBELETS_WORKERS,
            strategy.KubeHostUpgradeKubeletStep)


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
                         ]
        self._ignore_alarms += IGNORE_ALARMS
        self._single_controller = single_controller

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
            strategy.QueryAlarmsStep(ignore_alarms=self._ignore_alarms))
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
class SwUpgradeStrategy(SwUpdateStrategy):
    """
    Software Upgrade - Strategy
    """
    def __init__(self, uuid, storage_apply_type, worker_apply_type,
                 max_parallel_worker_hosts,
                 alarm_restrictions, start_upgrade, complete_upgrade,
                 ignore_alarms, single_controller):
        super(SwUpgradeStrategy, self).__init__(
            uuid,
            STRATEGY_NAME.SW_UPGRADE,
            SW_UPDATE_APPLY_TYPE.SERIAL,
            storage_apply_type,
            SW_UPDATE_APPLY_TYPE.IGNORE,
            worker_apply_type,
            max_parallel_worker_hosts,
            SW_UPDATE_INSTANCE_ACTION.MIGRATE,
            alarm_restrictions,
            ignore_alarms)

        # Note: The support for start_upgrade was implemented and (mostly)
        # tested, but there is a problem. When the sw-upgrade-start stage
        # runs, it will start the upgrade, upgrade controller-1 and swact to
        # it. However, when controller-1 becomes active, it will be using the
        # snapshot of the VIM database that was created when the upgrade was
        # started, so the strategy object created from the database will be
        # long out of date (it thinks the upgrade start step is still in
        # progress) and the strategy apply will fail. Fixing this would be
        # complex, so we will not support the start_upgrade option for now,
        # which would only have been for lab use.
        if start_upgrade:
            raise Exception("No support for start_upgrade")
        self._start_upgrade = start_upgrade
        self._complete_upgrade = complete_upgrade
        # The following alarms will not prevent a software upgrade operation
        IGNORE_ALARMS = ['900.005',  # Upgrade in progress
                         '900.201',  # Software upgrade auto apply in progress
                         '750.006',  # Configuration change requires reapply of cert-manager
                         ]
        self._ignore_alarms += IGNORE_ALARMS
        self._single_controller = single_controller
        self._nfvi_upgrade = None

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

    def build(self):
        """
        Build the strategy
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_QUERY)
        stage.add_step(strategy.QueryAlarmsStep(
            ignore_alarms=self._ignore_alarms))
        stage.add_step(strategy.QueryUpgradeStep())
        self.build_phase.add_stage(stage)
        super(SwUpgradeStrategy, self).build()

    def _add_upgrade_start_stage(self):
        """
        Add upgrade start strategy stage
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        host_table = tables.tables_get_host_table()
        controller_1_host = None
        for host in host_table.get_by_personality(HOST_PERSONALITY.CONTROLLER):
            if HOST_NAME.CONTROLLER_1 == host.name:
                controller_1_host = host
                break
        host_list = [controller_1_host]

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_START)
        # Do not ignore any alarms when starting an upgrade
        stage.add_step(strategy.QueryAlarmsStep(True))
        # Upgrade start can only be done from controller-0
        stage.add_step(strategy.SwactHostsStep(host_list))
        stage.add_step(strategy.UpgradeStartStep())
        stage.add_step(strategy.SystemStabilizeStep())
        self.apply_phase.add_stage(stage)

    def _add_upgrade_complete_stage(self):
        """
        Add upgrade complete strategy stage
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        host_table = tables.tables_get_host_table()
        controller_1_host = None
        for host in host_table.get_by_personality(HOST_PERSONALITY.CONTROLLER):
            if HOST_NAME.CONTROLLER_1 == host.name:
                controller_1_host = host
                break
        host_list = [controller_1_host]

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_COMPLETE)
        stage.add_step(strategy.QueryAlarmsStep(
            True, ignore_alarms=self._ignore_alarms))
        # Upgrade complete can only be done from controller-0
        stage.add_step(strategy.SwactHostsStep(host_list))
        stage.add_step(strategy.UpgradeActivateStep())
        stage.add_step(strategy.UpgradeCompleteStep())
        stage.add_step(strategy.SystemStabilizeStep())
        self.apply_phase.add_stage(stage)

    def _add_controller_strategy_stages(self, controllers, reboot):
        """
        Add controller software upgrade strategy stages
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        host_table = tables.tables_get_host_table()

        if 2 > host_table.total_by_personality(HOST_PERSONALITY.CONTROLLER):
            DLOG.warn("Not enough controllers to apply software upgrades.")
            reason = 'not enough controllers to apply software upgrades'
            return False, reason

        controller_0_host = None
        controller_1_host = None

        for host in controllers:
            if HOST_PERSONALITY.WORKER in host.personality:
                # Do nothing for AIO hosts. We let the worker code handle everything.
                # This is done to handle the case where stx-openstack is
                # installed and there could be instances running on the
                # AIO-DX controllers which need to be migrated.
                if self._single_controller:
                    DLOG.warn("Cannot apply software upgrades to AIO-SX deployment.")
                    reason = 'cannot apply software upgrades to AIO-SX deployment'
                    return False, reason
                else:
                    return True, ''
            elif HOST_NAME.CONTROLLER_1 == host.name:
                controller_1_host = host
            elif HOST_NAME.CONTROLLER_0 == host.name:
                controller_0_host = host

        if controller_1_host is not None:
            host_list = [controller_1_host]
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_CONTROLLERS)
            stage.add_step(strategy.QueryAlarmsStep(
                True, ignore_alarms=self._ignore_alarms))
            stage.add_step(strategy.LockHostsStep(host_list))
            stage.add_step(strategy.UpgradeHostsStep(host_list))
            # During an upgrade, unlock may need to retry. Bug details:
            # https://bugs.launchpad.net/starlingx/+bug/1946255
            stage.add_step(strategy.UnlockHostsStep(
                host_list,
                retry_count=strategy.UnlockHostsStep.MAX_RETRIES))
            # Allow up to four hours for controller disks to synchronize
            stage.add_step(strategy.WaitDataSyncStep(
                timeout_in_secs=4 * 60 * 60,
                ignore_alarms=self._ignore_alarms))
            self.apply_phase.add_stage(stage)

        if controller_0_host is not None:
            host_list = [controller_0_host]
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_CONTROLLERS)
            stage.add_step(strategy.QueryAlarmsStep(
                True, ignore_alarms=self._ignore_alarms))
            if controller_1_host is not None:
                # Only swact to controller-1 if it was upgraded. If we are only
                # upgrading controller-0, then controller-1 needs to be
                # active already.
                stage.add_step(strategy.SwactHostsStep(host_list))
            stage.add_step(strategy.LockHostsStep(host_list))
            stage.add_step(strategy.UpgradeHostsStep(host_list))
            # During an upgrade, unlock may need to retry. Bug details:
            # https://bugs.launchpad.net/starlingx/+bug/1946255
            stage.add_step(strategy.UnlockHostsStep(
                host_list,
                retry_count=strategy.UnlockHostsStep.MAX_RETRIES))
            # Allow up to four hours for controller disks to synchronize
            stage.add_step(strategy.WaitDataSyncStep(
                timeout_in_secs=4 * 60 * 60,
                ignore_alarms=self._ignore_alarms))
            self.apply_phase.add_stage(stage)

        return True, ''

    def _add_storage_strategy_stages(self, storage_hosts, reboot):
        """
        Add storage software upgrade strategy stages
        """
        from nfv_vim import strategy

        storage_0_host_list = list()
        storage_0_host_lists = list()
        other_storage_host_list = list()

        for host in storage_hosts:
            if HOST_NAME.STORAGE_0 == host.name:
                storage_0_host_list.append(host)
            else:
                other_storage_host_list.append(host)

        if len(storage_0_host_list) == 1:
            storage_0_host_lists, reason = self._create_storage_host_lists(
                storage_0_host_list)
            if storage_0_host_lists is None:
                return False, reason

        other_storage_host_lists, reason = self._create_storage_host_lists(
            other_storage_host_list)
        if other_storage_host_lists is None:
            return False, reason

        # Upgrade storage-0 first and on its own since it has a ceph monitor
        if len(storage_0_host_lists) == 1:
            combined_host_lists = storage_0_host_lists + other_storage_host_lists
        else:
            combined_host_lists = other_storage_host_lists

        for host_list in combined_host_lists:
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_STORAGE_HOSTS)
            stage.add_step(strategy.QueryAlarmsStep(
                True, ignore_alarms=self._ignore_alarms))
            stage.add_step(strategy.LockHostsStep(host_list))
            stage.add_step(strategy.UpgradeHostsStep(host_list))
            # During an upgrade, unlock may need to retry. Bug details:
            # https://bugs.launchpad.net/starlingx/+bug/1946255
            stage.add_step(strategy.UnlockHostsStep(
                host_list,
                retry_count=strategy.UnlockHostsStep.MAX_RETRIES))

            # After storage node(s) are unlocked, we need extra time to
            # allow the OSDs to go back in sync and the storage related
            # alarms to clear. We no longer wipe the OSD disks when upgrading
            # a storage node, so they should only be syncing data that changed
            # while they were being upgraded.
            stage.add_step(strategy.WaitDataSyncStep(
                timeout_in_secs=2 * 60 * 60,
                ignore_alarms=self._ignore_alarms))
            self.apply_phase.add_stage(stage)

        return True, ''

    def _add_worker_strategy_stages(self, worker_hosts, reboot):
        """
        Add worker software upgrade strategy stages
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        host_lists, reason = self._create_worker_host_lists(worker_hosts, reboot)
        if host_lists is None:
            return False, reason

        instance_table = tables.tables_get_instance_table()

        for host_list in host_lists:
            instance_list = list()

            for host in host_list:
                for instance in instance_table.on_host(host.name):
                    if not instance.is_locked():
                        instance_list.append(instance)
                    else:
                        DLOG.warn("Instance %s must not be shut down" %
                                  instance.name)
                        reason = ('instance %s must not be shut down' %
                                  instance.name)
                        return False, reason

            # Computes with no instances
            if 0 == len(instance_list):
                stage = strategy.StrategyStage(
                    strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_WORKER_HOSTS)
                stage.add_step(strategy.QueryAlarmsStep(
                    True, ignore_alarms=self._ignore_alarms))
                if HOST_PERSONALITY.CONTROLLER in host_list[0].personality:
                    stage.add_step(strategy.SwactHostsStep(host_list))
                stage.add_step(strategy.LockHostsStep(host_list))
                stage.add_step(strategy.UpgradeHostsStep(host_list))
                # During an upgrade, unlock may need to retry. Bug details:
                # https://bugs.launchpad.net/starlingx/+bug/1914836
                stage.add_step(strategy.UnlockHostsStep(
                    host_list,
                    retry_count=strategy.UnlockHostsStep.MAX_RETRIES))
                if HOST_PERSONALITY.CONTROLLER in host_list[0].personality:
                    # AIO Controller hosts will undergo WaitDataSyncStep step
                    # Allow up to four hours for controller disks to synchronize
                    stage.add_step(strategy.WaitDataSyncStep(
                        timeout_in_secs=4 * 60 * 60,
                        ignore_alarms=self._ignore_alarms))
                else:
                    # Worker hosts will undergo:
                    # 1) WaitAlarmsClear step if openstack is installed.
                    # 2) SystemStabilizeStep step if openstack is not installed.
                    if any([host.openstack_control or host.openstack_compute
                            for host in host_list]):
                        # Hosts with openstack that just need to wait for services to start up:
                        stage.add_step(strategy.WaitAlarmsClearStep(
                                timeout_in_secs=10 * 60,
                                ignore_alarms=self._ignore_alarms))
                    else:
                        stage.add_step(strategy.SystemStabilizeStep())
                self.apply_phase.add_stage(stage)
                continue

            # Computes with instances
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.SW_UPGRADE_WORKER_HOSTS)

            stage.add_step(strategy.QueryAlarmsStep(
                True, ignore_alarms=self._ignore_alarms))

            if SW_UPDATE_APPLY_TYPE.PARALLEL == self._worker_apply_type:
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

            stage.add_step(strategy.MigrateInstancesStep(instance_list))
            if HOST_PERSONALITY.CONTROLLER in host_list[0].personality:
                stage.add_step(strategy.SwactHostsStep(host_list))
            stage.add_step(strategy.LockHostsStep(host_list))
            stage.add_step(strategy.UpgradeHostsStep(host_list))
            # During an upgrade, unlock may need to retry. Bug details:
            # https://bugs.launchpad.net/starlingx/+bug/1914836
            stage.add_step(strategy.UnlockHostsStep(
                host_list,
                retry_count=strategy.UnlockHostsStep.MAX_RETRIES))
            if HOST_PERSONALITY.CONTROLLER in host_list[0].personality:
                # AIO Controller hosts will undergo WaitDataSyncStep step
                # Allow up to four hours for controller disks to synchronize
                stage.add_step(strategy.WaitDataSyncStep(
                    timeout_in_secs=4 * 60 * 60,
                    ignore_alarms=self._ignore_alarms))
            else:
                # Worker hosts will undergo:
                # 1) WaitAlarmsClear step if openstack is installed.
                # 2) SystemStabilizeStep step if openstack is not installed.
                if any([host.openstack_control or host.openstack_compute
                        for host in host_list]):
                    # Hosts with openstack that just need to wait for
                    # services to start up:
                    stage.add_step(strategy.WaitAlarmsClearStep(
                            timeout_in_secs=10 * 60,
                            ignore_alarms=self._ignore_alarms))
                else:
                    stage.add_step(strategy.SystemStabilizeStep())
            self.apply_phase.add_stage(stage)

        return True, ''

    def build_complete(self, result, result_reason):
        """
        Strategy Build Complete
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        result, result_reason = \
            super(SwUpgradeStrategy, self).build_complete(result, result_reason)

        DLOG.info("Build Complete Callback, result=%s, reason=%s."
                  % (result, result_reason))

        if result in [strategy.STRATEGY_RESULT.SUCCESS,
                      strategy.STRATEGY_RESULT.DEGRADED]:

            # Check whether the upgrade is in a valid state for orchestration
            if self.nfvi_upgrade is None:
                if not self._start_upgrade:
                    DLOG.warn("No upgrade in progress.")
                    self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                    self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
                    self.build_phase.result_reason = 'no upgrade in progress'
                    self.sw_update_obj.strategy_build_complete(
                        False, self.build_phase.result_reason)
                    self.save()
                    return
            else:
                if self._start_upgrade:
                    valid_states = [UPGRADE_STATE.STARTED,
                                    UPGRADE_STATE.DATA_MIGRATION_COMPLETE,
                                    UPGRADE_STATE.UPGRADING_CONTROLLERS,
                                    UPGRADE_STATE.UPGRADING_HOSTS]
                else:
                    valid_states = [UPGRADE_STATE.UPGRADING_CONTROLLERS,
                                    UPGRADE_STATE.UPGRADING_HOSTS]

                if self.nfvi_upgrade.state not in valid_states:
                    DLOG.warn("Invalid upgrade state for orchestration: %s." %
                              self.nfvi_upgrade.state)
                    self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                    self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
                    self.build_phase.result_reason = (
                        'invalid upgrade state for orchestration: %s' %
                        self.nfvi_upgrade.state)
                    self.sw_update_obj.strategy_build_complete(
                        False, self.build_phase.result_reason)
                    self.save()
                    return

                # If controller-1 has been upgraded and we have yet to upgrade
                # controller-0, then controller-1 must be active.
                if UPGRADE_STATE.UPGRADING_CONTROLLERS == self.nfvi_upgrade.state:
                    if HOST_NAME.CONTROLLER_1 != get_local_host_name():
                        DLOG.warn(
                            "Controller-1 must be active for orchestration to "
                            "upgrade controller-0.")
                        self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                        self.build_phase.result = \
                            strategy.STRATEGY_PHASE_RESULT.FAILED
                        self.build_phase.result_reason = (
                            'controller-1 must be active for orchestration to '
                            'upgrade controller-0')
                        self.sw_update_obj.strategy_build_complete(
                            False, self.build_phase.result_reason)
                        self.save()
                        return

            if self._nfvi_alarms:
                DLOG.warn(
                    "Active alarms found, can't apply software upgrade.")
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
                self.sw_update_obj.strategy_build_complete(
                    False, self.build_phase.result_reason)
                self.save()
                return

            host_table = tables.tables_get_host_table()
            for host in list(host_table.values()):
                # Only allow upgrade orchestration when all hosts are
                # available. It is not safe to automate upgrade application
                # when we do not have full redundancy.
                if not (host.is_unlocked() and host.is_enabled() and
                        host.is_available()):
                    DLOG.warn(
                        "All %s hosts must be unlocked-enabled-available, "
                        "can't apply software upgrades." % host.personality)
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

            controller_hosts = list()
            storage_hosts = list()
            worker_hosts = list()

            if self.nfvi_upgrade is None:
                # Start upgrade
                self._add_upgrade_start_stage()

                # All hosts will be upgraded
                for host in list(host_table.values()):
                    if HOST_PERSONALITY.CONTROLLER in host.personality:
                        controller_hosts.append(host)

                    elif HOST_PERSONALITY.STORAGE in host.personality:
                        storage_hosts.append(host)

                    if HOST_PERSONALITY.WORKER in host.personality:
                        worker_hosts.append(host)
            else:
                # Only hosts not yet upgraded will be upgraded
                to_load = self.nfvi_upgrade.to_release
                for host in list(host_table.values()):
                    if host.software_load == to_load:
                        # No need to upgrade this host
                        continue

                    if HOST_PERSONALITY.CONTROLLER in host.personality:
                        controller_hosts.append(host)

                    elif HOST_PERSONALITY.STORAGE in host.personality:
                        storage_hosts.append(host)

                    if HOST_PERSONALITY.WORKER in host.personality:
                        worker_hosts.append(host)

            STRATEGY_CREATION_COMMANDS = [
                (self._add_controller_strategy_stages,
                 controller_hosts, True),
                (self._add_storage_strategy_stages,
                 storage_hosts, True),
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

            if self._complete_upgrade:
                self._add_upgrade_complete_stage()

            if 0 == len(self.apply_phase.stages):
                DLOG.warn("No software upgrades need to be applied.")
                self._state = strategy.STRATEGY_STATE.BUILD_FAILED
                self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
                self.build_phase.result_reason = ('no software upgrades need to be '
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
        Initializes a software upgrade strategy object using the given dictionary
        """
        from nfv_vim import nfvi

        super(SwUpgradeStrategy, self).from_dict(data, build_phase, apply_phase,
                                                 abort_phase)
        self._single_controller = data['single_controller']
        self._start_upgrade = data['start_upgrade']
        self._complete_upgrade = data['complete_upgrade']
        nfvi_upgrade_data = data['nfvi_upgrade_data']
        if nfvi_upgrade_data:
            self._nfvi_upgrade = nfvi.objects.v1.Upgrade(
                nfvi_upgrade_data['state'],
                nfvi_upgrade_data['from_release'],
                nfvi_upgrade_data['to_release'])
        else:
            self._nfvi_upgrade = None

        return self

    def as_dict(self):
        """
        Represent the software upgrade strategy as a dictionary
        """
        data = super(SwUpgradeStrategy, self).as_dict()
        data['single_controller'] = self._single_controller
        data['start_upgrade'] = self._start_upgrade
        data['complete_upgrade'] = self._complete_upgrade
        if self._nfvi_upgrade:
            nfvi_upgrade_data = self._nfvi_upgrade.as_dict()
        else:
            nfvi_upgrade_data = None
        data['nfvi_upgrade_data'] = nfvi_upgrade_data

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

    def report_build_failure(self, reason):
        """
        Report a build failure for the strategy

        todo(abailey): this should be in the superclass
        """
        DLOG.warn("Strategy Build Failed: %s" % reason)
        self._state = strategy.STRATEGY_STATE.BUILD_FAILED
        self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
        self.build_phase.result_reason = reason
        self.sw_update_obj.strategy_build_complete(
            False,
            self.build_phase.result_reason)
        self.save()

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
                          QuerySwPatchesMixin,
                          QuerySwPatchHostsMixin,
                          PatchControllerHostsMixin,
                          PatchStorageHostsMixin,
                          PatchWorkerHostsMixin,
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
            '200.001',  # Locked Host
            '280.001',  # Subcloud resource off-line
            '280.002',  # Subcloud resource out-of-sync
            '700.004',  # VM stopped
            '750.006',  # Configuration change requires reapply of cert-manager
            '900.001',  # Patch in progress (kube orch uses patching)
            '900.007',  # Kube Upgrade in progress
            '900.401',  # kube-upgrade-auto-apply-inprogress
        ]
        # self._ignore_alarms is declared in parent class
        self._ignore_alarms += IGNORE_ALARMS

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
        stage.add_step(strategy.QueryAlarmsStep(
            ignore_alarms=self._ignore_alarms))
        # these query steps are paired with mixins that process their results
        stage.add_step(strategy.QueryKubeVersionsStep())
        stage.add_step(strategy.QueryKubeUpgradeStep())
        stage.add_step(strategy.QueryKubeHostUpgradeStep())
        stage.add_step(strategy.QuerySwPatchesStep())
        stage.add_step(strategy.QuerySwPatchHostsStep())

        self.build_phase.add_stage(stage)
        super(KubeUpgradeStrategy, self).build()

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
        # Next stage after download images is upgrade networking
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
        # Next stage after networking is second control plane (if duplex)
        self._add_kube_upgrade_first_control_plane_stage()

    def _add_kube_upgrade_first_control_plane_stage(self):
        """
        Add first controller control plane kube upgrade stage
        This stage only occurs after networking
        It then proceeds to the next stage
        """
        from nfv_vim import nfvi
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_FIRST_CONTROL_PLANE)
        first_host = self.get_first_host()
        # force argument is ignored by control plane API
        force = True
        stage.add_step(strategy.KubeHostUpgradeControlPlaneStep(
            first_host,
            force,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_FIRST_MASTER,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_FIRST_MASTER_FAILED)
        )
        self.apply_phase.add_stage(stage)
        # Next stage after first control plane is second control plane
        self._add_kube_upgrade_second_control_plane_stage()

    def _add_kube_upgrade_second_control_plane_stage(self):
        """
        Add second control plane kube upgrade stage
        This stage only occurs after networking and if this is a duplex.
        It then proceeds to the next stage
        """
        from nfv_vim import nfvi
        from nfv_vim import strategy

        second_host = self.get_second_host()
        if second_host is not None:
            # force argument is ignored by control plane API
            force = True
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_SECOND_CONTROL_PLANE)
            stage.add_step(strategy.KubeHostUpgradeControlPlaneStep(
                second_host,
                force,
                nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_SECOND_MASTER,
                nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_SECOND_MASTER_FAILED)
            )
            self.apply_phase.add_stage(stage)
        # Next stage after second control plane is to apply kube patch
        self._add_kube_upgrade_patch_stage()

    def _check_host_patch(self, host, new_patches):
        """
        Check a host for whether it is patch current.
        :returns: (Boolean,Boolean) host is patch current, host needs reboot
        """
        # If any new patches have been applied, assume the host will need it.
        # If a patch was controller or worker only then this assumption
        # may not be true.

        # There is no way in the vim to determine from a patch if a reboot
        # will be required until after the patch is applied
        if new_patches:
            return (False, False)

        for host_entry in self._nfvi_sw_patch_hosts:
            if host_entry['name'] == host.name:
                return (host_entry['patch_current'],
                        host_entry['requires_reboot'])

        # Did not find a matching entry in the sw patch hosts list.
        # We cannot determine if it is patch current
        return (False, False)

    def _add_kube_upgrade_patch_stage(self):
        """
        Add patch steps for the kubelet patch
        If required 'applied' patches have not already been applied, fail this
        stage.  This stage is meant to apply the patches tagged as 'available'
        for the kube upgrade.  The patches are then installed on the hosts.
        """
        from nfv_vim import strategy
        from nfv_vim import tables

        applied_patches = None
        available_patches = None
        for kube_version_object in self.nfvi_kube_versions_list:
            if kube_version_object['kube_version'] == self._to_version:
                applied_patches = kube_version_object['applied_patches']
                available_patches = kube_version_object['available_patches']
                break

        # todo(abailey): handle 'committed' state

        # This section validates the 'applied_patches' for a kube upgrade.
        # Note: validation fails on the first required patch in wrong state
        # it does not indicate all pre-requisite patches that are invalid.
        if applied_patches:
            for kube_patch in applied_patches:
                matching_patch = None
                for patch in self.nfvi_sw_patches:
                    if patch['name'] == kube_patch:
                        matching_patch = patch
                        break
                # - Fail if the required patch is missing
                # - Fail if the required patch is not applied
                # - Fail if the required patch is not installed on all hosts
                if matching_patch is None:
                    self.report_build_failure("Missing a required patch: [%s]"
                                              % kube_patch)
                    return
                elif matching_patch['repo_state'] != PATCH_REPO_STATE_APPLIED:
                    self.report_build_failure(
                         "Required pre-applied patch: [%s] is not applied."
                         % kube_patch)
                    return
                elif matching_patch['patch_state'] != PATCH_STATE_APPLIED:
                    self.report_build_failure(
                         "Required patch: [%s] is not installed on all hosts."
                         % kube_patch)
                    return
                else:
                    DLOG.debug("Verified patch: [%s] is applied and installed"
                               % kube_patch)

        # This section validates the 'available_patches' for a kube upgrade.
        # It also sets up the apply and install steps.
        # 'available_patches' are the patches that need to be applied and
        # installed on all hosts during kube upgrade orchestration after the
        # control plane has been setup.
        patches_to_apply = []
        patches_need_host_install = False
        if available_patches:
            for kube_patch in available_patches:
                matching_patch = None
                for patch in self.nfvi_sw_patches:
                    if patch['name'] == kube_patch:
                        matching_patch = patch
                        break
                # - Fail if the required patch is missing
                # - Apply the patch if it is not yet applied
                # - Install the patch on any hosts where it is not installed.
                if matching_patch is None:
                    self.report_build_failure("Missing a required patch: [%s]"
                                              % kube_patch)
                    return
                # if there is an applied_patch that is not applied, fail
                elif matching_patch['repo_state'] != PATCH_REPO_STATE_APPLIED:
                    DLOG.debug("Preparing to apply available patch %s"
                               % kube_patch)
                    patches_to_apply.append(kube_patch)
                    # we apply the patch, so it must be installed on the hosts
                    patches_need_host_install = True
                elif matching_patch['patch_state'] != PATCH_STATE_APPLIED:
                    # One of the patches is not fully installed on all hosts
                    patches_need_host_install = True
                else:
                    DLOG.debug("Skipping available patch %s already applied"
                               % kube_patch)

        if patches_to_apply:
            # Add a stage to 'apply' the patches
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_PATCH)
            stage.add_step(strategy.ApplySwPatchesStep(patches_to_apply))
            self.apply_phase.add_stage(stage)

        if patches_to_apply or patches_need_host_install:
            # add stages to host-install the patches on the different hosts

            # each of the lists has its own stage if it is not empty
            # kubernetes does not run on storage hosts, but it has kube rpms
            controller_0_reboot = []
            controller_0_no_reboot = []
            controller_1_reboot = []
            controller_1_no_reboot = []
            worker_hosts_reboot = []
            worker_hosts_no_reboot = []
            storage_hosts_reboot = []
            storage_hosts_no_reboot = []

            # todo(abailey): refactor the code duplication from  SwPatch
            host_table = tables.tables_get_host_table()
            for host in list(host_table.values()):
                # filter the host out if we do not need to patch it
                current, reboot = self._check_host_patch(host,
                                                         patches_to_apply)
                if not current:
                    if HOST_NAME.CONTROLLER_0 == host.name:
                        if reboot:
                            controller_0_reboot.append(host)
                        else:
                            controller_0_no_reboot.append(host)
                    elif HOST_NAME.CONTROLLER_1 == host.name:
                        if reboot:
                            controller_1_reboot.append(host)
                        else:
                            controller_1_no_reboot.append(host)
                    elif HOST_PERSONALITY.STORAGE in host.personality:
                        if reboot:
                            storage_hosts_reboot.append(host)
                        else:
                            storage_hosts_no_reboot.append(host)

                    # above, An AIO will be added to the controller list, but
                    # ignored internally by _add_controller_strategy_stages
                    # so we add it also to the worker list
                    if HOST_PERSONALITY.WORKER in host.personality:
                        # Ignore worker hosts that are powered down
                        if not host.is_offline():
                            if reboot:
                                worker_hosts_reboot.append(host)
                            else:
                                worker_hosts_no_reboot.append(host)

            # always process but no-reboot before reboot
            # for controllers of same mode, controller-1 before controller-0
            STRATEGY_CREATION_COMMANDS = [
                # controller-1 no-reboot
                (self._add_controller_strategy_stages,
                 controller_1_no_reboot,
                 False),
                (self._add_controller_strategy_stages,
                 controller_0_no_reboot,
                 False),
                (self._add_controller_strategy_stages,
                 controller_1_reboot,
                 True),
                (self._add_controller_strategy_stages,
                 controller_0_reboot,
                 True),
                # then storage
                (self._add_storage_strategy_stages,
                 storage_hosts_no_reboot,
                 False),
                (self._add_storage_strategy_stages,
                 storage_hosts_reboot,
                 True),
                # workers last
                (self._add_worker_strategy_stages,
                 worker_hosts_no_reboot,
                 False),
                (self._add_worker_strategy_stages,
                 worker_hosts_reboot,
                 True)
            ]

            for add_strategy_stages_function, host_list, reboot in \
                    STRATEGY_CREATION_COMMANDS:
                if host_list:
                    # sort each host list by name before adding stages
                    sorted_host_list = sorted(host_list,
                                              key=lambda host: host.name)
                    success, reason = add_strategy_stages_function(
                        sorted_host_list, reboot)
                    if not success:
                        self.report_build_failure(reason)
                        return
        else:
            DLOG.info("No 'available_patches' need to be applied or installed")

        # next stage after this are kubelets, which are updated for all hosts
        self._add_kube_upgrade_kubelets_stage()

    def _add_kube_upgrade_kubelets_stage(self):
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
        HOST_STAGES = [
            (self._add_kubelet_controller_strategy_stages,
             controller_1_std,
             True),
            (self._add_kubelet_controller_strategy_stages,
             controller_0_std,
             True),
            (self._add_kubelet_worker_strategy_stages,
             controller_1_workers,
             True),
            (self._add_kubelet_worker_strategy_stages,
             controller_0_workers,
             not self._single_controller),  # We do NOT reboot an AIO-SX host
            (self._add_kubelet_worker_strategy_stages,
             worker_hosts,
             True)
        ]
        for add_kubelet_stages_function, host_list, reboot in HOST_STAGES:
            if host_list:
                sorted_host_list = sorted(host_list,
                                          key=lambda host: host.name)
                success, reason = add_kubelet_stages_function(sorted_host_list,
                                                              reboot)
                if not success:
                    self.report_build_failure(reason)
                    return
        # stage after kubelets is kube upgrade complete stage
        self._add_kube_upgrade_complete_stage()

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
        # stage after kube upgrade complete stage, cleans up the kube upgrade
        self._add_kube_upgrade_cleanup_stage()

    def _add_kube_upgrade_cleanup_stage(self):
        """
        kube upgrade cleanup stage deletes the kube upgrade.
        This stage occurs after all kube upgrade is completed
        """
        from nfv_vim import strategy
        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_CLEANUP)
        stage.add_step(strategy.KubeUpgradeCleanupStep())
        self.apply_phase.add_stage(stage)

    def report_build_failure(self, reason):
        DLOG.warn("Strategy Build Failed: %s" % reason)
        self._state = strategy.STRATEGY_STATE.BUILD_FAILED
        self.build_phase.result = strategy.STRATEGY_PHASE_RESULT.FAILED
        self.build_phase.result_reason = reason
        self.sw_update_obj.strategy_build_complete(
            False,
            self.build_phase.result_reason)
        self.save()

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

            # After downloading images -> upgrade networking
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_DOWNLOADED_IMAGES:
                self._add_kube_upgrade_networking_stage,

            # if networking state failed, resync at networking state
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_NETWORKING_FAILED:
                self._add_kube_upgrade_networking_stage,

            # After networking -> upgrade first control plane
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_NETWORKING:
                self._add_kube_upgrade_first_control_plane_stage,

            # if upgrading first control plane failed, resume there
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_FIRST_MASTER_FAILED:
                self._add_kube_upgrade_first_control_plane_stage,

            # After first control plane -> upgrade second control plane
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_FIRST_MASTER:
                self._add_kube_upgrade_second_control_plane_stage,

            # if upgrading second control plane failed, resume there
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_SECOND_MASTER_FAILED:
                self._add_kube_upgrade_second_control_plane_stage,

            # After second control plane , proceed with patching
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_SECOND_MASTER:
                self._add_kube_upgrade_patch_stage,

            # kubelets are next kube upgrade phase after second patch applied
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_KUBELETS:
                self._add_kube_upgrade_kubelets_stage,

            # kubelets applied and upgrade is completed, delete the upgrade
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_COMPLETE:
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
