#
# Copyright (c) 2015-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_common import strategy


def normalize_release(release):
    """Normalize a release value into list format

    Prior to the componentization feature, the release was stored as a string rather
    than a list of strings. Because of that, when running upgrade from older versions,
    the data restored after a reboot on host-lock and host-unlock would return the str
    format, while the code expects [str];
    """
    if isinstance(release, str):
        return [release]
    return release


def validate_operation(operation):
    if operation.is_inprogress():
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""
    elif operation.is_failed():
        return strategy.STRATEGY_STEP_RESULT.FAILED, operation.reason
    return strategy.STRATEGY_STEP_RESULT.SUCCESS, ""


class AbstractStrategyStep(strategy.StrategyStep):
    """An abstract base class for strategy steps."""

    def __init__(self, step_name, timeout_in_secs):
        super().__init__(step_name, timeout_in_secs=timeout_in_secs)

    def from_dict(self, data):
        """Returns the step object initialized using the given dictionary."""

        super().from_dict(data)
        return self

    def as_dict(self):
        """Represent the step as a dictionary."""

        data = super().as_dict()
        # Next 3 lines are required for all strategy steps and may be
        # overridden by subclass in some cases
        data["entity_type"] = ""
        data["entity_names"] = []
        data["entity_uuids"] = []
        return data
