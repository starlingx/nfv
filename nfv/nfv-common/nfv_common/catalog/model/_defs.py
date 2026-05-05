#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_common.helpers import Constant
from nfv_common.helpers import Singleton


class ConnectionType(metaclass=Singleton):
    """Connection Type Constants."""

    UNKNOWN = Constant("unknown")
    VIRTUAL_PORT = Constant("virtual-port")
    VIRTUAL_NIC_ADDRESS = Constant("virtual-nic-address")
    PHYSICAL_PORT = Constant("physical-port")
    PHYSICAL_NIC_ADDRESS = Constant("physical-nic-address")


class ConnectivityType(metaclass=Singleton):
    """Connectivity Type Constants."""

    UNKNOWN = Constant("unknown")
    E_LINE = Constant("E-Line")
    E_LAN = Constant("E-LAN")
    E_TREE = Constant("E-Tree")


# Constant Instantiation
CONNECTION_TYPE = ConnectionType()
CONNECTIVITY_TYPE = ConnectivityType()
