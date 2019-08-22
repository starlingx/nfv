#
# Copyright (c) 2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_common import debug

from nfv_plugins.nfvi_plugins.openstack.objects import OPENSTACK_SERVICE
from nfv_plugins.nfvi_plugins.openstack.objects import PLATFORM_SERVICE
from nfv_plugins.nfvi_plugins.openstack.rest_api import rest_api_request

import json

DLOG = debug.debug_get_logger('nfv_plugins.nfvi_plugins.openstack.fm')


def assemble_api_cmd(url, cmd):
    """
    Adapt Address to Different Url Format
    """
    if url.endswith('/'):
        return url + cmd
    else:
        return url + "/" + cmd


def get_alarms(token, fm_service=PLATFORM_SERVICE.FM):
    """
    Asks Fault Management for customer alarms
    """
    url = token.get_service_url(fm_service)
    if url is None:
        raise ValueError("OpenStack FM URL is invalid")

    api_cmd = assemble_api_cmd(url, "alarms?include_suppress=True")

    response = rest_api_request(token, "GET", api_cmd)
    return response


def get_logs(token, start=None, end=None, fm_service=PLATFORM_SERVICE.FM):
    """
    Asks Fault Management for customer logs
    """
    url = token.get_service_url(fm_service)
    if url is None:
        raise ValueError("OpenStack FM URL is invalid")

    api_cmd = assemble_api_cmd(url, "event_log?logs=True")

    if start is not None and end is not None:
        api_cmd += ("&q.field=start&q.field=end&q.op=eq&q.op=eq"
                    "&q.value=%s&q.value=%s"
                    % (str(start).replace(' ', 'T').replace(':', '%3A'),
                       str(end).replace(' ', 'T').replace(':', '%3A')))

    elif start is not None:
        api_cmd += ("&q.field=start;q.op=eq;q.value=%s"
                    % str(start).replace(' ', 'T').replace(':', '%3A'))
    elif end is not None:
        api_cmd += ("&q.field=end;q.op=eq;q.value=%s"
                    % str(end).replace(' ', 'T').replace(':', '%3A'))

    api_cmd += '&limit=100'

    response = rest_api_request(token, "GET", api_cmd)
    return response


def get_alarm_history(token, start=None, end=None, fm_service=PLATFORM_SERVICE.FM):
    """
    Asks Fault Management for customer alarm history
    """
    url = token.get_service_url(fm_service)
    if url is None:
        raise ValueError("OpenStack FM URL is invalid")

    api_cmd = assemble_api_cmd(url, "event_log?alarms=True")

    if start is not None and end is not None:
        api_cmd += ("&q.field=start&q.field=end&q.op=eq&q.op=eq"
                    "&q.value=%s&q.value=%s"
                    % (str(start).replace(' ', 'T').replace(':', '%3A'),
                       str(end).replace(' ', 'T').replace(':', '%3A')))

    elif start is not None:
        api_cmd += ("&q.field=start;q.op=eq;q.value='%s'"
                    % str(start).replace(' ', 'T').replace(':', '%3A'))
    elif end is not None:
        api_cmd += ("&q.field=end;q.op=eq;q.value='%s'"
                    % str(end).replace(' ', 'T').replace(':', '%3A'))

    api_cmd += '&limit=100'

    response = rest_api_request(token, "GET", api_cmd)
    return response


def raise_alarm(token, alarm_data="", fm_service=OPENSTACK_SERVICE.FM):
    """
    Raise customer alarm to Fault Management
    """
    url = token.get_service_url(fm_service)
    if url is None:
        raise ValueError("OpenStack FM URL is invalid")

    api_cmd = assemble_api_cmd(url, "alarms")

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"

    json_alarm_data = json.dumps(alarm_data)
    response = rest_api_request(token, "POST", api_cmd, api_cmd_headers, json_alarm_data)

    return response


def clear_alarm(token, fm_uuid="", fm_service=OPENSTACK_SERVICE.FM):
    """
    Clear customer alarm to Fault Management
    """
    url = token.get_service_url(fm_service)
    if url is None:
        raise ValueError("OpenStack FM URL is invalid")

    api_cmd = assemble_api_cmd(url, "alarms")

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"

    payload = ('{"id": "%s"}' % fm_uuid)

    rest_api_request(token, "DELETE", api_cmd, api_cmd_headers, payload)
    return
