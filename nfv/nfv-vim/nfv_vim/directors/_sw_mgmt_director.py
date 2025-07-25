#
# Copyright (c) 2015-2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import six
import uuid

from nfv_common import config
from nfv_common import debug
from nfv_common import schedule

from nfv_common.helpers import Singleton

from nfv_vim import objects
from nfv_vim import strategy

DLOG = debug.debug_get_logger('nfv_vim.sw_mgmt_director')

_sw_mgmt_director = None


@six.add_metaclass(Singleton)
class SwMgmtDirector(object):
    """
    Software Management Director
    """
    def __init__(self, sw_update,
                 ignore_alarms, single_controller):
        self._sw_update = sw_update
        self._ignore_alarms = ignore_alarms
        self._single_controller = single_controller

    @property
    def sw_update(self):
        """
        Returns the current software update
        """
        return self._sw_update

    @property
    def single_controller(self):
        """
        Returns whether this is a single controller configuration
        """
        return self._single_controller

    def create_sw_patch_strategy(self, controller_apply_type, storage_apply_type,
                                 swift_apply_type, worker_apply_type,
                                 max_parallel_worker_hosts,
                                 default_instance_action, alarm_restrictions,
                                 callback):
        """
        Create Software Patch Strategy
        """
        strategy_uuid = str(uuid.uuid4())

        if self._sw_update is not None:
            # Do not schedule the callback - if creation failed because a
            # strategy already exists, the callback will attempt to operate
            # on the old strategy, which is not what we want.
            reason = "strategy already exists of type:%s" % self._sw_update._sw_update_type
            return None, reason

        self._sw_update = objects.SwPatch()
        success, reason = self._sw_update.strategy_build(
            strategy_uuid, controller_apply_type,
            storage_apply_type, swift_apply_type,
            worker_apply_type, max_parallel_worker_hosts,
            default_instance_action, alarm_restrictions,
            self._ignore_alarms, self._single_controller)

        schedule.schedule_function_call(callback, success, reason,
                                        self._sw_update.strategy)
        return strategy_uuid, ''

    def create_sw_upgrade_strategy(self,
                                   controller_apply_type, storage_apply_type, worker_apply_type,
                                   max_parallel_worker_hosts, default_instance_action,
                                   alarm_restrictions, release, rollback, delete,
                                   snapshot, callback):
        """
        Create Software Upgrade Strategy
        """
        strategy_uuid = str(uuid.uuid4())

        if self._sw_update is not None:
            # Do not schedule the callback - if creation failed because a
            # strategy already exists, the callback will attempt to operate
            # on the old strategy, which is not what we want.
            reason = "strategy already exists of type:%s" % self._sw_update._sw_update_type
            return None, reason

        self._sw_update = objects.SwUpgrade()
        success, reason = self._sw_update.strategy_build(
            strategy_uuid, controller_apply_type, storage_apply_type,
            worker_apply_type, max_parallel_worker_hosts, default_instance_action,
            alarm_restrictions, release, rollback, delete, snapshot,
            self._ignore_alarms, self._single_controller)

        # TODO(jkraitbe): All create_* functions should have this check.
        #   In fact, create functions should be reworked into single function.
        # If the strategy failed to create scheduling will cause timeouts.
        if not success:
            del self._sw_update
            self._sw_update = None
            return None, reason

        schedule.schedule_function_call(callback, success, reason,
                                        self._sw_update.strategy)
        return strategy_uuid, ''

    def create_system_config_update_strategy(self, controller_apply_type,
                                             storage_apply_type, worker_apply_type,
                                             max_parallel_worker_hosts,
                                             default_instance_action,
                                             alarm_restrictions, callback):
        """
        Create System Config Update Strategy
        """
        strategy_uuid = str(uuid.uuid4())

        if self._sw_update is not None:
            # Do not schedule the callback - if creation failed because a
            # strategy already exists, the callback will attempt to operate
            # on the old strategy, which is not what we want.
            reason = "strategy already exists of type:%s" % self._sw_update._sw_update_type
            return None, reason

        self._sw_update = objects.SystemConfigUpdate()
        success, reason = self._sw_update.strategy_build(
            strategy_uuid, controller_apply_type, storage_apply_type,
            worker_apply_type, max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions, self._ignore_alarms,
            self._single_controller)

        schedule.schedule_function_call(callback, success, reason,
                                        self._sw_update.strategy)
        return strategy_uuid, ''

    def create_fw_update_strategy(self,
                                  controller_apply_type,
                                  storage_apply_type,
                                  worker_apply_type,
                                  max_parallel_worker_hosts,
                                  default_instance_action,
                                  alarm_restrictions,
                                  callback):
        """
        Create Firmware Update Strategy
        """
        strategy_uuid = str(uuid.uuid4())

        if self._sw_update is not None:
            # Do not schedule the callback - if creation failed because a
            # strategy already exists, the callback will attempt to operate
            # on the old strategy, which is not what we want.
            reason = "strategy already exists of type:%s" % self._sw_update._sw_update_type
            return None, reason

        self._sw_update = objects.FwUpdate()
        success, reason = self._sw_update.strategy_build(
            strategy_uuid, controller_apply_type,
            storage_apply_type,
            worker_apply_type, max_parallel_worker_hosts,
            default_instance_action, alarm_restrictions,
            self._ignore_alarms, self._single_controller)

        schedule.schedule_function_call(callback, success, reason,
                                        self._sw_update.strategy)
        return strategy_uuid, ''

    def create_kube_rootca_update_strategy(self,
                                           controller_apply_type,
                                           storage_apply_type,
                                           worker_apply_type,
                                           max_parallel_worker_hosts,
                                           default_instance_action,
                                           alarm_restrictions,
                                           expiry_date,
                                           subject,
                                           cert_file,
                                           callback):
        """
        Create Kubernetes Root CA Update Strategy
        """
        strategy_uuid = str(uuid.uuid4())

        if self._sw_update is not None:
            # Do not schedule the callback - if creation failed because a
            # strategy already exists, the callback will attempt to operate
            # on the old strategy, which is not what we want.
            reason = "strategy already exists of type:%s" % self._sw_update._sw_update_type
            return None, reason

        self._sw_update = objects.KubeRootcaUpdate()
        success, reason = self._sw_update.strategy_build(
            strategy_uuid,
            controller_apply_type,
            storage_apply_type,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            self._ignore_alarms,
            self._single_controller,
            expiry_date,
            subject,
            cert_file)

        schedule.schedule_function_call(callback,
                                        success,
                                        reason,
                                        self._sw_update.strategy)
        return strategy_uuid, ''

    def create_kube_upgrade_strategy(self,
                                     controller_apply_type,
                                     storage_apply_type,
                                     worker_apply_type,
                                     max_parallel_worker_hosts,
                                     default_instance_action,
                                     alarm_restrictions,
                                     to_version,
                                     callback):
        """
        Create Kubernetes Upgrade Strategy
        """
        strategy_uuid = str(uuid.uuid4())

        if self._sw_update is not None:
            # Do not schedule the callback - if creation failed because a
            # strategy already exists, the callback will attempt to operate
            # on the old strategy, which is not what we want.
            reason = "strategy already exists of type:%s" % self._sw_update._sw_update_type
            return None, reason

        self._sw_update = objects.KubeUpgrade()
        success, reason = self._sw_update.strategy_build(
            strategy_uuid,
            controller_apply_type,
            storage_apply_type,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            self._ignore_alarms,
            to_version,
            self._single_controller)

        schedule.schedule_function_call(callback,
                                        success,
                                        reason,
                                        self._sw_update.strategy)
        return strategy_uuid, ''

    def apply_sw_update_strategy(self, strategy_uuid, stage_id, callback):
        """
        Apply Software Update Strategy
        """
        success, reason = self._sw_update.strategy_apply(strategy_uuid, stage_id)
        schedule.schedule_function_call(callback, success, reason,
                                        self._sw_update.strategy)
        return

    def abort_sw_update_strategy(self, strategy_uuid, stage_id, callback):
        """
        Abort Software Update Strategy
        """
        success, reason = self._sw_update.strategy_abort(strategy_uuid, stage_id)
        schedule.schedule_function_call(callback, success, reason,
                                        self._sw_update.strategy)
        return

    def delete_sw_update_strategy(self, strategy_uuid, force, callback):
        """
        Delete Software Update Strategy
        """
        success, reason = self._sw_update.strategy_delete(strategy_uuid, force)
        if success:
            self._sw_update.remove()
            del self._sw_update
            self._sw_update = None
        schedule.schedule_function_call(callback, success, reason, strategy_uuid)
        return

    def get_sw_update_strategy(self, sw_update_type):
        """
        Get Software Update Strategy
        """
        if self._sw_update is not None:
            if self._sw_update.sw_update_type == sw_update_type:
                return self._sw_update.strategy
            elif sw_update_type == objects.SW_UPDATE_TYPE.CURRENT_STRATEGY:
                return self._sw_update.strategy
        return None

    def host_lock_failed(self, host):
        """
        Called when a lock of a host failed
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.HOST_LOCK_FAILED, host)

    def disable_host_services_failed(self, host):
        """
        Called when disabling services on a host failed
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.DISABLE_HOST_SERVICES_FAILED, host)

    def enable_host_services_failed(self, host):
        """
        Called when enabling services on a host failed
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.ENABLE_HOST_SERVICES_FAILED, host)

    def kube_host_cordon_failed(self, host):
        """
        Called when a kube host cordon fails
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.KUBE_HOST_CORDON_FAILED, host)

    def kube_host_uncordon_failed(self, host):
        """
        Called when a kube host uncordon fails
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.KUBE_HOST_UNCORDON_FAILED, host)

    def host_unlock_failed(self, host):
        """
        Called when a unlock of a host failed
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.HOST_UNLOCK_FAILED, host)

    def host_reboot_failed(self, host):
        """
        Called when a reboot of a host failed
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.HOST_REBOOT_FAILED, host)

    def host_swact_failed(self, host):
        """
        Called when a swact of a host failed
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.HOST_SWACT_FAILED, host)

    def host_upgrade_failed(self, result):
        """
        Called when an upgrade of a host failed
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.HOST_UPGRADE_FAILED, result)

    def host_upgrade_changed(self, result):
        """
        Called when an upgrade of a host succeeded
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.HOST_UPGRADE_CHANGED, result)

    def host_fw_update_abort_failed(self, host):
        """
        Called when firmware update abort for a host failed
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.HOST_FW_UPDATE_ABORT_FAILED, host)

    def host_fw_update_failed(self, host):
        """
        Called when a firmware update of a host failed
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.HOST_FW_UPDATE_FAILED, host)

    def system_config_update_failed(self, host):
        """
        Called when a system config update for a host phase fails
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.SYSTEM_CONFIG_UPDATE_HOST_FAILED,
                host)

    def kube_host_rootca_update_failed(self, host):
        """
        Called when a kube footca update for a host phase fails
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.KUBE_ROOTCA_UPDATE_HOST_FAILED,
                host)

    def kube_host_upgrade_control_plane_failed(self, host):
        """
        Called when a kube host upgrade for control plane fails
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.KUBE_HOST_UPGRADE_CONTROL_PLANE_FAILED,
                host)

    def kube_host_upgrade_kubelet_failed(self, host):
        """
        Called when a kube host upgrade for kubelet fails
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.KUBE_HOST_UPGRADE_KUBELET_FAILED,
                host)

    def host_audit(self, host):
        """
        Called when a host audit is to be performed
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.HOST_AUDIT, host)

    def host_state_change(self, host):
        """
        Called when a host has changed state
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.HOST_STATE_CHANGED, host)

    def instance_audit(self, instance):
        """
        Called when an instance audit is to be performed
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.INSTANCE_AUDIT, instance)

    def instance_state_change(self, instance):
        """
        Called when an instance has changed state
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.INSTANCE_STATE_CHANGED, instance)

    def migrate_instances_failed(self, reason):
        """
        Called when a migrate instances operation has failed
        """
        if self._sw_update is not None:
            self._sw_update.handle_event(
                strategy.STRATEGY_EVENT.MIGRATE_INSTANCES_FAILED, reason)

    def kube_host_upgrade_list(self, event_data):
        """
        Kubernetes host upgrade list handle_event called
        """
        if event_data['completed']:
            event = strategy.STRATEGY_EVENT.QUERY_KUBE_HOST_UPGRADE_COMPLETED
        else:
            event = strategy.STRATEGY_EVENT.QUERY_KUBE_HOST_UPGRADE_FAILED
        if self._sw_update is not None:
            self._sw_update.handle_event(
                event, event_data)


def get_sw_mgmt_director():
    """
    Returns the Software Management Director
    """
    return _sw_mgmt_director


def sw_mgmt_director_initialize():
    """
    Initialize Software Management Director
    """
    from nfv_vim import database

    global _sw_mgmt_director

    if config.section_exists('sw-mgmt-configuration'):
        section = config.CONF['sw-mgmt-configuration']
        alarm_string = section.get('ignore_alarms', None)
        if alarm_string:
            ignore_alarms = [alarm.strip() for alarm in alarm_string.split(',')]
        else:
            ignore_alarms = []
        single_controller \
            = (section.get('single_controller', 'false').lower() == 'true')

    else:
        ignore_alarms = []
        single_controller = False

    sw_update_objs = database.database_sw_update_get_list()
    if sw_update_objs:
        if len(sw_update_objs) == 1:
            sw_update = sw_update_objs[0]
        else:
            DLOG.error("More than one software update found")
            sw_update = sw_update_objs[-1]
    else:
        sw_update = None

    _sw_mgmt_director = SwMgmtDirector(sw_update,
                                       ignore_alarms,
                                       single_controller)


def sw_mgmt_director_finalize():
    """
    Finalize Software Management Director
    """
    pass
