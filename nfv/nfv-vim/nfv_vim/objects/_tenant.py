#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_common import debug
from nfv_vim.objects._object import ObjectData

DLOG = debug.debug_get_logger("nfv_vim.objects.tenant")


class Tenant(ObjectData):
    """Tenant Object."""

    def __init__(self, uuid, name, description, enabled):
        super().__init__("1.0.0")
        self.update(
            {"uuid": uuid, "name": name, "description": description, "enabled": enabled}
        )
