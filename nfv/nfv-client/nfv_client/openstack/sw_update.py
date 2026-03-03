#
# Copyright (c) 2016-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import json

from nfv_client.auth_types import AUTH_TYPES
from nfv_client.openstack import rest_api
from nfv_client import sw_update


class StrategyStep:
    step_id = None
    step_name = None
    entity_type = None
    entity_names = []
    entity_uuids = []
    timeout = None
    start_date_time = None
    end_date_time = None
    result = None
    reason = None

    def __repr__(self):
        return "%s" % str(self.__dict__)  # noqa: H501


class StrategyStage:
    stage_id = None
    stage_name = None
    steps = []
    total_steps = None
    current_step = None
    timeout = None
    start_date_time = None
    end_date_time = None
    inprogress = None
    result = None
    reason = None

    def __repr__(self):
        return "%s" % str(self.__dict__)  # noqa: H501


class StrategyPhase:
    phase_name = None
    stages = []
    total_stages = None
    current_stage = None
    stop_at_stage = None
    timeout = None
    start_date_time = None
    end_date_time = None
    inprogress = None
    completion_percentage = None
    result = None
    reason = None
    response = None

    def __repr__(self):
        return "%s" % str(self.__dict__)  # noqa: H501


class Strategy:
    uuid = None
    name = None
    release = None
    release_id = None
    metapackages = None
    kube_version = None
    controller_apply_type = None
    storage_apply_type = None
    swift_apply_type = None
    worker_apply_type = None
    max_parallel_worker_hosts = None
    default_instance_action = None
    alarm_restrictions = None
    current_phase = None
    current_phase_completion_percentage = None
    state = None
    build_phase = None
    apply_phase = None
    abort_phase = None

    def __repr__(self):
        return "%s" % str(self.__dict__)  # noqa: H501


def _get_strategy_step_object_from_response(response):
    """Convert the Rest-API response into a strategy step object."""

    step = StrategyStep()
    step.step_id = response["step-id"]
    step.step_name = response["step-name"]
    step.entity_type = response["entity-type"]
    step.entity_names = response["entity-names"]
    step.entity_uuids = response["entity-uuids"]
    step.timeout = response["timeout"]
    step.start_date_time = response["start-date-time"]
    step.end_date_time = response["end-date-time"]
    step.result = response["result"]
    step.reason = response["reason"]
    return step


def _get_strategy_stage_object_from_response(response):
    """Convert the Rest-API response into a strategy stage object."""

    stage = StrategyStage()
    stage.stage_id = response["stage-id"]
    stage.stage_name = response["stage-name"]
    stage.total_steps = response["total-steps"]
    stage.current_step = response["current-step"]
    stage.timeout = response["timeout"]
    stage.start_date_time = response["start-date-time"]
    stage.end_date_time = response["end-date-time"]
    stage.inprogress = response["inprogress"]
    stage.result = response["result"]
    stage.reason = response["reason"]

    stage.steps = []
    for step in response["steps"]:
        stage.steps.append(_get_strategy_step_object_from_response(step))

    return stage


def _get_strategy_phase_object_from_response(response):
    """Convert the Rest-API response into a strategy phase object."""

    phase = StrategyPhase()
    phase.phase_name = response["phase-name"]
    phase.total_stages = response["total-stages"]
    phase.current_stage = response["current-stage"]
    phase.stop_at_stage = response["stop-at-stage"]
    phase.timeout = response["timeout"]
    phase.start_date_time = response["start-date-time"]
    phase.end_date_time = response["end-date-time"]
    phase.inprogress = response["inprogress"]
    phase.completion_percentage = response["completion-percentage"]
    phase.result = response["result"]
    phase.reason = response["reason"]
    phase.response = response.get("response")

    phase.stages = []
    for stage in response["stages"]:
        phase.stages.append(_get_strategy_stage_object_from_response(stage))

    return phase


def _get_strategy_object_from_response(response):
    """Convert the Rest-API response into a strategy object."""

    strategy_data = response.get("strategy", None)
    if strategy_data is None:
        return None
    strategy = Strategy()
    strategy.uuid = strategy_data["uuid"]
    strategy.name = strategy_data["name"]
    if strategy.name == sw_update.STRATEGY_NAME_SW_UPGRADE:
        strategy.kube_version = strategy_data.get("kube-version")

        # When the release information has not been fully retrieved yet,
        # only display the release parameter the user sent. Otherwise,
        # display release-id and metapackage data.
        if strategy_data.get("release-id") and strategy_data.get("metapackages"):
            strategy.release_id = strategy_data["release-id"]
            strategy.metapackages = strategy_data["metapackages"]
        else:
            strategy.release = strategy_data["release"]

    strategy.controller_apply_type = strategy_data["controller-apply-type"]
    strategy.storage_apply_type = strategy_data["storage-apply-type"]
    strategy.swift_apply_type = strategy_data["swift-apply-type"]
    strategy.worker_apply_type = strategy_data["worker-apply-type"]
    strategy.max_parallel_worker_hosts = strategy_data["max-parallel-worker-hosts"]
    strategy.default_instance_action = strategy_data["default-instance-action"]
    strategy.alarm_restrictions = strategy_data["alarm-restrictions"]
    strategy.current_phase = strategy_data["current-phase"]
    strategy.current_phase_completion_percentage = strategy_data[
        "current-phase-completion-percentage"
    ]
    strategy.state = strategy_data["state"]

    strategy.build_phase = _get_strategy_phase_object_from_response(
        strategy_data["build-phase"]
    )
    strategy.apply_phase = _get_strategy_phase_object_from_response(
        strategy_data["apply-phase"]
    )
    strategy.abort_phase = _get_strategy_phase_object_from_response(
        strategy_data["abort-phase"]
    )

    return strategy


def _get_current_strategy_from_response(response):
    """Returns Strategy Type and State."""

    current_strategy = {}
    strategy_data = response.get("strategy", None)
    if strategy_data is None:
        return None
    strategy = Strategy()
    strategy.name = strategy_data["name"]
    strategy.state = strategy_data["state"]
    if strategy.name is not None:
        current_strategy[strategy.name] = strategy.state
    return current_strategy


def get_strategies(
    token_id,
    url,
    strategy_name,
    username=None,
    user_domain_name=None,
    tenant=None,
    auth_type=AUTH_TYPES.KEYSTONE,
):
    """Software Update - Get Strategies."""

    api_cmd = url + "/api/orchestration/%s/strategy" % strategy_name

    api_cmd_headers = {}
    if username:
        api_cmd_headers["X-User"] = username
    if tenant:
        api_cmd_headers["X-Tenant"] = tenant
    if user_domain_name:
        api_cmd_headers["X-User-Domain-Name"] = user_domain_name

    response = rest_api.request(
        token_id, "GET", api_cmd, api_cmd_headers, auth_type=auth_type
    )
    if not response:
        return None

    return _get_strategy_object_from_response(response)


def get_strategy(
    token_id,
    url,
    strategy_name,
    strategy_uuid,
    username=None,
    user_domain_name=None,
    tenant=None,
    auth_type=AUTH_TYPES.KEYSTONE,
):
    """Software Update - Get Strategy."""

    api_cmd = url + "/api/orchestration/%s/strategy/%s" % (strategy_name, strategy_uuid)

    api_cmd_headers = {}
    if username:
        api_cmd_headers["X-User"] = username
    if tenant:
        api_cmd_headers["X-Tenant"] = tenant
    if user_domain_name:
        api_cmd_headers["X-User-Domain-Name"] = user_domain_name

    response = rest_api.request(
        token_id, "GET", api_cmd, api_cmd_headers, auth_type=auth_type
    )
    if not response:
        return None

    return _get_strategy_object_from_response(response)


def create_strategy(
    token_id,
    url,
    strategy_name,
    controller_apply_type,
    storage_apply_type,
    swift_apply_type,
    worker_apply_type,
    max_parallel_worker_hosts,
    default_instance_action,
    alarm_restrictions,
    username=None,
    user_domain_name=None,
    tenant=None,
    auth_type=AUTH_TYPES.KEYSTONE,
    **kwargs,
):
    """Software Update - Create Strategy."""

    api_cmd = url + "/api/orchestration/%s/strategy" % strategy_name

    api_cmd_headers = {}
    api_cmd_headers["Content-Type"] = "application/json"
    if username:
        api_cmd_headers["X-User"] = username
    if tenant:
        api_cmd_headers["X-Tenant"] = tenant
    if user_domain_name:
        api_cmd_headers["X-User-Domain-Name"] = user_domain_name

    api_cmd_payload = {}
    if sw_update.STRATEGY_NAME_FW_UPDATE == strategy_name:
        api_cmd_payload["default-instance-action"] = default_instance_action
    elif sw_update.STRATEGY_NAME_KUBE_ROOTCA_UPDATE == strategy_name:
        # Note that the payload contains '-' and not '_'
        if "expiry_date" in kwargs and kwargs["expiry_date"]:
            api_cmd_payload["expiry-date"] = kwargs["expiry_date"]
        if "subject" in kwargs and kwargs["subject"]:
            api_cmd_payload["subject"] = kwargs["subject"]
        api_cmd_payload["default-instance-action"] = default_instance_action
    elif sw_update.STRATEGY_NAME_KUBE_UPGRADE == strategy_name:
        # required: 'to_version' passed to strategy as 'to-version'
        api_cmd_payload["to-version"] = kwargs["to_version"]
        api_cmd_payload["default-instance-action"] = default_instance_action
    elif sw_update.STRATEGY_NAME_SYSTEM_CONFIG_UPDATE == strategy_name:
        api_cmd_payload["default-instance-action"] = default_instance_action
    elif sw_update.STRATEGY_NAME_SW_UPGRADE == strategy_name:
        api_cmd_payload["default-instance-action"] = default_instance_action
        api_cmd_payload["release"] = kwargs["release"]
        api_cmd_payload["rollback"] = kwargs.get("rollback")
        api_cmd_payload["delete"] = kwargs.get("delete")

        # Append following parameters only if they were provided.
        # This is to support API call backwards compatibility, where
        # the parameters are not provided.
        if kwargs.get("snapshot"):
            api_cmd_payload["snapshot"] = kwargs.get("snapshot")
        if kwargs.get("pre_upgrade_deploy"):
            api_cmd_payload["pre-upgrade-deploy"] = kwargs.get("pre_upgrade_deploy")
        if kwargs.get("kube_upgrade"):
            api_cmd_payload["kube-upgrade"] = kwargs.get("kube_upgrade")
        if kwargs.get("cleanup"):
            api_cmd_payload["cleanup"] = kwargs.get("cleanup")

    api_cmd_payload["controller-apply-type"] = controller_apply_type
    api_cmd_payload["storage-apply-type"] = storage_apply_type
    api_cmd_payload["worker-apply-type"] = worker_apply_type
    if max_parallel_worker_hosts is not None:
        api_cmd_payload["max-parallel-worker-hosts"] = max_parallel_worker_hosts
    api_cmd_payload["alarm-restrictions"] = alarm_restrictions
    response = rest_api.request(
        token_id,
        "POST",
        api_cmd,
        api_cmd_headers,
        json.dumps(api_cmd_payload),
        auth_type=auth_type,
    )
    if not response:
        return None

    return _get_strategy_object_from_response(response)


def delete_strategy(
    token_id,
    url,
    strategy_name,
    force=False,
    username=None,
    user_domain_name=None,
    tenant=None,
    auth_type=AUTH_TYPES.KEYSTONE,
):
    """Software Update - Delete Strategy."""

    api_cmd = url + "/api/orchestration/%s/strategy" % strategy_name

    api_cmd_headers = {}
    api_cmd_headers["Content-Type"] = "application/json"
    if username:
        api_cmd_headers["X-User"] = username
    if tenant:
        api_cmd_headers["X-Tenant"] = tenant
    if user_domain_name:
        api_cmd_headers["X-User-Domain-Name"] = user_domain_name

    api_cmd_payload = {}
    api_cmd_payload["force"] = force

    response = rest_api.request(
        token_id,
        "DELETE",
        api_cmd,
        api_cmd_headers,
        json.dumps(api_cmd_payload),
        auth_type=auth_type,
    )
    # We expect an empty response body for this request (204 NO CONTENT). If
    # there is no response body it is a 404 NOT FOUND which means there was
    # no strategy to delete.
    if response is None:
        return False

    return True


def apply_strategy(
    token_id,
    url,
    strategy_name,
    stage_id=None,
    username=None,
    user_domain_name=None,
    tenant=None,
    auth_type=AUTH_TYPES.KEYSTONE,
):
    """Software Update - Apply Strategy."""

    api_cmd = url + ("/api/orchestration/%s/strategy/actions" % strategy_name)

    api_cmd_headers = {}
    api_cmd_headers["Content-Type"] = "application/json"
    if username:
        api_cmd_headers["X-User"] = username
    if tenant:
        api_cmd_headers["X-Tenant"] = tenant
    if user_domain_name:
        api_cmd_headers["X-User-Domain-Name"] = user_domain_name

    api_cmd_payload = {}
    if stage_id is None:
        api_cmd_payload["action"] = "apply-all"
    else:
        api_cmd_payload["action"] = "apply-stage"
        api_cmd_payload["stage-id"] = stage_id

    response = rest_api.request(
        token_id,
        "POST",
        api_cmd,
        api_cmd_headers,
        json.dumps(api_cmd_payload),
        auth_type=auth_type,
    )
    if not response:
        return None

    return _get_strategy_object_from_response(response)


def abort_strategy(
    token_id,
    url,
    strategy_name,
    stage_id,
    username=None,
    user_domain_name=None,
    tenant=None,
    auth_type=AUTH_TYPES.KEYSTONE,
):
    """Software Update - Abort Strategy."""

    api_cmd = url + ("/api/orchestration/%s/strategy/actions" % strategy_name)

    api_cmd_headers = {}
    api_cmd_headers["Content-Type"] = "application/json"
    if username:
        api_cmd_headers["X-User"] = username
    if tenant:
        api_cmd_headers["X-Tenant"] = tenant
    if user_domain_name:
        api_cmd_headers["X-User-Domain-Name"] = user_domain_name

    api_cmd_payload = {}
    api_cmd_payload["action"] = "abort-stage"
    api_cmd_payload["stage-id"] = stage_id

    response = rest_api.request(
        token_id,
        "POST",
        api_cmd,
        api_cmd_headers,
        json.dumps(api_cmd_payload),
        auth_type=auth_type,
    )
    if not response:
        return None

    return _get_strategy_object_from_response(response)


def get_current_strategy(
    token_id,
    url,
    username=None,
    user_domain_name=None,
    tenant=None,
    auth_type=AUTH_TYPES.KEYSTONE,
):
    """Get The Current Active Strategy Type And State."""

    api_cmd = url + "/api/orchestration/current-strategy/strategy"

    api_cmd_headers = {}
    if username:
        api_cmd_headers["X-User"] = username
    if tenant:
        api_cmd_headers["X-Tenant"] = tenant
    if user_domain_name:
        api_cmd_headers["X-User-Domain-Name"] = user_domain_name

    response = rest_api.request(
        token_id, "GET", api_cmd, api_cmd_headers, auth_type=auth_type
    )
    if response["strategy"] is not None:
        return _get_current_strategy_from_response(response)

    return None
