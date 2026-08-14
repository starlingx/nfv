#
# Copyright (c) 2015-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_common import debug
from nfv_vim import directors
from nfv_vim import objects
from nfv_vim import rpc

DLOG = debug.debug_get_logger("nfv_vim.vim_sw_update_api_events")

_sw_update_strategy_create_operations = {}
_sw_update_strategy_apply_operations = {}
_sw_update_strategy_abort_operations = {}
_sw_update_strategy_delete_operations = {}


def _vim_sw_update_api_create_strategy_callback(success, reason, strategy):
    """Handle Sw-Update Create Strategy API callback."""

    global _sw_update_strategy_create_operations

    if strategy is not None:
        DLOG.info(
            "Create sw-update strategy callback, uuid=%s, reason=%s."
            % (strategy.uuid, reason)
        )

        connection = _sw_update_strategy_create_operations.get(strategy.uuid, None)
        if connection is not None:
            response = rpc.APIResponseCreateSwUpdateStrategy()
            if success:
                response.strategy = strategy.as_json()
            else:
                response.result = rpc.RPC_MSG_RESULT.FAILED

            connection.send(response.serialize())
            DLOG.verbose("Sent response=%s." % response)
            connection.close()
            del _sw_update_strategy_create_operations[strategy.uuid]


def vim_sw_update_api_create_strategy(connection, msg):
    """Handle Sw-Update Create Strategy API request."""

    global _sw_update_strategy_create_operations

    DLOG.info("Create sw-update strategy.")

    if "parallel" == msg.controller_apply_type:
        controller_apply_type = objects.SW_UPDATE_APPLY_TYPE.PARALLEL
    elif "serial" == msg.controller_apply_type:
        controller_apply_type = objects.SW_UPDATE_APPLY_TYPE.SERIAL
    else:
        controller_apply_type = objects.SW_UPDATE_APPLY_TYPE.IGNORE

    if "parallel" == msg.storage_apply_type:
        storage_apply_type = objects.SW_UPDATE_APPLY_TYPE.PARALLEL
    elif "serial" == msg.storage_apply_type:
        storage_apply_type = objects.SW_UPDATE_APPLY_TYPE.SERIAL
    else:
        storage_apply_type = objects.SW_UPDATE_APPLY_TYPE.IGNORE

    if "parallel" == msg.worker_apply_type:
        worker_apply_type = objects.SW_UPDATE_APPLY_TYPE.PARALLEL
    elif "serial" == msg.worker_apply_type:
        worker_apply_type = objects.SW_UPDATE_APPLY_TYPE.SERIAL
    else:
        worker_apply_type = objects.SW_UPDATE_APPLY_TYPE.IGNORE

    if msg.max_parallel_worker_hosts is not None:
        max_parallel_worker_hosts = msg.max_parallel_worker_hosts
    else:
        max_parallel_worker_hosts = 2

    if "migrate" == msg.default_instance_action:
        default_instance_action = objects.SW_UPDATE_INSTANCE_ACTION.MIGRATE
    else:
        default_instance_action = objects.SW_UPDATE_INSTANCE_ACTION.STOP_START

    if "strict" == msg.alarm_restrictions:
        alarm_restrictions = objects.SW_UPDATE_ALARM_RESTRICTION.STRICT
    elif "permissive" == msg.alarm_restrictions:
        alarm_restrictions = objects.SW_UPDATE_ALARM_RESTRICTION.PERMISSIVE
    else:
        alarm_restrictions = objects.SW_UPDATE_ALARM_RESTRICTION.RELAXED

    sw_mgmt_director = directors.get_sw_mgmt_director()
    if "sw-upgrade" == msg.sw_update_type:
        release = msg.release
        rollback = msg.rollback
        delete = msg.delete
        cleanup = msg.cleanup
        snapshot = msg.snapshot
        kube_upgrade = msg.kube_upgrade
        pre_upgrade_deploy = msg.pre_upgrade_deploy
        uuid, reason = sw_mgmt_director.create_sw_upgrade_strategy(
            controller_apply_type,
            storage_apply_type,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            release,
            rollback,
            delete,
            cleanup,
            snapshot,
            kube_upgrade,
            pre_upgrade_deploy,
            _vim_sw_update_api_create_strategy_callback,
        )
    elif "fw-update" == msg.sw_update_type:
        uuid, reason = sw_mgmt_director.create_fw_update_strategy(
            controller_apply_type,
            storage_apply_type,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            _vim_sw_update_api_create_strategy_callback,
        )
    elif "kube-rootca-update" == msg.sw_update_type:
        expiry_date = msg.expiry_date
        subject = msg.subject
        uuid, reason = sw_mgmt_director.create_kube_rootca_update_strategy(
            controller_apply_type,
            storage_apply_type,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            expiry_date,
            subject,
            _vim_sw_update_api_create_strategy_callback,
        )
    elif "kube-upgrade" == msg.sw_update_type:
        to_version = msg.to_version
        uuid, reason = sw_mgmt_director.create_kube_upgrade_strategy(
            controller_apply_type,
            storage_apply_type,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            to_version,
            _vim_sw_update_api_create_strategy_callback,
        )
    elif "system-config-update" == msg.sw_update_type:
        uuid, reason = sw_mgmt_director.create_system_config_update_strategy(
            controller_apply_type,
            storage_apply_type,
            worker_apply_type,
            max_parallel_worker_hosts,
            default_instance_action,
            alarm_restrictions,
            _vim_sw_update_api_create_strategy_callback,
        )
    else:
        DLOG.error("Invalid message name: %s" % msg.sw_update_type)
        response = rpc.APIResponseCreateSwUpdateStrategy()
        # todo(abailey): consider adding error_string to other error types
        response.result = rpc.RPC_MSG_RESULT.FAILED
        connection.send(response.serialize())
        DLOG.verbose("Sent response=%s." % response)
        connection.close()
        return

    if uuid is None:
        response = rpc.APIResponseCreateSwUpdateStrategy()
        # change this to a prefix...
        if reason is not None and reason.startswith("strategy already exists"):
            response.result = rpc.RPC_MSG_RESULT.CONFLICT
            response.error_string = reason
        elif reason is not None and reason:
            response.result = rpc.RPC_MSG_RESULT.FAILED
            response.error_string = reason
        else:
            response.result = rpc.RPC_MSG_RESULT.FAILED
        connection.send(response.serialize())
        DLOG.verbose("Sent response=%s." % response)
        connection.close()
        return

    _sw_update_strategy_create_operations[uuid] = connection


def _vim_sw_update_api_apply_strategy_callback(success, reason, strategy):
    """Handle Sw-Update Apply Strategy API callback."""

    global _sw_update_strategy_apply_operations

    if strategy is not None:
        DLOG.info(
            "Apply sw-update strategy callback, uuid=%s, reason=%s."
            % (strategy.uuid, reason)
        )

        connection = _sw_update_strategy_apply_operations.get(strategy.uuid, None)
        if connection is not None:
            response = rpc.APIResponseApplySwUpdateStrategy()
            if success:
                response.strategy = strategy.as_json()
            else:
                response.result = rpc.RPC_MSG_RESULT.FAILED

            connection.send(response.serialize())
            connection.close()
            DLOG.verbose("Sent response=%s." % response)
            del _sw_update_strategy_apply_operations[strategy.uuid]


def vim_sw_update_api_apply_strategy(connection, msg):
    """Handle Sw-Update Apply Strategy API request."""

    DLOG.info("Apply sw-update strategy: (%s) called." % msg.sw_update_type)
    if "sw-upgrade" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.SW_UPGRADE
    elif "fw-update" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.FW_UPDATE
    elif "kube-rootca-update" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.KUBE_ROOTCA_UPDATE
    elif "kube-upgrade" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.KUBE_UPGRADE
    elif "system-config-update" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.SYSTEM_CONFIG_UPDATE
    else:
        DLOG.error("Invalid message name: %s" % msg.sw_update_type)
        sw_update_type = "unknown"
    sw_mgmt_director = directors.get_sw_mgmt_director()
    strategy = sw_mgmt_director.get_sw_update_strategy(sw_update_type)
    if strategy is None:
        DLOG.info("No sw-update strategy to apply.")
        response = rpc.APIResponseApplySwUpdateStrategy()
        response.result = rpc.RPC_MSG_RESULT.NOT_FOUND
        connection.send(response.serialize())
        DLOG.verbose("Sent response=%s." % response)
        connection.close()
        return

    _sw_update_strategy_apply_operations[strategy.uuid] = connection

    sw_mgmt_director.apply_sw_update_strategy(
        strategy.uuid, msg.stage_id, _vim_sw_update_api_apply_strategy_callback
    )


def _vim_sw_update_api_abort_strategy_callback(success, reason, strategy):
    """Handle Sw-Update Abort Strategy API callback."""

    global _sw_update_strategy_abort_operations

    if strategy is not None:
        DLOG.info(
            "Abort sw-update strategy callback, uuid=%s, reason=%s."
            % (strategy.uuid, reason)
        )

        connection = _sw_update_strategy_abort_operations.get(strategy.uuid, None)
        if connection is not None:
            response = rpc.APIResponseAbortSwUpdateStrategy()
            if success:
                response.strategy = strategy.as_json()
            else:
                response.result = rpc.RPC_MSG_RESULT.FAILED

            connection.send(response.serialize())
            connection.close()
            DLOG.verbose("Sent response=%s." % response)
            del _sw_update_strategy_abort_operations[strategy.uuid]


def _send_response(connection, error_message):
    DLOG.warn(error_message)

    response = rpc.APIResponseAbortSwUpdateStrategy()
    response.result = rpc.RPC_MSG_RESULT.FAILED
    response.error_string = error_message
    connection.send(response.serialize())

    DLOG.verbose("Sent response=%s." % response)
    connection.close()


def _is_abortable(strategy):
    """Validates if the strategy and its current stage and step, accepts abort.

    :param strategy: The software update strategy object to validate.
    :return: A tuple containing a boolean indicating if the strategy can be aborted
    and an error message string if it cannot be aborted.
    :rtype: tuple(bool, str or None)
    """

    if not strategy.is_applying():
        return False, (
            "Abort rejected: abort can only be executed when the strategy is applying"
        )
    elif not strategy.is_abortable():
        return False, (
            f"Abort rejected: abort is not supported for {strategy.name} in the "
            "current configuration."
        )

    current_stage_index = strategy.apply_phase.current_stage

    # If the index is equal to or higher than the amount of stages, the strategy
    # will have just completed the last stage. Nevertheless, we maintain current
    # behavior by allowing the abort to be executed.
    if current_stage_index >= len(strategy.apply_phase.stages):
        DLOG.warn("The strategy is complete, skipping abort check.")
        return True

    current_stage = strategy.apply_phase.stages[current_stage_index]
    if not current_stage.is_abortable():
        return False, (
            f"Abort rejected: cannot abort during {current_stage.name} stage."
        )

    current_step_index = current_stage.current_step

    # If the index is equal to or higher than the amount of steps, the strategy
    # will have just completed the current stage. Nevertheless, we maintain current
    # behavior by allowing the abort to be executed.
    if current_step_index >= len(current_stage.steps):
        DLOG.warn("The current stage is complete, skipping abort check.")
        return True, None

    current_step = current_stage.steps[current_step_index]
    if not current_step.is_abortable():
        return False, (f"Abort rejected: cannot abort during {current_step.name} step.")
    return True, None


def vim_sw_update_api_abort_strategy(connection, msg):
    """Handle Sw-Update Abort Strategy API request."""

    DLOG.info("Abort sw-update strategy.")
    if "sw-upgrade" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.SW_UPGRADE
    elif "fw-update" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.FW_UPDATE
    elif "kube-rootca-update" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.KUBE_ROOTCA_UPDATE
    elif "kube-upgrade" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.KUBE_UPGRADE
    elif "system-config-update" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.SYSTEM_CONFIG_UPDATE
    else:
        DLOG.error("Invalid message name: %s" % msg.sw_update_type)
        sw_update_type = "unknown"
    sw_mgmt_director = directors.get_sw_mgmt_director()
    strategy = sw_mgmt_director.get_sw_update_strategy(sw_update_type)
    if strategy is None:
        DLOG.info("No sw-update strategy to abort.")
        response = rpc.APIResponseAbortSwUpdateStrategy()
        response.result = rpc.RPC_MSG_RESULT.NOT_FOUND
        connection.send(response.serialize())
        DLOG.verbose("Sent response=%s." % response)
        connection.close()
        return

    is_abortable, abort_rejected_msg = _is_abortable(strategy)
    if not is_abortable:
        _send_response(connection, abort_rejected_msg)
        return

    _sw_update_strategy_abort_operations[strategy.uuid] = connection

    sw_mgmt_director.abort_sw_update_strategy(
        strategy.uuid, msg.stage_id, _vim_sw_update_api_abort_strategy_callback
    )


def _vim_sw_update_api_delete_strategy_callback(success, reason, strategy_uuid):
    """Handle Sw-Update Delete Strategy API callback."""

    global _sw_update_strategy_delete_operations

    DLOG.info(
        "Delete sw-update strategy callback, uuid=%s, reason=%s."
        % (strategy_uuid, reason)
    )

    connection = _sw_update_strategy_delete_operations.get(strategy_uuid, None)
    if connection is not None:
        response = rpc.APIResponseDeleteSwUpdateStrategy()
        if not success:
            response.result = rpc.RPC_MSG_RESULT.FAILED

        connection.send(response.serialize())
        connection.close()
        DLOG.verbose("Sent response=%s." % response)
        del _sw_update_strategy_delete_operations[strategy_uuid]


def vim_sw_update_api_delete_strategy(connection, msg):
    """Handle Sw-Update Delete Strategy API request."""

    DLOG.info("Delete sw-update strategy, force=%s.", msg.force)
    if "sw-upgrade" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.SW_UPGRADE
    elif "fw-update" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.FW_UPDATE
    elif "kube-rootca-update" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.KUBE_ROOTCA_UPDATE
    elif "kube-upgrade" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.KUBE_UPGRADE
    elif "system-config-update" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.SYSTEM_CONFIG_UPDATE
    else:
        DLOG.error("Invalid message name: %s" % msg.sw_update_type)
        sw_update_type = "unknown"
    sw_mgmt_director = directors.get_sw_mgmt_director()
    strategy = sw_mgmt_director.get_sw_update_strategy(sw_update_type)
    if strategy is None:
        DLOG.info("No sw-update strategy to delete.")
        response = rpc.APIResponseDeleteSwUpdateStrategy()
        response.result = rpc.RPC_MSG_RESULT.NOT_FOUND
        connection.send(response.serialize())
        DLOG.verbose("Sent response=%s." % response)
        connection.close()
        return

    _sw_update_strategy_delete_operations[strategy.uuid] = connection

    sw_mgmt_director.delete_sw_update_strategy(
        strategy.uuid, msg.force, _vim_sw_update_api_delete_strategy_callback
    )


def vim_sw_update_api_get_strategy(connection, msg):
    """Handle Sw-Update Get Strategy API request."""

    DLOG.verbose("Get sw-update strategy.")
    if "sw-upgrade" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.SW_UPGRADE
    elif "fw-update" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.FW_UPDATE
    elif "kube-rootca-update" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.KUBE_ROOTCA_UPDATE
    elif "kube-upgrade" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.KUBE_UPGRADE
    elif "system-config-update" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.SYSTEM_CONFIG_UPDATE
    elif "current-strategy" == msg.sw_update_type:
        sw_update_type = objects.SW_UPDATE_TYPE.CURRENT_STRATEGY
    else:
        DLOG.error("Invalid message name: %s" % msg.sw_update_type)
        sw_update_type = "unknown"
    response = rpc.APIResponseGetSwUpdateStrategy()
    sw_mgmt_director = directors.get_sw_mgmt_director()
    strategy = sw_mgmt_director.get_sw_update_strategy(sw_update_type)
    if strategy is None:
        DLOG.verbose("No sw-update strategy exists.")
        response.result = rpc.RPC_MSG_RESULT.NOT_FOUND

    elif msg.uuid is None:
        response.strategy = strategy.as_json()

    elif msg.uuid != strategy.uuid:
        DLOG.info("No sw-update strategy exists matching strategy uuid %s." % msg.uuid)
        response.result = rpc.RPC_MSG_RESULT.NOT_FOUND

    else:
        response.strategy = strategy.as_json()

    connection.send(response.serialize())
    DLOG.verbose("Sent response=%s." % response)
    connection.close()


def vim_sw_update_api_initialize():
    """Initialize VIM Software Update API Handling."""


def vim_sw_update_api_finalize():
    """Finalize VIM Software Update API Handling."""
