#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_common import debug
from nfv_vim.objects._object import ObjectData

DLOG = debug.debug_get_logger("nfv_vim.objects.network")


class Subnet(ObjectData):
    """Subnet Object."""

    def __init__(
        self,
        uuid,
        name,
        ip_version,
        subnet_ip,
        subnet_prefix,
        gateway_ip,
        network_uuid,
        is_dhcp_enabled,
    ):
        super().__init__("1.0.0")
        self.update(
            {
                "uuid": uuid,
                "name": name,
                "ip_version": ip_version,
                "subnet_ip": subnet_ip,
                "subnet_prefix": subnet_prefix,
                "gateway_ip": gateway_ip,
                "network_uuid": network_uuid,
                "is_dhcp_enabled": is_dhcp_enabled,
            }
        )
