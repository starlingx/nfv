#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_common.helpers import Constant
from nfv_common.helpers import Constants
from nfv_common.helpers import Singleton

from nfv_vim.nfvi.objects.v1._object import ObjectData


class GuestServiceNames(Constants, metaclass=Singleton):
    """Guest Service Name Constants."""

    UNKNOWN = Constant("unknown")
    HEARTBEAT = Constant("heartbeat")


class GuestServiceAdministrativeState(Constants, metaclass=Singleton):
    """Guest Service Administrative State Constants."""

    UNKNOWN = Constant("unknown")
    LOCKED = Constant("locked")
    UNLOCKED = Constant("unlocked")


class GuestServiceOperationalState(Constants, metaclass=Singleton):
    """Guest Service Operational State Constants."""

    UNKNOWN = Constant("unknown")
    ENABLED = Constant("enabled")
    DISABLED = Constant("disabled")


# Guest Service Constant Instantiation
GUEST_SERVICE_NAME = GuestServiceNames()
GUEST_SERVICE_ADMIN_STATE = GuestServiceAdministrativeState()
GUEST_SERVICE_OPER_STATE = GuestServiceOperationalState()


class GuestService(ObjectData):
    """NFVI Guest Service Object."""

    def __init__(self, name, admin_state, oper_state, restart_timeout=None):
        super(GuestService, self).__init__("1.0.0")
        self.update(
            dict(
                name=name,
                admin_state=admin_state,
                oper_state=oper_state,
                restart_timeout=restart_timeout,
            )
        )

    def as_dict(self):
        """Represent Guest Service data object as dictionary."""

        data = dict()
        data["name"] = self.name
        data["admin_state"] = self.admin_state
        data["oper_state"] = self.oper_state
        if self.restart_timeout is not None:
            data["restart_timeout"] = self.restart_timeout
        return data
