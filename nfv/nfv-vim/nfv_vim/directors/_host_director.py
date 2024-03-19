#
# Copyright (c) 2015-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import six

from nfv_common import debug
from nfv_common.helpers import coroutine
from nfv_common.helpers import Singleton

from nfv_vim import nfvi
from nfv_vim import objects
from nfv_vim import tables

from nfv_vim.directors._directors_defs import Operation
from nfv_vim.directors._directors_defs import OPERATION_STATE
from nfv_vim.directors._directors_defs import OPERATION_TYPE

DLOG = debug.debug_get_logger('nfv_vim.host_director')

_host_director = None


@six.add_metaclass(Singleton)
class HostDirector(object):
    """
    Host Director
    """

    def __init__(self):
        self._host_operation = None

    @coroutine
    def _nfvi_lock_host_callback(self):
        """
        NFVI Lock Host Callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Lock Host callback response=%s." % response)
        if not response['completed']:
            DLOG.info("Lock of host %s failed, reason=%s."
                      % (response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.LOCK_HOSTS != self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.host_lock_failed(host)

    def _nfvi_lock_host(self, host_uuid, host_name):
        """
        NFVI Lock Host
        """
        nfvi.nfvi_lock_host(host_uuid, host_name, self._nfvi_lock_host_callback())

    @coroutine
    def _nfvi_disable_host_services_callback(self, service):
        """
        NFVI Disable Host Services Callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Disable Host %s Services callback "
                     "response=%s." % (service, response))
        if not response['completed']:
            DLOG.info("Disable of %s services on host %s failed"
                      ", reason=%s."
                      % (service, response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.DISABLE_HOST_SERVICES != \
                    self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.disable_host_services_failed(host)

    def _nfvi_disable_host_services(self, host_uuid, host_name,
                                    host_personality, host_offline, service):
        """
        NFVI Disable Host Services
        """
        if service == objects.HOST_SERVICES.COMPUTE:
            nfvi.nfvi_disable_compute_host_services(
                host_uuid, host_name, host_personality,
                self._nfvi_disable_host_services_callback(
                    objects.HOST_SERVICES.COMPUTE))
        elif service == objects.HOST_SERVICES.GUEST:
            nfvi.nfvi_disable_guest_host_services(
                host_uuid, host_name, host_personality,
                self._nfvi_disable_host_services_callback(
                    objects.HOST_SERVICES.GUEST))
        elif service == objects.HOST_SERVICES.CONTAINER:
            nfvi.nfvi_disable_container_host_services(
                host_uuid, host_name, host_personality, host_offline,
                self._nfvi_disable_host_services_callback(
                    objects.HOST_SERVICES.CONTAINER))
        else:
            DLOG.error("Trying to disable unknown service: %s" % service)

    @coroutine
    def _nfvi_enable_host_services_callback(self, service):
        """
        NFVI Enable Host Services Callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Enable Host %s Services callback "
                     "response=%s." % (service, response))
        if not response['completed']:
            DLOG.info("Enable of %s services on host %s failed, reason=%s."
                      % (service, response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.ENABLE_HOST_SERVICES != \
                    self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name,
                                self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.enable_host_services_failed(host)

    def _nfvi_enable_host_services(self, host_uuid, host_name,
                                   host_personality, service):
        """
        NFVI Enable Host Services
        """
        if service == objects.HOST_SERVICES.COMPUTE:
            nfvi.nfvi_enable_compute_host_services(
                host_uuid, host_name, host_personality,
                self._nfvi_enable_host_services_callback(
                    objects.HOST_SERVICES.COMPUTE))
        elif service == objects.HOST_SERVICES.GUEST:
            nfvi.nfvi_enable_guest_host_services(
                host_uuid, host_name, host_personality,
                self._nfvi_enable_host_services_callback(
                    objects.HOST_SERVICES.GUEST))
        elif service == objects.HOST_SERVICES.CONTAINER:
            nfvi.nfvi_enable_container_host_services(
                host_uuid, host_name, host_personality,
                self._nfvi_enable_host_services_callback(
                    objects.HOST_SERVICES.CONTAINER))
        elif service == objects.HOST_SERVICES.NETWORK:
            nfvi.nfvi_enable_network_host_services(
                host_uuid, host_name, host_personality,
                self._nfvi_enable_host_services_callback(
                    objects.HOST_SERVICES.NETWORK))
        else:
            DLOG.error("Trying to enable unknown service: %s" % service)

    @coroutine
    def _nfvi_unlock_host_callback(self):
        """
        NFVI Unlock Host Callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Unlock Host callback response=%s." % response)
        if not response['completed']:
            DLOG.info("Unlock of host %s failed, reason=%s."
                      % (response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.UNLOCK_HOSTS != self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.host_unlock_failed(host)

    def _nfvi_unlock_host(self, host_uuid, host_name):
        """
        NFVI Unlock Host
        """
        nfvi.nfvi_unlock_host(host_uuid, host_name,
                              self._nfvi_unlock_host_callback())

    @coroutine
    def _nfvi_reboot_host_callback(self):
        """
        NFVI Reboot Host Callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Reboot Host callback response=%s." % response)
        if not response['completed']:
            DLOG.info("Reboot of host %s failed, reason=%s."
                      % (response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.REBOOT_HOSTS != self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.host_reboot_failed(host)

    def _nfvi_reboot_host(self, host_uuid, host_name):
        """
        NFVI Reboot Host
        """
        nfvi.nfvi_reboot_host(host_uuid, host_name,
                              self._nfvi_reboot_host_callback())

    @coroutine
    def _nfvi_upgrade_host_callback(self):
        """
        NFVI Upgrade Host Callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Upgrade Host callback response=%s." % response)
        if not response['completed']:
            DLOG.info("Upgrade of host %s failed, reason=%s."
                      % (response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.UPGRADE_HOSTS != self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.host_upgrade_failed(host)

    def _nfvi_upgrade_host(self, host_uuid, host_name):
        """
        NFVI Upgrade Host
        """
        nfvi.nfvi_upgrade_host(host_uuid, host_name,
                               self._nfvi_upgrade_host_callback())

    @coroutine
    def _nfvi_swact_host_callback(self):
        """
        NFVI Swact Host Callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Swact Host callback response=%s." % response)
        if not response['completed']:
            DLOG.info("Swact of host %s failed, reason=%s."
                      % (response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.SWACT_HOSTS != self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.host_swact_failed(host)

    def _nfvi_swact_host(self, host_uuid, host_name):
        """
        NFVI Swact Host
        """
        nfvi.nfvi_swact_from_host(host_uuid, host_name,
                                  self._nfvi_swact_host_callback())

    @coroutine
    def _nfvi_fw_update_host_callback(self):
        """
        NFVI Firmware Update Host Callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Firmware Update Host callback response=%s." % response)
        if not response['completed']:
            DLOG.info("Firmware Image Update for host %s failed, reason=%s."
                      % (response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.FW_UPDATE_HOSTS != self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.host_fw_update_failed(host)

    def _nfvi_fw_update_host(self, host_uuid, host_name):
        """
        NFVI Firmware Image Update Host
        """
        nfvi.nfvi_host_device_image_update(host_uuid, host_name, self._nfvi_fw_update_host_callback())

    @coroutine
    def _nfvi_fw_update_abort_callback(self):
        """
        NFVI Abort Firmware Update callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Abort Firmware Update callback response=%s." % response)
        if not response['completed']:
            DLOG.info("Get Host Devices for host %s failed, reason=%s."
                      % (response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.FW_UPDATE_ABORT_HOSTS != self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.host_fw_update_abort_failed(host)

    def _nfvi_fw_update_abort_host(self, host_uuid, host_name):
        """
        NFVI Abort Firmware Update
        """
        nfvi.nfvi_host_device_image_update_abort(host_uuid, host_name, self._nfvi_fw_update_abort_callback())

    def host_operation_inprogress(self):
        """
        Returns true if a lock of hosts
        """
        if self._host_operation is not None:
            return self._host_operation.is_inprogress()
        return False

    @staticmethod
    def host_has_instances(host, skip_stopped=False):
        """
        Returns true if a host has instances located on it
        """
        from nfv_vim import directors

        instance_director = directors.get_instance_director()
        return instance_director.host_has_instances(host, skip_stopped=skip_stopped)

    @staticmethod
    def host_instances_moved(host, host_operation):
        """
        Notifies the host director that all the instances have been moved from
        a host
        """
        host.notify_instances_moved(host_operation)

    @staticmethod
    def host_instances_stopped(host, host_operation):
        """
        Notifies the host director that all the instances have been stopped on
        a host
        """
        host.notify_instances_stopped(host_operation)

    @staticmethod
    def host_enabled(host):
        """
        Notifies the host director that a host is enabled
        """
        from nfv_vim import directors

        DLOG.info("Notify other directors that the host %s is enabled."
                  % host.name)
        instance_director = directors.get_instance_director()
        instance_director.recover_instances()

    @staticmethod
    def host_services_disabling(host):
        """
        Notifies the host director that host services are being disabled
        """
        from nfv_vim import directors

        DLOG.info("Notify other directors that the host %s services are "
                  "disabling." % host.name)
        instance_director = directors.get_instance_director()
        host_operation = instance_director.host_services_disabling(host)
        return host_operation

    @staticmethod
    def host_services_disabled(host):
        """
        Notifies the host director that host services are disabled
        """
        from nfv_vim import directors

        DLOG.info("Notify other directors that the host %s services are "
                  "disabled." % host.name)
        instance_director = directors.get_instance_director()
        host_operation = instance_director.host_services_disabled(host)
        return host_operation

    @staticmethod
    def host_disabled(host):
        """
        Notifies the host director that a host is disabled
        """
        from nfv_vim import directors

        DLOG.info("Notify other directors that the host %s is disabled."
                  % host.name)

        instance_director = directors.get_instance_director()
        instance_director.host_disabled(host)

    @staticmethod
    def host_offline(host):
        """
        Notifies the host director that a host is offline
        """
        from nfv_vim import directors

        DLOG.info("Notify other directors that the host %s is offline."
                  % host.name)
        instance_director = directors.get_instance_director()
        instance_director.host_offline(host)
        # Now that the host is offline, we may be able to recover instances
        # on that host (i.e. evacuate them).
        instance_director.recover_instances()

    @staticmethod
    def host_audit(host):
        """
        Notifies the host director that a host audit is in progress
        """
        from nfv_vim import directors

        DLOG.verbose("Notify other directors that a host %s audit is in progress."
                     % host.name)
        instance_director = directors.get_instance_director()
        instance_director.host_audit(host)

        sw_mgmt_director = directors.get_sw_mgmt_director()
        sw_mgmt_director.host_audit(host)

    @staticmethod
    def host_abort(host):
        """
        Notifies the host director that a host abort is in progress
        """
        from nfv_vim import directors

        DLOG.info("Notify other directors that a host %s abort is in progress."
                  % host.name)
        instance_director = directors.get_instance_director()
        instance_director.host_operation_cancel(host.name)

    @staticmethod
    def host_state_change_notify(host):
        """
        Notifies the host director that a host has changed state
        """
        from nfv_vim import directors

        DLOG.info("Host %s state change notification." % host.name)

        sw_mgmt_director = directors.get_sw_mgmt_director()
        sw_mgmt_director.host_state_change(host)

    def lock_hosts(self, host_names):
        """
        Lock a list of hosts
        """
        DLOG.info("Lock hosts: %s" % host_names)

        host_operation = Operation(OPERATION_TYPE.LOCK_HOSTS)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            if host.is_locking():
                host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)

            elif host.is_locked():
                host_operation.add_host(host.name, OPERATION_STATE.COMPLETED)

            else:
                host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
                self._nfvi_lock_host(host.uuid, host.name)

        if host_operation.is_inprogress():
            self._host_operation = host_operation

        return host_operation

    def unlock_hosts(self, host_names):
        """
        Unlock a list of hosts
        """
        DLOG.info("Unlock hosts: %s" % host_names)

        host_operation = Operation(OPERATION_TYPE.UNLOCK_HOSTS)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            if host.is_locked():
                host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
                self._nfvi_unlock_host(host.uuid, host.name)

            elif host.is_unlocking():
                host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)

            else:
                host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)

        if host_operation.is_inprogress():
            self._host_operation = host_operation

        return host_operation

    def reboot_hosts(self, host_names):
        """
        Reboot a list of hosts
        """
        DLOG.info("Reboot hosts: %s" % host_names)

        host_operation = Operation(OPERATION_TYPE.REBOOT_HOSTS)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            if host.is_locked():
                host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
                self._nfvi_reboot_host(host.uuid, host.name)

            else:
                reason = "Cannot reboot unlocked host %s." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

        if host_operation.is_inprogress():
            self._host_operation = host_operation

        return host_operation

    def upgrade_hosts(self, host_names):
        """
        Upgrade a list of hosts
        """
        DLOG.info("Upgrade hosts: %s" % host_names)

        host_operation = Operation(OPERATION_TYPE.UPGRADE_HOSTS)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
            self._nfvi_upgrade_host(host.uuid, host.name)

        if host_operation.is_inprogress():
            self._host_operation = host_operation

        return host_operation

    def swact_hosts(self, host_names):
        """
        Swact a list of hosts
        """
        DLOG.info("Swact hosts: %s" % host_names)

        host_operation = Operation(OPERATION_TYPE.SWACT_HOSTS)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
            self._nfvi_swact_host(host.uuid, host.name)

        if host_operation.is_inprogress():
            self._host_operation = host_operation

        return host_operation

    def fw_update_hosts(self, host_names):
        """
        Firmware Update hosts
        """
        DLOG.info("Firmware Update hosts: %s" % host_names)

        host_operation = Operation(OPERATION_TYPE.FW_UPDATE_HOSTS)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
            self._nfvi_fw_update_host(host.uuid, host.name)

        if host_operation.is_inprogress():
            self._host_operation = host_operation

        return host_operation

    def fw_update_abort_hosts(self, host_names):
        """
        Firmware Update Abort Hosts
        """
        DLOG.info("Firmware Update Abort for hosts: %s" % host_names)

        host_operation = Operation(OPERATION_TYPE.FW_UPDATE_ABORT_HOSTS)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
            self._nfvi_fw_update_abort_host(host.uuid, host.name)

        if host_operation.is_inprogress():
            self._host_operation = host_operation

        return host_operation

    @coroutine
    def _nfvi_kube_host_upgrade_control_plane_callback(self):
        """
        NFVI Kube Host Upgrade Control Plane Callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Kube Host Upgrade Control Plane response=%s."
                     % response)
        if not response['completed']:
            DLOG.info("Kube Host Upgrade Control Plane failed. Host:%s, reason=%s."
                      % (response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.KUBE_UPGRADE_HOSTS != self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.kube_host_upgrade_control_plane_failed(host)

    def _nfvi_kube_host_upgrade_control_plane(self,
                                              host_uuid,
                                              host_name,
                                              force):
        """
        NFVI Kube Host Upgrade Control Plane
        """
        nfvi.nfvi_kube_host_upgrade_control_plane(
            host_uuid,
            host_name,
            force,
            self._nfvi_kube_host_upgrade_control_plane_callback())

    def kube_upgrade_hosts_control_plane(self, host_names, force):
        """
        Kube Upgrade Hosts Control Plane for multiple hosts
        """
        DLOG.info("Kube Host Upgrade control plane for hosts: %s" % host_names)

        host_operation = \
            Operation(OPERATION_TYPE.KUBE_UPGRADE_HOSTS)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
            self._nfvi_kube_host_upgrade_control_plane(host.uuid,
                                                       host.name,
                                                       force)

        if host_operation.is_inprogress():
            self._host_operation = host_operation

        return host_operation

    # cordon
    @coroutine
    def _nfvi_kube_host_cordon_callback(self):
        """
        NFVI Kube Host Cordon Callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Kube Host Cordon response=%s." % response)
        if not response['completed']:
            DLOG.info("Kube Host Upgrade Cordon failed. Host:%s, reason=%s."
                      % (response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.KUBE_UPGRADE_HOSTS != self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.kube_host_cordon_failed(host)

    def _nfvi_kube_host_cordon(self,
                               host_uuid,
                               host_name,
                               force):
        """
        NFVI Kube Host Cordon
        """
        nfvi.nfvi_kube_host_cordon(
            host_uuid,
            host_name,
            force,
            self._nfvi_kube_host_cordon_callback())

    def kube_host_cordon(self, host_names, force):
        """
        Kube Host Cordon for multiple hosts
        """
        DLOG.info("Kube Host Cordon for hosts: %s" % host_names)

        host_operation = \
            Operation(OPERATION_TYPE.KUBE_UPGRADE_HOSTS)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
            self._nfvi_kube_host_cordon(host.uuid,
                                        host.name,
                                        force)
        if host_operation.is_inprogress():
            self._host_operation = host_operation
        return host_operation

    # uncordon
    @coroutine
    def _nfvi_kube_host_uncordon_callback(self):
        """
        NFVI Kube Host Uncordon Callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Kube Host Uncordon response=%s." % response)
        if not response['completed']:
            DLOG.info("Kube Host Upgrade Uncordon failed. Host:%s, reason=%s."
                      % (response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.KUBE_UPGRADE_HOSTS != self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.kube_host_uncordon_failed(host)

    def _nfvi_kube_host_uncordon(self,
                                 host_uuid,
                                 host_name,
                                 force):
        """
        NFVI Kube Host Uncordon
        """
        nfvi.nfvi_kube_host_uncordon(
            host_uuid,
            host_name,
            force,
            self._nfvi_kube_host_uncordon_callback())

    def kube_host_uncordon(self, host_names, force):
        """
        Kube Host Uncordon for multiple hosts
        """
        DLOG.info("Kube Host Uncordon for hosts: %s" % host_names)

        host_operation = \
            Operation(OPERATION_TYPE.KUBE_UPGRADE_HOSTS)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
            self._nfvi_kube_host_uncordon(host.uuid,
                                        host.name,
                                        force)
        if host_operation.is_inprogress():
            self._host_operation = host_operation
        return host_operation

    @coroutine
    def _nfvi_kube_host_upgrade_kubelet_callback(self):
        """
        NFVI Kube Host Upgrade Kubelet Callback (for a single host)
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Kube Host Upgrade Kubelet response=%s."
                     % response)
        if not response['completed']:
            DLOG.info("Kube Host Upgrade Kubelet failed. Host:%s, reason=%s."
                      % (response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.KUBE_UPGRADE_HOSTS != self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.kube_host_upgrade_kubelet_failed(host)

    def _nfvi_kube_host_upgrade_kubelet(self, host_uuid, host_name, force):
        """
        NFVI Kube Host Upgrade Kubelet
        """
        nfvi.nfvi_kube_host_upgrade_kubelet(
            host_uuid,
            host_name,
            force,
            self._nfvi_kube_host_upgrade_kubelet_callback())

    def kube_upgrade_hosts_kubelet(self, host_names, force):
        """
        Kube Upgrade Hosts Kubelet for multiple hosts
        """
        DLOG.info("Kube Host Upgrade kubelet for hosts: %s" % host_names)

        host_operation = \
            Operation(OPERATION_TYPE.KUBE_UPGRADE_HOSTS)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
            self._nfvi_kube_host_upgrade_kubelet(host.uuid, host.name, force)

        if host_operation.is_inprogress():
            self._host_operation = host_operation

        return host_operation

    @coroutine
    def _nfvi_kube_rootca_update_host_callback(self):
        """
        NFVI Kube Root CA Update Host Callback (for a single host)
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.verbose("NFVI Kube Root CA Update Host response=%s." % response)
        if not response['completed']:
            DLOG.info("Kube Root CA Update failed. Host:%s, reason=%s."
                      % (response['host_name'], response['reason']))

            host_table = tables.tables_get_host_table()
            host = host_table.get(response['host_name'], None)
            if host is None:
                DLOG.verbose("Host %s does not exist." % response['host_name'])
                return

            if self._host_operation is None:
                DLOG.verbose("No host %s operation in progress." % host.name)
                return

            if OPERATION_TYPE.KUBE_ROOTCA_UPDATE_HOSTS \
               != self._host_operation.operation_type:
                DLOG.verbose("Unexpected host %s operation %s, ignoring."
                             % (host.name, self._host_operation.operation_type))
                return

            sw_mgmt_director = directors.get_sw_mgmt_director()
            sw_mgmt_director.kube_host_rootca_update_failed(host)

    def _nfvi_kube_rootca_update_host(self, host_uuid, host_name, update_type,
                                      in_progress_state, completed_state,
                                      failed_state):
        """NFVI Kube Root CA Update - Host"""
        nfvi.nfvi_kube_rootca_update_host(
            host_uuid,
            host_name,
            update_type,
            in_progress_state,
            completed_state,
            failed_state,
            self._nfvi_kube_rootca_update_host_callback())

    def kube_rootca_update_hosts_by_type(self, host_names, update_type,
                                         in_progress_state, completed_state,
                                         failed_state):
        """Utility method for Kube Root CA Update - Host"""
        DLOG.info("Kube RootCA Update %s (%s) for hosts: %s"
                   % (update_type, in_progress_state, host_names))
        host_operation = Operation(OPERATION_TYPE.KUBE_ROOTCA_UPDATE_HOSTS)
        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation
            host_operation.add_host(host.name,
                                    OPERATION_STATE.INPROGRESS)
            self._nfvi_kube_rootca_update_host(host.uuid,
                                               host.name,
                                               update_type,
                                               in_progress_state,
                                               completed_state,
                                               failed_state)
        if host_operation.is_inprogress():
            self._host_operation = host_operation
        return host_operation

    def disable_host_services(self, host_names, service):
        """
        Disable a host service on a list of hosts
        """
        DLOG.info("Disable host services: %s service: %s" %
                  (host_names, service))

        host_operation = Operation(OPERATION_TYPE.DISABLE_HOST_SERVICES)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        host_list = list()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            host.host_services_locked = True
            if (objects.HOST_SERVICE_STATE.DISABLED ==
                    host.host_service_state(service)):
                host_operation.add_host(host.name, OPERATION_STATE.COMPLETED)
            else:
                host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
                host_list.append(host)

        for host in host_list:
            self._nfvi_disable_host_services(
                host.uuid, host.name, host.personality, host.is_offline,
                service)

        if host_operation.is_inprogress():
            self._host_operation = host_operation

        return host_operation

    def enable_host_services(self, host_names, service):
        """
        Enable a host service on a list of hosts
        """
        DLOG.info("Enable host services: %s service: %s" %
                  (host_names, service))

        host_operation = Operation(OPERATION_TYPE.ENABLE_HOST_SERVICES)

        if self._host_operation is not None:
            DLOG.debug("Canceling previous host operation %s, before "
                       "continuing with host operation %s."
                       % (self._host_operation.operation_type,
                          host_operation.operation_type))
            self._host_operation = None

        host_table = tables.tables_get_host_table()
        host_list = list()
        for host_name in host_names:
            host = host_table.get(host_name, None)
            if host is None:
                reason = "Unknown host %s given." % host_name
                DLOG.info(reason)
                host_operation.set_failed(reason)
                return host_operation

            host.host_services_locked = False
            if (objects.HOST_SERVICE_STATE.ENABLED ==
                    host.host_service_state(service)):
                host_operation.add_host(host.name, OPERATION_STATE.COMPLETED)
            else:
                host_operation.add_host(host.name, OPERATION_STATE.INPROGRESS)
                host_list.append(host)

        for host in host_list:
            self._nfvi_enable_host_services(
                host.uuid, host.name, host.personality, service)

        if host_operation.is_inprogress():
            self._host_operation = host_operation

        return host_operation

    @coroutine
    def _nfvi_get_kube_host_upgrade_list_callback(self):
        """
        Get Kube Host Upgrade List Callback
        """
        from nfv_vim import directors

        response = (yield)
        DLOG.debug("Get kube host upgrade list callback response=%s." % response)
        sw_mgmt_director = directors.get_sw_mgmt_director()
        sw_mgmt_director.kube_host_upgrade_list(response)

    def _nfvi_get_kube_host_upgrade_list(self):
        """
        NFVI Kube host upgrade list
        """
        nfvi.nfvi_get_kube_host_upgrade_list(
            self._nfvi_get_kube_host_upgrade_list_callback())


def get_host_director():
    """
    Returns the Host Director
    """
    return _host_director


def host_director_initialize():
    """
    Initialize Host Director
    """
    global _host_director

    _host_director = HostDirector()


def host_director_finalize():
    """
    Finalize Host Director
    """
    pass
