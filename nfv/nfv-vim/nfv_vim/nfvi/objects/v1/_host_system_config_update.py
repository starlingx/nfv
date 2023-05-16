#
# Copyright (c) 2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_vim.nfvi.objects.v1._object import ObjectData


class HostSystemConfigUpdate(ObjectData):
    """
    NFVI Host System Config Update Object
    """
    def __init__(self, name, unlock_request):
        super(HostSystemConfigUpdate, self).__init__('1.0.0')
        self.update(dict(name=name,
                         unlock_request=unlock_request))
