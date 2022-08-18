#
# Copyright (c) 2015-2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import copy
import json
from nfv_common import debug

from nfv_plugins.nfvi_plugins.openstack.objects import PLATFORM_SERVICE
from nfv_plugins.nfvi_plugins.openstack.rest_api import rest_api_request

DLOG = debug.debug_get_logger('nfv_plugins.nfvi_plugins.openstack.sysinv')

# WARNING: Any change to this timeout must be reflected in the config.ini
# file for the nfvi plugins.
REST_API_REQUEST_TIMEOUT = 60


KUBE_ROOTCA_UPDATE_ENDPOINT = "/kube_rootca_update"
KUBE_ROOTCA_UPDATE_GENERATE_CERT_ENDPOINT = \
    KUBE_ROOTCA_UPDATE_ENDPOINT + "/generate_cert"
KUBE_ROOTCA_UPDATE_PODS_ENDPOINT = KUBE_ROOTCA_UPDATE_ENDPOINT + "/pods"
KUBE_ROOTCA_UPDATE_HOSTS_ENDPOINT = KUBE_ROOTCA_UPDATE_ENDPOINT + "/hosts"
KUBE_ROOTCA_UPDATE_UPLOAD_CERT_ENDPOINT = \
    KUBE_ROOTCA_UPDATE_ENDPOINT + "/upload_cert"


# todo(abailey): refactor _api_get, etc.. into rest_api.py
def _api_cmd(token, endpoint):
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")
    api_cmd = url + endpoint
    return api_cmd


def _api_cmd_headers():
    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"
    return api_cmd_headers


def _api_delete(token, endpoint):
    """
    Generic DELETE for a sysinv endpoint
    """
    api_cmd = _api_cmd(token, endpoint)
    api_cmd_headers = _api_cmd_headers()
    response = rest_api_request(token,
                                "DELETE",
                                api_cmd,
                                api_cmd_headers,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def _api_get(token, endpoint):
    """
    Perform a generic GET for a particular sysinv API endpoint
    """
    api_cmd = _api_cmd(token, endpoint)
    response = rest_api_request(token,
                                "GET",
                                api_cmd,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def _api_patch_dict(token, endpoint, patch_dict):
    """
    Generic PATCH for a sysinv endpoint that passes a json dict
    Some endpoints expect a dict, while others expect a list
    """
    api_cmd = _api_cmd(token, endpoint)
    api_cmd_headers = _api_cmd_headers()
    return rest_api_request(token,
                            "PATCH",
                            api_cmd,
                            api_cmd_headers,
                            json.dumps(patch_dict),
                            timeout_in_secs=REST_API_REQUEST_TIMEOUT)


def _api_post(token, endpoint, api_cmd_payload):
    """
    Generic POST to a sysinv endpoint with a payload
    """
    api_cmd = _api_cmd(token, endpoint)
    api_cmd_headers = _api_cmd_headers()
    response = rest_api_request(token,
                                "POST",
                                api_cmd,
                                api_cmd_headers,
                                json.dumps(api_cmd_payload),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


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


def get_kube_host_upgrades(token):
    """
    Asks System Inventory for information about the kube host upgrades
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/kube_host_upgrades"

    response = rest_api_request(token, "GET", api_cmd,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def get_kube_rootca_update(token):
    """
    Asks System Inventory for information about the kube rootca update
    """
    return _api_get(token, KUBE_ROOTCA_UPDATE_ENDPOINT)


def get_kube_rootca_host_update_list(token):
    """
    Asks System Inventory for information about the kube rootca host updates
    """
    return _api_get(token, KUBE_ROOTCA_UPDATE_HOSTS_ENDPOINT)


def get_kube_upgrade(token):
    """
    Asks System Inventory for information about the kube upgrade
    """
    # todo(abailey): refactor using _api_get
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/kube_upgrade"

    response = rest_api_request(token, "GET", api_cmd,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def get_kube_version(token, kube_version):
    """
    Asks System Inventory for information a kube version
    """
    # todo(abailey): refactor using _api_get
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/kube_versions/" + kube_version

    response = rest_api_request(token, "GET", api_cmd,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def get_kube_versions(token):
    """
    Asks System Inventory for information about the kube versions
    """
    # todo(abailey): refactor using _api_get
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/kube_versions"

    response = rest_api_request(token, "GET", api_cmd,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def kube_rootca_update_start(token, force=False, alarm_ignore_list=None):
    """
    Ask System Inventory to start a kube rootca update
    """
    api_cmd_payload = dict()
    api_cmd_payload['force'] = force
    if alarm_ignore_list is not None:
        api_cmd_payload['alarm_ignore_list'] = copy.copy(alarm_ignore_list)
    return _api_post(token, KUBE_ROOTCA_UPDATE_ENDPOINT, api_cmd_payload)


def kube_rootca_update_generate_cert(token, expiry_date=None, subject=None):
    """
    Ask System Inventory to kube rootca update generate a cert
    """
    api_cmd_payload = dict()
    # even if these values are None, they need to be passed to sysinv API
    api_cmd_payload['expiry_date'] = expiry_date
    api_cmd_payload['subject'] = subject
    return _api_post(token, KUBE_ROOTCA_UPDATE_GENERATE_CERT_ENDPOINT,
                     api_cmd_payload)


def kube_rootca_update_upload_cert(token, cert_file):
    """
    Ask System Inventory to kube rootca update upload a cert file
    This uses POST for a file, which urllib does not work well with.
    """
    api_cmd = _api_cmd(token, KUBE_ROOTCA_UPDATE_UPLOAD_CERT_ENDPOINT)
    api_cmd_headers = _api_cmd_headers()
    api_cmd_payload = dict()

    # The API is expecting requests.post formatted data
    with open(cert_file, "rb") as cert_file_handle:
        # file handle automatically closed once this request is sent
        response = rest_api_request(token,
                                    "POST",
                                    api_cmd,
                                    api_cmd_headers,
                                    json.dumps(api_cmd_payload),
                                    timeout_in_secs=REST_API_REQUEST_TIMEOUT,
                                    file_to_post=cert_file_handle)
    return response


def kube_rootca_update_abort(token):
    """
    Ask System Inventory to kube rootca update abort
    """
    api_cmd_payload = list()
    state_data = dict()
    state_data['path'] = "/state"
    state_data['value'] = 'update-aborted'
    state_data['op'] = "replace"
    api_cmd_payload.append(state_data)
    return _api_patch_dict(token,
                           KUBE_ROOTCA_UPDATE_ENDPOINT,
                           api_cmd_payload)


def kube_rootca_update_complete(token):
    """
    Ask System Inventory to kube rootca update complete
    """
    api_cmd_payload = list()
    state_data = dict()
    state_data['path'] = "/state"
    state_data['value'] = 'update-completed'
    state_data['op'] = "replace"
    api_cmd_payload.append(state_data)
    return _api_patch_dict(token,
                           KUBE_ROOTCA_UPDATE_ENDPOINT,
                           api_cmd_payload)


def kube_rootca_update_host(token, host_uuid, phase):
    """
    Utility method to post to kube rootca update pods endpoint phase
    Valid phase values are:  [trust-both-cas, trust-new-ca, update-certs]
    """
    api_cmd = "/ihosts/%s/kube_update_ca " % host_uuid

    api_cmd_payload = dict()
    api_cmd_payload['phase'] = phase
    return _api_post(token, api_cmd, api_cmd_payload)


def kube_rootca_update_pods(token, phase):
    """
    Utility method to post to kube rootca update pods endpoint phase
    Valid phase values are:  [trust-both-cas, trust-new-ca]
    """
    api_cmd_payload = dict()
    api_cmd_payload['phase'] = phase
    return _api_post(token, KUBE_ROOTCA_UPDATE_PODS_ENDPOINT, api_cmd_payload)


def kube_upgrade_start(token, to_version, force=False, alarm_ignore_list=None):
    """
    Ask System Inventory to start a kube upgrade
    """
    # todo(abailey): refactor using _post_api_request
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/kube_upgrade"

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    api_cmd_payload = dict()
    api_cmd_payload['to_version'] = to_version
    api_cmd_payload['force'] = force
    if alarm_ignore_list is not None:
        api_cmd_payload['alarm_ignore_list'] = copy.copy(alarm_ignore_list)

    response = rest_api_request(token,
                                "POST",
                                api_cmd,
                                api_cmd_headers,
                                json.dumps(api_cmd_payload),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def _patch_kube_upgrade_state(token, new_value):
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/kube_upgrade"

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    api_cmd_payload = list()
    host_data = dict()
    host_data['path'] = "/state"
    host_data['value'] = new_value
    host_data['op'] = "replace"
    api_cmd_payload.append(host_data)

    return rest_api_request(token,
                            "PATCH",
                            api_cmd,
                            api_cmd_headers,
                            json.dumps(api_cmd_payload),
                            timeout_in_secs=REST_API_REQUEST_TIMEOUT)


def kube_upgrade_cleanup(token):
    """
    Ask System Inventory to delete the kube upgrade
    """
    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/kube_upgrade"

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    response = rest_api_request(token, "DELETE", api_cmd, api_cmd_headers,
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def kube_upgrade_complete(token):
    """
    Ask System Inventory to kube upgrade complete
    """
    return _patch_kube_upgrade_state(token, "upgrade-complete")


def kube_upgrade_download_images(token):
    """
    Ask System Inventory to kube upgrade download images
    """
    return _patch_kube_upgrade_state(token, "downloading-images")


def kube_upgrade_networking(token):
    """
    Ask System Inventory to kube upgrade networking
    """
    return _patch_kube_upgrade_state(token, "upgrading-networking")


def _kube_host_upgrade(token, host_uuid, target_operation, force):
    """
    Invoke a POST for a host kube-upgrade operation

    target_operation one of: kube_upgrade_control_plane, kube_upgrade_kubelet
    force is a 'string'
    """

    url = token.get_service_url(PLATFORM_SERVICE.SYSINV)
    if url is None:
        raise ValueError("OpenStack SysInv URL is invalid")

    api_cmd = url + "/ihosts/%s/%s" % (host_uuid, target_operation)

    api_cmd_headers = dict()
    api_cmd_headers['Content-Type'] = "application/json"
    api_cmd_headers['User-Agent'] = "vim/1.0"

    api_cmd_payload = dict()
    api_cmd_payload['force'] = force

    response = rest_api_request(token,
                                "POST",
                                api_cmd,
                                api_cmd_headers,
                                json.dumps(api_cmd_payload),
                                timeout_in_secs=REST_API_REQUEST_TIMEOUT)
    return response


def kube_host_upgrade_control_plane(token, host_uuid, force="true"):
    """
    Ask System Inventory to kube HOST upgrade control plane
    """
    return _kube_host_upgrade(token,
                              host_uuid,
                              "kube_upgrade_control_plane",
                              force)


def kube_host_upgrade_kubelet(token, host_uuid, force="true"):
    """
    Ask System Inventory to kube HOST upgrade kubelet
    """
    return _kube_host_upgrade(token,
                              host_uuid,
                              "kube_upgrade_kubelet",
                              force)


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
