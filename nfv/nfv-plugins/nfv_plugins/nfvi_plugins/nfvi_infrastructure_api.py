#
# Copyright (c) 2015-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import datetime
import iso8601
import json
from six.moves import http_client as httplib

from nfv_common import debug
from nfv_common import tcp

from nfv_vim import nfvi

from nfv_plugins.nfvi_plugins import config

from nfv_plugins.nfvi_plugins.clients import kubernetes_client

from nfv_plugins.nfvi_plugins.openstack import exceptions
from nfv_plugins.nfvi_plugins.openstack import fm
from nfv_plugins.nfvi_plugins.openstack import mtc
from nfv_plugins.nfvi_plugins.openstack import openstack
from nfv_plugins.nfvi_plugins.openstack import rest_api
from nfv_plugins.nfvi_plugins.openstack import sysinv
from nfv_plugins.nfvi_plugins.openstack import usm

from nfv_plugins.nfvi_plugins.openstack.objects import OPENSTACK_SERVICE

DLOG = debug.debug_get_logger('nfv_plugins.nfvi_plugins.infrastructure_api')

# Allow 3600 seconds to determine if a kube rootca host update has stalled
MAX_KUBE_ROOTCA_HOST_UPDATE_DURATION = 3600


def host_state(host_uuid, host_name, host_personality, host_sub_functions,
               host_admin_state, host_oper_state, host_avail_status,
               sub_function_oper_state, sub_function_avail_status,
               data_port_oper_state, data_port_avail_status,
               data_port_fault_handling_enabled):
    """
    Takes as input the host state info received from maintenance.
    Returns a tuple of administrative state, operational state, availability
    status and nfvi-data for a host from the perspective of being able to
    host services and instances.
    """
    nfvi_data = dict()
    nfvi_data['uuid'] = host_uuid
    nfvi_data['name'] = host_name
    nfvi_data['personality'] = host_personality
    nfvi_data['subfunctions'] = host_sub_functions
    nfvi_data['admin_state'] = host_admin_state
    nfvi_data['oper_state'] = host_oper_state
    nfvi_data['avail_status'] = host_avail_status
    nfvi_data['subfunction_name'] = 'n/a'
    nfvi_data['subfunction_oper'] = 'n/a'
    nfvi_data['subfunction_avail'] = 'n/a'
    nfvi_data['data_ports_name'] = 'n/a'
    nfvi_data['data_ports_oper'] = 'n/a'
    nfvi_data['data_ports_avail'] = 'n/a'

    if 'worker' != host_personality and 'worker' in host_sub_functions:
        if sub_function_oper_state is not None:
            nfvi_data['subfunction_name'] = 'worker'
            nfvi_data['subfunction_oper'] = sub_function_oper_state
            nfvi_data['subfunction_avail'] = sub_function_avail_status

    if data_port_oper_state is not None:
        nfvi_data['data_ports_name'] = 'data-ports'
        nfvi_data['data_ports_oper'] = data_port_oper_state
        nfvi_data['data_ports_avail'] = data_port_avail_status

    if nfvi.objects.v1.HOST_OPER_STATE.ENABLED != host_oper_state:
        return (host_admin_state, host_oper_state, host_avail_status,
                nfvi_data)

    if 'worker' != host_personality and 'worker' in host_sub_functions:
        if nfvi.objects.v1.HOST_OPER_STATE.ENABLED != sub_function_oper_state:
            return (host_admin_state, sub_function_oper_state,
                    sub_function_avail_status, nfvi_data)

    if 'worker' == host_personality or 'worker' in host_sub_functions:
        if data_port_fault_handling_enabled:
            if data_port_oper_state is not None:
                if data_port_avail_status in \
                        [nfvi.objects.v1.HOST_AVAIL_STATUS.FAILED,
                         nfvi.objects.v1.HOST_AVAIL_STATUS.OFFLINE]:
                    data_port_avail_status \
                        = nfvi.objects.v1.HOST_AVAIL_STATUS.FAILED_COMPONENT

                return (host_admin_state, data_port_oper_state,
                        data_port_avail_status, nfvi_data)
            else:
                DLOG.info("Data port state is not available, defaulting host "
                          "%s operational state to unknown." % host_name)
                return (host_admin_state,
                        nfvi.objects.v1.HOST_OPER_STATE.UNKNOWN,
                        nfvi.objects.v1.HOST_AVAIL_STATUS.UNKNOWN, nfvi_data)

    return (host_admin_state, host_oper_state, host_avail_status,
            nfvi_data)


class NFVIInfrastructureAPI(nfvi.api.v1.NFVIInfrastructureAPI):
    """
    NFVI Infrastructure API Class Definition
    """
    _name = 'Infrastructure-API'
    _version = '1.0.0'
    _provider = 'Wind River'
    _signature = '22b3dbf6-e4ba-441b-8797-fb8a51210a43'

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def provider(self):
        return self._provider

    @property
    def signature(self):
        return self._signature

    @staticmethod
    def _host_supports_kubernetes(personality):
        return ('worker' in personality or 'controller' in personality)

    @staticmethod
    def _get_host_labels(host_label_list):

        openstack_compute = False
        openstack_control = False
        remote_storage = False

        OS_COMPUTE = nfvi.objects.v1.HOST_LABEL_KEYS.OS_COMPUTE_NODE
        OS_CONTROL = nfvi.objects.v1.HOST_LABEL_KEYS.OS_CONTROL_PLANE
        REMOTE_STORAGE = nfvi.objects.v1.HOST_LABEL_KEYS.REMOTE_STORAGE
        LABEL_ENABLED = nfvi.objects.v1.HOST_LABEL_VALUES.ENABLED

        for host_label in host_label_list:

            if host_label['label_key'] == OS_COMPUTE:
                if host_label['label_value'] == LABEL_ENABLED:
                    openstack_compute = True
            elif host_label['label_key'] == OS_CONTROL:
                if host_label['label_value'] == LABEL_ENABLED:
                    openstack_control = True
            elif host_label['label_key'] == REMOTE_STORAGE:
                if host_label['label_value'] == LABEL_ENABLED:
                    remote_storage = True

        return (openstack_compute, openstack_control, remote_storage)

    def __init__(self):
        super(NFVIInfrastructureAPI, self).__init__()
        self._platform_token = None
        self._openstack_token = None
        self._platform_directory = None
        self._openstack_directory = None
        self._rest_api_server = None
        self._host_add_callbacks = list()
        self._host_action_callbacks = list()
        self._host_state_change_callbacks = list()
        self._host_get_callbacks = list()
        self._sw_update_get_callbacks = list()
        self._host_upgrade_callbacks = list()
        self._host_update_callbacks = list()
        self._host_notification_callbacks = list()
        self._neutron_extensions = None
        self._data_port_fault_handling_enabled = False
        self._host_listener = None

    def _host_supports_nova_compute(self, personality):
        return (('worker' in personality) and
                (self._openstack_directory.get_service_info(
                    OPENSTACK_SERVICE.NOVA) is not None))

    def set_response_error(self, response, activity, issue="did not complete"):
        """Utility method to consistently log and report an API error activity

        :param str activity: the API action that failed
        :param dict response: The response dict to store the error 'reason'
        """
        error_string = "{} {}.".format(activity, issue)
        DLOG.error(error_string)
        response['reason'] = error_string

    def get_datanetworks(self, future, host_uuid, callback):
        """
        Get host data networks from the plugin
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(sysinv.get_datanetworks, self._platform_token,
                        host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("SysInv get-datanetworks did not complete.")
                return

            response['result-data'] = future.result.data
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to get host %s data "
                               "networks, error=%s." % (host_uuid, e))

        except Exception as e:
            DLOG.exception("Caught exception while trying to get host %s data networks, "
                           "error=%s." % (host_uuid, e))

        finally:
            callback.send(response)
            callback.close()

    def get_system_info(self, future, callback):
        """
        Get information about the system from the plugin
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(sysinv.get_system_info, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("SysInv get-system-info did not complete.")
                return

            system_data_list = future.result.data
            if 1 < len(system_data_list):
                DLOG.critical("Too many systems retrieved, num_systems=%i"
                              % len(system_data_list))

            system_obj = None

            for system_data in system_data_list['isystems']:
                if system_data['description'] is None:
                    system_data['description'] = ""

                system_obj = nfvi.objects.v1.System(system_data['name'],
                                                    system_data['description'])
                break

            response['result-data'] = system_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to get system "
                               "info, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to get system info, "
                           "error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def get_system_state(self, future, callback):
        """
        Get the state of the system from the plugin
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(mtc.system_query, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Mtc system-query did not complete.")
                return

            if httplib.ACCEPTED == future.result.ancillary_data.status_code:
                host_data_list = None
            else:
                host_data_list = future.result.data['hosts']

            response['result-data'] = host_data_list
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to query the "
                               "state of the system, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to query the "
                           "state of the system, error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def get_hosts(self, future, callback):
        """
        Get a list of hosts
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        response['incomplete-hosts'] = list()
        response['host-groups'] = list()

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    return

                self._platform_token = future.result.data

            future.work(sysinv.get_hosts, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Get-Hosts did not complete.")
                return

            host_data_list = future.result.data

            host_objs = list()

            for host_data in host_data_list['ihosts']:
                if host_data['hostname'] is None:
                    continue

                if host_data['subfunctions'] is None:
                    continue

                future.work(mtc.host_query, self._platform_token,
                            host_data['uuid'], host_data['hostname'])
                future.result = (yield)

                if not future.result.is_complete():
                    DLOG.error("Query-Host-State did not complete, "
                               "host=%s." % host_data['hostname'])
                    response['incomplete-hosts'].append(host_data['hostname'])
                    continue

                state = future.result.data['state']

                host_uuid = host_data['uuid']
                host_name = host_data['hostname']
                host_personality = host_data['personality']
                host_sub_functions = host_data.get('subfunctions', [])
                host_admin_state = state['administrative']
                host_oper_state = state['operational']
                host_avail_status = state['availability']
                sub_function_oper_state = state.get('subfunction_oper',
                                                    None)
                sub_function_avail_status = state.get('subfunction_avail',
                                                      None)
                data_port_oper_state = state.get('data_ports_oper', None)
                data_port_avail_status = state.get('data_ports_avail', None)
                host_action = (host_data.get('ihost_action') or "")
                host_action = host_action.rstrip('-')
                software_load = host_data['software_load']
                target_load = host_data['target_load']
                device_image_update = host_data['device_image_update']

                future.work(sysinv.get_host_labels, self._platform_token,
                            host_uuid)
                future.result = (yield)

                if not future.result.is_complete():
                    DLOG.error("Get-Host-Labels did not complete.")
                    response['incomplete-hosts'].append(host_data['hostname'])
                    continue

                host_label_list = future.result.data['labels']

                openstack_compute, openstack_control, remote_storage = \
                    self._get_host_labels(host_label_list)

                admin_state, oper_state, avail_status, nfvi_data \
                    = host_state(host_uuid, host_name, host_personality,
                                 host_sub_functions, host_admin_state,
                                 host_oper_state, host_avail_status,
                                 sub_function_oper_state,
                                 sub_function_avail_status,
                                 data_port_oper_state,
                                 data_port_avail_status,
                                 self._data_port_fault_handling_enabled)

                host_obj = nfvi.objects.v1.Host(host_uuid, host_name,
                                                host_sub_functions,
                                                admin_state, oper_state,
                                                avail_status,
                                                host_action,
                                                host_data['uptime'],
                                                software_load,
                                                target_load,
                                                device_image_update,
                                                openstack_compute,
                                                openstack_control,
                                                remote_storage,
                                                nfvi_data)

                host_objs.append(host_obj)

                host_group_data = host_data.get('peers', None)
                if host_group_data is None:
                    continue

                if 'storage' not in host_sub_functions:
                    continue

                host_group_obj = next((x for x in response['host-groups']
                                       if host_group_data['name'] in x.name), None)
                if host_group_obj is None:
                    host_group_obj = nfvi.objects.v1.HostGroup(
                        host_group_data['name'], [host_name],
                        [nfvi.objects.v1.HOST_GROUP_POLICY.STORAGE_REPLICATION])
                    response['host-groups'].append(host_group_obj)
                else:
                    host_group_obj.member_names.append(host_name)

            response['result-data'] = host_objs
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to get hosts, "
                               "error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to get host list, "
                           "error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def get_host(self, future, host_uuid, host_name, callback):
        """
        Get host details
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.get_host, self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            host_data = future.result.data

            future.work(mtc.host_query, self._platform_token,
                        host_data['uuid'], host_data['hostname'])
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Query-Host-State did not complete, host=%s."
                           % host_data['hostname'])
                return

            state = future.result.data['state']

            host_uuid = host_data['uuid']
            host_name = host_data['hostname']
            host_personality = host_data['personality']
            host_sub_functions = host_data.get('subfunctions', [])
            host_admin_state = state['administrative']
            host_oper_state = state['operational']
            host_avail_status = state['availability']
            sub_function_oper_state = state.get('subfunction_oper', None)
            sub_function_avail_status = state.get('subfunction_avail', None)
            data_port_oper_state = state.get('data_ports_oper', None)
            data_port_avail_status = state.get('data_ports_avail', None)
            host_action = (host_data.get('ihost_action') or "").rstrip('-')
            software_load = host_data['software_load']
            target_load = host_data['target_load']
            device_image_update = host_data['device_image_update']

            admin_state, oper_state, avail_status, nfvi_data \
                = host_state(host_uuid, host_name, host_personality,
                             host_sub_functions, host_admin_state,
                             host_oper_state, host_avail_status,
                             sub_function_oper_state,
                             sub_function_avail_status,
                             data_port_oper_state,
                             data_port_avail_status,
                             self._data_port_fault_handling_enabled)

            future.work(sysinv.get_host_labels, self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Get-Host-Labels did not complete, host=%s."
                           % host_name)
                return

            host_label_list = future.result.data['labels']

            openstack_compute, openstack_control, remote_storage = \
                self._get_host_labels(host_label_list)

            host_obj = nfvi.objects.v1.Host(host_uuid, host_name,
                                            host_sub_functions,
                                            admin_state, oper_state,
                                            avail_status,
                                            host_action,
                                            host_data['uptime'],
                                            software_load,
                                            target_load,
                                            device_image_update,
                                            openstack_compute,
                                            openstack_control,
                                            remote_storage,
                                            nfvi_data)

            response['result-data'] = host_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to get host "
                               "details, host=%s, error=%s." % (host_name, e))

        except Exception as e:
            DLOG.exception("Caught exception while trying to get host "
                           "details, host=%s, error=%s." % (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def get_host_devices(self, future, host_uuid, host_name, callback):
        """
        Get host device list details
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.get_host_devices,
                        self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            host_data = future.result.data

            response['result-data'] = host_data
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception trying to get_host_devices"
                               "details, host=%s, error=%s." % (host_name, e))

        except Exception as e:
            DLOG.exception("Caught exception trying to get_host_devices "
                           "details, host=%s, error=%s." % (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def get_host_device(self, future, host_uuid, host_name,
                        device_uuid, device_name, callback):
        """
        Get host device details
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.get_host_device,
                        self._platform_token, device_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            host_data = future.result.data

            response['result-data'] = host_data
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception trying to get_host_device "
                               "details, host=%s, device=%s, error=%s." %
                               (host_name, device_name, e))

        except Exception as e:
            DLOG.exception("Caught exception trying to get_host_device "
                           "details, host=%s, device=%s, error=%s." %
                           (host_name, device_name, e))

        finally:
            callback.send(response)
            callback.close()

    def host_device_image_update(self, future, host_uuid, host_name, callback):
        """
        Update a host device image
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.host_device_image_update,
                        self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            host_data = future.result.data

            response['result-data'] = host_data
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception requesting a host device "
                               "image update, host=%s, error=%s." %
                               (host_name, e))

        except Exception as e:
            DLOG.exception("Caught exception requesting a host device "
                           "image update, host=%s, error=%s." %
                           (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def host_device_image_update_abort(self, future, host_uuid, host_name, callback):
        """
        Abort a host device image update
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.host_device_image_update_abort,
                        self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            host_data = future.result.data

            response['result-data'] = host_data
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception requesting host device "
                               "image update abort, host=%s, error=%s." %
                               (host_name, e))

        except Exception as e:
            DLOG.exception("Caught exception requesting host device "
                           "image update abort, host=%s, error=%s." %
                           (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def kube_rootca_update_abort(self, future, callback):
        """Invokes sysinv kube-rootca-update-abort"""
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-rootca-update-abort'
        sysinv_method = sysinv.kube_rootca_update_abort
        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))
            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)
                if not future.result.is_complete() or \
                        future.result.data is None:
                    self.set_response_error(response, "Openstack get-token")
                    return
                self._platform_token = future.result.data
            future.work(sysinv_method, self._platform_token)
            future.result = (yield)
            if not future.result.is_complete():
                self.set_response_error(response, action_type)
                return
            api_data = future.result.data
            result_obj = nfvi.objects.v1.KubeRootcaUpdate(api_data['state'])
            response['result-data'] = result_obj
            response['completed'] = True
        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()
            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason
        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))
        finally:
            callback.send(response)
            callback.close()

    def kube_rootca_update_complete(self, future, callback):
        """Invokes sysinv kube-rootca-update-complete"""
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-rootca-update-complete'
        sysinv_method = sysinv.kube_rootca_update_complete
        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))
            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)
                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return
                self._platform_token = future.result.data
            future.work(sysinv_method, self._platform_token)
            future.result = (yield)
            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return
            api_data = future.result.data
            result_obj = nfvi.objects.v1.KubeRootcaUpdate(api_data['state'])
            response['result-data'] = result_obj
            response['completed'] = True
        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()
            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason
        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))
        finally:
            callback.send(response)
            callback.close()

    def kube_rootca_update_generate_cert(self, future,
                                         expiry_date, subject, callback):
        """Invokes sysinv kube-rootca-update-generate-cert"""
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-rootca-update-generate-cert'
        sysinv_method = sysinv.kube_rootca_update_generate_cert
        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))
            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)
                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return
                self._platform_token = future.result.data
            future.work(sysinv_method, self._platform_token,
                        expiry_date=expiry_date,
                        subject=subject)
            future.result = (yield)
            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return
            api_data = future.result.data
            new_cert_identifier = api_data['success']
            response['result-data'] = new_cert_identifier
            response['completed'] = True
        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()
            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason
        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))
        finally:
            callback.send(response)
            callback.close()

    def kube_rootca_update_upload_cert(self, future, cert_file, callback):
        """Invokes sysinv kube-rootca-update-upload-cert"""
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-rootca-update-upload-cert'
        sysinv_method = sysinv.kube_rootca_update_upload_cert
        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))
            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)
                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return
                self._platform_token = future.result.data
            future.work(sysinv_method, self._platform_token,
                        cert_file=cert_file)
            future.result = (yield)
            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return
            api_data = future.result.data
            new_cert_identifier = api_data['success']
            response['result-data'] = new_cert_identifier
            response['completed'] = True
        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()
            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason
        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))
        finally:
            callback.send(response)
            callback.close()

    def kube_rootca_update_host(self, future, host_uuid, host_name,
                               update_type,
                               in_progress_state,
                               completed_state,
                               failed_state,
                               callback):
        """
        Kube Root CA Update a host for a particular update_type (phase)
        """
        response = dict()
        response['completed'] = False
        response['host_uuid'] = host_uuid
        response['host_name'] = host_name
        response['reason'] = ''
        action_type = 'kube-rootca-update-host'
        sysinv_method = sysinv.kube_rootca_update_host
        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))
            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)
                if not future.result.is_complete() or \
                        future.result.data is None:
                    self.set_response_error(response, "Openstack get-token")
                    return
                self._platform_token = future.result.data

            # This is wasteful but we need to check if host updating/updated,
            # so we can skip or wait for it, rather than issue an action.
            # todo(abailey): Update sysinv API to support a single host query
            # todo(abailey): update vim schema for a table for these entries
            # todo(abailey): this should be removed and put in directory once
            # schema is updated
            future.work(sysinv.get_kube_rootca_host_update_list,
                        self._platform_token)
            future.result = (yield)
            if not future.result.is_complete():
                self.set_response_error(response,
                                        "SysInv get-kube-rootca-host-updates")
                return
            sysinv_result_key = "kube_host_updates"
            results_list = future.result.data[sysinv_result_key]
            results_obj = self._extract_kube_rootca_host_updates(results_list)
            # walk the list and find the object for this host
            # Do the match based on hostname since the id will not match
            host_state = None
            for host_obj in results_obj:
                if host_obj.hostname == host_name:
                    host_state = host_obj.state
                    result_obj = host_obj
                    break
            DLOG.info("Existing Host state for %s is %s"
                      % (host_name, host_state))

            if host_state == in_progress_state:
                # Do not re-invoke the action.  It is already in progress
                # the host_obj in the loop above can be returned as result_obj

                # the operation may have stalled and the kube rootca code in
                # sysinv does not have code to detect this, so we check
                # last_updated  and abort if too much time spent in-progress
                # the updated_at field must exist is we are in-progress
                updated_at = iso8601.parse_date(result_obj['updated_at'])
                now = iso8601.parse_date(datetime.datetime.utcnow().isoformat())
                delta = (now - updated_at).total_seconds()
                if delta > MAX_KUBE_ROOTCA_HOST_UPDATE_DURATION:
                    # still in progress after this amount of time, it is likely
                    # a broken state.  Need to abort.
                    self.set_response_error(response, action_type,
                                            issue="timed out (in-progress)")
                    return
                pass
            elif host_state == completed_state:
                # Do not re-invoke the action.  It is already completed
                # the host_obj in the loop above can be returned as result_obj
                pass
            else:
                # Every other state (including failed) means we invoke API
                future.work(sysinv_method,
                            self._platform_token,
                            host_uuid,
                            update_type)
                future.result = (yield)
                if not future.result.is_complete():
                    self.set_response_error(response, action_type)
                    return
                api_data = future.result.data
                result_obj = nfvi.objects.v1.KubeRootcaHostUpdate(
                    api_data['id'],
                    api_data['hostname'],
                    api_data['target_rootca_cert'],
                    api_data['effective_rootca_cert'],
                    api_data['state'],
                    api_data['created_at'],
                    api_data['updated_at']
                )
            # result_obj is the host_obj from the loop, or the API result
            response['result-data'] = result_obj
            response['completed'] = True
        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()
            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason
        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))
        finally:
            callback.send(response)
            callback.close()

    def kube_rootca_update_pods(self, future, phase, callback):
        """Invokes sysinv kube-rootca-update-pods for a certain phase"""
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-rootca-update-pods'
        sysinv_method = sysinv.kube_rootca_update_pods
        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))
            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)
                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return
                self._platform_token = future.result.data
            future.work(sysinv_method, self._platform_token, phase)
            future.result = (yield)
            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return
            api_data = future.result.data
            result_obj = nfvi.objects.v1.KubeRootcaUpdate(api_data['state'])
            response['result-data'] = result_obj
            response['completed'] = True
        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()
            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason
        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))
        finally:
            callback.send(response)
            callback.close()

    def kube_rootca_update_start(self, future, force, alarm_ignore_list,
                                 callback):
        """Invokes sysinv kube-rootca-update-start"""
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-rootca-update-start'
        sysinv_method = sysinv.kube_rootca_update_start
        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))
            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)
                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return
                self._platform_token = future.result.data
            future.work(sysinv_method,
                        self._platform_token,
                        force=force,
                        alarm_ignore_list=alarm_ignore_list)
            future.result = (yield)
            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return
            api_data = future.result.data
            result_obj = nfvi.objects.v1.KubeRootcaUpdate(api_data['state'])
            response['result-data'] = result_obj
            response['completed'] = True
        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()
            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason
        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))
        finally:
            callback.send(response)
            callback.close()

    def _extract_kube_rootca_host_updates(self, kube_rootca_update_host_list):
        """
        Return a list of KubeRootcaHostUpdate objects from sysinv api results.
        """
        result_list = []
        for host_data in kube_rootca_update_host_list:
            result_list.append(
                nfvi.objects.v1.KubeRootcaHostUpdate(
                    host_data['id'],  # host_id
                    host_data['hostname'],
                    host_data['target_rootca_cert'],
                    host_data['effective_rootca_cert'],
                    host_data['state'],
                    host_data['created_at'],
                    host_data['updated_at']
                )
            )
        return result_list

    def get_kube_rootca_host_update_list(self, future, callback):
        """
        Get information about the kube rootca host update list from the plugin
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        activity = "SysInv get-kube-rootca-host-updates"
        sysinv_method = sysinv.get_kube_rootca_host_update_list
        sysinv_result_key = "kube_host_updates"

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    error_string = "OpenStack get-token  did not complete"
                    DLOG.error(error_string)
                    response['reason'] = error_string
                    return
                self._platform_token = future.result.data

            # Query the sysinv method
            future.work(sysinv_method, self._platform_token)
            future.result = (yield)
            if not future.result.is_complete():
                error_string = "{} did not complete".format(activity)
                DLOG.error(error_string)
                response['reason'] = error_string
                return
            results_list = future.result.data[sysinv_result_key]
            results_obj = self._extract_kube_rootca_host_updates(results_list)
            response['result-data'] = results_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()
                response['reason'] = "token expired"
            else:
                DLOG.exception("Caught exception %s err=%s" % (activity, e))
                response['reason'] = repr(e)
        except Exception as e:
            DLOG.exception("Caught exception %s err=%s" % (activity, e))
            response['reason'] = repr(e)
        finally:
            callback.send(response)
            callback.close()

    def _extract_kube_host_upgrade_list(self,
                                        kube_host_upgrade_list,
                                        host_list):
        """
        Return a list of KubeHostUpgrade objects from sysinv api results.
        """

        # Map the ID to the uuid from host_list
        host_map = dict()
        for host in host_list:
            host_map[host['id']] = host['uuid']
        result_list = []
        for host_data in kube_host_upgrade_list:
            host_uuid = host_map[host_data['host_id']]
            result_list.append(
                nfvi.objects.v1.KubeHostUpgrade(
                    host_data['host_id'],
                    host_uuid,
                    host_data['target_version'],
                    host_data['control_plane_version'],
                    host_data['kubelet_version'],
                    host_data['status'])
            )
        return result_list

    def get_kube_host_upgrade_list(self, future, callback):
        """
        Get information about the kube host upgrade list from the plugin
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        activity = "SysInv get-kube-host-upgrades"

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            # Query the kube host upgrade list
            future.work(sysinv.get_kube_host_upgrades, self._platform_token)
            future.result = (yield)
            if not future.result.is_complete():
                error_string = "{} did not complete".format(activity)
                DLOG.error(error_string)
                response['reason'] = error_string
                return
            kube_host_upgrade_list = future.result.data["kube_host_upgrades"]

            # Also query the host list, kube_host_upgrades does not have uuid
            future.work(sysinv.get_hosts, self._platform_token)
            future.result = (yield)
            if not future.result.is_complete():
                DLOG.error("Sysinv Get-Hosts did not complete.")
                return
            host_list = future.result.data["ihosts"]

            results_obj = \
                self._extract_kube_host_upgrade_list(kube_host_upgrade_list,
                                                     host_list)
            response['result-data'] = results_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception kube host upgrade list err=%s"
                               % e)
        except Exception as e:
            DLOG.exception("Caught exception kube host upgrade list err=%s"
                           % e)
        finally:
            callback.send(response)
            callback.close()

    def _extract_kube_upgrade(self, kube_upgrade_data_list):
        """
        Return a KubeUpgrade object from sysinv api results.

        Returns None if there are no items in the list.
        Returns first kube upgrade object, but the API should never return
        more than one object.
        """

        if 1 < len(kube_upgrade_data_list):
            DLOG.critical("Too many kube upgrades returned, num=%i"
                          % len(kube_upgrade_data_list))

        elif 0 == len(kube_upgrade_data_list):
            DLOG.info("No kube upgrade exists, num=%i"
                      % len(kube_upgrade_data_list))

        kube_upgrade_obj = None
        for kube_upgrade_data in kube_upgrade_data_list:
            kube_upgrade_obj = nfvi.objects.v1.KubeUpgrade(
                kube_upgrade_data['state'],
                kube_upgrade_data['from_version'],
                kube_upgrade_data['to_version'])
            break
        return kube_upgrade_obj

    def _extract_kube_rootca_update(self, data_list):
        """
        Return a KubeRootCaUpdate object from sysinv api results.

        Returns None if there are no items in the list.
        Returns first object, but the API should never return
        more than one object.
        """
        description = 'kube rootca update'
        if 1 < len(data_list):
            DLOG.critical("Too many %s returned, num=%i"
                          % (description, len(data_list)))

        elif 0 == len(data_list):
            DLOG.info("No %s exists, num=%i"
                      % (description, len(data_list)))

        # todo(abailey): refactor this code to to reusable for other objects
        result_obj = None
        for result_data in data_list:
            result_obj = nfvi.objects.v1.KubeRootcaUpdate(result_data['state'])
            break
        return result_obj

    def get_kube_rootca_update(self, future, callback):
        """
        Get information about the kube rootca update from the plugin
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'get-kube-rootca-update'
        sysinv_method = sysinv.get_kube_rootca_update
        result_key = 'kube_rootca_updates'
        extraction_method = self._extract_kube_rootca_update

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    response['reason'] = "OpenStack get-token did not complete"
                    return

                self._platform_token = future.result.data

            future.work(sysinv_method, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                response['reason'] = "{} did not complete".format(action_type)
                return

            result_obj_data_list = future.result.data[result_key]
            result_obj = extraction_method(result_obj_data_list)
            response['result-data'] = result_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            # todo(abailey): refactor the code for uniform error handling
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()
                response['reason'] = 'token expired'

            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
                response['reason'] = repr(e)
        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))
            response['reason'] = repr(e)

        finally:
            callback.send(response)
            callback.close()

    def get_kube_upgrade(self, future, callback):
        """
        Get information about the kube upgrade from the plugin
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'get-kube-upgrade'
        # todo(abailey): refactor to use sysinv_method

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(sysinv.get_kube_upgrade, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("SysInv get-kube-upgrade did not complete.")
                return

            kube_upgrade_data_list = future.result.data['kube_upgrades']
            kube_upgrade_obj = \
                self._extract_kube_upgrade(kube_upgrade_data_list)
            response['result-data'] = kube_upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))

        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))

        finally:
            callback.send(response)
            callback.close()

    def _extract_kube_version(self, kube_data):
        """
        Return a KubeVersion from sysinv API results.
        """
        # sysinv api returns a field called 'version' which is a reserved field
        # in vim object data structure.  It is stored as kube_version
        return nfvi.objects.v1.KubeVersion(kube_data['version'],
                                           kube_data['state'],
                                           kube_data['target'],
                                           kube_data['upgrade_from'],
                                           kube_data['downgrade_to'],
                                           kube_data['applied_patches'],
                                           kube_data['available_patches'])

    def get_kube_version_list(self, future, callback):
        """
        Get information about the kube versions list from the plugin
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'get-kube-versions'

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))
            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)
                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return
                self._platform_token = future.result.data

            # get_kube_versions only returns a limited amount of data about the
            # kubernetes versions.  Individual API calls get the patch info.
            future.work(sysinv.get_kube_versions, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return

            # walk the list of versions and get the patch info
            kube_versions_list = list()
            limited_kube_version_list = future.result.data['kube_versions']
            for kube_list_entry in limited_kube_version_list:
                kube_ver = kube_list_entry['version']
                future.work(sysinv.get_kube_version,
                            self._platform_token,
                            kube_ver)
                future.result = (yield)
                if not future.result.is_complete():
                    DLOG.error("%s for version:%s did not complete."
                               % (action_type, kube_ver))
                    return
                # returns a single object
                kube_ver_data = future.result.data
                kube_versions_list.append(
                    self._extract_kube_version(kube_ver_data))

            response['result-data'] = kube_versions_list
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()
            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))
        finally:
            callback.send(response)
            callback.close()

    def kube_host_upgrade_control_plane(self,
                                        future,
                                        host_uuid,
                                        host_name,
                                        force,
                                        callback):
        """
        Start kube host upgrade 'control plane' for a particular controller
        """
        response = dict()
        response['completed'] = False
        response['host_uuid'] = host_uuid
        response['host_name'] = host_name
        response['reason'] = ''
        action_type = 'kube-host-upgrade-control-plane'
        sysinv_method = sysinv.kube_host_upgrade_control_plane

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            # invoke the actual kube_host_upgrade method
            future.work(sysinv_method,
                        self._platform_token,
                        host_uuid,
                        force)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return
            # result was a host object. Need to query to get kube upgrade obj
            future.work(sysinv.get_kube_upgrade, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("SysInv get-kube-upgrade did not complete.")
                return

            kube_upgrade_data_list = future.result.data['kube_upgrades']
            kube_upgrade_obj = \
                self._extract_kube_upgrade(kube_upgrade_data_list)
            response['result-data'] = kube_upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason

        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))

        finally:
            callback.send(response)
            callback.close()

    def kube_host_upgrade_kubelet(self,
                                  future,
                                  host_uuid,
                                  host_name,
                                  force,
                                  callback):
        """
        Start kube host upgrade 'kubelet' for a particular host
        """
        response = dict()
        response['completed'] = False
        response['host_uuid'] = host_uuid
        response['host_name'] = host_name
        response['reason'] = ''
        action_type = 'kube-host-upgrade-kubelet'
        sysinv_method = sysinv.kube_host_upgrade_kubelet

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            # invoke the actual kube_host_upgrade method
            future.work(sysinv_method,
                        self._platform_token,
                        host_uuid,
                        force)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return
            # result was a host object. Need to query to get kube upgrade obj
            future.work(sysinv.get_kube_upgrade, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("SysInv get-kube-upgrade did not complete.")
                return

            kube_upgrade_data_list = future.result.data['kube_upgrades']
            kube_upgrade_obj = \
                self._extract_kube_upgrade(kube_upgrade_data_list)
            response['result-data'] = kube_upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason

        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))

        finally:
            callback.send(response)
            callback.close()

    def kube_upgrade_abort(self, future, callback):
        """Invokes sysinv kube-upgrade-abort"""
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-upgrade-abort'
        sysinv_method = sysinv.kube_upgrade_abort
        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))
            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)
                if not future.result.is_complete() or \
                        future.result.data is None:
                    self.set_response_error(response, "Openstack get-token")
                    return
                self._platform_token = future.result.data
            future.work(sysinv_method, self._platform_token)
            future.result = (yield)
            if not future.result.is_complete():
                self.set_response_error(response, action_type)
                return
            api_data = future.result.data
            result_obj = nfvi.objects.v1.KubeUpgrade(
                api_data['state'],
                api_data['from_version'],
                api_data['to_version'])
            response['result-data'] = result_obj
            response['completed'] = True
        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()
            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason
        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))
        finally:
            callback.send(response)
            callback.close()

    def kube_upgrade_cleanup(self, future, callback):
        """
        kube upgrade cleanup
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-upgrade-cleanup'

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(sysinv.kube_upgrade_cleanup, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return

            # The result should be empty. no result data to report back
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason

        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))

        finally:
            callback.send(response)
            callback.close()

    def kube_upgrade_complete(self, future, callback):
        """
        kube upgrade complete
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-upgrade-complete'

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(sysinv.kube_upgrade_complete, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return

            kube_upgrade_data = future.result.data
            kube_upgrade_obj = nfvi.objects.v1.KubeUpgrade(
                kube_upgrade_data['state'],
                kube_upgrade_data['from_version'],
                kube_upgrade_data['to_version'])

            response['result-data'] = kube_upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason

        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))

        finally:
            callback.send(response)
            callback.close()

    def kube_upgrade_download_images(self, future, callback):
        """
        Start kube upgrade download images
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-upgrade-download-images'

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(sysinv.kube_upgrade_download_images,
                        self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return

            kube_upgrade_data = future.result.data
            kube_upgrade_obj = nfvi.objects.v1.KubeUpgrade(
                kube_upgrade_data['state'],
                kube_upgrade_data['from_version'],
                kube_upgrade_data['to_version'])

            response['result-data'] = kube_upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))

        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))

        finally:
            callback.send(response)
            callback.close()

    def kube_pre_application_update(self, future, callback):
        """
        Start kube pre application update
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-pre-application-update'

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(sysinv.kube_pre_application_update,
                        self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return

            kube_upgrade_data = future.result.data
            kube_upgrade_obj = nfvi.objects.v1.KubeUpgrade(
                kube_upgrade_data['state'],
                kube_upgrade_data['from_version'],
                kube_upgrade_data['to_version'])

            response['result-data'] = kube_upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))

        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))

        finally:
            callback.send(response)
            callback.close()

    def kube_post_application_update(self, future, callback):
        """
        Start kube post application update
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-post-application-update'

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(sysinv.kube_post_application_update,
                        self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return

            kube_upgrade_data = future.result.data
            kube_upgrade_obj = nfvi.objects.v1.KubeUpgrade(
                kube_upgrade_data['state'],
                kube_upgrade_data['from_version'],
                kube_upgrade_data['to_version'])

            response['result-data'] = kube_upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))

        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))

        finally:
            callback.send(response)
            callback.close()

    def kube_upgrade_networking(self, future, callback):
        """
        Start kube upgrade networking
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-upgrade-networking'

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(sysinv.kube_upgrade_networking, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return

            kube_upgrade_data = future.result.data
            kube_upgrade_obj = nfvi.objects.v1.KubeUpgrade(
                kube_upgrade_data['state'],
                kube_upgrade_data['from_version'],
                kube_upgrade_data['to_version'])

            response['result-data'] = kube_upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))

        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))

        finally:
            callback.send(response)
            callback.close()

    def kube_upgrade_storage(self, future, callback):
        """
        Start kube upgrade storage
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-upgrade-storage'

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(sysinv.kube_upgrade_storage, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("%s did not complete." % action_type)
                return

            kube_upgrade_data = future.result.data
            kube_upgrade_obj = nfvi.objects.v1.KubeUpgrade(
                kube_upgrade_data['state'],
                kube_upgrade_data['from_version'],
                kube_upgrade_data['to_version'])

            response['result-data'] = kube_upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))

        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))

        finally:
            callback.send(response)
            callback.close()

    def kube_upgrade_start(self, future, to_version, force, alarm_ignore_list,
                           callback):
        """
        Start a kube upgrade
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''
        action_type = 'kube-upgrade-start'

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(sysinv.kube_upgrade_start,
                        self._platform_token,
                        to_version,
                        force=force,
                        alarm_ignore_list=alarm_ignore_list)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("SysInv kube-upgrade-start did not complete.")
                response['reason'] = "did not complete."
                return

            future.work(sysinv.get_kube_upgrade, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("SysInv get-kube-upgrade did not complete.")
                response['reason'] = "did not complete."
                return

            kube_upgrade_data_list = future.result.data['kube_upgrades']
            kube_upgrade_obj = \
                self._extract_kube_upgrade(kube_upgrade_data_list)
            response['result-data'] = kube_upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught API exception while trying %s. error=%s"
                               % (action_type, e))
            response['reason'] = e.http_response_reason

        except Exception as e:
            DLOG.exception("Caught exception while trying %s. error=%s"
                           % (action_type, e))

        finally:
            callback.send(response)
            callback.close()

    def get_upgrade(self, future, release, callback):
        """
        Get information about the software deploy from the plugin
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(usm.sw_deploy_get_release, self._platform_token, release)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("USM software deploy get release did not complete.")
                return

            release_data = future.result.data
            release_info = release_data["metadata"].get(release, None)

            future.work(usm.sw_deploy_host_list, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("USM software deploy host list did not complete.")
                return

            hosts_info_data = future.result.data

            upgrade_obj = nfvi.objects.v1.Upgrade(
                release,
                release_info,
                hosts_info_data["data"],
            )

            response['result-data'] = upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to get upgrade "
                               "info, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to get upgrade info, "
                           "error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def sw_deploy_precheck(self, future, release, callback):
        """
        Precheck a USM software deploy
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(usm.sw_deploy_precheck, self._platform_token, release)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("USM software deploy precheck did not complete.")
                return

            upgrade_obj = nfvi.objects.v1.Upgrade(
                release,
                None,
                None)

            response['result-data'] = upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to precheck "
                               "USM software deploy, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to precheck USM software deploy, "
                           "error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def upgrade_start(self, future, release, callback):
        """
        Start a USM software deploy
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            upgrade_data = future.result.data
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(usm.sw_deploy_start, self._platform_token, release)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("USM software deploy start did not complete.")
                return

            upgrade_obj = nfvi.objects.v1.Upgrade(
                release,
                upgrade_data,
                None)

            response['result-data'] = upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to start "
                               "USM software deploy, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to start USM software deploy, "
                           "error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def upgrade_activate(self, future, release, callback):
        """
        Activate a USM software deployement
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(usm.sw_deploy_activate, self._platform_token, release)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("USM software deploy activate did not complete.")
                return

            upgrade_data = future.result.data
            upgrade_obj = nfvi.objects.v1.Upgrade(
                release,
                upgrade_data,
                None)

            response['result-data'] = upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to activate "
                               "USM software deploy, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to activate USM software deploy, "
                           "error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def upgrade_complete(self, future, release, callback):
        """
        Complete a USM software deployement
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(usm.sw_deploy_complete, self._platform_token, release)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("USM software deploy complete did not complete.")
                return

            upgrade_data = future.result.data
            upgrade_obj = nfvi.objects.v1.Upgrade(
                release,
                upgrade_data,
                None)

            response['result-data'] = upgrade_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to complete "
                               "USM software deploy, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to complete USM software deploy, "
                           "error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def delete_host_services(self, future, host_uuid, host_name,
                             host_personality, callback):
        """
        Delete Host Services, notifies kubernetes client to delete services
        for a host.
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._host_supports_kubernetes(host_personality):
                response['reason'] = 'failed to delete kubernetes services'

                # Send the delete request to kubernetes.
                future.work(kubernetes_client.delete_node, host_name)
                future.result = (yield)

                if not future.result.is_complete():
                    DLOG.error("Kubernetes delete_node failed, operation "
                               "did not complete, host_uuid=%s, host_name=%s."
                               % (host_uuid, host_name))
                    return

            response['completed'] = True
            response['reason'] = ''

        except Exception as e:
            DLOG.exception("Caught exception while trying to delete %s "
                           "kubernetes host services, error=%s."
                           % (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def enable_host_services(self, future, host_uuid, host_name,
                             host_personality, callback):
        """
        Enable Host Services, notify kubernetes client to enable services
        for a host.
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._host_supports_kubernetes(host_personality):
                response['reason'] = 'failed to enable kubernetes services'

                # To enable kubernetes we remove the NoExecute taint from the
                # node. This allows new pods to be scheduled on the node.
                future.work(kubernetes_client.untaint_node,
                            host_name, "NoExecute", "services")
                future.result = (yield)

                if future.result.is_complete():
                    DLOG.info("Taint services=disabled:NoExecute successfully "
                              "removed from host, host_uuid=%s, host_name=%s."
                               % (host_uuid, host_name))
                else:
                    DLOG.error("Kubernetes untaint_node failed, operation "
                               "did not complete, host_uuid=%s, host_name=%s."
                               % (host_uuid, host_name))
                    return

            response['completed'] = True
            response['reason'] = ''

        except Exception as e:
            DLOG.exception("Caught exception while trying to enable %s "
                           "kubernetes host services, error=%s."
                           % (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def disable_host_services(self, future, host_uuid,
                              host_name, host_personality, host_offline,
                              callback):
        """
        Disable Host Services, notifies kubernetes client to disable services
        for a host.
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._host_supports_kubernetes(host_personality):
                response['reason'] = 'failed to disable kubernetes services'

                # To disable kubernetes we add the NoExecute taint to the
                # node. This removes pods that can be scheduled elsewhere
                # and prevents new pods from scheduling on the node.
                future.work(kubernetes_client.taint_node,
                            host_name, "NoExecute", "services", "disabled")

                future.result = (yield)

                if future.result.is_complete():
                    DLOG.info("Taint services=disabled:NoExecute successfully "
                              "added to host, host_uuid=%s, host_name=%s."
                               % (host_uuid, host_name))
                else:
                    DLOG.error("Kubernetes taint_node failed, operation "
                               "did not complete, host_uuid=%s, host_name=%s."
                               % (host_uuid, host_name))
                    return

                if host_offline:
                    # If the disabled node is offline, we also mark all
                    # the pods on the node as not ready. This will ensure
                    # kubernetes takes action immediately (e.g. to disable
                    # endpoints associated with the pods) instead of waiting
                    # for a grace period to determine the node is unavailable.
                    future.work(kubernetes_client.mark_all_pods_not_ready,
                                host_name, "NodeOffline")

                    future.result = (yield)

                    if not future.result.is_complete():
                        DLOG.error("Kubernetes mark_all_pods_not_ready failed, "
                                   "operation did not complete, host_uuid=%s, "
                                   "host_name=%s."
                                   % (host_uuid, host_name))
                        return

            response['completed'] = True
            response['reason'] = ''

        except Exception as e:
            DLOG.exception("Caught exception while trying to disable %s "
                           "kubernetes host services, error=%s."
                           % (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def notify_host_services_enabled(self, future, host_uuid, host_name,
                                     callback):
        """
        Notify host services are now enabled
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.notify_host_services_enabled,
                        self._platform_token,
                        host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            host_data = future.result.data

            future.work(mtc.host_query, self._platform_token,
                        host_data['uuid'], host_data['hostname'])
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Query-Host-State did not complete, host=%s."
                           % host_data['hostname'])
                return

            state = future.result.data['state']

            host_uuid = host_data['uuid']
            host_name = host_data['hostname']
            host_personality = host_data['personality']
            host_sub_functions = host_data.get('subfunctions', [])
            host_admin_state = state['administrative']
            host_oper_state = state['operational']
            host_avail_status = state['availability']
            sub_function_oper_state = state.get('subfunction_oper', None)
            sub_function_avail_status = state.get('subfunction_avail', None)
            data_port_oper_state = state.get('data_ports_oper', None)
            data_port_avail_status = state.get('data_ports_avail', None)
            host_action = (host_data.get('ihost_action') or "").rstrip('-')
            software_load = host_data['software_load']
            target_load = host_data['target_load']
            device_image_update = host_data['device_image_update']

            admin_state, oper_state, avail_status, nfvi_data \
                = host_state(host_uuid, host_name, host_personality,
                             host_sub_functions, host_admin_state,
                             host_oper_state, host_avail_status,
                             sub_function_oper_state,
                             sub_function_avail_status,
                             data_port_oper_state,
                             data_port_avail_status,
                             self._data_port_fault_handling_enabled)

            future.work(sysinv.get_host_labels, self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Get-Host-Labels did not complete, host=%s."
                           % host_name)
                return

            host_label_list = future.result.data['labels']

            openstack_compute, openstack_control, remote_storage = \
                self._get_host_labels(host_label_list)

            host_obj = nfvi.objects.v1.Host(host_uuid, host_name,
                                            host_sub_functions,
                                            admin_state, oper_state,
                                            avail_status,
                                            host_action,
                                            host_data['uptime'],
                                            software_load,
                                            target_load,
                                            device_image_update,
                                            openstack_compute,
                                            openstack_control,
                                            remote_storage,
                                            nfvi_data)

            response['result-data'] = host_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to notify "
                               "host services enabled, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to notify "
                           "host services are enabled, error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def notify_host_services_disabled(self, future, host_uuid, host_name,
                                      callback):
        """
        Notify host services are now disabled
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.notify_host_services_disabled,
                        self._platform_token,
                        host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            host_data = future.result.data

            future.work(mtc.host_query, self._platform_token,
                        host_data['uuid'], host_data['hostname'])
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Query-Host-State did not complete, host=%s."
                           % host_data['hostname'])
                return

            state = future.result.data['state']

            host_uuid = host_data['uuid']
            host_name = host_data['hostname']
            host_personality = host_data['personality']
            host_sub_functions = host_data.get('subfunctions', [])
            host_admin_state = state['administrative']
            host_oper_state = state['operational']
            host_avail_status = state['availability']
            sub_function_oper_state = state.get('subfunction_oper', None)
            sub_function_avail_status = state.get('subfunction_avail', None)
            data_port_oper_state = state.get('data_ports_oper', None)
            data_port_avail_status = state.get('data_ports_avail', None)
            host_action = (host_data.get('ihost_action') or "").rstrip('-')
            software_load = host_data['software_load']
            target_load = host_data['target_load']
            device_image_update = host_data['device_image_update']

            admin_state, oper_state, avail_status, nfvi_data \
                = host_state(host_uuid, host_name, host_personality,
                             host_sub_functions, host_admin_state,
                             host_oper_state, host_avail_status,
                             sub_function_oper_state,
                             sub_function_avail_status,
                             data_port_oper_state,
                             data_port_avail_status,
                             self._data_port_fault_handling_enabled)

            future.work(sysinv.get_host_labels, self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Get-Host-Labels did not complete, host=%s."
                           % host_name)
                return

            host_label_list = future.result.data['labels']

            openstack_compute, openstack_control, remote_storage = \
                self._get_host_labels(host_label_list)

            host_obj = nfvi.objects.v1.Host(host_uuid, host_name,
                                            host_sub_functions,
                                            admin_state, oper_state,
                                            avail_status,
                                            host_action,
                                            host_data['uptime'],
                                            software_load,
                                            target_load,
                                            device_image_update,
                                            openstack_compute,
                                            openstack_control,
                                            remote_storage,
                                            nfvi_data)

            response['result-data'] = host_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to notify "
                               "host services disabled, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to notify "
                           "host services are disabled, error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def notify_host_services_disable_extend(self, future, host_uuid, host_name,
                                            callback):
        """
        Notify host services disable timeout needs to be extended
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.notify_host_services_disable_extend,
                        self._platform_token,
                        host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            host_data = future.result.data

            future.work(mtc.host_query, self._platform_token,
                        host_data['uuid'], host_data['hostname'])
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Query-Host-State did not complete, host=%s."
                           % host_data['hostname'])
                return

            state = future.result.data['state']

            host_uuid = host_data['uuid']
            host_name = host_data['hostname']
            host_personality = host_data['personality']
            host_sub_functions = host_data.get('subfunctions', [])
            host_admin_state = state['administrative']
            host_oper_state = state['operational']
            host_avail_status = state['availability']
            sub_function_oper_state = state.get('subfunction_oper', None)
            sub_function_avail_status = state.get('subfunction_avail', None)
            data_port_oper_state = state.get('data_ports_oper', None)
            data_port_avail_status = state.get('data_ports_avail', None)
            software_load = host_data['software_load']
            target_load = host_data['target_load']
            device_image_update = host_data['device_image_update']

            admin_state, oper_state, avail_status, nfvi_data \
                = host_state(host_uuid, host_name, host_personality,
                             host_sub_functions, host_admin_state,
                             host_oper_state, host_avail_status,
                             sub_function_oper_state,
                             sub_function_avail_status,
                             data_port_oper_state,
                             data_port_avail_status,
                             self._data_port_fault_handling_enabled)

            future.work(sysinv.get_host_labels, self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Get-Host-Labels did not complete, host=%s."
                           % host_name)
                return

            host_label_list = future.result.data['labels']

            openstack_compute, openstack_control, remote_storage = \
                self._get_host_labels(host_label_list)

            host_obj = nfvi.objects.v1.Host(host_uuid, host_name,
                                            host_sub_functions,
                                            admin_state, oper_state,
                                            avail_status,
                                            host_data['ihost_action'],
                                            host_data['uptime'],
                                            software_load,
                                            target_load,
                                            device_image_update,
                                            openstack_compute,
                                            openstack_control,
                                            remote_storage,
                                            nfvi_data)

            response['result-data'] = host_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to notify "
                               "host services disable extend, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to notify "
                           "host services disable extend, error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def notify_host_services_disable_failed(self, future, host_uuid, host_name,
                                            reason, callback):
        """
        Notify host services disable failed
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.notify_host_services_disable_failed,
                        self._platform_token, host_uuid, reason)
            future.result = (yield)

            if not future.result.is_complete():
                return

            host_data = future.result.data

            future.work(mtc.host_query, self._platform_token,
                        host_data['uuid'], host_data['hostname'])
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Query-Host-State did not complete, host=%s."
                           % host_data['hostname'])
                return

            state = future.result.data['state']

            host_uuid = host_data['uuid']
            host_name = host_data['hostname']
            host_personality = host_data['personality']
            host_sub_functions = host_data.get('subfunctions', [])
            host_admin_state = state['administrative']
            host_oper_state = state['operational']
            host_avail_status = state['availability']
            sub_function_oper_state = state.get('subfunction_oper', None)
            sub_function_avail_status = state.get('subfunction_avail', None)
            data_port_oper_state = state.get('data_ports_oper', None)
            data_port_avail_status = state.get('data_ports_avail', None)
            software_load = host_data['software_load']
            target_load = host_data['target_load']
            device_image_update = host_data['device_image_update']

            admin_state, oper_state, avail_status, nfvi_data \
                = host_state(host_uuid, host_name, host_personality,
                             host_sub_functions, host_admin_state,
                             host_oper_state, host_avail_status,
                             sub_function_oper_state,
                             sub_function_avail_status,
                             data_port_oper_state,
                             data_port_avail_status,
                             self._data_port_fault_handling_enabled)

            future.work(sysinv.get_host_labels, self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Get-Host-Labels did not complete, host=%s."
                           % host_name)
                return

            host_label_list = future.result.data['labels']

            openstack_compute, openstack_control, remote_storage = \
                self._get_host_labels(host_label_list)

            host_obj = nfvi.objects.v1.Host(host_uuid, host_name,
                                            host_sub_functions,
                                            admin_state, oper_state,
                                            avail_status,
                                            host_data['ihost_action'],
                                            host_data['uptime'],
                                            software_load,
                                            target_load,
                                            device_image_update,
                                            openstack_compute,
                                            openstack_control,
                                            remote_storage,
                                            nfvi_data)

            response['result-data'] = host_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to notify "
                               "host services disable failed, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to notify "
                           "host services disable failed, error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def notify_host_services_deleted(self, future, host_uuid, host_name,
                                     callback):
        """
        Notify host services have been deleted
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.notify_host_services_deleted,
                        self._platform_token,
                        host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to notify "
                               "host services deleted, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to notify "
                           "host services are deleted, error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def notify_host_services_delete_failed(self, future, host_uuid, host_name,
                                           reason, callback):
        """
        Notify host services delete failed
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.notify_host_services_delete_failed,
                        self._platform_token, host_uuid, reason)
            future.result = (yield)

            if not future.result.is_complete():
                return

            host_data = future.result.data

            future.work(mtc.host_query, self._platform_token,
                        host_data['uuid'], host_data['hostname'])
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Query-Host-State did not complete, host=%s."
                           % host_data['hostname'])
                return

            state = future.result.data['state']

            host_uuid = host_data['uuid']
            host_name = host_data['hostname']
            host_personality = host_data['personality']
            host_sub_functions = host_data.get('subfunctions', [])
            host_admin_state = state['administrative']
            host_oper_state = state['operational']
            host_avail_status = state['availability']
            sub_function_oper_state = state.get('subfunction_oper', None)
            sub_function_avail_status = state.get('subfunction_avail', None)
            data_port_oper_state = state.get('data_ports_oper', None)
            data_port_avail_status = state.get('data_ports_avail', None)
            software_load = host_data['software_load']
            target_load = host_data['target_load']
            device_image_update = host_data['device_image_update']

            admin_state, oper_state, avail_status, nfvi_data \
                = host_state(host_uuid, host_name, host_personality,
                             host_sub_functions, host_admin_state,
                             host_oper_state, host_avail_status,
                             sub_function_oper_state,
                             sub_function_avail_status,
                             data_port_oper_state,
                             data_port_avail_status,
                             self._data_port_fault_handling_enabled)

            future.work(sysinv.get_host_labels, self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Get-Host-Labels did not complete, host=%s."
                           % host_name)
                return

            host_label_list = future.result.data['labels']

            openstack_compute, openstack_control, remote_storage = \
                self._get_host_labels(host_label_list)

            host_obj = nfvi.objects.v1.Host(host_uuid, host_name,
                                            host_sub_functions,
                                            admin_state, oper_state,
                                            avail_status,
                                            host_data['ihost_action'],
                                            host_data['uptime'],
                                            software_load,
                                            target_load,
                                            device_image_update,
                                            openstack_compute,
                                            openstack_control,
                                            remote_storage,
                                            nfvi_data)

            response['result-data'] = host_obj
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to notify "
                               "host services delete failed, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to notify "
                           "host services delete failed, error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def notify_host_failed(self, future, host_uuid, host_name,
                           host_personality, callback):
        """
        Notify host failed
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            # Only applies to worker hosts
            if not self._host_supports_nova_compute(host_personality):
                response['completed'] = True
                return

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s, host_name=%s." % (host_uuid,
                                                                host_name))
                    return

                self._platform_token = future.result.data

            # Send a host failed notification to maintenance
            future.work(mtc.notify_host_severity, self._platform_token,
                        host_uuid, host_name, mtc.HOST_SEVERITY.FAILED)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Host failed notification, operation did not "
                           "complete, host_uuid=%s, host_name=%s."
                           % (host_uuid, host_name))
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to notify "
                               "host failed, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to notify "
                           "host that a host is failed, error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def kube_host_cordon(self, future, host_uuid, host_name, force, callback):
        """
        Cordon a host
        """

        # ignoring the force argument for now
        response = dict()
        response['completed'] = False
        response['host_uuid'] = host_uuid
        response['host_name'] = host_name
        response['reason'] = ''

        action_type = 'kube-host-cordon'
        sysinv_method = sysinv.kube_host_cordon
        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            # cordon wants a hostname and not a host_uuid
            future.work(sysinv_method, self._platform_token, host_name, force)
            future.result = (yield)

            if not future.result.is_complete():
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to %s "
                               "a host %s, error=%s." % (action_type, host_name, e))
                response['reason'] = e.http_response_reason

        except Exception as e:
            DLOG.exception("Caught exception while trying to %s a "
                           "host %s, error=%s." % (action_type, host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def kube_host_uncordon(self, future, host_uuid, host_name, force, callback):
        """
        Uncordon a host
        """
        response = dict()
        response['completed'] = False
        response['host_uuid'] = host_uuid
        response['host_name'] = host_name
        response['reason'] = ''

        action_type = 'kube-host-uncordon'
        sysinv_method = sysinv.kube_host_uncordon
        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            # uncordon wants a hostname and not a host_uuid
            future.work(sysinv_method, self._platform_token, host_name, force)
            future.result = (yield)

            if not future.result.is_complete():
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to %s "
                               "a host %s, error=%s." % (action_type, host_name, e))
                response['reason'] = e.http_response_reason

        except Exception as e:
            DLOG.exception("Caught exception while trying to %s a "
                           "host %s, error=%s." % (action_type, host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def lock_host(self, future, host_uuid, host_name, callback):
        """
        Lock a host
        """
        response = dict()
        response['completed'] = False
        response['host_uuid'] = host_uuid
        response['host_name'] = host_name
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.lock_host, self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to lock "
                               "a host %s, error=%s." % (host_name, e))
                response['reason'] = e.http_response_reason

        except Exception as e:
            DLOG.exception("Caught exception while trying to lock a "
                           "host %s, error=%s." % (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def unlock_host(self, future, host_uuid, host_name, callback):
        """
        Unlock a host
        """
        response = dict()
        response['completed'] = False
        response['host_uuid'] = host_uuid
        response['host_name'] = host_name
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.unlock_host, self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to unlock "
                               "a host %s, error=%s." % (host_name, e))
                response['reason'] = e.http_response_reason

        except Exception as e:
            DLOG.exception("Caught exception while trying to unlock a "
                           "host %s, error=%s." % (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def reboot_host(self, future, host_uuid, host_name, callback):
        """
        Reboot a host
        """
        response = dict()
        response['completed'] = False
        response['host_uuid'] = host_uuid
        response['host_name'] = host_name
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.reboot_host, self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to reboot "
                               "a host %s, error=%s." % (host_name, e))
                response['reason'] = e.http_response_reason

        except Exception as e:
            DLOG.exception("Caught exception while trying to reboot a "
                           "host %s, error=%s." % (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def upgrade_host(self, future, host_uuid, host_name, callback):
        """
        Upgrade a host
        """
        response = dict()
        response['completed'] = False
        response['host_uuid'] = host_uuid
        response['host_name'] = host_name
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(usm.sw_deploy_execute, self._platform_token, host_name)
            future.result = (yield)

            if not future.result.is_complete():
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to upgrade "
                               "a host %s, error=%s." % (host_name, e))
                response['reason'] = e.http_response_reason

        except Exception as e:
            DLOG.exception("Caught exception while trying to upgrade a "
                           "host %s, error=%s." % (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def swact_from_host(self, future, host_uuid, host_name, callback):
        """
        Swact from a host
        """
        response = dict()
        response['completed'] = False
        response['host_uuid'] = host_uuid
        response['host_name'] = host_name
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete, "
                               "host_uuid=%s." % host_uuid)
                    return

                self._platform_token = future.result.data

            future.work(sysinv.swact_from_host, self._platform_token, host_uuid)
            future.result = (yield)

            if not future.result.is_complete():
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to swact "
                               "from a host %s, error=%s." % (host_name, e))
                response['reason'] = e.http_response_reason

        except Exception as e:
            DLOG.exception("Caught exception while trying to swact from a "
                           "host %s, error=%s." % (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def get_alarms(self, future, callback):
        """
        Get alarms
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(fm.get_alarms, self._platform_token)
            future.result = (yield)

            if not future.result.is_complete():
                return

            alarms = list()

            for alarm_data in future.result.data['alarms']:
                alarm = nfvi.objects.v1.Alarm(
                    alarm_data['uuid'], alarm_data['alarm_id'],
                    alarm_data['entity_instance_id'], alarm_data['severity'],
                    alarm_data['reason_text'], alarm_data['timestamp'],
                    alarm_data['mgmt_affecting'])
                alarms.append(alarm)

            response['result-data'] = alarms
            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to get alarms, "
                               "error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to get alarms, "
                           "error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def get_logs(self, future, start_period, end_period, callback):
        """
        Get logs
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(fm.get_logs, self._platform_token, start_period,
                        end_period)
            future.result = (yield)

            if not future.result.is_complete():
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to get logs, "
                               "error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to get logs, "
                           "error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def get_alarm_history(self, future, start_period, end_period, callback):
        """
        Get alarm history
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._platform_token is None or \
                    self._platform_token.is_expired():
                future.work(openstack.get_token, self._platform_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._platform_token = future.result.data

            future.work(fm.get_alarm_history, self._platform_token,
                        start_period, end_period)
            future.result = (yield)

            if not future.result.is_complete():
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._platform_token is not None:
                    self._platform_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to get alarm "
                               "history, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to get alarm "
                           "history, error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def get_terminating_pods(self, future, host_name, callback):
        """
        Get list of terminating pods on a host
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            future.work(kubernetes_client.get_terminating_pods, host_name)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Kubernetes get_terminating_pods failed, operation "
                           "did not complete, host_name=%s" % host_name)
                return

            response['result-data'] = future.result.data
            response['completed'] = True

        except Exception as e:
            DLOG.exception("Caught exception while trying to get "
                           "terminating pods on %s, error=%s." % (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def get_deployment_host(self, future, host_name, callback):
        """
        Get a host resource from the deployment namespace space
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            future.work(kubernetes_client.get_deployment_host, host_name)
            future.result = (yield)

            if not future.result.is_complete():
                DLOG.error("Kubernetes get_deployment_host failed, operation "
                           "did not complete, host_name=%s" % host_name)
                self.set_response_error(response, "Kubernetes get-deployment-host")
                return

            response['result-data'] = future.result.data
            response['completed'] = True

        except Exception as e:
            DLOG.exception("Caught exception while trying to get "
                           "deployment hosts: %s, error=%s." % (host_name, e))

        finally:
            callback.send(response)
            callback.close()

    def list_deployment_hosts(self, future, callback):
        """
        List a hosts resource from the deployment namespace space
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            future.work(kubernetes_client.list_deployment_hosts)
            future.result = (yield)

            if not future.result.is_complete() or future.result.data is None:
                DLOG.error("Kubernetes list_deployment_hosts failed, operation "
                           "did not complete.")
                self.set_response_error(response, "Kubernetes list-deployment-hosts")
                return

            hosts = list()
            for host_data in future.result.data:
                host = nfvi.objects.v1.HostSystemConfigUpdate(
                    host_data['name'], host_data['unlock_request'])
                hosts.append(host)

            response['result-data'] = hosts
            response['completed'] = True

        except Exception as e:
            DLOG.exception("Caught exception while trying to list "
                           "deployment hosts, error=%s." % (e))

        finally:
            callback.send(response)
            callback.close()

    def get_system_config_unlock_request(self, future, host_names, callback):
        """
        Get unlock request from host resource status
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))
            result = list()
            for host_name in host_names:
                future.work(kubernetes_client.get_deployment_host, host_name)
                future.result = (yield)

                if not future.result.is_complete():
                    DLOG.error("Cannot get resource of host: %s from deployment "
                               "namespace." % host_name)
                    self.set_response_error(response, "Kubernetes get-deployment-host")
                    return

                if future.result.data['unlock_request'] != 'unlock_required':
                    # The host is not ready for unlock, do not update the reason
                    # as the the transitional status is expected.
                    DLOG.debug("Host: %s is not ready for unlock." % host_name)
                    return

                host_resource = nfvi.objects.v1.HostSystemConfigUpdate(
                    future.result.data['name'],
                    future.result.data['unlock_request']
                )
                result.append(host_resource)

            response['completed'] = True
            response['result-data'] = result

        except Exception as e:
            DLOG.exception("Caught exception while trying to check the unlock "
                           "requst from kubernetes deployment namespace %s, "
                           "error=%s." % (host_name, e))
        finally:
            callback.send(response)
            callback.close()

    def sw_update_rest_api_get_handler(self, request_dispatch):
        """
        Software update Rest-API GET handler callback
        """

        DLOG.verbose("Sw-update rest-api get path: %s." % request_dispatch.path)

        http_payload = None
        http_response = httplib.OK

        for callback in self._sw_update_get_callbacks:
            sw_update_type, in_progress = callback()

            http_payload = dict()
            http_payload['status'] = 'success'
            http_payload['sw-update-type'] = sw_update_type
            http_payload['in-progress'] = in_progress

        request_dispatch.send_response(http_response)

        if http_payload is not None:
            request_dispatch.send_header('Content-Type', 'application/json')
            request_dispatch.end_headers()
            request_dispatch.wfile.write(json.dumps(http_payload).encode())
        request_dispatch.done()

    def host_rest_api_get_handler(self, request_dispatch):
        """
        Host Rest-API GET handler callback
        """
        content_len = int(request_dispatch.headers.get('content-length', 0))
        content = request_dispatch.rfile.read(content_len)
        http_payload = None
        http_response = httplib.OK

        if content:
            host_data = json.loads(content)
            host_uuid = host_data.get('uuid', None)
            host_name = host_data.get('hostname', None)

            if host_uuid is not None and host_name is not None:
                for callback in self._host_get_callbacks:
                    success, instances, instances_failed, instances_stopped \
                        = callback(host_uuid, host_name)
                    if success:
                        http_payload = dict()
                        http_payload['status'] = "success"
                        http_payload['instances'] = instances
                        http_payload['instances-failed'] = instances_failed
                        http_payload['instances-stopped'] = instances_stopped
                    else:
                        http_response = httplib.BAD_REQUEST
            else:
                DLOG.error("Invalid host get data received, host_uuid=%s, "
                           "host_name=%s." % (host_uuid, host_name))
                http_response = httplib.BAD_REQUEST
        else:
            http_response = httplib.NO_CONTENT

        DLOG.debug("Host rest-api get path: %s." % request_dispatch.path)
        request_dispatch.send_response(http_response)

        if http_payload is not None:
            request_dispatch.send_header('Content-Type', 'application/json')
            request_dispatch.end_headers()
            request_dispatch.wfile.write(json.dumps(http_payload).encode())
        request_dispatch.done()

    def host_rest_api_patch_handler(self, request_dispatch):
        """
        Host Rest-API PATCH handler callback
        """
        content_len = int(request_dispatch.headers.get('content-length', 0))
        content = request_dispatch.rfile.read(content_len)
        http_payload = None
        http_response = httplib.OK

        if content:
            host_data = json.loads(content)
            host_uuid = host_data.get('uuid', None)
            host_name = host_data.get('hostname', None)
            action = host_data.get('action', None)
            state_change = host_data.get('state-change', None)
            upgrade = host_data.get('upgrade', None)

            if action is not None:
                do_action = None
                if action == "unlock":
                    do_action = nfvi.objects.v1.HOST_ACTION.UNLOCK
                elif action == "lock":
                    do_action = nfvi.objects.v1.HOST_ACTION.LOCK
                elif action == "force-lock":
                    do_action = nfvi.objects.v1.HOST_ACTION.LOCK_FORCE

                if host_uuid is not None and host_name is not None \
                        and do_action is not None:
                    for callback in self._host_action_callbacks:
                        success = callback(host_uuid, host_name, do_action)
                        if not success:
                            http_response = httplib.BAD_REQUEST
                else:
                    DLOG.error("Invalid host action data received, "
                               "host_uuid=%s, host_name=%s, action=%s."
                               % (host_uuid, host_name, action))
                    http_response = httplib.BAD_REQUEST

            elif state_change is not None:
                # State change notification from maintenance
                if host_uuid is not None and host_name is not None:

                    host_personality = host_data['personality']
                    host_sub_functions = host_data.get('subfunctions', [])
                    host_admin_state = state_change['administrative']
                    host_oper_state = state_change['operational']
                    host_avail_status = state_change['availability']
                    sub_function_oper_state = state_change.get(
                        'subfunction_oper', None)
                    sub_function_avail_status = state_change.get(
                        'subfunction_avail', None)
                    data_port_oper_state = state_change.get(
                        'data_ports_oper', None)
                    data_port_avail_status = state_change.get(
                        'data_ports_avail', None)

                    admin_state, oper_state, avail_status, nfvi_data \
                        = host_state(host_uuid, host_name, host_personality,
                                     host_sub_functions, host_admin_state,
                                     host_oper_state, host_avail_status,
                                     sub_function_oper_state,
                                     sub_function_avail_status,
                                     data_port_oper_state,
                                     data_port_avail_status,
                                     self._data_port_fault_handling_enabled)

                    for callback in self._host_state_change_callbacks:
                        success = callback(host_uuid, host_name, admin_state,
                                           oper_state, avail_status, nfvi_data)
                        if not success:
                            http_response = httplib.BAD_REQUEST

                    if httplib.OK == http_response:
                        http_payload = dict()
                        http_payload['status'] = "success"

                else:
                    DLOG.error("Invalid host state-change data received, "
                               "host_uuid=%s, host_name=%s, state_change=%s."
                               % (host_uuid, host_name, state_change))
                    http_response = httplib.BAD_REQUEST

            elif upgrade is not None:

                if host_uuid is not None and host_name is not None:

                    upgrade_inprogress = upgrade['inprogress']
                    recover_instances = upgrade['recover-instances']

                    for callback in self._host_upgrade_callbacks:
                        success = callback(host_uuid, host_name, upgrade_inprogress,
                                           recover_instances)
                        if not success:
                            http_response = httplib.BAD_REQUEST

                    if httplib.OK == http_response:
                        http_payload = dict()
                        http_payload['status'] = "success"

                else:
                    DLOG.error("Invalid host upgrade data received, "
                               "host_uuid=%s, host_name=%s, upgrade=%s."
                               % (host_uuid, host_name, upgrade))
                    http_response = httplib.BAD_REQUEST

            elif host_uuid is not None and host_name is not None:

                for callback in self._host_update_callbacks:
                    success = callback(host_uuid, host_name)
                    if not success:
                        http_response = httplib.BAD_REQUEST

                if httplib.OK == http_response:
                    http_payload = dict()
                    http_payload['status'] = "success"

            else:
                DLOG.error("Invalid host patch data received, host_data=%s."
                           % host_data)
                http_response = httplib.BAD_REQUEST
        else:
            http_response = httplib.NO_CONTENT

        DLOG.debug("Host rest-api patch path: %s." % request_dispatch.path)
        request_dispatch.send_response(http_response)

        if http_payload is not None:
            request_dispatch.send_header('Content-Type', 'application/json')
            request_dispatch.end_headers()
            request_dispatch.wfile.write(json.dumps(http_payload).encode())
        request_dispatch.done()

    def host_rest_api_post_handler(self, request_dispatch):
        """
        Host Rest-API POST handler callback
        """
        content_len = int(request_dispatch.headers.get('content-length', 0))
        content = request_dispatch.rfile.read(content_len)
        http_response = httplib.OK
        if content:
            host_data = json.loads(content)

            subfunctions = host_data.get('subfunctions', None)

            if host_data['hostname'] is None:
                DLOG.info("Invalid host name received, host_name=%s."
                          % host_data['hostname'])

            elif subfunctions is None:
                DLOG.error("Invalid host subfunctions received, "
                           "host_subfunctions=%s." % subfunctions)

            else:
                for callback in self._host_add_callbacks:
                    success = callback(host_data['uuid'],
                                       host_data['hostname'])
                    if not success:
                        http_response = httplib.BAD_REQUEST
        else:
            http_response = httplib.NO_CONTENT

        DLOG.debug("Host rest-api post path: %s." % request_dispatch.path)
        request_dispatch.send_response(http_response)
        request_dispatch.done()

    def host_rest_api_delete_handler(self, request_dispatch):
        """
        Host Rest-API DELETE handler callback
        """
        content_len = int(request_dispatch.headers.get('content-length', 0))
        content = request_dispatch.rfile.read(content_len)
        http_response = httplib.OK

        if content:
            host_data = json.loads(content)
            host_uuid = host_data.get('uuid', None)
            host_name = host_data.get('hostname', None)
            action = host_data.get('action', "")

            do_action = None
            if action == "delete":
                do_action = nfvi.objects.v1.HOST_ACTION.DELETE
            else:
                http_response = httplib.BAD_REQUEST
                DLOG.error("Host rest-api delete unrecognized action: %s."
                           % do_action)

            if host_name is not None and host_uuid is not None \
                    and do_action is not None:
                for callback in self._host_action_callbacks:
                    success = callback(host_uuid, host_name, do_action)
                    if not success:
                        http_response = httplib.BAD_REQUEST
            else:
                DLOG.error("Invalid host delete data received, host_uuid=%s, "
                           "host_name=%s, action=%s." % (host_uuid, host_name,
                                                         action))
                http_response = httplib.BAD_REQUEST
        else:
            http_response = httplib.NO_CONTENT

        DLOG.debug("Host rest-api delete path: %s." % request_dispatch.path)
        request_dispatch.send_response(http_response)
        request_dispatch.done()

    def host_notification_handler(self, connection, msg):
        """
        Handle notifications from a host
        """
        if msg is not None:
            try:
                notification = json.loads(msg)

                version = notification.get('version', None)
                notify_type = notification.get('notify-type', None)
                notify_data = notification.get('notify-data', None)
                if notify_data is not None:
                    notify_data = json.loads(notify_data)

                if 1 == version:
                    for callback in self._host_notification_callbacks:
                        status = callback(connection.ip, notify_type, notify_data)
                        notification['status'] = status
                        connection.send(json.dumps(notification))
                else:
                    DLOG.error("Unknown version %s received, notification=%s"
                               % (version, notification))

                connection.close()

            except ValueError:
                DLOG.error("Message received is not valid, msg=%s" % msg)
                connection.close()

    def register_host_add_callback(self, callback):
        """
        Register for host add notifications
        """
        self._host_add_callbacks.append(callback)

    def register_host_action_callback(self, callback):
        """
        Register for host action notifications
        """
        self._host_action_callbacks.append(callback)

    def register_host_state_change_callback(self, callback):
        """
        Register for host state change notifications
        """
        self._host_state_change_callbacks.append(callback)

    def register_sw_update_get_callback(self, callback):
        """
        Register for software update get notifications
        """
        self._sw_update_get_callbacks.append(callback)

    def register_host_get_callback(self, callback):
        """
        Register for host get notifications
        """
        self._host_get_callbacks.append(callback)

    def register_host_upgrade_callback(self, callback):
        """
        Register for host upgrade notifications
        """
        self._host_upgrade_callbacks.append(callback)

    def register_host_update_callback(self, callback):
        """
        Register for host update notifications
        """
        self._host_update_callbacks.append(callback)

    def register_host_notification_callback(self, callback):
        """
        Register for host notifications
        """
        self._host_notification_callbacks.append(callback)

    def initialize(self, config_file):
        """
        Initialize the plugin
        """
        config.load(config_file)
        self._platform_directory = openstack.get_directory(
            config, openstack.SERVICE_CATEGORY.PLATFORM)
        self._openstack_directory = openstack.get_directory(
            config, openstack.SERVICE_CATEGORY.OPENSTACK)

        self._rest_api_server = rest_api.rest_api_get_server(
            config.CONF['infrastructure-rest-api']['host'],
            config.CONF['infrastructure-rest-api']['port'])

        data_port_fault_handling_enabled_str = \
            config.CONF['infrastructure-rest-api'].get(
                'data_port_fault_handling_enabled', 'True')

        if data_port_fault_handling_enabled_str in ['True', 'true', 'T', 't',
                                                    'Yes', 'yes', 'Y', 'y', '1']:
            self._data_port_fault_handling_enabled = True
        else:
            self._data_port_fault_handling_enabled = False

        self._rest_api_server.add_handler('GET', '/nfvi-plugins/v1/hosts*',
                                          self.host_rest_api_get_handler)

        self._rest_api_server.add_handler('PATCH', '/nfvi-plugins/v1/hosts*',
                                          self.host_rest_api_patch_handler)

        self._rest_api_server.add_handler('POST', '/nfvi-plugins/v1/hosts*',
                                          self.host_rest_api_post_handler)

        self._rest_api_server.add_handler('DELETE', '/nfvi-plugins/v1/hosts*',
                                          self.host_rest_api_delete_handler)

        self._rest_api_server.add_handler('GET', '/nfvi-plugins/v1/sw-update*',
                                          self.sw_update_rest_api_get_handler)

        auth_key = \
            config.CONF['host-listener'].get(
                'authorization_key', 'NFV Infrastructure Notification')

        self._host_listener = tcp.TCPServer(config.CONF['host-listener']['host'],
                                            config.CONF['host-listener']['port'],
                                            self.host_notification_handler,
                                            max_connections=32, auth_key=auth_key)

    def finalize(self):
        """
        Finalize the plugin
        """
        if self._host_listener is not None:
            self._host_listener.shutdown()
