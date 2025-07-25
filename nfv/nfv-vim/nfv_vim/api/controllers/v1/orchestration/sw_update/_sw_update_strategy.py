
# Copyright (c) 2015-2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import json
import pecan
from pecan import rest
import six
from six.moves import http_client as httplib
from wsme import types as wsme_types
import wsmeext.pecan as wsme_pecan

from nfv_common import debug
from nfv_common import validate
from nfv_vim.api.acl.policies import fw_update_strategy_policy
from nfv_vim.api.acl.policies import kube_rootca_update_strategy_policy
from nfv_vim.api.acl.policies import kube_upgrade_strategy_policy
from nfv_vim.api.acl.policies import sw_update_strategy_policy
from nfv_vim.api.acl.policies import sw_upgrade_strategy_policy
from nfv_vim.api.acl.policies import system_config_update_strategy_policy
from nfv_vim.api.acl import policy

from nfv_vim import rpc

from nfv_vim.api.controllers.v1.orchestration.sw_update._sw_update_defs import SW_UPDATE_ACTION
from nfv_vim.api.controllers.v1.orchestration.sw_update._sw_update_defs import SW_UPDATE_ALARM_RESTRICTION_TYPES
from nfv_vim.api.controllers.v1.orchestration.sw_update._sw_update_defs import SW_UPDATE_APPLY_TYPE
from nfv_vim.api.controllers.v1.orchestration.sw_update._sw_update_defs import SW_UPDATE_NAME
from nfv_vim.api.controllers.v1.orchestration.sw_update._sw_update_defs import SwUpdateActions
from nfv_vim.api.controllers.v1.orchestration.sw_update._sw_update_defs import SwUpdateAlarmRestrictionTypes
from nfv_vim.api.controllers.v1.orchestration.sw_update._sw_update_defs import SwUpdateApplyTypes
from nfv_vim.api.controllers.v1.orchestration.sw_update._sw_update_defs import SwUpdateInstanceActionTypes
from nfv_vim.api.controllers.v1.orchestration.sw_update._sw_update_defs import SwUpdateNames

DLOG = debug.debug_get_logger('nfv_vim.api.sw_update.strategy')

MIN_PARALLEL_HOSTS = 2
MAX_PARALLEL_FW_UPDATE_HOSTS = 5
MAX_PARALLEL_KUBE_ROOTCA_UPDATE_HOSTS = 10
MAX_PARALLEL_KUBE_UPGRADE_HOSTS = 10
MAX_PARALLEL_PATCH_HOSTS = 100
MAX_PARALLEL_SYSTEM_CONFIG_UPDATE_HOSTS = 100
MAX_PARALLEL_UPGRADE_HOSTS = 10


def _get_sw_update_type_from_path(path):
    split_path = path.split('/')
    if 'sw-upgrade' in split_path:
        return SW_UPDATE_NAME.SW_UPGRADE
    elif 'system-config-update' in split_path:
        return SW_UPDATE_NAME.SYSTEM_CONFIG_UPDATE
    elif 'fw-update' in split_path:
        return SW_UPDATE_NAME.FW_UPDATE
    elif 'kube-rootca-update' in split_path:
        return SW_UPDATE_NAME.KUBE_ROOTCA_UPDATE
    elif 'kube-upgrade' in split_path:
        return SW_UPDATE_NAME.KUBE_UPGRADE
    elif 'current-strategy' in split_path:
        return SW_UPDATE_NAME.CURRENT_STRATEGY
    else:
        DLOG.error("Unknown sw_update_type in path: %s" % path)
        return 'unknown'


class SwUpdateStrategyStageStepData(wsme_types.Base):
    """
    Software Update Strategy - Stage Step Data
    """
    step_id = wsme_types.wsattr(int, name='step-id')
    step_name = wsme_types.wsattr(six.text_type, name='step-name')
    timeout = wsme_types.wsattr(int, name='timeout')
    entity_type = wsme_types.wsattr(six.text_type, name='entity-type')
    entity_uuids = wsme_types.wsattr([six.text_type], name='entity-uuids')
    entity_names = wsme_types.wsattr([six.text_type], name='entity-names')
    result = wsme_types.wsattr(six.text_type, name='result')
    reason = wsme_types.wsattr(six.text_type, name='reason')
    start_date_time = wsme_types.wsattr(six.text_type, name='start-date-time')
    end_date_time = wsme_types.wsattr(six.text_type, name='end-date-time')


class SwUpdateStrategyStageData(wsme_types.Base):
    """
    Software Update Strategy - Stage Data
    """
    stage_id = wsme_types.wsattr(int, name='stage-id')
    stage_name = wsme_types.wsattr(six.text_type, name='stage-name')
    timeout = wsme_types.wsattr(int, name='timeout')
    total_steps = wsme_types.wsattr(int, name='total-steps')
    current_step = wsme_types.wsattr(int, name='current-step')
    steps = wsme_types.wsattr([SwUpdateStrategyStageStepData], name='steps')
    inprogress = wsme_types.wsattr(bool, name='inprogress')
    result = wsme_types.wsattr(six.text_type, name='result')
    reason = wsme_types.wsattr(six.text_type, name='reason')
    start_date_time = wsme_types.wsattr(six.text_type, name='start-date-time')
    end_date_time = wsme_types.wsattr(six.text_type, name='end-date-time')


class SwUpdateStrategyPhaseData(wsme_types.Base):
    """
    Software Update Strategy - Phase Data
    """
    phase_name = wsme_types.wsattr(six.text_type, name='phase-name')
    timeout = wsme_types.wsattr(int, name='timeout')
    total_stages = wsme_types.wsattr(int, name='total-stages')
    current_stage = wsme_types.wsattr(int, name='current-stage')
    stop_at_stage = wsme_types.wsattr(int, name='stop-at-stage')
    stages = wsme_types.wsattr([SwUpdateStrategyStageData], name='stages')
    inprogress = wsme_types.wsattr(bool, name='inprogress')
    completion_percentage = wsme_types.wsattr(int, name='completion-percentage')
    result = wsme_types.wsattr(six.text_type, name='result')
    reason = wsme_types.wsattr(six.text_type, name='reason')
    response = wsme_types.wsattr(six.text_type, name='response')
    start_date_time = wsme_types.wsattr(six.text_type, name='start-date-time')
    end_date_time = wsme_types.wsattr(six.text_type, name='end-date-time')


class SwUpdateStrategyData(wsme_types.Base):
    """
    Software Update Strategy - Data
    """
    uuid = wsme_types.wsattr(six.text_type, name='uuid')
    name = wsme_types.wsattr(SwUpdateNames, name='name')
    release = wsme_types.wsattr(six.text_type, mandatory=False,
                                name='release')
    controller_apply_type = wsme_types.wsattr(SwUpdateApplyTypes,
                                              name='controller-apply-type')
    storage_apply_type = wsme_types.wsattr(SwUpdateApplyTypes,
                                           name='storage-apply-type')
    swift_apply_type = wsme_types.wsattr(SwUpdateApplyTypes,
                                         name='swift-apply-type')
    worker_apply_type = wsme_types.wsattr(SwUpdateApplyTypes,
                                          name='worker-apply-type')
    max_parallel_worker_hosts = wsme_types.wsattr(
        int, name='max-parallel-worker-hosts')
    default_instance_action = wsme_types.wsattr(SwUpdateInstanceActionTypes,
                                                name='default-instance-action')
    alarm_restrictions = wsme_types.wsattr(SwUpdateAlarmRestrictionTypes,
                                           name='alarm-restrictions')
    state = wsme_types.wsattr(six.text_type, name='state')
    current_phase = wsme_types.wsattr(six.text_type, name='current-phase')
    current_phase_completion_percentage \
        = wsme_types.wsattr(int, name='current-phase-completion-percentage')
    build_phase = wsme_types.wsattr(SwUpdateStrategyPhaseData, name='build-phase')
    apply_phase = wsme_types.wsattr(SwUpdateStrategyPhaseData, name='apply-phase')
    abort_phase = wsme_types.wsattr(SwUpdateStrategyPhaseData, name='abort-phase')


class SwUpgradeStrategyCreateData(wsme_types.Base):
    """
    Software Upgrade Strategy - Create Data
    """
    controller_apply_type = wsme_types.wsattr(SwUpdateApplyTypes, mandatory=True,
                                              name='controller-apply-type')
    release = wsme_types.wsattr(six.text_type, mandatory=False,
                                name='release')
    rollback = wsme_types.wsattr(bool, mandatory=False,
                                 name='rollback')
    delete = wsme_types.wsattr(bool, mandatory=False,
                                 name='delete')
    snapshot = wsme_types.wsattr(bool, mandatory=False,
                                 name='snapshot')
    storage_apply_type = wsme_types.wsattr(SwUpdateApplyTypes, mandatory=True,
                                           name='storage-apply-type')
    worker_apply_type = wsme_types.wsattr(SwUpdateApplyTypes, mandatory=True,
                                          name='worker-apply-type')
    max_parallel_worker_hosts = wsme_types.wsattr(
        int, mandatory=False, name='max-parallel-worker-hosts')
    default_instance_action = wsme_types.wsattr(SwUpdateInstanceActionTypes,
                                                mandatory=True,
                                                name='default-instance-action')
    alarm_restrictions = wsme_types.wsattr(
        SwUpdateAlarmRestrictionTypes, mandatory=False,
        default=SW_UPDATE_ALARM_RESTRICTION_TYPES.STRICT,
        name='alarm-restrictions')


class SwUpdateStrategyDeleteData(wsme_types.Base):
    """
    Software Update Strategy - Delete Data
    """
    force = wsme_types.wsattr(bool, mandatory=False, name='force',
                              default=False)


class SystemConfigUpdateStrategyCreateData(wsme_types.Base):
    """
    System Config Update Strategy - Create Data
    """
    controller_apply_type = wsme_types.wsattr(SwUpdateApplyTypes, mandatory=True,
                                              name='controller-apply-type')
    storage_apply_type = wsme_types.wsattr(SwUpdateApplyTypes, mandatory=True,
                                           name='storage-apply-type')
    worker_apply_type = wsme_types.wsattr(SwUpdateApplyTypes, mandatory=True,
                                          name='worker-apply-type')
    max_parallel_worker_hosts = wsme_types.wsattr(
        int, mandatory=False, name='max-parallel-worker-hosts')
    default_instance_action = wsme_types.wsattr(SwUpdateInstanceActionTypes,
                                                mandatory=True,
                                                name='default-instance-action')
    alarm_restrictions = wsme_types.wsattr(
        SwUpdateAlarmRestrictionTypes, mandatory=False,
        default=SW_UPDATE_ALARM_RESTRICTION_TYPES.STRICT,
        name='alarm-restrictions')


class FwUpdateStrategyCreateData(wsme_types.Base):
    """
    Firmware Update Strategy - Create Data
    """
    controller_apply_type = wsme_types.wsattr(SwUpdateApplyTypes, mandatory=True,
                                              name='controller-apply-type')
    storage_apply_type = wsme_types.wsattr(SwUpdateApplyTypes, mandatory=True,
                                           name='storage-apply-type')
    worker_apply_type = wsme_types.wsattr(SwUpdateApplyTypes, mandatory=True,
                                          name='worker-apply-type')
    max_parallel_worker_hosts = wsme_types.wsattr(
        int, mandatory=False, name='max-parallel-worker-hosts')
    default_instance_action = wsme_types.wsattr(SwUpdateInstanceActionTypes,
                                                mandatory=True,
                                                name='default-instance-action')
    alarm_restrictions = wsme_types.wsattr(
        SwUpdateAlarmRestrictionTypes, mandatory=False,
        default=SW_UPDATE_ALARM_RESTRICTION_TYPES.STRICT,
        name='alarm-restrictions')


class KubeRootcaUpdateStrategyCreateData(wsme_types.Base):
    """
    Kubernetes Root CA Update Strategy - Create Data
    """
    expiry_date = wsme_types.wsattr(six.text_type,
                                    mandatory=False,
                                    name='expiry-date')
    subject = wsme_types.wsattr(six.text_type,
                                mandatory=False,
                                name='subject')
    cert_file = wsme_types.wsattr(six.text_type,
                                  mandatory=False,
                                  name='cert-file')
    storage_apply_type = wsme_types.wsattr(SwUpdateApplyTypes,
                                           mandatory=True,
                                           name='storage-apply-type')
    worker_apply_type = wsme_types.wsattr(SwUpdateApplyTypes,
                                          mandatory=True,
                                          name='worker-apply-type')
    max_parallel_worker_hosts = wsme_types.wsattr(
        int,
        mandatory=False,
        name='max-parallel-worker-hosts')
    default_instance_action = wsme_types.wsattr(SwUpdateInstanceActionTypes,
                                                mandatory=True,
                                                name='default-instance-action')
    alarm_restrictions = wsme_types.wsattr(
        SwUpdateAlarmRestrictionTypes,
        mandatory=False,
        default=SW_UPDATE_ALARM_RESTRICTION_TYPES.STRICT,
        name='alarm-restrictions')


class KubeUpgradeStrategyCreateData(wsme_types.Base):
    """
    Kubernetes Upgrade Strategy - Create Data
    """
    to_version = wsme_types.wsattr(six.text_type,
                                   mandatory=True,
                                   name='to-version')
    storage_apply_type = wsme_types.wsattr(SwUpdateApplyTypes,
                                           mandatory=True,
                                           name='storage-apply-type')
    worker_apply_type = wsme_types.wsattr(SwUpdateApplyTypes,
                                          mandatory=True,
                                          name='worker-apply-type')
    max_parallel_worker_hosts = wsme_types.wsattr(
        int,
        mandatory=False,
        name='max-parallel-worker-hosts')
    default_instance_action = wsme_types.wsattr(SwUpdateInstanceActionTypes,
                                                mandatory=True,
                                                name='default-instance-action')
    alarm_restrictions = wsme_types.wsattr(
        SwUpdateAlarmRestrictionTypes,
        mandatory=False,
        default=SW_UPDATE_ALARM_RESTRICTION_TYPES.STRICT,
        name='alarm-restrictions')


class SwUpdateStrategyActionData(wsme_types.Base):
    """
    Software Update Strategy - Action Data
    """
    action = wsme_types.wsattr(SwUpdateActions, mandatory=True, name='action')
    stage_id = wsme_types.wsattr(int, mandatory=False, name='stage-id')


class SwUpdateStrategyQueryData(wsme_types.Base):
    """
    Software Update Strategy - Query Data
    """
    strategy = wsme_types.wsattr(SwUpdateStrategyData, default=None,
                                 name='strategy')

    @staticmethod
    def convert_strategy_phase(phase_data):
        phase = SwUpdateStrategyPhaseData()
        phase.phase_name = phase_data['name']
        phase.timeout = phase_data['timeout']
        phase.total_stages = phase_data['total_stages']
        phase.current_stage = phase_data['current_stage']
        phase.stop_at_stage = phase_data['stop_at_stage']
        phase.stages = list()
        for stage_data in phase_data['stages']:
            stage = SwUpdateStrategyStageData()
            stage.stage_id = stage_data['id']
            stage.stage_name = stage_data['name']
            stage.timeout = stage_data['timeout']
            stage.total_steps = stage_data['total_steps']
            stage.current_step = stage_data['current_step']
            stage.steps = list()
            for step_data in stage_data['steps']:
                step = SwUpdateStrategyStageStepData()
                step.step_id = step_data['id']
                step.step_name = step_data['name']
                step.timeout = step_data['timeout']
                step.entity_type = step_data['entity_type']
                step.entity_uuids = step_data['entity_uuids']
                step.entity_names = step_data['entity_names']
                step.result = step_data['result']
                step.reason = step_data['result_reason']
                step.start_date_time = step_data['start_date_time']
                step.end_date_time = step_data['end_date_time']
                stage.steps.append(step)
            stage.inprogress = stage_data['inprogress']
            stage.result = stage_data['result']
            stage.reason = stage_data['result_reason']
            stage.start_date_time = stage_data['start_date_time']
            stage.end_date_time = stage_data['end_date_time']
            phase.stages.append(stage)
        phase.inprogress = phase_data['inprogress']
        phase.completion_percentage = phase_data['completion_percentage']
        phase.result = phase_data['result']
        phase.reason = phase_data['result_reason']
        phase.response = phase_data['result_response']
        phase.start_date_time = phase_data['start_date_time']
        phase.end_date_time = phase_data['end_date_time']
        return phase

    def convert_strategy(self, strategy_data):
        strategy = SwUpdateStrategyData()
        strategy.uuid = strategy_data['uuid']
        strategy.name = strategy_data['name']
        if strategy.name == SW_UPDATE_NAME.SW_UPGRADE:
            strategy.release = strategy_data['release']
        strategy.controller_apply_type = strategy_data['controller_apply_type']
        strategy.storage_apply_type = strategy_data['storage_apply_type']
        strategy.swift_apply_type = strategy_data['swift_apply_type']
        strategy.worker_apply_type = strategy_data['worker_apply_type']
        strategy.max_parallel_worker_hosts = \
            strategy_data['max_parallel_worker_hosts']
        strategy.default_instance_action = strategy_data['default_instance_action']
        strategy.alarm_restrictions = strategy_data['alarm_restrictions']
        strategy.state = strategy_data['state']
        strategy.current_phase = strategy_data['current_phase']
        strategy.current_phase_completion_percentage \
            = strategy_data['current_phase_completion_percentage']
        strategy.build_phase = \
            self.convert_strategy_phase(strategy_data['build_phase'])
        strategy.apply_phase = \
            self.convert_strategy_phase(strategy_data['apply_phase'])
        strategy.abort_phase = \
            self.convert_strategy_phase(strategy_data['abort_phase'])
        self.strategy = strategy

    def convert_current_strategy(self, strategy_data):
        strategy = SwUpdateStrategyData()
        strategy.name = strategy_data['name']
        strategy.state = strategy_data['state']
        self.strategy = strategy


class SwUpdateStrategyActionAPI(rest.RestController):
    """
    Software Update Strategy Action Rest API
    """
    @wsme_pecan.wsexpose(SwUpdateStrategyQueryData, six.text_type,
                         body=SwUpdateStrategyActionData,
                         status_code=httplib.ACCEPTED)
    def post(self, request_data):
        if wsme_types.Unset == request_data.stage_id:
            if SW_UPDATE_ACTION.APPLY_STAGE == request_data.action or \
                    SW_UPDATE_ACTION.ABORT_STAGE == request_data.action:
                DLOG.error("No stage-id received")
                return pecan.abort(httplib.BAD_REQUEST, "No stage-id received")
            request_data.stage_id = None

        if SW_UPDATE_ACTION.APPLY_ALL == request_data.action or \
                SW_UPDATE_ACTION.APPLY_STAGE == request_data.action:
            rpc_request = rpc.APIRequestApplySwUpdateStrategy()
            rpc_request.sw_update_type = _get_sw_update_type_from_path(
                pecan.request.path)
            rpc_request.stage_id = request_data.stage_id
            vim_connection = pecan.request.vim.open_connection()
            vim_connection.send(rpc_request.serialize())
            msg = vim_connection.receive(timeout_in_secs=30)
            if msg is None:
                DLOG.error("No response received.")
                return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

            response = rpc.RPCMessage.deserialize(msg)
            if rpc.RPC_MSG_TYPE.APPLY_SW_UPDATE_STRATEGY_RESPONSE != response.type:
                DLOG.error("Unexpected message type received, msg_type=%s."
                           % response.type)
                return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

            if rpc.RPC_MSG_RESULT.SUCCESS == response.result:
                strategy = json.loads(response.strategy)
                query_data = SwUpdateStrategyQueryData()
                query_data.convert_strategy(strategy)
                return query_data

            elif rpc.RPC_MSG_RESULT.NOT_FOUND == response.result:
                DLOG.info("No strategy exists")
                return pecan.abort(httplib.NOT_FOUND)

            DLOG.error("Unexpected result received, result=%s." % response.result)
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        elif SW_UPDATE_ACTION.ABORT == request_data.action or \
                SW_UPDATE_ACTION.ABORT_STAGE == request_data.action:
            rpc_request = rpc.APIRequestAbortSwUpdateStrategy()
            rpc_request.sw_update_type = _get_sw_update_type_from_path(
                pecan.request.path)
            rpc_request.stage_id = request_data.stage_id
            vim_connection = pecan.request.vim.open_connection()
            vim_connection.send(rpc_request.serialize())
            msg = vim_connection.receive(timeout_in_secs=30)
            if msg is None:
                DLOG.error("No response received.")
                return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

            response = rpc.RPCMessage.deserialize(msg)
            if rpc.RPC_MSG_TYPE.ABORT_SW_UPDATE_STRATEGY_RESPONSE != response.type:
                DLOG.error("Unexpected message type received, msg_type=%s."
                           % response.type)
                return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

            if rpc.RPC_MSG_RESULT.SUCCESS == response.result:
                strategy = json.loads(response.strategy)
                query_data = SwUpdateStrategyQueryData()
                query_data.convert_strategy(strategy)
                return query_data

            elif rpc.RPC_MSG_RESULT.NOT_FOUND == response.result:
                DLOG.info("No strategy exists")
                return pecan.abort(httplib.NOT_FOUND)

            DLOG.error("Unexpected result received, result=%s." % response.result)
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        DLOG.error("Unexpected action received, result=%s." % request_data.action)
        return pecan.abort(httplib.BAD_REQUEST)

    def enforce_policy(self, method_name, auth_context_dict):
        """Check policy rules for each action of this controller."""
        # this handles the apply and abort requests
        if method_name == "post":
            policy.check(sw_update_strategy_policy.POLICY_ROOT % "post", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        else:
            policy.check('admin_in_system_projects', {}, auth_context_dict)


class SwUpdateStrategyAPI(rest.RestController):
    """
    Software Update Strategy Rest API
    """
    actions = SwUpdateStrategyActionAPI()

    @wsme_pecan.wsexpose(SwUpdateStrategyQueryData, six.text_type, status_code=httplib.OK)
    def get_one(self, strategy_uuid):
        if not validate.valid_uuid_str(strategy_uuid):
            DLOG.error("Invalid strategy uuid received, uuid=%s." % strategy_uuid)
            return pecan.abort(httplib.BAD_REQUEST,
                               "Invalid strategy uuid, uuid=%s" % strategy_uuid)

        rpc_request = rpc.APIRequestGetSwUpdateStrategy()
        rpc_request.uuid = strategy_uuid
        vim_connection = pecan.request.vim.open_connection()
        vim_connection.send(rpc_request.serialize())
        msg = vim_connection.receive(timeout_in_secs=30)
        if msg is None:
            DLOG.error("No response received.")
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        response = rpc.RPCMessage.deserialize(msg)
        if rpc.RPC_MSG_TYPE.GET_SW_UPDATE_STRATEGY_RESPONSE != response.type:
            DLOG.error("Unexpected message type received, msg_type=%s."
                       % response.type)
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        if rpc.RPC_MSG_RESULT.SUCCESS == response.result:
            strategy = json.loads(response.strategy)
            query_data = SwUpdateStrategyQueryData()
            query_data.convert_strategy(strategy)
            return query_data

        elif rpc.RPC_MSG_RESULT.NOT_FOUND == response.result:
            DLOG.debug("No strategy exists matching strategy uuid %s"
                       % strategy_uuid)
            return pecan.abort(httplib.NOT_FOUND)

        DLOG.error("Unexpected result received, result=%s." % response.result)
        return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

    @wsme_pecan.wsexpose(SwUpdateStrategyQueryData, status_code=httplib.OK)
    def get_all(self):
        rpc_request = rpc.APIRequestGetSwUpdateStrategy()
        rpc_request.sw_update_type = _get_sw_update_type_from_path(
            pecan.request.path)
        vim_connection = pecan.request.vim.open_connection()
        vim_connection.send(rpc_request.serialize())
        msg = vim_connection.receive(timeout_in_secs=30)
        if msg is None:
            DLOG.error("No response received.")
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        response = rpc.RPCMessage.deserialize(msg)
        if rpc.RPC_MSG_TYPE.GET_SW_UPDATE_STRATEGY_RESPONSE != response.type:
            DLOG.error("Unexpected message type received, msg_type=%s."
                       % response.type)
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        if rpc.RPC_MSG_RESULT.SUCCESS == response.result:
            strategy = json.loads(response.strategy)
            query_data = SwUpdateStrategyQueryData()
            query_data.convert_strategy(strategy)
            return query_data

        elif rpc.RPC_MSG_RESULT.NOT_FOUND == response.result:
            DLOG.verbose("No strategy exists.")
            query_data = SwUpdateStrategyQueryData()
            return query_data

        DLOG.error("Unexpected result received, result=%s." % response.result)
        return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

    @wsme_pecan.wsexpose(None, six.text_type, body=SwUpdateStrategyDeleteData,
                         status_code=httplib.OK)
    def delete(self, request_data):
        rpc_request = rpc.APIRequestDeleteSwUpdateStrategy()
        rpc_request.sw_update_type = _get_sw_update_type_from_path(
            pecan.request.path)
        rpc_request.force = request_data.force
        vim_connection = pecan.request.vim.open_connection()
        vim_connection.send(rpc_request.serialize())
        msg = vim_connection.receive(timeout_in_secs=30)
        if msg is None:
            DLOG.error("No response received.")
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        response = rpc.RPCMessage.deserialize(msg)
        if rpc.RPC_MSG_TYPE.DELETE_SW_UPDATE_STRATEGY_RESPONSE != response.type:
            DLOG.error("Unexpected message type received, msg_type=%s."
                       % response.type)
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        if rpc.RPC_MSG_RESULT.SUCCESS == response.result:
            return

        elif rpc.RPC_MSG_RESULT.NOT_FOUND == response.result:
            DLOG.info("No strategy exists")
            return pecan.abort(httplib.NOT_FOUND)

        elif rpc.RPC_MSG_RESULT.FAILED == response.result:
            DLOG.info("Strategy delete failed")
            # TODO(abailey): consider adding error_string to
            #     DELETE_SW_UPDATE_STRATEGY_RESPONSE
            return pecan.abort(httplib.CONFLICT)

        DLOG.error("Unexpected result received, result=%s." % response.result)
        return pecan.abort(httplib.INTERNAL_SERVER_ERROR)


class SwUpgradeStrategyAPI(SwUpdateStrategyAPI):
    """
    Software Upgrade Strategy Rest API
    """
    @wsme_pecan.wsexpose(SwUpdateStrategyQueryData,
                         body=SwUpgradeStrategyCreateData,
                         status_code=httplib.OK)
    def post(self, request_data):
        rpc_request = rpc.APIRequestCreateSwUpgradeStrategy()
        rpc_request.sw_update_type = _get_sw_update_type_from_path(
            pecan.request.path)
        rpc_request.release = request_data.release
        rpc_request.rollback = request_data.rollback
        rpc_request.delete = request_data.delete
        rpc_request.snapshot = request_data.snapshot
        rpc_request.controller_apply_type = request_data.controller_apply_type
        rpc_request.storage_apply_type = request_data.storage_apply_type
        rpc_request.swift_apply_type = SW_UPDATE_APPLY_TYPE.IGNORE
        rpc_request.worker_apply_type = request_data.worker_apply_type
        if wsme_types.Unset != request_data.max_parallel_worker_hosts:
            if request_data.max_parallel_worker_hosts < MIN_PARALLEL_HOSTS \
                    or request_data.max_parallel_worker_hosts > \
                    MAX_PARALLEL_UPGRADE_HOSTS:
                return pecan.abort(
                    httplib.BAD_REQUEST,
                    "Invalid value for max-parallel-worker-hosts")
            rpc_request.max_parallel_worker_hosts = \
                request_data.max_parallel_worker_hosts
        rpc_request.default_instance_action = request_data.default_instance_action
        rpc_request.alarm_restrictions = request_data.alarm_restrictions
        vim_connection = pecan.request.vim.open_connection()
        vim_connection.send(rpc_request.serialize())
        msg = vim_connection.receive(timeout_in_secs=30)
        if msg is None:
            DLOG.error("No response received.")
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        response = rpc.RPCMessage.deserialize(msg)
        if rpc.RPC_MSG_TYPE.CREATE_SW_UPDATE_STRATEGY_RESPONSE != response.type:
            DLOG.error("Unexpected message type received, msg_type=%s."
                       % response.type)
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        if rpc.RPC_MSG_RESULT.SUCCESS == response.result:
            strategy = json.loads(response.strategy)
            query_data = SwUpdateStrategyQueryData()
            query_data.convert_strategy(strategy)
            return query_data
        elif rpc.RPC_MSG_RESULT.FAILED == response.result and response.error_string:
            return pecan.abort(httplib.BAD_REQUEST, response.error_string)
        elif rpc.RPC_MSG_RESULT.CONFLICT == response.result:
            return pecan.abort(httplib.CONFLICT, response.error_string)

        DLOG.error("Unexpected result received, result=%s." % response.result)
        return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

    def enforce_policy(self, method_name, auth_context_dict):
        """Check policy rules for each action of this controller."""
        if method_name == "delete":
            policy.check(sw_upgrade_strategy_policy.POLICY_ROOT % "delete", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        elif method_name in ["get_all", "get_one"]:
            policy.check(sw_upgrade_strategy_policy.POLICY_ROOT % "get", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        elif method_name == "post":
            policy.check(sw_upgrade_strategy_policy.POLICY_ROOT % "add", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        else:
            policy.check('admin_in_system_projects', {}, auth_context_dict)


class SystemConfigUpdateStrategyAPI(SwUpdateStrategyAPI):
    """
    System Config Update Strategy Rest API
    """
    @wsme_pecan.wsexpose(SwUpdateStrategyQueryData,
                         body=SystemConfigUpdateStrategyCreateData,
                         status_code=httplib.OK)
    def post(self, request_data):
        rpc_request = rpc.APIRequestCreateSwUpdateStrategy()
        rpc_request.sw_update_type = _get_sw_update_type_from_path(
            pecan.request.path)
        rpc_request.controller_apply_type = request_data.controller_apply_type
        rpc_request.storage_apply_type = request_data.storage_apply_type
        rpc_request.worker_apply_type = request_data.worker_apply_type
        if wsme_types.Unset != request_data.max_parallel_worker_hosts:
            if request_data.max_parallel_worker_hosts < MIN_PARALLEL_HOSTS \
                    or request_data.max_parallel_worker_hosts > \
                    MAX_PARALLEL_SYSTEM_CONFIG_UPDATE_HOSTS:
                return pecan.abort(
                    httplib.BAD_REQUEST,
                    "Invalid value for max-parallel-worker-hosts")
            rpc_request.max_parallel_worker_hosts = \
                request_data.max_parallel_worker_hosts
        rpc_request.default_instance_action = request_data.default_instance_action
        rpc_request.alarm_restrictions = request_data.alarm_restrictions
        vim_connection = pecan.request.vim.open_connection()
        vim_connection.send(rpc_request.serialize())
        msg = vim_connection.receive(timeout_in_secs=30)
        if msg is None:
            DLOG.error("No response received.")
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        response = rpc.RPCMessage.deserialize(msg)
        if rpc.RPC_MSG_TYPE.CREATE_SW_UPDATE_STRATEGY_RESPONSE != response.type:
            DLOG.error("Unexpected message type received, msg_type=%s."
                       % response.type)
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        if rpc.RPC_MSG_RESULT.SUCCESS == response.result:
            strategy = json.loads(response.strategy)
            query_data = SwUpdateStrategyQueryData()
            query_data.convert_strategy(strategy)
            return query_data
        elif rpc.RPC_MSG_RESULT.FAILED == response.result and response.error_string:
            return pecan.abort(httplib.BAD_REQUEST, response.error_string)
        elif rpc.RPC_MSG_RESULT.CONFLICT == response.result:
            return pecan.abort(httplib.CONFLICT, response.error_string)

        DLOG.error("Unexpected result received, result=%s." % response.result)
        return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

    def enforce_policy(self, method_name, auth_context_dict):
        """Check policy rules for each action of this controller."""
        if method_name == "delete":
            policy.check(system_config_update_strategy_policy.POLICY_ROOT % "delete",
                           {}, auth_context_dict, exc=policy.PolicyForbidden)
        elif method_name in ["get_all", "get_one"]:
            policy.check(system_config_update_strategy_policy.POLICY_ROOT % "get",
                           {}, auth_context_dict, exc=policy.PolicyForbidden)
        elif method_name == "post":
            policy.check(system_config_update_strategy_policy.POLICY_ROOT % "add",
                           {}, auth_context_dict, exc=policy.PolicyForbidden)
        else:
            policy.check('admin_in_system_projects', {}, auth_context_dict)


class FwUpdateStrategyAPI(SwUpdateStrategyAPI):
    """
    Firmware Update Strategy Rest API
    """
    @wsme_pecan.wsexpose(SwUpdateStrategyQueryData,
                         body=FwUpdateStrategyCreateData,
                         status_code=httplib.OK)
    def post(self, request_data):
        rpc_request = rpc.APIRequestCreateSwUpdateStrategy()
        rpc_request.sw_update_type = _get_sw_update_type_from_path(
            pecan.request.path)
        rpc_request.controller_apply_type = request_data.controller_apply_type
        rpc_request.storage_apply_type = request_data.storage_apply_type
        rpc_request.worker_apply_type = request_data.worker_apply_type
        if wsme_types.Unset != request_data.max_parallel_worker_hosts:
            if request_data.max_parallel_worker_hosts < MIN_PARALLEL_HOSTS \
                    or request_data.max_parallel_worker_hosts > \
                    MAX_PARALLEL_FW_UPDATE_HOSTS:
                return pecan.abort(
                    httplib.BAD_REQUEST,
                    "Invalid value for max-parallel-worker-hosts")
            rpc_request.max_parallel_worker_hosts = \
                request_data.max_parallel_worker_hosts
        rpc_request.default_instance_action = request_data.default_instance_action
        rpc_request.alarm_restrictions = request_data.alarm_restrictions
        vim_connection = pecan.request.vim.open_connection()
        vim_connection.send(rpc_request.serialize())
        msg = vim_connection.receive(timeout_in_secs=30)
        if msg is None:
            DLOG.error("No response received.")
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        response = rpc.RPCMessage.deserialize(msg)
        if rpc.RPC_MSG_TYPE.CREATE_SW_UPDATE_STRATEGY_RESPONSE != response.type:
            DLOG.error("Unexpected message type received, msg_type=%s."
                       % response.type)
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        if rpc.RPC_MSG_RESULT.SUCCESS == response.result:
            strategy = json.loads(response.strategy)
            query_data = SwUpdateStrategyQueryData()
            query_data.convert_strategy(strategy)
            return query_data
        elif rpc.RPC_MSG_RESULT.FAILED == response.result and response.error_string:
            return pecan.abort(httplib.BAD_REQUEST, response.error_string)
        elif rpc.RPC_MSG_RESULT.CONFLICT == response.result:
            return pecan.abort(httplib.CONFLICT, response.error_string)

        DLOG.error("Unexpected result received, result=%s." % response.result)
        return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

    def enforce_policy(self, method_name, auth_context_dict):
        """Check policy rules for each action of this controller."""
        if method_name == "delete":
            policy.check(fw_update_strategy_policy.POLICY_ROOT % "delete", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        elif method_name in ["get_all", "get_one"]:
            policy.check(fw_update_strategy_policy.POLICY_ROOT % "get", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        elif method_name == "post":
            policy.check(fw_update_strategy_policy.POLICY_ROOT % "add", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        else:
            policy.check('admin_in_system_projects', {}, auth_context_dict)


class KubeRootcaUpdateStrategyAPI(SwUpdateStrategyAPI):
    """
    Kubernetes Root CA Update Strategy Rest API
    """

    @wsme_pecan.wsexpose(SwUpdateStrategyQueryData,
                         body=KubeRootcaUpdateStrategyCreateData,
                         status_code=httplib.OK)
    def post(self, request_data):
        rpc_request = rpc.APIRequestCreateKubeRootcaUpdateStrategy()
        rpc_request.sw_update_type = _get_sw_update_type_from_path(
            pecan.request.path)
        if wsme_types.Unset != request_data.expiry_date:
            # Validate the expiry_date
            is_valid, reason = validate.validate_expiry_date(
                request_data.expiry_date)
            if not is_valid:
                return pecan.abort(httplib.BAD_REQUEST, reason)
            rpc_request.expiry_date = request_data.expiry_date
        if wsme_types.Unset != request_data.subject:
            # Validate the subject
            is_valid, reason = validate.validate_certificate_subject(
                request_data.subject)
            if not is_valid:
                return pecan.abort(httplib.BAD_REQUEST, reason)
            rpc_request.subject = request_data.subject
        if wsme_types.Unset != request_data.cert_file:
            # todo(abailey): Should investigate if cert_file can be validated
            rpc_request.cert_file = request_data.cert_file
        rpc_request.controller_apply_type = SW_UPDATE_APPLY_TYPE.SERIAL
        rpc_request.storage_apply_type = request_data.storage_apply_type
        rpc_request.worker_apply_type = request_data.worker_apply_type
        if wsme_types.Unset != request_data.max_parallel_worker_hosts:
            if request_data.max_parallel_worker_hosts < MIN_PARALLEL_HOSTS:
                return pecan.abort(
                    httplib.BAD_REQUEST,
                    "Invalid value for max-parallel-worker-hosts:(%s) < (%s)"
                    % (request_data.max_parallel_worker_hosts,
                       MIN_PARALLEL_HOSTS))
            if (request_data.max_parallel_worker_hosts >
                MAX_PARALLEL_KUBE_ROOTCA_UPDATE_HOSTS):
                return pecan.abort(
                    httplib.BAD_REQUEST,
                    "Invalid value for max-parallel-worker-hosts:(%s) > (%s)"
                    % (request_data.max_parallel_worker_hosts,
                       MAX_PARALLEL_KUBE_ROOTCA_UPDATE_HOSTS))
            rpc_request.max_parallel_worker_hosts = \
                request_data.max_parallel_worker_hosts
        rpc_request.default_instance_action = request_data.default_instance_action
        rpc_request.alarm_restrictions = request_data.alarm_restrictions
        vim_connection = pecan.request.vim.open_connection()
        vim_connection.send(rpc_request.serialize())
        msg = vim_connection.receive(timeout_in_secs=30)
        if msg is None:
            DLOG.error("No response received.")
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        response = rpc.RPCMessage.deserialize(msg)
        if (rpc.RPC_MSG_TYPE.CREATE_SW_UPDATE_STRATEGY_RESPONSE !=
            response.type):
            DLOG.error("Unexpected message type received, msg_type=%s."
                       % response.type)
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        if rpc.RPC_MSG_RESULT.SUCCESS == response.result:
            strategy = json.loads(response.strategy)
            query_data = SwUpdateStrategyQueryData()
            query_data.convert_strategy(strategy)
            return query_data
        elif rpc.RPC_MSG_RESULT.FAILED == response.result and response.error_string:
            return pecan.abort(httplib.BAD_REQUEST, response.error_string)
        elif rpc.RPC_MSG_RESULT.CONFLICT == response.result:
            return pecan.abort(httplib.CONFLICT, response.error_string)

        DLOG.error("Unexpected result received, result=%s." % response.result)
        return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

    def enforce_policy(self, method_name, auth_context_dict):
        """Check policy rules for each action of this controller."""
        if method_name == "delete":
            policy.check(kube_rootca_update_strategy_policy.POLICY_ROOT % "delete", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        elif method_name in ["get_all", "get_one"]:
            policy.check(kube_rootca_update_strategy_policy.POLICY_ROOT % "get", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        elif method_name == "post":
            policy.check(kube_rootca_update_strategy_policy.POLICY_ROOT % "add", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        else:
            policy.check('admin_in_system_projects', {}, auth_context_dict)


class KubeUpgradeStrategyAPI(SwUpdateStrategyAPI):
    """
    Kubernetes Upgrade Strategy Rest API
    """
    @wsme_pecan.wsexpose(SwUpdateStrategyQueryData,
                         body=KubeUpgradeStrategyCreateData,
                         status_code=httplib.OK)
    def post(self, request_data):
        rpc_request = rpc.APIRequestCreateKubeUpgradeStrategy()
        rpc_request.sw_update_type = _get_sw_update_type_from_path(
            pecan.request.path)
        request_data.to_version = request_data.to_version.lower()
        if request_data.to_version.startswith('v'):
            rpc_request.to_version = request_data.to_version
        else:
            rpc_request.to_version = "v{}".format(request_data.to_version)
        rpc_request.controller_apply_type = SW_UPDATE_APPLY_TYPE.SERIAL
        rpc_request.storage_apply_type = request_data.storage_apply_type
        rpc_request.worker_apply_type = request_data.worker_apply_type
        if wsme_types.Unset != request_data.max_parallel_worker_hosts:
            if request_data.max_parallel_worker_hosts < MIN_PARALLEL_HOSTS:
                return pecan.abort(
                    httplib.BAD_REQUEST,
                    "Invalid value for max-parallel-worker-hosts:(%s) < (%s)"
                    % (request_data.max_parallel_worker_hosts,
                       MIN_PARALLEL_HOSTS))
            if (request_data.max_parallel_worker_hosts >
                MAX_PARALLEL_KUBE_UPGRADE_HOSTS):
                return pecan.abort(
                    httplib.BAD_REQUEST,
                    "Invalid value for max-parallel-worker-hosts:(%s) > (%s)"
                    % (request_data.max_parallel_worker_hosts,
                       MAX_PARALLEL_KUBE_UPGRADE_HOSTS))
            rpc_request.max_parallel_worker_hosts = \
                request_data.max_parallel_worker_hosts
        rpc_request.default_instance_action = request_data.default_instance_action
        rpc_request.alarm_restrictions = request_data.alarm_restrictions
        vim_connection = pecan.request.vim.open_connection()
        vim_connection.send(rpc_request.serialize())
        msg = vim_connection.receive(timeout_in_secs=30)
        if msg is None:
            DLOG.error("No response received.")
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        response = rpc.RPCMessage.deserialize(msg)
        if (rpc.RPC_MSG_TYPE.CREATE_SW_UPDATE_STRATEGY_RESPONSE !=
            response.type):
            DLOG.error("Unexpected message type received, msg_type=%s."
                       % response.type)
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        if rpc.RPC_MSG_RESULT.SUCCESS == response.result:
            strategy = json.loads(response.strategy)
            query_data = SwUpdateStrategyQueryData()
            query_data.convert_strategy(strategy)
            return query_data
        elif rpc.RPC_MSG_RESULT.FAILED == response.result and response.error_string:
            return pecan.abort(httplib.BAD_REQUEST, response.error_string)
        elif rpc.RPC_MSG_RESULT.CONFLICT == response.result:
            return pecan.abort(httplib.CONFLICT, response.error_string)

        DLOG.error("Unexpected result received, result=%s." % response.result)
        return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

    def enforce_policy(self, method_name, auth_context_dict):
        """Check policy rules for each action of this controller."""
        if method_name == "delete":
            policy.check(kube_upgrade_strategy_policy.POLICY_ROOT % "delete", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        elif method_name in ["get_all", "get_one"]:
            policy.check(kube_upgrade_strategy_policy.POLICY_ROOT % "get", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        elif method_name == "post":
            policy.check(kube_upgrade_strategy_policy.POLICY_ROOT % "add", {},
                           auth_context_dict, exc=policy.PolicyForbidden)
        else:
            policy.check('admin_in_system_projects', {}, auth_context_dict)


class CurrentStrategyAPI(SwUpdateStrategyAPI):
    """
    Current Strategy Rest API
    """
    @wsme_pecan.wsexpose(SwUpdateStrategyQueryData, status_code=httplib.OK)
    def get_all(self):
        rpc_request = rpc.APIRequestGetSwUpdateStrategy()
        rpc_request.sw_update_type = _get_sw_update_type_from_path(
            pecan.request.path)
        vim_connection = pecan.request.vim.open_connection()
        vim_connection.send(rpc_request.serialize())
        msg = vim_connection.receive(timeout_in_secs=30)
        if msg is None:
            DLOG.error("No response received.")
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        response = rpc.RPCMessage.deserialize(msg)
        if rpc.RPC_MSG_TYPE.GET_SW_UPDATE_STRATEGY_RESPONSE != response.type:
            DLOG.error("Unexpected message type received, msg_type=%s."
                       % response.type)
            return pecan.abort(httplib.INTERNAL_SERVER_ERROR)

        if rpc.RPC_MSG_RESULT.SUCCESS == response.result:
            strategy = json.loads(response.strategy)
            query_data = SwUpdateStrategyQueryData()
            query_data.convert_current_strategy(strategy)
            return query_data

        elif rpc.RPC_MSG_RESULT.NOT_FOUND == response.result:
            DLOG.verbose("No strategy exists.")
            query_data = SwUpdateStrategyQueryData()
            return query_data

        DLOG.error("Unexpected result received, result=%s." % response.result)
        return pecan.abort(httplib.INTERNAL_SERVER_ERROR)
