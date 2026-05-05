#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_common.helpers import Constant
from nfv_common.helpers import Constants
from nfv_common.helpers import Singleton
from nfv_vim.nfvi.objects.v1._object import ObjectData


class NetworkAdministrativeState(Constants, metaclass=Singleton):
    """Network Administrative State Constants."""

    UNKNOWN = Constant("unknown")
    LOCKED = Constant("locked")
    UNLOCKED = Constant("unlocked")


class NetworkOperationalState(Constants, metaclass=Singleton):
    """Network Operational State Constants."""

    UNKNOWN = Constant("unknown")
    ENABLED = Constant("enabled")
    DISABLED = Constant("disabled")


class NetworkAvailabilityStatus(Constants, metaclass=Singleton):
    """Network Availability Status Constants."""

    UNKNOWN = Constant("unknown")
    NONE = Constant("")
    FAILED = Constant("failed")
    BUILDING = Constant("building")


# Network Constant Instantiation
NETWORK_ADMIN_STATE = NetworkAdministrativeState()
NETWORK_OPER_STATE = NetworkOperationalState()
NETWORK_AVAIL_STATUS = NetworkAvailabilityStatus()


class NetworkProviderData(ObjectData):
    """NFVI Network Provider Data Object."""

    def __init__(self, physical_network, network_type, segmentation_id):
        super().__init__("1.0.0")
        self.update(
            {
                "physical_network": physical_network,
                "network_type": network_type,
                "segmentation_id": segmentation_id,
            }
        )


class Network(ObjectData):
    """NFVI Network Object."""

    def __init__(
        self,
        uuid,
        name,
        admin_state,
        oper_state,
        avail_status,
        is_shared,
        mtu,
        provider_data=None,
    ):
        super().__init__("1.0.0")
        self.update(
            {
                "uuid": uuid,
                "name": name,
                "admin_state": admin_state,
                "oper_state": oper_state,
                "avail_status": avail_status,
                "is_shared": is_shared,
                "mtu": mtu,
                "provider_data": provider_data,
            }
        )
