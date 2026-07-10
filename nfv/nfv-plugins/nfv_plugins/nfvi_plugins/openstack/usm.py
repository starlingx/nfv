#
# Copyright (c) 2024-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import json
import os

from nfv_common import debug
from nfv_plugins.nfvi_plugins.openstack.objects import PLATFORM_SERVICE
from nfv_plugins.nfvi_plugins.openstack.rest_api import rest_api_request
from nfv_vim import nfvi

REST_API_REQUEST_TIMEOUT = 60
REST_API_DEPLOY_START_TIMEOUT = 120
REST_API_DEPLOY_HOST_TIMEOUT = 240
REST_API_DEPLOY_DELETE_TIMEOUT = 300

DLOG = debug.debug_get_logger("nfv_plugins.nfvi_plugins.openstack.usm")


def _usm_api_cmd(token, endpoint):
    base_url = token.get_service_url(PLATFORM_SERVICE.USM)
    if base_url is None:
        raise ValueError("PlatformService USM URL is invalid")

    url = os.path.join(base_url, "v1/", endpoint)
    return url


def _api_cmd_headers():
    api_cmd_headers = {}
    api_cmd_headers["Content-Type"] = "application/json"
    api_cmd_headers["User-Agent"] = "vim/1.0"
    return api_cmd_headers


def _api_get(token, url):
    """Perform a generic GET for a particular API endpoint."""

    response = rest_api_request(
        token, "GET", url, timeout_in_secs=REST_API_REQUEST_TIMEOUT
    )
    return response


def _api_post(
    token, url, payload, headers=None, timeout_in_secs=REST_API_REQUEST_TIMEOUT
):
    """Generic POST to an endpoint with a payload."""

    if headers is None:
        headers = _api_cmd_headers()

    response = rest_api_request(
        token,
        "POST",
        url,
        headers,
        json.dumps(payload),
        timeout_in_secs=timeout_in_secs,
    )
    return response


def _api_delete(token, url, timeout_in_secs=REST_API_REQUEST_TIMEOUT):
    """Perform DELETE on a particular endpoint."""

    response = rest_api_request(token, "DELETE", url, timeout_in_secs=timeout_in_secs)
    return response


def sw_deploy_get_releases(token, release_id=None):
    """Query USM for information about all releases or a specified one."""

    uri = "release"
    if release_id:
        uri = f"release/{release_id}"
    url = _usm_api_cmd(token, uri)
    response = _api_get(token, url)
    return response


def sw_deploy_show(token):
    """Query USM for information about a specific upgrade."""

    return _api_get(token, _usm_api_cmd(token, "deploy"))


def sw_deploy_host_list(token):
    """Query USM for information about a hosts during a deployment."""

    return _api_get(token, _usm_api_cmd(token, "deploy_host"))


def sw_deploy_precheck(token, release, force=False, snapshot=False):
    """Ask USM to precheck before a deployment."""

    url = _usm_api_cmd(token, "deploy/precheck")
    data = {"releases": release}
    if force:
        data["force"] = force
    if snapshot:
        data["options"] = ["snapshot=true"]
    response = _api_post(token, url, data)
    return response


def sw_deploy_start(token, release, force=False, snapshot=False):
    """Ask USM to start a deployment."""

    url = _usm_api_cmd(token, "deploy/start")
    data = {"releases": release}
    if force:
        data["force"] = force
    if snapshot:
        data["options"] = ["snapshot=true"]

    response = _api_post(
        token, url, data, timeout_in_secs=REST_API_DEPLOY_START_TIMEOUT
    )
    return response


def sw_deploy_execute(token, host_name):
    """Ask USM to execute a deployment on a host."""

    uri = f"deploy_host/{host_name}"
    url = _usm_api_cmd(token, uri)
    response = _api_post(token, url, {}, timeout_in_secs=REST_API_DEPLOY_HOST_TIMEOUT)
    return response


def sw_deploy_rollback(token, host_name):
    """Ask USM to rollback a deployment on a host."""

    uri = f"deploy_host/{host_name}/rollback"
    url = _usm_api_cmd(token, uri)
    response = _api_post(token, url, {})
    return response


def sw_deploy_activate(token):
    """Ask USM activate a deployment."""

    return _api_post(token, _usm_api_cmd(token, "deploy/activate"), {})


def sw_deploy_complete(token):
    """Ask USM complete a deployment."""

    return _api_post(token, _usm_api_cmd(token, "deploy/complete"), {})


def sw_deploy_delete(token):
    """Ask USM delete a deployment."""

    return _api_delete(
        token,
        _usm_api_cmd(token, "deploy"),
        timeout_in_secs=REST_API_DEPLOY_DELETE_TIMEOUT,
    )


def sw_deploy_abort(token):
    """Ask USM abort a deployment."""

    return _api_post(token, _usm_api_cmd(token, "deploy/abort"), {})


def sw_deploy_activate_rollback(token):
    """Ask USM activate rollback a deployment."""

    return _api_post(token, _usm_api_cmd(token, "deploy/activate_rollback"), {})


def sw_system_deploy_init(token, release, kube_version=None):
    """Ask USM to initialize a system deployment."""

    uri = f"system_deploy/{release}/init"
    url = _usm_api_cmd(token, uri)
    data = {}
    if kube_version:
        data["kube_version"] = kube_version

    response = _api_post(token, url, data)
    return response


def sw_system_deploy_delete(token):
    """Ask USM to delete a system deployment."""

    uri = "system_deploy"
    url = _usm_api_cmd(token, uri)

    response = _api_delete(token, url)
    return response


def sw_system_deploy_show(token):
    """Query USM for information about system deploy (template endpoint)."""

    uri = "system_deploy"
    url = _usm_api_cmd(token, uri)
    response = _api_get(token, url)
    return response


def _parse_version(sw_version):
    """Parse a dotted version string into a tuple of integers.

    This allows numeric comparison of releases so that, e.g. "9.0.0" is
    correctly treated as older than "11.0.0".
    """

    return tuple(int(section) for section in str(sw_version).split("."))


def _retrieve_release_data(to_release, from_release):
    if _parse_version(to_release) > _parse_version(from_release):
        return True, False
    return False, True


def _retrieve_release_info(token, sw_version):
    release_data = sw_deploy_get_releases(token).result_data

    try:
        return next(
            release for release in release_data if release["sw_version"] == sw_version
        )
    except StopIteration:
        error = f"Software release not found: {sw_version}"
        raise EnvironmentError(error)


def sw_deploy_get_upgrade_obj(token, release, upgrade_obj, precheck_data=None):
    """Quickly gather all information about a software deployment."""

    release_id = None
    metapackages = []
    release_info = None
    downgrade = False
    upgrade = False
    error_template = (
        "{}, check /var/log/nfv-vim.log or /var/log/software.log for more information."
    )

    deploy_data = sw_deploy_show(token).result_data
    hosts_info = sw_deploy_host_list(token).result_data or None
    system_deploy_data = sw_system_deploy_show(token).result_data

    try:
        deploy_info = deploy_data[0] if deploy_data else None
    except IndexError as e:
        error = f"Failed to parse 'software deploy show': {e}"
        DLOG.exception(f"{error}: \n{deploy_data=}")
        raise ValueError(error_template.format(error)) from e

    try:
        system_deploy_info = system_deploy_data[0] if system_deploy_data else None
    except IndexError as e:
        error = f"Failed to parse 'software system-deploy show': {e}"
        DLOG.exception(f"{error}: \n{system_deploy_data=}")
        raise ValueError(error_template.format(error)) from e

    # should only ever look for upgrade, downgrade and release info
    if precheck_data:
        upgrade, downgrade = _retrieve_release_data(
            precheck_data["to_release"], precheck_data["from_release"]
        )
        # When the upgrade object is created for the very first time, it does not
        # have the metapackages data filled, so it needs to be set once the
        # information is received in precheck.
        upgrade_obj.metapackages = list(precheck_data["additional_data"])
        release_info = _retrieve_release_info(token, precheck_data["to_release"])
        release_id = release_info.get("release_id")
        DLOG.info(
            f"Detected, {upgrade=}, {downgrade=}, "
            f"target={release_id}, "
            f"reboot_required={release_info['reboot_required']}, "
            f"to_version={precheck_data['to_release']}, "
            f"metapackages={upgrade_obj.metapackages}"
        )
    elif deploy_info:
        upgrade, downgrade = _retrieve_release_data(
            deploy_info["to_release"], deploy_info["from_release"]
        )

        if upgrade_obj:
            release_id = upgrade_obj.release_info.get("release_id")
            release_info = sw_deploy_get_releases(token, release_id).result_data
        else:
            # When the strategy is created with a deployment already in progress, the
            # precheck won't be executed, so the information needs to be retrieved
            # in full
            release_info = _retrieve_release_info(token, deploy_info["to_release"])
            release_id = release_info.get("release_id")
            # The metapackage name is stored as:
            # [['distcloud', '26.09.0', '26.09.1000']]
            metapackages = [
                f"{metapackage_info[0]}_{metapackage_info[2]}"
                for metapackage_info in (deploy_info.get("metapackages") or [])
            ]
    elif upgrade_obj:
        # When there's no active deployment and no precheck data, the information needs
        # to be retrieved from the upgrade object's last state, since it will already
        # exists.
        release_info = sw_deploy_get_releases(
            token, upgrade_obj.release_info["release_id"]
        ).result_data
    else:
        # This can be reached when:
        # 1. The query-upgrade is executed prior to a software deployment being
        # started. At that moment, precheck won't have been executed yet to fill the
        # information required to retrieve the release data.
        # 2. Running the sw-deploy strategy with --cleanup and the deployment was
        # already deleted
        DLOG.info("No release information was retrieved, proceeding without it")
    # During a major release the packages list will be too big and will break RPC calls.
    if release_info:
        release_info["packages_count"] = len(release_info.pop("packages", []))
        release_info["upgrade"] = upgrade
        release_info["downgrade"] = downgrade
        release_info["vim_rr"] = release_info["reboot_required"]

    if upgrade_obj:
        upgrade_obj.update(release_info, deploy_info, hosts_info, system_deploy_info)
        return upgrade_obj

    return nfvi.objects.v1.Upgrade(
        release,
        metapackages,
        release_info,
        deploy_info,
        hosts_info,
        system_deploy_info,
    )
