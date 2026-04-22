#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_common.helpers import Constant
from nfv_common.helpers import Constants
from nfv_common.helpers import Singleton


class NfviErrorCodes(Constants, metaclass=Singleton):
    """
    NFVI - Error Code Constants
    """
    TOKEN_EXPIRED = Constant('token-expired')
    NOT_FOUND = Constant('not-found')


# Constant Instantiation
NFVI_ERROR_CODE = NfviErrorCodes()
