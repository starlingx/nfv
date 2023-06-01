#
# Copyright (c) 2020-2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_common import debug
from nfv_common import timers

from nfv_common.helpers import coroutine

from nfv_vim import alarm
from nfv_vim import event_log
from nfv_vim import nfvi

from nfv_vim.objects._sw_update import SW_UPDATE_ALARM_TYPES
from nfv_vim.objects._sw_update import SW_UPDATE_EVENT_IDS
from nfv_vim.objects._sw_update import SW_UPDATE_TYPE
from nfv_vim.objects._sw_update import SwUpdate

DLOG = debug.debug_get_logger('nfv_vim.objects.kube_upgrade')
DEFAULT_KUBE_AUDIT_RATE = 5


class KubeUpgrade(SwUpdate):
    """
    Kubernetes Upgrade Object
    """
    def __init__(self, sw_update_uuid=None, strategy_data=None):
        super(KubeUpgrade, self).__init__(
            sw_update_type=SW_UPDATE_TYPE.KUBE_UPGRADE,
            sw_update_uuid=sw_update_uuid,
            strategy_data=strategy_data)
        # these next two values are used by the audit
        self._kube_upgrade = None
        self._kube_upgrade_hosts = list()

    def strategy_build(self,
                       strategy_uuid,
                       controller_apply_type,
                       storage_apply_type,
                       worker_apply_type,
                       max_parallel_worker_hosts,
                       default_instance_action,
                       alarm_restrictions,
                       ignore_alarms,
                       to_version,
                       single_controller):
        """
        Create a kubernetes upgrade strategy
        """
        from nfv_vim import strategy

        if self._strategy:
            reason = "strategy already exists of type:%s" % self._sw_update_type
            return False, reason

        self._strategy = \
            strategy.KubeUpgradeStrategy(strategy_uuid,
                                         controller_apply_type,
                                         storage_apply_type,
                                         worker_apply_type,
                                         max_parallel_worker_hosts,
                                         default_instance_action,
                                         alarm_restrictions,
                                         ignore_alarms,
                                         to_version,
                                         single_controller)
        self._strategy.sw_update_obj = self
        self._strategy.build()
        self._persist()
        return True, ''

    def strategy_build_complete(self, success, reason):
        """
        Creation of a kubernetes upgrade strategy complete
        """
        DLOG.info("Kubernetes upgrade strategy build complete.")
        pass

    @staticmethod
    def alarm_type(alarm_type):
        """
        Returns ALARM_TYPE corresponding to SW_UPDATE_ALARM_TYPES
        """
        ALARM_TYPE_MAPPING = {
            SW_UPDATE_ALARM_TYPES.APPLY_INPROGRESS:
                alarm.ALARM_TYPE.KUBE_UPGRADE_AUTO_APPLY_INPROGRESS,
            SW_UPDATE_ALARM_TYPES.APPLY_ABORTING:
                alarm.ALARM_TYPE.KUBE_UPGRADE_AUTO_APPLY_ABORTING,
            SW_UPDATE_ALARM_TYPES.APPLY_FAILED:
                alarm.ALARM_TYPE.KUBE_UPGRADE_AUTO_APPLY_FAILED,
        }
        return ALARM_TYPE_MAPPING[alarm_type]

    @staticmethod
    def event_id(event_id):
        """
        Returns EVENT_ID corresponding to SW_UPDATE_EVENT_IDS
        """
        EVENT_ID_MAPPING = {
            SW_UPDATE_EVENT_IDS.APPLY_START:
                event_log.EVENT_ID.KUBE_UPGRADE_AUTO_APPLY_START,
            SW_UPDATE_EVENT_IDS.APPLY_INPROGRESS:
                event_log.EVENT_ID.KUBE_UPGRADE_AUTO_APPLY_INPROGRESS,
            SW_UPDATE_EVENT_IDS.APPLY_REJECTED:
                event_log.EVENT_ID.KUBE_UPGRADE_AUTO_APPLY_REJECTED,
            SW_UPDATE_EVENT_IDS.APPLY_CANCELLED:
                event_log.EVENT_ID.KUBE_UPGRADE_AUTO_APPLY_CANCELLED,
            SW_UPDATE_EVENT_IDS.APPLY_FAILED:
                event_log.EVENT_ID.KUBE_UPGRADE_AUTO_APPLY_FAILED,
            SW_UPDATE_EVENT_IDS.APPLY_COMPLETED:
                event_log.EVENT_ID.KUBE_UPGRADE_AUTO_APPLY_COMPLETED,
            SW_UPDATE_EVENT_IDS.APPLY_ABORT:
                event_log.EVENT_ID.KUBE_UPGRADE_AUTO_APPLY_ABORT,
            SW_UPDATE_EVENT_IDS.APPLY_ABORTING:
                event_log.EVENT_ID.KUBE_UPGRADE_AUTO_APPLY_ABORTING,
            SW_UPDATE_EVENT_IDS.APPLY_ABORT_REJECTED:
                event_log.EVENT_ID.KUBE_UPGRADE_AUTO_APPLY_ABORT_REJECTED,
            SW_UPDATE_EVENT_IDS.APPLY_ABORT_FAILED:
                event_log.EVENT_ID.KUBE_UPGRADE_AUTO_APPLY_ABORT_FAILED,
            SW_UPDATE_EVENT_IDS.APPLY_ABORTED:
                event_log.EVENT_ID.KUBE_UPGRADE_AUTO_APPLY_ABORTED,
        }
        return EVENT_ID_MAPPING[event_id]

    def nfvi_update(self):
        """
        NFVI Update
        """
        if self._strategy is None:
            if self._alarms:
                alarm.clear_sw_update_alarm(self._alarms)
            return False

        if self.strategy.is_applying():
            if not self._alarms:
                self._alarms = alarm.raise_sw_update_alarm(
                    self.alarm_type(SW_UPDATE_ALARM_TYPES.APPLY_INPROGRESS))
                event_log.sw_update_issue_log(
                    self.event_id(SW_UPDATE_EVENT_IDS.APPLY_INPROGRESS))

        elif (self.strategy.is_apply_failed() or
              self.strategy.is_apply_timed_out()):
            # we do not raise additional alarms
            if self._alarms:
                alarm.clear_sw_update_alarm(self._alarms)
            return False

        elif self.strategy.is_aborting():
            if not self._alarms:
                self._alarms = alarm.raise_sw_update_alarm(
                    self.alarm_type(SW_UPDATE_ALARM_TYPES.APPLY_ABORTING))
                event_log.sw_update_issue_log(
                    self.event_id(SW_UPDATE_EVENT_IDS.APPLY_ABORTING))

        else:
            if self._alarms:
                alarm.clear_sw_update_alarm(self._alarms)
            return False

        return True

    @coroutine
    def nfvi_kube_upgrade_callback(self, timer_id):
        """
        Audit Kube Upgrade Callback
        """
        from nfv_vim import strategy
        response = (yield)

        if response['completed']:
            DLOG.debug("Audit-Kube-Upgrade callback, response=%s." % response)
            last_state = self._kube_upgrade.state if self._kube_upgrade else None
            self._kube_upgrade = response['result-data']
            current_state = self._kube_upgrade.state if self._kube_upgrade else None
            if last_state != current_state:
                self.handle_event(strategy.STRATEGY_EVENT.KUBE_UPGRADE_CHANGED,
                                  self._kube_upgrade)
        else:
            DLOG.error("Audit-Kube-Upgrade callback, not completed, "
                       "response=%s." % response)

        self._nfvi_audit_inprogress = False

    @coroutine
    def nfvi_kube_host_upgrade_list_callback(self, timer_id):
        """
        Audit Kube Host Upgrade Callback
        """
        from nfv_vim import strategy
        response = (yield)

        if response['completed']:
            DLOG.debug("Audit-Kube-Host-Upgrade callback, response=%s." % response)
            self._kube_upgrade_hosts = response['result-data']
            # todo(abailey): this needs to detect the change
            self.handle_event(strategy.STRATEGY_EVENT.KUBE_HOST_UPGRADE_CHANGED,
                              self._kube_upgrade)
        else:
            DLOG.error("Audit-Kube-Upgrade callback, not completed, "
                       "response=%s." % response)

        self._nfvi_audit_inprogress = False

    @coroutine
    def nfvi_audit(self):
        """
        Audit NFVI layer
        """
        while True:
            timer_id = (yield)

            DLOG.debug("Audit alarms, timer_id=%s." % timer_id)
            self.nfvi_alarms_clear()
            nfvi.nfvi_get_alarms(self.nfvi_alarms_callback(timer_id))
            if not nfvi.nfvi_fault_mgmt_plugin_disabled():
                nfvi.nfvi_get_openstack_alarms(
                    self.nfvi_alarms_callback(timer_id))
            self._nfvi_audit_inprogress = True
            while self._nfvi_audit_inprogress:
                timer_id = (yield)
            # nfvi_alarms_callback sets timer to 2 seconds
            # leave timer at 2 seconds for the next two audit calls

            DLOG.debug("Audit kube upgrade, timer_id=%s." % timer_id)
            nfvi.nfvi_get_kube_upgrade(
                self.nfvi_kube_upgrade_callback(timer_id))
            self._nfvi_audit_inprogress = True
            while self._nfvi_audit_inprogress:
                timer_id = (yield)

            current_state = self._kube_upgrade.state if self._kube_upgrade else None
            # only audit the kube hosts when upgrading kubelets
            if current_state in ["upgrading-kubelets",
                                 "upgraded-kubelets"]:
                DLOG.debug("Audit kube upgrade hosts, timer_id=%s." % timer_id)
                nfvi.nfvi_get_kube_host_upgrade_list(
                    self.nfvi_kube_host_upgrade_list_callback(timer_id))

                self._nfvi_audit_inprogress = True
                while self._nfvi_audit_inprogress:
                    timer_id = (yield)

            # set timer to DEFAULT_KUBE_AUDIT_RATE
            timers.timers_reschedule_timer(timer_id, DEFAULT_KUBE_AUDIT_RATE)
            if not self.nfvi_update():
                DLOG.info("Audit no longer needed.")
                break

            DLOG.debug("Audit kube upgrade still running, timer_id=%s." %
                       timer_id)

        self._nfvi_timer_id = None
