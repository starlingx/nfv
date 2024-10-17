#
# Copyright (c) 2016-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import json
from nfv_client import sw_update
import os
import requests

CAFILE = os.environ.get('REQUESTS_CA_BUNDLE')
STRATEGY_EXISTS = 'strategy already exists.'


def request(token_id, method, api_cmd, api_cmd_headers=None,
            api_cmd_payload=None, timeout_in_secs=40):
    """
    Make a rest-api request
    Note: Using a default timeout of 40 seconds. The VIM's internal handling
    of these requests times out after 30 seconds - we want that to happen
    first (if possible).
    Library usage: 'urllib' library is replaced by 'requests' library - 'urllib'
    has limitation to support huge multiple connection requests in parallel.
    """
    headers = {"Accept": "application/json"}
    if token_id:
        headers["X-Auth-Token"] = token_id

    if api_cmd_headers:
        headers.update(api_cmd_headers)
    if api_cmd_payload:
        api_cmd_payload = json.loads(api_cmd_payload)
    try:
        response = requests.request(
            method, api_cmd, headers=headers, json=api_cmd_payload,
            timeout=timeout_in_secs, verify=CAFILE
        )
        response.raise_for_status()

        # Check if the content type starts with 'application/json'
        content_type = response.headers.get('content-type', '')
        if content_type.startswith('application/json'):
            return response.json()
        else:
            return response.text

    except requests.HTTPError as e:
        status_code = e.response.status_code
        if status_code == requests.codes.not_found:  # pylint: disable=no-member
            return None
        elif status_code == requests.codes.conflict:  # pylint: disable=no-member
            error_response = json.loads(response.text)
            if 'faultstring' in error_response and sw_update.STRATEGY_NAME_SW_UPGRADE in error_response.get('faultstring'):
                raise Exception(
                        "Operation failed: conflict detected.strategy already exists of type:sw-deploy")
            else:
                raise Exception(
                        f"Operation failed: conflict detected. {error_response.get('faultstring', STRATEGY_EXISTS)}")
        elif status_code == requests.codes.forbidden:  # pylint: disable=no-member
            raise Exception("Authorization failed")
        else:
            raise Exception(f"HTTP error: {e}")
