#
# Copyright (c) 2015-2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_common import debug

from nfv_vim.rpc._rpc_defs import RPC_MSG_RESULT
from nfv_vim.rpc._rpc_defs import RPC_MSG_TYPE
from nfv_vim.rpc._rpc_defs import RPC_MSG_VERSION
from nfv_vim.rpc._rpc_message import RPCMessage

DLOG = debug.debug_get_logger('nfv_vim.rpc.sw_update')


class APIRequestCreateSwUpdateStrategy(RPCMessage):
    """
    RPC API Request Message - Create Software Update Strategy
    """
    sw_update_type = None
    controller_apply_type = None
    storage_apply_type = None
    swift_apply_type = None
    worker_apply_type = None
    max_parallel_worker_hosts = None
    default_instance_action = None
    alarm_restrictions = None

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.CREATE_SW_UPDATE_STRATEGY_REQUEST,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIRequestCreateSwUpdateStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        msg['sw_update_type'] = self.sw_update_type
        msg['controller_apply_type'] = self.controller_apply_type
        msg['storage_apply_type'] = self.storage_apply_type
        msg['swift_apply_type'] = self.swift_apply_type
        msg['worker_apply_type'] = self.worker_apply_type
        msg['max_parallel_worker_hosts'] = self.max_parallel_worker_hosts
        msg['default_instance_action'] = self.default_instance_action
        msg['alarm_restrictions'] = self.alarm_restrictions

    def deserialize_payload(self, msg):
        self.sw_update_type = msg.get('sw_update_type', None)
        self.controller_apply_type = msg.get('controller_apply_type', None)
        self.storage_apply_type = msg.get('storage_apply_type', None)
        self.swift_apply_type = msg.get('swift_apply_type', None)
        self.worker_apply_type = msg.get('worker_apply_type', None)
        self.max_parallel_worker_hosts = msg.get(
            'max_parallel_worker_hosts', None)
        self.default_instance_action = msg.get('default_instance_action', None)
        self.alarm_restrictions = msg.get('alarm_restrictions', None)

    def __str__(self):
        return "create-sw-update-strategy request: %s" % self.deserialize_payload


class APIRequestCreateSwUpgradeStrategy(APIRequestCreateSwUpdateStrategy):
    """
    RPC API Request Message - Create Software Deploy Strategy
    """
    release = None
    rollback = None
    delete = None
    snapshot = None

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.CREATE_SW_UPGRADE_STRATEGY_REQUEST,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIRequestCreateSwUpgradeStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        super(APIRequestCreateSwUpgradeStrategy, self).serialize_payload(msg)
        msg['release'] = self.release
        msg['rollback'] = self.rollback
        msg['delete'] = self.delete
        msg['snapshot'] = self.snapshot

    def deserialize_payload(self, msg):
        super(APIRequestCreateSwUpgradeStrategy, self).deserialize_payload(msg)
        self.release = msg.get('release', None)
        self.rollback = msg.get('rollback', None)
        self.delete = msg.get('delete', None)
        self.snapshot = msg.get('snapshot', None)

    def __str__(self):
        return "create-sw-deploy-strategy request: %s" % self.deserialize_payload


class APIRequestCreateKubeRootcaUpdateStrategy(APIRequestCreateSwUpdateStrategy):
    """
    RPC API Request Message - Create Kube Root CA Update Strategy
    """
    expiry_date = None
    subject = None

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.CREATE_KUBE_ROOTCA_UPDATE_STRATEGY_REQUEST,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIRequestCreateKubeRootcaUpdateStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        super(APIRequestCreateKubeRootcaUpdateStrategy, self).serialize_payload(msg)
        msg['expiry_date'] = self.expiry_date
        msg['subject'] = self.subject

    def deserialize_payload(self, msg):
        super(APIRequestCreateKubeRootcaUpdateStrategy, self).deserialize_payload(msg)
        self.expiry_date = msg.get('expiry_date', None)
        self.subject = msg.get('subject', None)

    def __str__(self):
        return "create-kube-rootca-update-strategy request: %s" % self.deserialize_payload


class APIRequestCreateKubeUpgradeStrategy(APIRequestCreateSwUpdateStrategy):
    """
    RPC API Request Message - Create Kube Upgrade Strategy
    """
    to_version = None

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.CREATE_KUBE_UPGRADE_STRATEGY_REQUEST,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIRequestCreateKubeUpgradeStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        super(APIRequestCreateKubeUpgradeStrategy, self).serialize_payload(msg)
        msg['to_version'] = self.to_version

    def deserialize_payload(self, msg):
        super(APIRequestCreateKubeUpgradeStrategy, self).deserialize_payload(msg)
        self.to_version = msg.get('to_version', None)

    def __str__(self):
        return "create-kube-upgrade-strategy request: %s" % self.deserialize_payload


class APIRequestCreateSystemConfigUpdateStrategy(APIRequestCreateSwUpdateStrategy):
    """
    RPC API Request Message - Create System Config Update Strategy
    """
    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.CREATE_SYSTEM_CONFIG_UPDATE_STRATEGY_REQUEST,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIRequestCreateSystemConfigUpdateStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def __str__(self):
        return "create-system-config-update-strategy request: %s" % \
            self.deserialize_payload


class APIResponseCreateSwUpdateStrategy(RPCMessage):
    """
    RPC API Response Message - Create Software Update Strategy
    """
    strategy = None
    error_string = None

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.CREATE_SW_UPDATE_STRATEGY_RESPONSE,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIResponseCreateSwUpdateStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        msg['strategy'] = self.strategy
        msg['error_string'] = self.error_string

    def deserialize_payload(self, msg):
        self.strategy = msg.get('strategy', None)
        self.error_string = msg.get('error_string', None)

    def __str__(self):
        return "create-sw-update-strategy response: %s" % self.strategy


class APIRequestApplySwUpdateStrategy(RPCMessage):
    """
    RPC API Request Message - Apply Software Update Strategy
    """
    sw_update_type = None
    stage_id = None

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.APPLY_SW_UPDATE_STRATEGY_REQUEST,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIRequestApplySwUpdateStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        msg['sw_update_type'] = self.sw_update_type
        if self.stage_id is not None:
            msg['stage_id'] = str(self.stage_id)

    def deserialize_payload(self, msg):
        self.sw_update_type = msg.get('sw_update_type', None)
        stage_id = msg.get('stage_id', None)
        if stage_id is not None:
            self.stage_id = int(stage_id)

    def __str__(self):
        return "apply-sw-update-strategy request"


class APIResponseApplySwUpdateStrategy(RPCMessage):
    """
    RPC API Response Message - Apply Software Update Strategy
    """
    strategy = None

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.APPLY_SW_UPDATE_STRATEGY_RESPONSE,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIResponseApplySwUpdateStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        msg['strategy'] = self.strategy

    def deserialize_payload(self, msg):
        self.strategy = msg.get('strategy', None)

    def __str__(self):
        return "apply-sw-update-strategy response"


class APIRequestAbortSwUpdateStrategy(RPCMessage):
    """
    RPC API Request Message - Abort Software Update Strategy
    """
    sw_update_type = None
    stage_id = None

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.ABORT_SW_UPDATE_STRATEGY_REQUEST,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIRequestAbortSwUpdateStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        msg['sw_update_type'] = self.sw_update_type
        if self.stage_id is not None:
            msg['stage_id'] = str(self.stage_id)

    def deserialize_payload(self, msg):
        self.sw_update_type = msg.get('sw_update_type', None)
        stage_id = msg.get('stage_id', None)
        if stage_id is not None:
            self.stage_id = int(stage_id)

    def __str__(self):
        return "abort-sw-update-strategy request"


class APIResponseAbortSwUpdateStrategy(RPCMessage):
    """
    RPC API Response Message - Abort Software Update Strategy
    """
    strategy = None

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.ABORT_SW_UPDATE_STRATEGY_RESPONSE,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIResponseAbortSwUpdateStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        msg['strategy'] = self.strategy

    def deserialize_payload(self, msg):
        self.strategy = msg.get('strategy', None)

    def __str__(self):
        return "abort-sw-update-strategy response"


class APIRequestDeleteSwUpdateStrategy(RPCMessage):
    """
    RPC API Request Message - Delete Software Update Strategy
    """
    sw_update_type = None
    force = False

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.DELETE_SW_UPDATE_STRATEGY_REQUEST,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIRequestDeleteSwUpdateStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        msg['sw_update_type'] = self.sw_update_type
        msg['force'] = str(self.force)

    def deserialize_payload(self, msg):
        self.sw_update_type = msg.get('sw_update_type', None)
        force = msg.get('force', None)
        if force is None:
            self.force = False
        else:
            self.force = force in ['True', 'true']

    def __str__(self):
        return "delete-sw-update-strategy request"


class APIResponseDeleteSwUpdateStrategy(RPCMessage):
    """
    RPC API Response Message - Delete Software Update Strategy
    """
    strategy = None

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.DELETE_SW_UPDATE_STRATEGY_RESPONSE,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIResponseDeleteSwUpdateStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        msg['strategy'] = self.strategy

    def deserialize_payload(self, msg):
        self.strategy = msg.get('strategy', None)

    def __str__(self):
        return "delete-sw-update-strategy response"


class APIRequestGetSwUpdateStrategy(RPCMessage):
    """
    RPC API Request Message - Get Software Update Strategy
    """
    sw_update_type = None
    uuid = None

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.GET_SW_UPDATE_STRATEGY_REQUEST,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIRequestGetSwUpdateStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        msg['sw_update_type'] = self.sw_update_type
        msg['uuid'] = self.uuid

    def deserialize_payload(self, msg):
        self.sw_update_type = msg.get('sw_update_type', None)
        self.uuid = msg.get('uuid', None)

    def __str__(self):
        return "get-sw-update-strategy request"


class APIResponseGetSwUpdateStrategy(RPCMessage):
    """
    RPC API Response Message - Get Software Update Strategy
    """
    strategy = None

    def __init__(self, msg_version=RPC_MSG_VERSION.VERSION_1_0,
                 msg_type=RPC_MSG_TYPE.GET_SW_UPDATE_STRATEGY_RESPONSE,
                 msg_result=RPC_MSG_RESULT.SUCCESS):
        super(APIResponseGetSwUpdateStrategy, self).__init__(
            msg_version, msg_type, msg_result)

    def serialize_payload(self, msg):
        msg['strategy'] = self.strategy

    def deserialize_payload(self, msg):
        self.strategy = msg.get('strategy', None)

    def __str__(self):
        return "get-sw-update-strategy response: %s" % self.strategy
