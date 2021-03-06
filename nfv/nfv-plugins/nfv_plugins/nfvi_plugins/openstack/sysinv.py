#
# Copyright (c) 2015-2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import json
from nfv_common import debug

from nfv_plugins.nfvi_plugins.openstack.objects import PLATFORM_SERVICE
from nfv_plugins.nfvi_plugins.openstack.rest_api import rest_api_request

DLOG = debug.debug_get_logger('nfv_plugins.nfvi_plugins.openstack.sysinv')

# WARNING: Any change to this timeout must be reflected in the config.ini
# file for the nfvi plugins.
REST_API_REQUEST_TIMEOUT = 45


def get_datanetworks(token, host_uuid):
    """
    Get all data networks on a host.
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/" + host_uuid + "/interface_datanetworks"
    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    response = rest_api_request(token, "GET", api_cmd, api_cmd_headers,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    result_data = response.result_data['interface_datanetworks']

    return result_data


def get_system_info(token):
    """
    Asks System Inventory for information about the system, such as
    the name of the system
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/isystems"

    response = rest_api_request(token, "GET", api_cmd,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def get_hosts(token):
    """
    Asks System Inventory for a list of hosts
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts"

    response = rest_api_request(token, "GET", api_cmd,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def get_host(token, host_uuid):
    """
    Asks System Inventory for a host details
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s" % host_uuid

    response = rest_api_request(token, "GET", api_cmd,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def get_host_labels(token, host_uuid):
    """
    Asks System Inventory for host label details
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s/labels" % host_uuid

    response = rest_api_request(token, "GET", api_cmd,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def get_upgrade(token):
    """
    Asks System Inventory for information about the upgrade
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/upgrade"

    response = rest_api_request(token, "GET", api_cmd,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def upgrade_start(token):
    """
    Ask System Inventory to start an upgrade
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/upgrade"

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    api_cmd_payload = dict()
    api_cmd_payload['force'] = "false"

    response = rest_api_request(token, "POST", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_payload),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def upgrade_activate(token):
    """
    Ask System Inventory to activate an upgrade
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/upgrade"

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    host_data = dict()
    host_data['path'] = "/state"
    host_data['value'] = "activation-requested"
    host_data['op'] = "replace"

    api_cmd_payload = list()
    api_cmd_payload.append(host_data)

    response = rest_api_request(token, "PATCH", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_payload),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def upgrade_complete(token):
    """
    Ask System Inventory to complete an upgrade
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/upgrade"

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    response = rest_api_request(token, "DELETE", api_cmd, api_cmd_headers,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def get_host_lvgs(token, host_uuid):
    """
    Asks System Inventory for a list logical volume groups for a host
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s/ilvgs" % host_uuid

    response = rest_api_request(token, "GET", api_cmd,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def notify_host_services_enabled(token, host_uuid):
    """
    Notify System Inventory that host services are enabled
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    api_cmd_payload = dict()
    api_cmd_payload['path'] = '/action'
    api_cmd_payload['value'] = 'services-enabled'
    api_cmd_payload['op'] = 'replace'

    api_cmd_list = list()
    api_cmd_list.append(api_cmd_payload)

    response = rest_api_request(token, "PATCH", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_list),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def notify_host_services_disabled(token, host_uuid):
    """
    Notify System Inventory that host services are disabled
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    api_cmd_payload = dict()
    api_cmd_payload['path'] = '/action'
    api_cmd_payload['value'] = 'services-disabled'
    api_cmd_payload['op'] = 'replace'

    api_cmd_list = list()
    api_cmd_list.append(api_cmd_payload)

    response = rest_api_request(token, "PATCH", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_list),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def notify_host_services_disable_extend(token, host_uuid):
    """
    Notify System Inventory that host services disable needs to be extended
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    api_cmd_payload_action = dict()
    api_cmd_payload_action['path'] = '/action'
    api_cmd_payload_action['value'] = 'services-disable-extend'
    api_cmd_payload_action['op'] = 'replace'

    api_cmd_list = list()
    api_cmd_list.append(api_cmd_payload_action)

    response = rest_api_request(token, "PATCH", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_list),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def notify_host_services_disable_failed(token, host_uuid, reason):
    """
    Notify System Inventory that host services disable failed
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    api_cmd_payload_action = dict()
    api_cmd_payload_action['path'] = '/action'
    api_cmd_payload_action['value'] = 'services-disable-failed'
    api_cmd_payload_action['op'] = 'replace'

    api_cmd_payload_reason = dict()
    api_cmd_payload_reason['path'] = '/vim_progress_status'
    api_cmd_payload_reason['value'] = str(reason)
    api_cmd_payload_reason['op'] = 'replace'

    api_cmd_list = list()
    api_cmd_list.append(api_cmd_payload_action)
    api_cmd_list.append(api_cmd_payload_reason)

    response = rest_api_request(token, "PATCH", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_list),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def notify_host_services_deleted(token, host_uuid):
    """
    Notify System Inventory that host services have been deleted
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    response = rest_api_request(token, "DELETE", api_cmd, api_cmd_headers,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def notify_host_services_delete_failed(token, host_uuid, reason):
    """
    Notify System Inventory that host services delete failed
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    api_cmd_payload_action = dict()
    api_cmd_payload_action['path'] = '/action'
    api_cmd_payload_action['value'] = 'services-delete-failed'
    api_cmd_payload_action['op'] = 'replace'

    api_cmd_payload_reason = dict()
    api_cmd_payload_reason['path'] = '/vim_progress_status'
    api_cmd_payload_reason['value'] = str(reason)
    api_cmd_payload_reason['op'] = 'replace'

    api_cmd_list = list()
    api_cmd_list.append(api_cmd_payload_action)
    api_cmd_list.append(api_cmd_payload_reason)

    response = rest_api_request(token, "PATCH", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_list),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def lock_host(token, host_uuid):
    """
    Ask System Inventory to lock a host
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    host_data = dict()
    host_data['path'] = "/action"
    host_data['value'] = "lock"
    host_data['op'] = "replace"

    api_cmd_payload = list()
    api_cmd_payload.append(host_data)

    response = rest_api_request(token, "PATCH", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_payload),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def unlock_host(token, host_uuid):
    """
    Ask System Inventory to unlock a host
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    host_data = dict()
    host_data['path'] = "/action"
    host_data['value'] = "unlock"
    host_data['op'] = "replace"

    api_cmd_payload = list()
    api_cmd_payload.append(host_data)

    response = rest_api_request(token, "PATCH", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_payload),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def reboot_host(token, host_uuid):
    """
    Ask System Inventory to reboot a host
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    host_data = dict()
    host_data['path'] = "/action"
    host_data['value'] = "reboot"
    host_data['op'] = "replace"

    api_cmd_payload = list()
    api_cmd_payload.append(host_data)

    response = rest_api_request(token, "PATCH", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_payload),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def upgrade_host(token, host_uuid):
    """
    Ask System Inventory to upgrade a host
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s/upgrade" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    api_cmd_payload = dict()
    api_cmd_payload['force'] = "false"

    response = rest_api_request(token, "POST", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_payload),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def swact_from_host(token, host_uuid):
    """
    Ask System Inventory to swact from a host
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    host_data = dict()
    host_data['path'] = "/action"
    host_data['value'] = "swact"
    host_data['op'] = "replace"

    api_cmd_payload = list()
    api_cmd_payload.append(host_data)

    response = rest_api_request(token, "PATCH", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_payload),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def get_host_devices(token, host_uuid):
    """
    Asks System Inventory for host device details
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s/pci_devices" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    response = rest_api_request(token, "GET", api_cmd, api_cmd_headers,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def get_host_device(token, device_uuid):
    """
    Asks System Inventory for host details for specific device
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/pci_devices/%s" % device_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    response = rest_api_request(token, "GET", api_cmd, api_cmd_headers,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def host_device_image_update(token, host_uuid):
    """
    Asks System Inventory to start a host device image update
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s/device_image_update" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    api_cmd_payload = dict()

    response = rest_api_request(token, "POST", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_payload),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def host_device_image_update_abort(token, host_uuid):
    """
    Asks System Inventory to abort a host device image update
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s/device_image_update_abort" % host_uuid

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    api_cmd_payload = dict()

    response = rest_api_request(token, "POST", api_cmd, api_cmd_headers,
                                json.dumps(api_cmd_payload),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response
