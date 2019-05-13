#
# Copyright (C) 2019 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_common import debug
from nfv_common import tasks

from nfv_vim.nfvi._nfvi_plugin import NFVIPlugin

DLOG = debug.debug_get_logger('nfv_vim.nfvi.nfvi_fault_mgmt_plugin')


class NFVIFaultMgmtPlugin(NFVIPlugin):
    """
    NFVI Fault Management Plugin
    """
    _version = '1.0.0'
    _signature = '2808f351-92bb-482c-b873-66ab232254af'
    _plugin_type = 'fault_mgmt_plugin'

    def __init__(self, namespace, pool):
        scheduler = tasks.TaskScheduler('fault_mgmt_plugin', pool)
        super(NFVIFaultMgmtPlugin, self).__init__(
            namespace,
            NFVIFaultMgmtPlugin._version,
            NFVIFaultMgmtPlugin._signature,
            NFVIFaultMgmtPlugin._plugin_type,
            scheduler)
