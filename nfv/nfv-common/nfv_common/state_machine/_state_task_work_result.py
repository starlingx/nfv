#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_common.helpers import Constant
from nfv_common.helpers import Singleton


class _StateTaskWorkResult(metaclass=Singleton):
    """State Task Work Result - Constants."""

    WAIT = Constant("wait")
    SUCCESS = Constant("success")
    FAILED = Constant("failed")
    DEGRADED = Constant("degraded")
    ABORTED = Constant("aborted")
    TIMED_OUT = Constant("timed-out")


# Constant Instantiation
STATE_TASK_WORK_RESULT = _StateTaskWorkResult()
