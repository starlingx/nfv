#
# Copyright (C) 2019 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
from six.moves import http_client as httplib

from nfv_common import debug
from nfv_plugins.nfvi_plugins import config
from nfv_plugins.nfvi_plugins.openstack import exceptions
from nfv_plugins.nfvi_plugins.openstack import fm
from nfv_plugins.nfvi_plugins.openstack.objects import OPENSTACK_SERVICE
from nfv_plugins.nfvi_plugins.openstack import openstack
from nfv_vim import nfvi

DLOG = debug.debug_get_logger('nfv_plugins.nfvi_plugins.fault_mgmt_api')


class NFVIFaultMgmtAPI(nfvi.api.v1.NFVIFaultMgmtAPI):
    """
    NFV Fault Management API Class Definition
    """
    _name = 'Fault-Management-API'
    _version = '1.0.0'
    _provider = 'StarlingX'
    _signature = '2808f351-92bb-482c-b873-66ab232254af'

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

    def __init__(self):
        super(NFVIFaultMgmtAPI, self).__init__()
        self._openstack_token = None
        self._openstack_directory = None

    def get_openstack_alarms(self, future, callback):
        """
        Get alarms
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._openstack_token is None or \
                    self._openstack_token.is_expired():
                future.work(openstack.get_token, self._openstack_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._openstack_token = future.result.data

            future.work(fm.get_alarms, self._openstack_token, OPENSTACK_SERVICE.FM)
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
                if self._openstack_token is not None:
                    self._openstack_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to get alarms, "
                               "error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to get alarms, "
                           "error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def get_openstack_logs(self, future, start_period, end_period, callback):
        """
        Get logs
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._openstack_token is None or \
                    self._openstack_token.is_expired():
                future.work(openstack.get_token, self._openstack_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._openstack_token = future.result.data

            future.work(fm.get_logs, self._openstack_token, start_period,
                        end_period)
            future.result = (yield)

            if not future.result.is_complete():
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._openstack_token is not None:
                    self._openstack_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to get logs, "
                               "error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to get logs, "
                           "error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def get_openstack_alarm_history(self, future, start_period, end_period, callback):
        """
        Get alarm history
        """
        response = dict()
        response['completed'] = False
        response['reason'] = ''

        try:
            future.set_timeouts(config.CONF.get('nfvi-timeouts', None))

            if self._openstack_token is None or \
                    self._openstack_token.is_expired():
                future.work(openstack.get_token, self._openstack_directory)
                future.result = (yield)

                if not future.result.is_complete() or \
                        future.result.data is None:
                    DLOG.error("OpenStack get-token did not complete.")
                    return

                self._openstack_token = future.result.data

            future.work(fm.get_alarm_history, self._openstack_token,
                        start_period, end_period)
            future.result = (yield)

            if not future.result.is_complete():
                return

            response['completed'] = True

        except exceptions.OpenStackRestAPIException as e:
            if httplib.UNAUTHORIZED == e.http_status_code:
                response['error-code'] = nfvi.NFVI_ERROR_CODE.TOKEN_EXPIRED
                if self._openstack_token is not None:
                    self._openstack_token.set_expired()

            else:
                DLOG.exception("Caught exception while trying to get alarm "
                               "history, error=%s." % e)

        except Exception as e:
            DLOG.exception("Caught exception while trying to get alarm "
                           "history, error=%s." % e)

        finally:
            callback.send(response)
            callback.close()

    def initialize(self, config_file):
        """
        Initialize the plugin
        """
        config.load(config_file)
        self._openstack_directory = openstack.get_directory(
            config, openstack.SERVICE_CATEGORY.OPENSTACK)

    def finalize(self):
        """
        Finalize the plugin
        """
        pass
