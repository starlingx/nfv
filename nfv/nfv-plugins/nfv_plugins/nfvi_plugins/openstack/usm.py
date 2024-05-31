#
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import json
import os

from nfv_common import debug
from nfv_plugins.nfvi_plugins.openstack.objects import PLATFORM_SERVICE
from nfv_plugins.nfvi_plugins.openstack.rest_api import rest_api_request


REST_API_REQUEST_TIMEOUT = 60

DLOG = debug.debug_get_logger('nfv_plugins.nfvi_plugins.openstack.usm')


def _usm_api_cmd(token, endpoint):
    base_url = token.get_service_url(PLATFORM_SERVICE.USM)
    if base_url is None:
        raise ValueError("PlatformService USM URL is invalid")

    url = os.path.join(base_url, "v1/", endpoint)
    return url


def _api_cmd_headers():
    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"
    return api_cmd_headers


def _api_get(token, url):
    """
    Perform a generic GET for a particular API endpoint
    """

    response = rest_api_request(token,
                                "GET",
                                url,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def _api_post(token, url, payload, headers=None, timeout_in_secs=REST_API_REQUEST_TIMEOUT):
    """
    Generic POST to an endpoint with a payload
    """
    if headers is None:
        headers = _api_cmd_headers()

    response = rest_api_request(token,
                                "POST",
                                url,
                                headers,
                                json.dumps(payload),
                                timeout_in_secs)
    return response


def sw_deploy_get_release(token, release):
    """
    Query USM for information about a specific upgrade
    """

    uri = f"release"  # noqa:F541 pylint: disable=W1309
    url = _usm_api_cmd(token, uri)
    response = _api_get(token, url)
    return response


def sw_deploy_show(token):
    """
    Query USM for information about a specific upgrade
    """

    uri = f"deploy"  # noqa:F541 pylint: disable=W1309
    url = _usm_api_cmd(token, uri)
    response = _api_get(token, url)
    return response


def sw_deploy_host_list(token):
    """
    Query USM for information about a hosts during a deployment
    """

    uri = "deploy_host"
    url = _usm_api_cmd(token, uri)
    response = _api_get(token, url)
    return response


def sw_deploy_precheck(token, release, force=False):
    """
    Ask USM to precheck before a deployment
    """

    uri = f"deploy/{release}/precheck"
    data = {"force": force} if force else {}
    url = _usm_api_cmd(token, uri)
    response = _api_post(token, url, data)
    return response


def sw_deploy_start(token, release, force=False):
    """
    Ask USM to start a deployment
    """

    uri = f"deploy/{release}/start"
    url = _usm_api_cmd(token, uri)
    data = {"force": force} if force else {}
    response = _api_post(token, url, data)
    return response


def sw_deploy_execute(token, host_name):
    """
    Ask USM to execute a deployment on a host
    """

    uri = f"deploy_host/{host_name}"
    url = _usm_api_cmd(token, uri)
    response = _api_post(token, url, {})
    return response


def sw_deploy_activate(token):
    """
    Ask USM activate a deployment
    """

    uri = f"deploy/activate"  # noqa:F541 pylint: disable=W1309
    url = _usm_api_cmd(token, uri)
    response = _api_post(token, url, {})
    return response


def sw_deploy_complete(token):
    """
    Ask USM complete a deployment
    """

    uri = f"deploy/complete"  # noqa:F541 pylint: disable=W1309
    url = _usm_api_cmd(token, uri)
    response = _api_post(token, url, {})
    return response
