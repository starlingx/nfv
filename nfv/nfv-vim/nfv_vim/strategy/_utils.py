#
# Copyright (c) 2015-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_common import debug
from nfv_common.helpers import coroutine
from nfv_common import strategy
from nfv_common import timers

DLOG = debug.debug_get_logger("nfv_vim.strategy._utils")


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


def parse_version(sw_version):
    """Parse a dotted version string into a tuple of integers.

    This allows numeric comparison of releases so that, e.g. "9.0.0" is
    correctly treated as older than "11.0.0".
    """

    return tuple(int(section) for section in str(sw_version).split("."))


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


class TimerBasedPollingStep(AbstractStrategyStep):
    """Base class for strategy steps that poll using a self-scheduling timer.

    Subclasses must implement:
        _poll_action(): Called every poll interval to perform the actual query.

    The timer is created when apply() is called and is automatically cleaned up
    on completion (success/failure) or timeout. Subclasses should call
    _cleanup_timer() before calling stage.step_complete() in their callbacks.

    Unlike HOST_AUDIT-driven steps, this avoids the 30-second host FSM audit
    gate and polls at a predictable, configurable interval.
    """

    #: Default interval between polls, in seconds. Subclasses may override.
    POLL_INTERVAL_IN_SECS = 5

    #: Default initial delay before first poll, in seconds. Subclasses may override.
    FIRST_POLL_DELAY_IN_SECS = 10

    def __init__(
        self,
        step_name,
        timeout_in_secs,
        poll_interval_in_secs=None,
        first_poll_delay_in_secs=None,
    ):
        super().__init__(step_name, timeout_in_secs=timeout_in_secs)
        self._poll_interval_in_secs = (
            poll_interval_in_secs
            if poll_interval_in_secs is not None
            else self.POLL_INTERVAL_IN_SECS
        )
        self._first_poll_delay_in_secs = (
            first_poll_delay_in_secs
            if first_poll_delay_in_secs is not None
            else self.FIRST_POLL_DELAY_IN_SECS
        )
        self._poll_timer_id = None
        self._poll_in_progress = False

    def _cleanup_timer(self):
        """Delete the polling timer if it exists."""

        if self._poll_timer_id is not None:
            timers.timers_delete_timer(self._poll_timer_id)
            self._poll_timer_id = None

    def _poll_action(self):
        """Perform the polling action. Must be overridden by subclass.

        This is called every poll interval. The subclass should initiate an
        async query and handle the result in a callback. Set
        self._poll_in_progress = True before starting the query, and reset it
        to False in the callback to allow the next poll to proceed.
        """
        raise NotImplementedError("Subclasses must implement _poll_action()")

    @coroutine
    def _poll_timer_callback(self):
        """Timer coroutine that periodically calls _poll_action."""

        while True:
            (yield)
            if not self._poll_in_progress:
                DLOG.debug("Step (%s) polling." % self._name)
                self._poll_action()

    def apply(self):
        """Start the polling timer and wait for completion."""

        DLOG.info("Step (%s) apply." % self._name)
        self._poll_timer_id = timers.timers_create_timer(
            self._name,
            self._first_poll_delay_in_secs,
            self._poll_interval_in_secs,
            self._poll_timer_callback,
        )
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""

    def handle_event(self, event, event_data=None):
        """No-op: polling is driven by the self-scheduling timer."""

        return False

    def from_dict(self, data):
        """Returns the step object initialized using the given dictionary."""

        super().from_dict(data)
        self._poll_interval_in_secs = self.POLL_INTERVAL_IN_SECS
        self._first_poll_delay_in_secs = self.FIRST_POLL_DELAY_IN_SECS
        self._poll_in_progress = False
        # Recreate the timer if the step was in progress (WAIT state) before
        # the restart. The framework does not re-call apply() on resume.
        if strategy.STRATEGY_STEP_RESULT.WAIT == self._result:
            self._poll_timer_id = timers.timers_create_timer(
                self._name,
                self._poll_interval_in_secs,
                self._poll_interval_in_secs,
                self._poll_timer_callback,
            )
        else:
            self._poll_timer_id = None
        return self

    def timeout(self):
        """Clean up timer on timeout."""

        self._cleanup_timer()
        return super().timeout()
