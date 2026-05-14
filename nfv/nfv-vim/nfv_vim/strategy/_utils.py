#
# Copyright (c) 2015-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_common import strategy
from nfv_vim.objects import HOST_NAME
from nfv_vim.objects import HOST_PERSONALITY


def get_first_host():
    """This corresponds to the first host that should be updated.

    In simplex env, first host: controller-0. In duplex env: controller-1.
    """
    from nfv_vim import tables

    controller_0_host = None
    controller_1_host = None
    host_table = tables.tables_get_host_table()
    for host in host_table.get_by_personality(HOST_PERSONALITY.CONTROLLER):
        if HOST_NAME.CONTROLLER_0 == host.name:
            controller_0_host = host
        if HOST_NAME.CONTROLLER_1 == host.name:
            controller_1_host = host
    if controller_1_host is None:
        # simplex
        return controller_0_host
    # duplex
    return controller_1_host


def get_second_host():
    """This corresponds to the second host that should be updated.

    In simplex env, second host: None. In duplex env: controller-0.
    """
    from nfv_vim import tables

    controller_0_host = None
    controller_1_host = None
    host_table = tables.tables_get_host_table()
    for host in host_table.get_by_personality(HOST_PERSONALITY.CONTROLLER):
        if HOST_NAME.CONTROLLER_0 == host.name:
            controller_0_host = host
        if HOST_NAME.CONTROLLER_1 == host.name:
            controller_1_host = host
    if controller_1_host is None:
        # simplex
        return None
    # duplex
    return controller_0_host


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
