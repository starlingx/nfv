#
# Copyright (C) 2019 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_common import debug
from nfv_vim.nfvi._nfvi_fault_mgmt_plugin import NFVIFaultMgmtPlugin

DLOG = debug.debug_get_logger('nfv_vim.nfvi.nfvi_fault_mgmt_module')

_fault_mgmt_plugin = None


def nfvi_fault_mgmt_plugin_disabled():
    """
    Get fault management plugin disabled status
    """
    return (_fault_mgmt_plugin is None)


def nfvi_get_openstack_alarms(callback):
    """
    Get alarms
    """
    cmd_id = _fault_mgmt_plugin.invoke_plugin('get_openstack_alarms', callback=callback)
    return cmd_id


def nfvi_get_openstack_logs(start_period, end_period, callback):
    """
    Get logs
    """
    cmd_id = _fault_mgmt_plugin.invoke_plugin('get_openstack_logs', start_period,
                                              end_period, callback=callback)
    return cmd_id


def nfvi_get_openstack_alarm_history(start_period, end_period, callback):
    """
    Get logs
    """
    cmd_id = _fault_mgmt_plugin.invoke_plugin('get_openstack_alarm_history', start_period,
                                              end_period, callback=callback)
    return cmd_id


def nfvi_fault_mgmt_initialize(config, pool):
    """
    Initialize the NFVI fault_mgmt package
    """
    global _fault_mgmt_plugin

    _fault_mgmt_plugin = NFVIFaultMgmtPlugin(config['namespace'], pool)
    _fault_mgmt_plugin.initialize(config['config_file'])


def nfvi_fault_mgmt_finalize():
    """
    Finalize the NFVI fault_mgmt package
    """
    if _fault_mgmt_plugin is not None:
        _fault_mgmt_plugin.finalize()
