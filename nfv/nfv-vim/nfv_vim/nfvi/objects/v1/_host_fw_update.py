#
# Copyright (c) 2015-2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_vim.nfvi.objects.v1._object import ObjectData


class HostFwUpdate(ObjectData):
    """
    NFVI Host Firmware Update Object
    """
    def __init__(self, hostname, personality, uuid):
        super(HostFwUpdate, self).__init__('1.0.0')
        self.update(dict(hostname=hostname,
                         personality=personality,
                         uuid=uuid))
