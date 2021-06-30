#
# Copyright (c) 2015-2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from fm_api import constants as fm_constants
from fm_api import fm_api
import json
from six.moves import http_client as httplib

from nfv_common import debug

import nfv_common.alarm.handlers.v1 as alarm_handlers_v1
import nfv_common.alarm.objects.v1 as alarm_objects_v1

from nfv_plugins.alarm_handlers import config
from nfv_plugins.nfvi_plugins.openstack import exceptions
from nfv_plugins.nfvi_plugins.openstack import fm
from nfv_plugins.nfvi_plugins.openstack.objects import OPENSTACK_SERVICE
from nfv_plugins.nfvi_plugins.openstack import openstack

DLOG = debug.debug_get_logger('nfv_plugins.alarm_handlers.fm')

_fm_alarm_id_mapping = dict([
    (alarm_objects_v1.ALARM_TYPE.MULTI_NODE_RECOVERY_MODE,
     fm_constants.FM_ALARM_ID_VM_MULTI_NODE_RECOVERY_MODE),
    (alarm_objects_v1.ALARM_TYPE.HOST_SERVICES_FAILED,
     fm_constants.FM_ALARM_ID_HOST_SERVICES_FAILED),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_FAILED,
     fm_constants.FM_ALARM_ID_VM_FAILED),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_SCHEDULING_FAILED,
     fm_constants.FM_ALARM_ID_VM_FAILED),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_PAUSED,
     fm_constants.FM_ALARM_ID_VM_PAUSED),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_SUSPENDED,
     fm_constants.FM_ALARM_ID_VM_SUSPENDED),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_STOPPED,
     fm_constants.FM_ALARM_ID_VM_STOPPED),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_REBOOTING,
     fm_constants.FM_ALARM_ID_VM_REBOOTING),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_REBUILDING,
     fm_constants.FM_ALARM_ID_VM_REBUILDING),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_EVACUATING,
     fm_constants.FM_ALARM_ID_VM_EVACUATING),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_LIVE_MIGRATING,
     fm_constants.FM_ALARM_ID_VM_LIVE_MIGRATING),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_COLD_MIGRATING,
     fm_constants.FM_ALARM_ID_VM_COLD_MIGRATING),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_COLD_MIGRATED,
     fm_constants.FM_ALARM_ID_VM_COLD_MIGRATED),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_COLD_MIGRATE_REVERTING,
     fm_constants.FM_ALARM_ID_VM_COLD_MIGRATE_REVERTING),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_RESIZING,
     fm_constants.FM_ALARM_ID_VM_RESIZING),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_RESIZED,
     fm_constants.FM_ALARM_ID_VM_RESIZED),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_RESIZE_REVERTING,
     fm_constants.FM_ALARM_ID_VM_RESIZE_REVERTING),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_GUEST_HEARTBEAT,
     fm_constants.FM_ALARM_ID_VM_GUEST_HEARTBEAT),
    (alarm_objects_v1.ALARM_TYPE.INSTANCE_GROUP_POLICY_CONFLICT,
     fm_constants.FM_ALARM_ID_VM_GROUP_POLICY_CONFLICT),
    (alarm_objects_v1.ALARM_TYPE.SW_PATCH_AUTO_APPLY_INPROGRESS,
     fm_constants.FM_ALARM_ID_SW_PATCH_AUTO_APPLY_INPROGRESS),
    (alarm_objects_v1.ALARM_TYPE.SW_PATCH_AUTO_APPLY_ABORTING,
     fm_constants.FM_ALARM_ID_SW_PATCH_AUTO_APPLY_ABORTING),
    (alarm_objects_v1.ALARM_TYPE.SW_PATCH_AUTO_APPLY_FAILED,
     fm_constants.FM_ALARM_ID_SW_PATCH_AUTO_APPLY_FAILED),
    (alarm_objects_v1.ALARM_TYPE.SW_UPGRADE_AUTO_APPLY_INPROGRESS,
     fm_constants.FM_ALARM_ID_SW_UPGRADE_AUTO_APPLY_INPROGRESS),
    (alarm_objects_v1.ALARM_TYPE.SW_UPGRADE_AUTO_APPLY_ABORTING,
     fm_constants.FM_ALARM_ID_SW_UPGRADE_AUTO_APPLY_ABORTING),
    (alarm_objects_v1.ALARM_TYPE.SW_UPGRADE_AUTO_APPLY_FAILED,
     fm_constants.FM_ALARM_ID_SW_UPGRADE_AUTO_APPLY_FAILED),
    (alarm_objects_v1.ALARM_TYPE.FW_UPDATE_AUTO_APPLY_INPROGRESS,
     fm_constants.FM_ALARM_ID_FW_UPDATE_AUTO_APPLY_INPROGRESS),
    (alarm_objects_v1.ALARM_TYPE.FW_UPDATE_AUTO_APPLY_ABORTING,
     fm_constants.FM_ALARM_ID_FW_UPDATE_AUTO_APPLY_ABORTING),
    (alarm_objects_v1.ALARM_TYPE.FW_UPDATE_AUTO_APPLY_FAILED,
     fm_constants.FM_ALARM_ID_FW_UPDATE_AUTO_APPLY_FAILED),
    (alarm_objects_v1.ALARM_TYPE.KUBE_UPGRADE_AUTO_APPLY_INPROGRESS,
     fm_constants.FM_ALARM_ID_KUBE_UPGRADE_AUTO_APPLY_INPROGRESS),
    (alarm_objects_v1.ALARM_TYPE.KUBE_UPGRADE_AUTO_APPLY_ABORTING,
     fm_constants.FM_ALARM_ID_KUBE_UPGRADE_AUTO_APPLY_ABORTING),
    (alarm_objects_v1.ALARM_TYPE.KUBE_UPGRADE_AUTO_APPLY_FAILED,
     fm_constants.FM_ALARM_ID_KUBE_UPGRADE_AUTO_APPLY_FAILED),
])

_fm_alarm_type_mapping = dict([
    (alarm_objects_v1.ALARM_EVENT_TYPE.COMMUNICATIONS_ALARM,
     fm_constants.FM_ALARM_TYPE_1),
    (alarm_objects_v1.ALARM_EVENT_TYPE.QUALITY_OF_SERVICE_ALARM,
     fm_constants.FM_ALARM_TYPE_2),
    (alarm_objects_v1.ALARM_EVENT_TYPE.PROCESSING_ERROR_ALARM,
     fm_constants.FM_ALARM_TYPE_3),
    (alarm_objects_v1.ALARM_EVENT_TYPE.EQUIPMENT_ALARM,
     fm_constants.FM_ALARM_TYPE_4),
    (alarm_objects_v1.ALARM_EVENT_TYPE.ENVIRONMENTAL_ALARM,
     fm_constants.FM_ALARM_TYPE_5),
    (alarm_objects_v1.ALARM_EVENT_TYPE.INTEGRITY_VIOLATION,
     fm_constants.FM_ALARM_TYPE_6),
    (alarm_objects_v1.ALARM_EVENT_TYPE.OPERATIONAL_VIOLATION,
     fm_constants.FM_ALARM_TYPE_7),
    (alarm_objects_v1.ALARM_EVENT_TYPE.PHYSICAL_VIOLATION,
     fm_constants.FM_ALARM_TYPE_8),
    (alarm_objects_v1.ALARM_EVENT_TYPE.SECURITY_SERVICE_VIOLATION,
     fm_constants.FM_ALARM_TYPE_9),
    (alarm_objects_v1.ALARM_EVENT_TYPE.MECHANISM_VIOLATION,
     fm_constants.FM_ALARM_TYPE_9),
    (alarm_objects_v1.ALARM_EVENT_TYPE.TIME_DOMAIN_VIOLATION,
     fm_constants.FM_ALARM_TYPE_10)
])

_fm_alarm_probable_cause = dict([
    (alarm_objects_v1.ALARM_PROBABLE_CAUSE.UNKNOWN,
     fm_constants.ALARM_PROBABLE_CAUSE_UNKNOWN),
    (alarm_objects_v1.ALARM_PROBABLE_CAUSE.SOFTWARE_ERROR,
     fm_constants.ALARM_PROBABLE_CAUSE_45),
    (alarm_objects_v1.ALARM_PROBABLE_CAUSE.SOFTWARE_PROGRAM_ERROR,
     fm_constants.ALARM_PROBABLE_CAUSE_47),
    (alarm_objects_v1.ALARM_PROBABLE_CAUSE.UNDERLYING_RESOURCE_UNAVAILABLE,
     fm_constants.ALARM_PROBABLE_CAUSE_55),
    (alarm_objects_v1.ALARM_PROBABLE_CAUSE.PROCEDURAL_ERROR,
     fm_constants.ALARM_PROBABLE_CAUSE_64)
])

_fm_alarm_severity_mapping = dict([
    (alarm_objects_v1.ALARM_SEVERITY.CLEARED,
     fm_constants.FM_ALARM_SEVERITY_CLEAR),
    (alarm_objects_v1.ALARM_SEVERITY.WARNING,
     fm_constants.FM_ALARM_SEVERITY_WARNING),
    (alarm_objects_v1.ALARM_SEVERITY.MINOR,
     fm_constants.FM_ALARM_SEVERITY_MINOR),
    (alarm_objects_v1.ALARM_SEVERITY.MAJOR,
     fm_constants.FM_ALARM_SEVERITY_MAJOR),
    (alarm_objects_v1.ALARM_SEVERITY.CRITICAL,
     fm_constants.FM_ALARM_SEVERITY_CRITICAL)
])


class FaultManagement(alarm_handlers_v1.AlarmHandler):
    """
    Fault Management Alarm Handler
    """
    _name = 'Fault-Management'
    _version = '1.0.0'
    _provider = 'Wind River'
    _signature = 'e33d7cf6-f270-4256-893e-16266ee4dd2e'

    _platform_alarm_db = dict()
    _openstack_alarm_db = dict()
    _fm_api = None
    _openstack_token = None
    _openstack_directory = None
    _openstack_fm_endpoint_disabled = False
    # This flag is used to disable raising alarm to containerized fm
    # and will be removed in future.
    _fault_management_pod_disabled = True

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def provider(self):
        return self._provider

    @property
    def signature(self):
        return self._signature

    @property
    def openstack_fm_endpoint_disabled(self):
        return self._openstack_fm_endpoint_disabled

    @property
    def openstack_token(self):
        if self._openstack_token is None or \
                   self._openstack_token.is_expired():
            self._openstack_token = openstack.get_token(self._openstack_directory)

        if self._openstack_token is None:
            raise Exception("OpenStack get-token did not complete.")

        return self._openstack_token

    def _format_alarm(self, alarm_data):
        fault = None
        fm_alarm_id = _fm_alarm_id_mapping.get(alarm_data.alarm_type, None)
        if fm_alarm_id is not None:
            fm_alarm_type = _fm_alarm_type_mapping[alarm_data.event_type]
            fm_severity = _fm_alarm_severity_mapping[alarm_data.perceived_severity]
            fm_probable_cause = _fm_alarm_probable_cause[alarm_data.probable_cause]
            fm_uuid = None

            fault = fm_api.Fault(fm_alarm_id, fm_constants.FM_ALARM_STATE_SET,
                                 alarm_data.entity_type, alarm_data.entity,
                                 fm_severity, alarm_data.specific_problem_text,
                                 fm_alarm_type, fm_probable_cause,
                                 alarm_data.proposed_repair_action,
                                 alarm_data.service_affecting,
                                 alarm_data.suppression_allowed,
                                 fm_uuid,
                                 timestamp=alarm_data.raised_timestamp)
        return fault

    def _raise_openstack_alarm(self, format_alarm):
        if self.openstack_fm_endpoint_disabled:
            DLOG.error("Openstack fm endpoint is disabled when raise openstack alarm.")
            return None

        try:
            result = fm.raise_alarm(self.openstack_token, format_alarm)
            result_data = json.loads(result.result_data)
            if result_data is not None:
                return result_data["uuid"]
            else:
                return None

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                if self._openstack_token is not None:
                    self._openstack_token.set_expired()
            else:
                DLOG.exception("Caught exception while trying to raise openstack alarm, "
                               "error=%s." % e)
        except Exception as e:
            DLOG.exception("Caught exception while trying to raise openstack alarm, "
                           "error=%s." % e)

    def raise_alarm(self, alarm_uuid, alarm_data):
        DLOG.debug("Raising alarm, uuid=%s." % alarm_uuid)

        fault = self._format_alarm(alarm_data)
        if fault is not None:
            # conditional statement 'self._fault_management_pod_disabled' is used
            # to disable raising alarm to containerized fm and will be removed in future.
            if "instance" in alarm_data.entity_type and (not self._fault_management_pod_disabled):
                fm_uuid = self._raise_openstack_alarm(fault.as_dict())
                self._openstack_alarm_db[alarm_uuid] = (alarm_data, fm_uuid)
            else:
                fm_uuid = self._fm_api.set_fault(fault)
                self._platform_alarm_db[alarm_uuid] = (alarm_data, fm_uuid)

            if fm_uuid is None:
                DLOG.error("Failed to raise alarm, uuid=%s, fm_uuid=%s."
                           % (alarm_uuid, fm_uuid))
            else:
                DLOG.info("Raised alarm, uuid=%s, fm_uuid=%s."
                          % (alarm_uuid, fm_uuid))
        else:
            DLOG.error("Unknown alarm type (%s) given." % alarm_data.alarm_type)

    def _clear_openstack_alarm(self, fm_uuid):
        if self.openstack_fm_endpoint_disabled:
            DLOG.error("Openstack fm endpoint is disabled when clear openstack alarm.")
            return

        if fm_uuid is None:
            return

        try:
            fm.clear_alarm(self.openstack_token, fm_uuid)

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                if self._openstack_token is not None:
                    self._openstack_token.set_expired()
            else:
                DLOG.exception("Caught exception while trying to clear alarm %s, "
                               "error=%s." % (fm_uuid, e))
        except Exception as e:
            DLOG.exception("Caught exception while trying to clear alarm %s, "
                           "error=%s." % (fm_uuid, e))

    def _clear_platform_alarm(self, alarm_uuid, alarm_data):
        fm_alarm_id = _fm_alarm_id_mapping[alarm_data.alarm_type]
        if self._fm_api.clear_fault(fm_alarm_id, alarm_data.entity):
            DLOG.info("Cleared alarm, uuid=%s." % alarm_uuid)
        else:
            DLOG.error("Failed to clear alarm, uuid=%s." % alarm_uuid)

    def clear_alarm(self, alarm_uuid):
        DLOG.debug("Clearing alarm, uuid=%s." % alarm_uuid)

        alarm_data, fm_uuid = self._platform_alarm_db.get(alarm_uuid, (None, None))
        if alarm_data is not None:
            self._clear_platform_alarm(alarm_uuid, alarm_data)
            # Always remove the alarm from our alarm db. If we failed to clear
            # the alarm, the audit will clear it later.
            del self._platform_alarm_db[alarm_uuid]

        alarm_data, fm_uuid = self._openstack_alarm_db.get(alarm_uuid, (None, None))
        if alarm_data is not None:
            self._clear_openstack_alarm(fm_uuid)
            del self._openstack_alarm_db[alarm_uuid]

    def _audit_openstack_alarms(self):
        DLOG.debug("Auditing openstack alarms.")
        if self.openstack_fm_endpoint_disabled:
            return

        fm_alarms = dict()

        try:
            result = fm.get_alarms(self.openstack_token, OPENSTACK_SERVICE.FM)
            fm_alarms = result.result_data["alarms"]

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                if self._openstack_token is not None:
                    self._openstack_token.set_expired()
            else:
                DLOG.exception("Caught exception while trying to audit openstack alarms, "
                               "error=%s." % e)
        except Exception as e:
            DLOG.exception("Caught exception while trying to audit openstack alarms, "
                           "error=%s." % e)

        # Check for missing alarms needing to be raised
        for alarm_uuid, (alarm_data, fm_uuid) in list(self._openstack_alarm_db.items()):
            if fm_uuid is None:
                self.raise_alarm(alarm_uuid, alarm_data)
            else:
                for fm_alarm in fm_alarms:
                    if fm_uuid == fm_alarm["uuid"]:
                        break
                    else:
                        DLOG.info("Re-raise of alarm, uuid=%s." % alarm_uuid)
                        self.raise_alarm(alarm_uuid, alarm_data)

        # Check for stale alarms needing to be cleared
        for fm_alarm in fm_alarms:
            for alarm_uuid, (alarm_data, fm_uuid) in list(self._openstack_alarm_db.items()):
                if fm_uuid == fm_alarm["uuid"]:
                    break
            else:
                DLOG.info("Clear stale alarm, fm_uuid=%s, fm_alarm_id=%s, "
                           "fm_entity_instance_id=%s."
                          % (fm_alarm["uuid"], fm_alarm["alarm_id"],
                             fm_alarm["entity_instance_id"]))
                self._clear_openstack_alarm(fm_alarm["uuid"])

    def _audit_platform_alarms(self):
        DLOG.debug("Auditing platform alarms.")
        for alarm_type in alarm_objects_v1.ALARM_TYPE:
            fm_alarm_id = _fm_alarm_id_mapping.get(alarm_type, None)
            if fm_alarm_id is None:
                continue

            fm_faults = self._fm_api.get_faults_by_id(fm_alarm_id)
            if not fm_faults:
                continue

            # Check for missing alarms needing to be raised
            for alarm_uuid, (alarm_data, fm_uuid) in list(self._platform_alarm_db.items()):
                if alarm_type == alarm_data.alarm_type:
                    if fm_uuid is None:
                        self.raise_alarm(alarm_uuid, alarm_data)
                    else:
                        for fm_fault in fm_faults:
                            if fm_uuid == fm_fault.uuid:
                                break
                        else:
                            DLOG.info("Re-raise of alarm, uuid=%s."
                                      % alarm_uuid)
                            self.raise_alarm(alarm_uuid, alarm_data)

            # Check for stale alarms needing to be cleared
            for fm_fault in fm_faults:
                for alarm_uuid, (alarm_data, fm_uuid) in list(self._platform_alarm_db.items()):
                    if fm_uuid == fm_fault.uuid:
                        break
                else:
                    DLOG.info("Clear stale alarm, fm_uuid=%s, fm_alarm_id=%s, "
                              "fm_entity_instance_id=%s."
                              % (fm_fault.uuid, fm_fault.alarm_id,
                                 fm_fault.entity_instance_id))

                    self._fm_api.clear_fault(fm_fault.alarm_id,
                                             fm_fault.entity_instance_id)

    def audit_alarms(self):
        DLOG.debug("Auditing alarms begin.")

        # conditional statement 'self._fault_management_pod_disabled' is used
        # to disable raising alarm to containerized fm and will be removed in future.
        if not self._fault_management_pod_disabled:
            self._audit_openstack_alarms()
        self._audit_platform_alarms()

        DLOG.debug("Audited alarms end.")

    def initialize(self, config_file):
        config.load(config_file)
        self._openstack_directory = openstack.get_directory(
            config, openstack.SERVICE_CATEGORY.OPENSTACK)
        self._fm_api = fm_api.FaultAPIs()

        DISABLED_LIST = ['Yes', 'yes', 'Y', 'y', 'True', 'true', 'T', 't', '1']
        self._openstack_fm_endpoint_disabled = (config.CONF['fm']['endpoint_disabled'] in DISABLED_LIST)
        # self._fault_management_pod_disabled is used to disable
        # raising alarm to containerized fm and will be removed in future.
        self._fault_management_pod_disabled = \
            (config.CONF['openstack'].get('fault_management_pod_disabled', 'True') in DISABLED_LIST)

    def finalize(self):
        return
