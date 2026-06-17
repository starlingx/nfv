#
# Copyright (c) 2015-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import json

from nfv_common import debug
from nfv_common.helpers import coroutine
from nfv_common import strategy
from nfv_common import timers
from nfv_vim.strategy._constants import STRATEGY_STEP_NAME
from nfv_vim.strategy._strategy_defs import STRATEGY_EVENT
from nfv_vim.strategy._utils import AbstractStrategyStep
from nfv_vim.strategy._utils import validate_operation
from nfv_vim import tables

DLOG = debug.debug_get_logger("nfv_vim.strategy.kube_upgrade.step")

KUBE_UPGRADE_START_ALARM_IGNORE = [
    "850.002",  # Kubernetes health check failed
    "900.022",  # Deployment finished (pending deploy delete)
    "900.023",  # Software release deploy in progress
    "900.201",  # Software deploy auto apply alarm
    "900.401",  # Kubernetes upgrade auto apply alarm
]


class AbstractKubeUpgradeStep(AbstractStrategyStep):
    def __init__(self, step_name, success_state, fail_state, timeout_in_secs=600):
        super().__init__(step_name, timeout_in_secs)
        # These two attributes are not persisted
        self._wait_time = 0
        self._query_inprogress = False
        # success and fail state validators are persisted
        self._success_state = success_state
        self._fail_state = fail_state

    def _handle_kube_upgrade_callback(self, response):
        """Handles the kube upgrade callback"""

        self._query_inprogress = False
        if response["completed"]:
            if self.strategy is None:
                # there is no longer a strategy.  abort.
                result = strategy.STRATEGY_STEP_RESULT.FAILED
                self.stage.step_complete(result, "strategy no longer exists")

            kube_upgrade_obj = response["result-data"]
            # replace the object in the strategy with the most recent object
            self.strategy.nfvi_kube_upgrade = kube_upgrade_obj

            # break out of the loop if fail or success states match
            if kube_upgrade_obj and kube_upgrade_obj.state == self._success_state:
                DLOG.debug(
                    "(%s) successfully reached (%s)."
                    % (self._name, self._success_state)
                )
                result = strategy.STRATEGY_STEP_RESULT.SUCCESS
                self.stage.step_complete(result, "")
            elif (
                self._fail_state is not None
                and kube_upgrade_obj.state == self._fail_state
            ):
                DLOG.warn(
                    "(%s) encountered failure state(%s)."
                    % (self._name, self._fail_state)
                )
                result = strategy.STRATEGY_STEP_RESULT.FAILED
                self.stage.step_complete(
                    result, "(%s) failed:(%s)" % (self._name, self._fail_state)
                )
            else:
                # Keep waiting for upgrade to reach success or fail state
                # timeout will occur if it is never reached.
                if kube_upgrade_obj:
                    kube_upgrade_obj_state = kube_upgrade_obj.state
                else:
                    kube_upgrade_obj_state = None
                DLOG.debug(
                    "(%s) in state (%s) waiting for (%s) or (%s)."
                    % (
                        self._name,
                        kube_upgrade_obj_state,
                        self._success_state,
                        self._fail_state,
                    )
                )
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    @coroutine
    def _get_kube_upgrade_callback(self):
        """Get Upgrade Callback."""

        response = yield
        DLOG.debug("(%s) callback response=%s." % (self._name, response))

        self._handle_kube_upgrade_callback(response)

    def _abort(self):
        """Returns the abort step related to this step."""

        return [KubeUpgradeAbortStep()] if self.strategy._single_controller else []

    def handle_event(self, event, event_data=None):
        """Handle Host events."""

        from nfv_vim import nfvi

        DLOG.debug("Step (%s) handle event (%s)." % (self._name, event))
        if event == STRATEGY_EVENT.KUBE_UPGRADE_CHANGED:
            # todo(abailey): use event data rather than re-querying
            self._query_inprogress = True
            nfvi.nfvi_get_kube_upgrade(self._get_kube_upgrade_callback())
            return True
        elif event == STRATEGY_EVENT.HOST_AUDIT:
            if 0 == self._wait_time:
                self._wait_time = timers.get_monotonic_timestamp_in_ms()
            now_ms = timers.get_monotonic_timestamp_in_ms()
            secs_expired = (now_ms - self._wait_time) // 1000
            # Wait 30 seconds before checking kube upgrade for first time
            if 30 <= secs_expired and not self._query_inprogress:
                self._query_inprogress = True
                nfvi.nfvi_get_kube_upgrade(self._get_kube_upgrade_callback())
            return True
        return False

    def from_dict(self, data):
        """Returns the step object initialized using the given dictionary."""

        super().from_dict(data)
        # these two attributes are not persisted
        self._wait_time = 0
        self._query_inprogress = False
        # validation states are persisted
        self._success_state = data["success_state"]
        self._fail_state = data["fail_state"]
        return self

    def as_dict(self):
        """Represent the kube upgrade step as a dictionary."""

        data = super().as_dict()
        data["success_state"] = self._success_state
        data["fail_state"] = self._fail_state
        return data


class AbstractKubeHostUpgradeStep(AbstractKubeUpgradeStep):
    """Kube Upgrade Host - Abstract Strategy Step.

    This operation issues a host command, which updates the kube upgrade object
    """

    def __init__(
        self,
        host,
        to_version,
        force,
        step_name,
        success_state,
        fail_state,
        timeout_in_secs=600,
    ):
        super().__init__(
            step_name, success_state, fail_state, timeout_in_secs=timeout_in_secs
        )
        self._to_version = to_version
        self._force = force
        # This class accepts only a single host
        # but serializes as a list of hosts (list size of one)
        self._hosts = []
        self._host_names = []
        self._host_uuids = []
        self._hosts.append(host)
        self._host_names.append(host.name)
        self._host_uuids.append(host.uuid)

    def from_dict(self, data):
        """Returns the step object initialized using the given dictionary."""

        super().from_dict(data)
        self._to_version = data["to_version"]
        self._force = data["force"]
        self._hosts = []
        self._host_uuids = []
        self._host_names = data["entity_names"]
        host_table = tables.tables_get_host_table()
        for host_name in self._host_names:
            host = host_table.get(host_name, None)
            if host is not None:
                self._hosts.append(host)
                self._host_uuids.append(host.uuid)
        return self

    def as_dict(self):
        """Represent the step as a dictionary."""

        data = super().as_dict()
        data["to_version"] = self._to_version
        data["force"] = self._force
        data["entity_type"] = "hosts"
        data["entity_names"] = self._host_names
        data["entity_uuids"] = self._host_uuids
        return data


class AbstractKubeHostListUpgradeStep(AbstractKubeUpgradeStep):
    """Kube Upgrade Host List - Abstract Strategy Step.

    This operation issues a host command, which updates the kube upgrade object
    It operates on a list of hosts
    Kube host operations can have intermediate (to_version) steps
    """

    def __init__(
        self,
        hosts,
        to_version,
        force,
        step_name,
        success_state,
        fail_state,
        timeout_in_secs=600,
    ):
        super().__init__(
            step_name, success_state, fail_state, timeout_in_secs=timeout_in_secs
        )
        self._to_version = to_version
        self._force = force
        self._hosts = hosts
        self._host_names = []
        self._host_uuids = []
        for host in hosts:
            self._host_names.append(host.name)
            self._host_uuids.append(host.uuid)

    def from_dict(self, data):
        """Returns the step object initialized using the given dictionary."""

        super().from_dict(data)
        self._to_version = data["to_version"]
        self._force = data["force"]
        self._hosts = []
        self._host_uuids = []
        self._host_names = data["entity_names"]
        host_table = tables.tables_get_host_table()
        for host_name in self._host_names:
            host = host_table.get(host_name, None)
            if host is not None:
                self._hosts.append(host)
                self._host_uuids.append(host.uuid)
        return self

    def as_dict(self):
        """Represent the step as a dictionary."""

        data = super().as_dict()
        data["to_version"] = self._to_version
        data["force"] = self._force
        data["entity_type"] = "hosts"
        data["entity_names"] = self._host_names
        data["entity_uuids"] = self._host_uuids
        return data


class KubeUpgradeAbortStep(AbstractKubeUpgradeStep):
    """Kube Upgrade - Abort - Strategy Step."""

    def __init__(self):
        from nfv_vim import nfvi

        super().__init__(
            STRATEGY_STEP_NAME.KUBE_UPGRADE_ABORT,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_ABORTED,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_ABORTING_FAILED,
        )

    @coroutine
    def _response_callback(self):
        """Kube Upgrade - Abort - Callback."""

        from nfv_vim import nfvi

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        if response["completed"]:
            if self.strategy is not None:
                self.strategy.nfvi_kube_upgrade = response["result-data"]

        # Calling abort on an aborted update returns a failure so we check
        if self.strategy is None:
            # return success if there is no more strategy
            self.stage.step_complete(
                strategy.STRATEGY_STEP_RESULT.SUCCESS, "no strategy"
            )
        elif self.strategy.nfvi_kube_upgrade is None:
            # return success if there is no more kube upgrade
            self.stage.step_complete(
                strategy.STRATEGY_STEP_RESULT.SUCCESS, "no kube upgrade"
            )
        elif self.strategy.nfvi_kube_upgrade.state == self._success_state:
            self.stage.step_complete(strategy.STRATEGY_STEP_RESULT.SUCCESS, "")
        elif (
            self.strategy.nfvi_kube_upgrade.state
            == nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_ABORTING
        ):
            pass
        else:
            # If the state does not match, the abort failed.
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(
                result, "Unexpected state: %s" % self.strategy.nfvi_kube_upgrade.state
            )

    def apply(self):
        """Kube Upgrade - Abort."""

        from nfv_vim import nfvi

        DLOG.info("Step (%s) apply." % self._name)
        nfvi.nfvi_kube_upgrade_abort(self._response_callback())
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""


class KubeUpgradeStartStep(AbstractKubeUpgradeStep):
    """Kube Upgrade Start - Strategy Step."""

    def __init__(self, to_version, force=False):

        from nfv_vim import nfvi

        super().__init__(
            STRATEGY_STEP_NAME.KUBE_UPGRADE_START,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_STARTED,
            None,
        )  # there is no failure state if upgrade-start fails
        # next 2 attributes must be persisted through from_dict/as_dict
        self._to_version = to_version
        self._force = force

    def abort(self):
        """Returns the abort step related to this step."""

        return self._abort()

    def from_dict(self, data):
        """Returns the step object initialized using the given dictionary."""

        super().from_dict(data)
        self._to_version = data["to_version"]
        self._force = data["force"]
        return self

    def as_dict(self):
        """Represent the kube upgrade step as a dictionary."""

        data = super().as_dict()
        data["to_version"] = self._to_version
        data["force"] = self._force
        return data

    @coroutine
    def _response_callback(self):
        """Kube Upgrade Start - Callback."""

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        # kube-upgrade-start will return a result when it completes,
        # so we do not want to use handle_event
        if response["completed"]:
            if self.strategy is not None:
                self.strategy.nfvi_kube_upgrade = response["result-data"]
            result = strategy.STRATEGY_STEP_RESULT.SUCCESS
            self.stage.step_complete(result, "")
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    def apply(self):
        """Kube Upgrade Start."""

        from nfv_vim import nfvi

        DLOG.info("Step (%s) apply." % self._name)

        nfvi.nfvi_kube_upgrade_start(
            self._to_version,
            self._force,
            KUBE_UPGRADE_START_ALARM_IGNORE,
            self._response_callback(),
        )
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""


class KubeUpgradeCleanupAbortedStep(AbstractKubeUpgradeStep):
    """Kube Upgrade Cleanup Aborted - Strategy Step."""

    # todo(abailey): this class could be replaced by KubeUpgradeCleanupStep
    # if it was enhanced to take an optional 'filter'
    def __init__(self):
        super().__init__(
            STRATEGY_STEP_NAME.KUBE_UPGRADE_CLEANUP_ABORTED,
            None,  # there is no success state for this cleanup activity
            None,
        )  # there is no failure state for this cleanup activity

    @coroutine
    def _response_callback(self):
        """Kube Upgrade Cleanup Aborted - Callback."""

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        # kube-upgrade-cleanup-aborted will return a result when it completes,
        # so we do not want to use handle_event
        if response["completed"]:
            if self.strategy is not None:
                # cleanup deletes the kube upgrade, clear it from the strategy
                self.strategy.nfvi_kube_upgrade = None
            result = strategy.STRATEGY_STEP_RESULT.SUCCESS
            self.stage.step_complete(result, "")
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    def apply(self):
        """Kube Upgrade Cleanup Aborted."""

        DLOG.info("Step (%s) apply." % self._name)

        from nfv_vim import nfvi

        # We only invoke this step if the state matches our filter
        filter_state = nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_ABORTED
        if self.strategy is not None:
            if self.strategy.nfvi_kube_upgrade is not None:
                if self.strategy.nfvi_kube_upgrade.state == filter_state:
                    DLOG.info(
                        "%s cleaning up %s"
                        % (self._name, self.strategy.nfvi_kube_upgrade.state)
                    )
                    nfvi.nfvi_kube_upgrade_cleanup(self._response_callback())
                    return strategy.STRATEGY_STEP_RESULT.WAIT, ""

        # All other cases, we claim success since the filter did not match
        return strategy.STRATEGY_STEP_RESULT.SUCCESS, ""


class KubeUpgradeCleanupStep(AbstractKubeUpgradeStep):
    """Kube Upgrade Cleanup - Strategy Step."""

    def __init__(self):
        super().__init__(
            STRATEGY_STEP_NAME.KUBE_UPGRADE_CLEANUP,
            None,  # there is no success state for this cleanup activity
            None,
        )  # there is no failure state for this cleanup activity

    @coroutine
    def _response_callback(self):
        """Kube Upgrade Cleanup - Callback."""

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        # kube-upgrade-cleanup will return a result when it completes,
        # so we do not want to use handle_event
        if response["completed"]:
            if self.strategy is not None:
                # cleanup deletes the kube upgrade, clear it from the strategy
                self.strategy.nfvi_kube_upgrade = None
            result = strategy.STRATEGY_STEP_RESULT.SUCCESS
            self.stage.step_complete(result, "")
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    def apply(self):
        """Kube Upgrade Cleanup."""

        from nfv_vim import nfvi

        DLOG.info("Step (%s) apply." % self._name)

        nfvi.nfvi_kube_upgrade_cleanup(self._response_callback())
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""


class KubeUpgradeCompleteStep(AbstractKubeUpgradeStep):
    """Kube Upgrade Complete - Strategy Step."""

    def __init__(self):
        from nfv_vim import nfvi

        super().__init__(
            STRATEGY_STEP_NAME.KUBE_UPGRADE_COMPLETE,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_COMPLETE,
            None,
        )  # there is no failure state for upgrade-complete

    def abort(self):
        """Returns the abort step related to this step."""

        return self._abort()

    @coroutine
    def _response_callback(self):
        """Kube Upgrade Complete - Callback."""

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        # kube-upgrade-complete will return a result when it completes,
        # so we do not want to use handle_event
        if response["completed"]:
            if self.strategy is not None:
                self.strategy.nfvi_kube_upgrade = response["result-data"]
            result = strategy.STRATEGY_STEP_RESULT.SUCCESS
            self.stage.step_complete(result, "")
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    def apply(self):
        """Kube Upgrade Complete."""

        from nfv_vim import nfvi

        DLOG.info("Step (%s) apply." % self._name)

        nfvi.nfvi_kube_upgrade_complete(self._response_callback())
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""


class KubeUpgradeDownloadImagesStep(AbstractKubeUpgradeStep):
    """Kube Upgrade Download Images - Strategy Step."""

    def __init__(self):
        from nfv_vim import nfvi

        super().__init__(
            STRATEGY_STEP_NAME.KUBE_UPGRADE_DOWNLOAD_IMAGES,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_DOWNLOADED_IMAGES,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADE_DOWNLOADING_IMAGES_FAILED,
            timeout_in_secs=1800,
        )

    def abort(self):
        """Returns the abort step related to this step."""

        return self._abort()

    @coroutine
    def _response_callback(self):
        """Kube Upgrade Download Images - Callback."""

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        if response["completed"]:
            if self.strategy is not None:
                self.strategy.nfvi_kube_upgrade = response["result-data"]
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    def apply(self):
        """Kube Upgrade Download Images."""

        from nfv_vim import nfvi

        DLOG.info("Step (%s) apply." % self._name)

        nfvi.nfvi_kube_upgrade_download_images(self._response_callback())
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""


class KubePreApplicationUpdateStep(AbstractKubeUpgradeStep):
    """Kube Pre Application Update - Strategy Step."""

    def __init__(self):
        from nfv_vim import nfvi

        super().__init__(
            STRATEGY_STEP_NAME.KUBE_PRE_APPLICATION_UPDATE,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_PRE_UPDATED_APPS,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_PRE_UPDATING_APPS_FAILED,
            timeout_in_secs=1800,
        )

    def abort(self):
        """Returns the abort step related to this step."""

        return self._abort()

    @coroutine
    def _response_callback(self):
        """Kube Pre Application Update - Callback."""

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        if response["completed"]:
            if self.strategy is not None:
                self.strategy.nfvi_kube_upgrade = response["result-data"]
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    def apply(self):
        """Kube Pre Application Update."""

        from nfv_vim import nfvi

        DLOG.info("Step (%s) apply." % self._name)

        nfvi.nfvi_kube_pre_application_update(self._response_callback())
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""


class KubePostApplicationUpdateStep(AbstractKubeUpgradeStep):
    """Kube Post Application Update - Strategy Step."""

    def __init__(self):
        from nfv_vim import nfvi

        super().__init__(
            STRATEGY_STEP_NAME.KUBE_POST_APPLICATION_UPDATE,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_POST_UPDATED_APPS,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_POST_UPDATING_APPS_FAILED,
            timeout_in_secs=1800,
        )

    def abort(self):
        """Returns the abort step related to this step."""

        return self._abort()

    @coroutine
    def _response_callback(self):
        """Kube Post Application Update - Callback."""

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        if response["completed"]:
            if self.strategy is not None:
                self.strategy.nfvi_kube_upgrade = response["result-data"]
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    def apply(self):
        """Kube Post Application Update."""

        from nfv_vim import nfvi

        DLOG.info("Step (%s) apply." % self._name)

        nfvi.nfvi_kube_post_application_update(self._response_callback())
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""


class KubeUpgradeNetworkingStep(AbstractKubeUpgradeStep):
    """Kube Upgrade Networking - Strategy Step."""

    def __init__(self):
        from nfv_vim import nfvi

        super().__init__(
            STRATEGY_STEP_NAME.KUBE_UPGRADE_NETWORKING,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_NETWORKING,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_NETWORKING_FAILED,
            timeout_in_secs=900,
        )

    def abort(self):
        """Returns the abort step related to this step."""

        return self._abort()

    @coroutine
    def _response_callback(self):
        """Kube Upgrade Networking - Callback."""

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        if response["completed"]:
            if self.strategy is not None:
                self.strategy.nfvi_kube_upgrade = response["result-data"]
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    def apply(self):
        """Kube Upgrade Networking."""

        from nfv_vim import nfvi

        DLOG.info("Step (%s) apply." % self._name)

        nfvi.nfvi_kube_upgrade_networking(self._response_callback())
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""


class KubeUpgradeStorageStep(AbstractKubeUpgradeStep):
    """Kube Upgrade Storage - Strategy Step."""

    def __init__(self):
        from nfv_vim import nfvi

        super().__init__(
            STRATEGY_STEP_NAME.KUBE_UPGRADE_STORAGE,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_STORAGE,
            nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_STORAGE_FAILED,
            timeout_in_secs=900,
        )

    def abort(self):
        """Returns the abort step related to this step."""

        return self._abort()

    @coroutine
    def _response_callback(self):
        """Kube Upgrade Storage - Callback."""

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        if response["completed"]:
            if self.strategy is not None:
                self.strategy.nfvi_kube_upgrade = response["result-data"]
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    def apply(self):
        """Kube Upgrade Storage."""

        from nfv_vim import nfvi

        nfvi.nfvi_kube_upgrade_storage(self._response_callback())
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""


class QueryKubeUpgradeStep(AbstractStrategyStep):
    """Query Kube Upgrade."""

    def __init__(self):
        super().__init__(STRATEGY_STEP_NAME.QUERY_KUBE_UPGRADE, timeout_in_secs=60)

    @coroutine
    def _get_kube_upgrade_callback(self):
        """Get Kube Upgrade Callback."""

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        if response["completed"]:
            if self.strategy is not None:
                self.strategy.nfvi_kube_upgrade = response["result-data"]

            result = strategy.STRATEGY_STEP_RESULT.SUCCESS
            self.stage.step_complete(result, "")
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    def apply(self):
        """Query Kube Upgrade."""

        from nfv_vim import nfvi

        DLOG.info("Step (%s) apply." % self._name)
        nfvi.nfvi_get_kube_upgrade(self._get_kube_upgrade_callback())
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""


class QueryKubeVersionsStep(AbstractStrategyStep):
    """Query Kube Versions

    This step should be used with its matching QueryKubeVersionsMixin.
    """

    def __init__(self):
        super().__init__(STRATEGY_STEP_NAME.QUERY_KUBE_VERSIONS, timeout_in_secs=60)

    @coroutine
    def _query_callback(self):
        """Get Kube Versions List Callback."""

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        if response["completed"]:
            if self.strategy is not None:
                self.strategy.nfvi_kube_versions_list = response["result-data"]

            result = strategy.STRATEGY_STEP_RESULT.SUCCESS
            self.stage.step_complete(result, "")
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    def apply(self):
        """Query Kube Versions List."""

        from nfv_vim import nfvi

        DLOG.info("Step (%s) apply." % self._name)
        nfvi.nfvi_get_kube_version_list(self._query_callback())
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""


class QueryKubeHostUpgradeStep(AbstractStrategyStep):
    """Query Kube Host Upgrade list."""

    MAX_RETRIES = 3

    def __init__(self, retry_count=MAX_RETRIES):
        super().__init__(
            STRATEGY_STEP_NAME.QUERY_KUBE_HOST_UPGRADE, timeout_in_secs=200
        )
        self._retry_count = retry_count

    @coroutine
    def _get_kube_host_upgrade_list_callback(self):
        """Get Kube Host Upgrade List Callback."""

        response = yield
        DLOG.debug("%s callback response=%s." % (self._name, response))

        if response["completed"]:
            if self.strategy is not None:
                self.strategy.nfvi_kube_host_upgrade_list = response["result-data"]

            result = strategy.STRATEGY_STEP_RESULT.SUCCESS
            self.stage.step_complete(result, "")
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(result, response["reason"])

    def apply(self):
        """Query Kube Host Upgrade List."""

        from nfv_vim import directors

        DLOG.info("Step (%s) apply." % self._name)

        host_director = directors.get_host_director()
        host_director._nfvi_get_kube_host_upgrade_list()
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""

    def handle_event(self, event, event_data=None):
        """Handle Query Kube Host upgrade event."""

        from nfv_vim import directors

        if event == STRATEGY_EVENT.QUERY_KUBE_HOST_UPGRADE_FAILED:
            if event_data is not None and self._retry_count > 0:
                # if kube host upgrade list fails and we have retries,
                # re-trigger the function
                DLOG.info(
                    "Step (%s) retry due to failure for (%s)."
                    % (self._name, str(event_data["reason"]))
                )

                self._retry_count = self._retry_count - 1
                host_director = directors.get_host_director()
                host_director._nfvi_get_kube_host_upgrade_list()
            else:
                # if kube host upgrade list fails and we are out of retries, fail
                result = strategy.STRATEGY_STEP_RESULT.FAILED
                self.stage.step_complete(result, event_data["reason"])
            return True

        elif event == STRATEGY_EVENT.QUERY_KUBE_HOST_UPGRADE_COMPLETED:
            if event_data is not None and self.strategy is not None:
                self.strategy.nfvi_kube_host_upgrade_list = event_data["result-data"]

            result = strategy.STRATEGY_STEP_RESULT.SUCCESS
            self.stage.step_complete(result, "")

        return False


class KubeHostCordonStep(AbstractKubeHostUpgradeStep):
    """Kube Host Cordon - Strategy Step."""

    def __init__(
        self,
        host,
        to_version,
        force,
        target_state,
        target_failure_state,
        timeout_in_secs=600,
    ):
        super().__init__(
            host,
            to_version,
            force,
            STRATEGY_STEP_NAME.KUBE_HOST_CORDON,
            target_state,
            target_failure_state,
            timeout_in_secs,
        )

    def abort(self):
        """Returns the abort step related to this step."""

        # todo(abailey): Unknown if this should include an uncordon if it fails
        return self._abort()

    def handle_event(self, event, event_data=None):
        """Handle Host events  - does not query kube host upgrade list but

        instead queries kube host upgrade directly.
        """
        DLOG.debug("Step (%s) handle event (%s)." % (self._name, event))

        if event == STRATEGY_EVENT.KUBE_HOST_CORDON_FAILED:
            host = event_data
            if host is not None and host.name in self._host_names:
                result = strategy.STRATEGY_STEP_RESULT.FAILED
                self.stage.step_complete(
                    result, "kube host cordon (%s) failed" % host.name
                )
                return True
        # return handle_event of parent class
        return super().handle_event(event, event_data=event_data)

    def apply(self):
        """Kube Host Cordon."""

        from nfv_vim import directors

        DLOG.info("Step (%s) apply to hostnames (%s)." % (self._name, self._host_names))
        host_director = directors.get_host_director()
        operation = host_director.kube_host_cordon(self._host_names, self._force)
        return validate_operation(operation)


class KubeHostUncordonStep(AbstractKubeHostUpgradeStep):
    """Kube Host Uncordon - Strategy Step."""

    def __init__(
        self,
        host,
        to_version,
        force,
        target_state,
        target_failure_state,
        timeout_in_secs=600,
    ):
        super().__init__(
            host,
            to_version,
            force,
            STRATEGY_STEP_NAME.KUBE_HOST_UNCORDON,
            target_state,
            target_failure_state,
            timeout_in_secs,
        )

    def abort(self):
        """Returns the abort step related to this step."""

        # todo(abailey): Unknown if this should include a cordon if it fails
        return self._abort()

    def handle_event(self, event, event_data=None):
        """Handle Host events  - does not query kube host upgrade list but

        instead queries kube host upgrade directly.
        """
        DLOG.debug("Step (%s) handle event (%s)." % (self._name, event))

        if event == STRATEGY_EVENT.KUBE_HOST_UNCORDON_FAILED:
            host = event_data
            if host is not None and host.name in self._host_names:
                result = strategy.STRATEGY_STEP_RESULT.FAILED
                self.stage.step_complete(
                    result, "kube host uncordon (%s) failed" % host.name
                )
                return True
        # return handle_event of parent class
        return super().handle_event(event, event_data=event_data)

    def apply(self):
        """Kube Host Uncordon."""

        from nfv_vim import directors

        DLOG.info("Step (%s) apply to hostnames (%s)." % (self._name, self._host_names))
        host_director = directors.get_host_director()
        operation = host_director.kube_host_uncordon(self._host_names, self._force)
        return validate_operation(operation)


class KubeHostUpgradeControlPlaneStep(AbstractKubeHostUpgradeStep):
    """Kube Host Upgrade Control Plane - Strategy Step.

    This operation issues a host command, which updates the kube upgrade object
    """

    _MAX_RETRIES = 3

    def __init__(
        self,
        host,
        to_version,
        force,
        target_state,
        target_failure_state,
        timeout_in_secs=420,
    ):
        super().__init__(
            host,
            to_version,
            force,
            STRATEGY_STEP_NAME.KUBE_HOST_UPGRADE_CONTROL_PLANE,
            target_state,
            target_failure_state,
            timeout_in_secs,
        )
        # Not persisted — resets on VIM restart
        self._transient_failure_retry_count = 0

    @coroutine
    def _get_kube_upgrade_callback(self):
        response = yield
        DLOG.debug("(%s) callback response=%s." % (self._name, response))

        self._query_inprogress = False

        if not response["completed"]:
            # Transient errors do not have an error-code
            if response.get("error-code") is None:
                if self._transient_failure_retry_count >= self._MAX_RETRIES:
                    result = strategy.STRATEGY_STEP_RESULT.FAILED
                    self.stage.step_complete(result, response["reason"])
                    return
                else:
                    self._transient_failure_retry_count += 1
                    DLOG.warn(
                        "A transient error occurred during kube-upgrade upgrade "
                        "control plane step, retrying "
                        f"{self._transient_failure_retry_count}/{self._MAX_RETRIES}..."
                    )
                    return

        # A successful or a failure response with an error code resets the counter,
        # because the callback handler will conclude the step.
        self._transient_failure_retry_count = 0
        self._handle_kube_upgrade_callback(response)

    def from_dict(self, data):
        """Returns the step object initialized using the given dictionary."""

        super().from_dict(data)
        self._transient_failure_retry_count = 0
        return self

    def abort(self):
        """Returns the abort step related to this step."""

        # todo(abailey): Unknown if this should include an uncordon if it fails
        return self._abort()

    def handle_event(self, event, event_data=None):
        """Handle Host events  - does not query kube host upgrade list but

        instead queries kube host upgrade directly.
        """
        DLOG.debug("Step (%s) handle event (%s)." % (self._name, event))

        if event == STRATEGY_EVENT.KUBE_HOST_UPGRADE_CONTROL_PLANE_FAILED:
            host = event_data
            if host is not None and host.name in self._host_names:
                result = strategy.STRATEGY_STEP_RESULT.FAILED
                self.stage.step_complete(
                    result, "kube host upgrade control plane (%s) failed" % host.name
                )
                return True
        # return handle_event of parent class
        return super().handle_event(event, event_data=event_data)

    def _is_control_plane_already_upgraded(self, kube_host_upgrade_list):
        """Check if host control plane is already at target version."""

        for host_uuid in self._host_uuids:
            for k_host in kube_host_upgrade_list:
                if k_host.host_uuid != host_uuid:
                    continue
                if k_host.control_plane_version == self._to_version:
                    DLOG.info(
                        "Host %s control plane already at version %s, "
                        "skipping upgrade." % (host_uuid, self._to_version)
                    )
                    return True
                break
        return False

    @coroutine
    def _get_kube_host_upgrade_list_callback(self):
        """Query kube host upgrade list to check if already upgraded."""

        response = yield
        DLOG.debug(
            "(%s) host upgrade list callback response=%s." % (self._name, response)
        )

        if response["completed"] and self.strategy is not None:
            self.strategy.nfvi_kube_host_upgrade_list = response["result-data"]

        if response["completed"] and self._is_control_plane_already_upgraded(
            response["result-data"]
        ):
            self.stage.step_complete(strategy.STRATEGY_STEP_RESULT.SUCCESS, "")
            return

        # Proceed with the upgrade
        from nfv_vim import directors

        host_director = directors.get_host_director()
        operation = host_director.kube_upgrade_hosts_control_plane(
            self._host_names, self._force
        )
        if operation.is_failed():
            self.stage.step_complete(
                strategy.STRATEGY_STEP_RESULT.FAILED, operation.reason
            )

    def apply(self):
        """Kube Host Upgrade Control Plane."""

        from nfv_vim import nfvi

        DLOG.info("Step (%s) apply to hostnames (%s)." % (self._name, self._host_names))
        nfvi.nfvi_get_kube_host_upgrade_list(
            self._get_kube_host_upgrade_list_callback()
        )
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""


class KubeHostUpgradeKubeletStep(AbstractKubeHostListUpgradeStep):
    """Kube Host Upgrade Kubelet - Strategy Step.

    This operation issues a host command, which indirectly updates the kube
    upgrade object, however additional calls to other hosts do not change it.
    """

    def __init__(self, hosts, to_version, force=True):
        super().__init__(
            hosts,
            to_version,
            force,
            STRATEGY_STEP_NAME.KUBE_HOST_UPGRADE_KUBELET,
            None,  # there is no kube upgrade success state for kubelets
            None,  # there is no kube upgrade failure state for kubelets
            timeout_in_secs=900,
        )  # kubelet takes longer than control plane

    def abort(self):
        """Returns the abort step related to this step."""

        # todo(abailey): Unknown if this should include an uncordon if it fails
        return self._abort()

    @coroutine
    def _get_kube_host_upgrade_list_callback(self):
        """Get Kube Host Upgrade List Callback."""

        from nfv_vim import nfvi

        objects_v1 = nfvi.objects.v1.KUBE_HOST_UPGRADE_STATE

        response = yield
        DLOG.debug("(%s) callback response=%s." % (self._name, response))

        self._query_inprogress = False
        if response["completed"]:
            self.strategy.nfvi_kube_host_upgrade_list = response["result-data"]

            host_count = 0
            match_count = 0
            for host_uuid in self._host_uuids:
                for k_host in self.strategy.nfvi_kube_host_upgrade_list:
                    if k_host.host_uuid == host_uuid:
                        if (
                            k_host.kubelet_version == self._to_version
                            and k_host.status == objects_v1.KUBE_HOST_UPGRADED_KUBELET
                        ):
                            DLOG.info(
                                "Kubelet upgraded to version %s for host %s"
                                % (self._to_version, host_uuid)
                            )
                            match_count += 1
                        host_count += 1
                        # break out of inner loop, since uuids match
                        break
                if host_count == len(self._host_uuids):
                    # this is a pointless break
                    break
            if match_count == len(self._host_uuids):
                result = strategy.STRATEGY_STEP_RESULT.SUCCESS
                DLOG.info("Kubelet upgrade completed")
                self.stage.step_complete(result, "")
            else:
                # keep waiting for kubelet state to change
                pass
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            DLOG.info("Kubelet upgrade failed")
            self.stage.step_complete(result, response["reason"])

    def handle_event(self, event, event_data=None):
        """Handle Host events  - queries kube host upgrade list

        Override to bypass checking for kube upgrade state.
        """
        from nfv_vim import nfvi

        DLOG.debug("Step (%s) handle event (%s)." % (self._name, event))

        if event == STRATEGY_EVENT.KUBE_HOST_UPGRADE_KUBELET_FAILED:
            host = event_data
            if host is not None and host.name in self._host_names:
                result = strategy.STRATEGY_STEP_RESULT.FAILED
                self.stage.step_complete(
                    result, "kube host upgrade kubelet (%s) failed" % host.name
                )
                return True
        elif event == STRATEGY_EVENT.KUBE_HOST_UPGRADE_CHANGED:
            DLOG.info(
                "Event %s in progress" % (STRATEGY_EVENT.KUBE_HOST_UPGRADE_CHANGED)
            )
            self._query_inprogress = True
            nfvi.nfvi_get_kube_host_upgrade_list(
                self._get_kube_host_upgrade_list_callback()
            )
            return True
        elif event == STRATEGY_EVENT.HOST_AUDIT:
            DLOG.info("Event %s in progress" % (STRATEGY_EVENT.HOST_AUDIT))
            # Wait time not required as we have a timeout initialized
            # in init method.
            if not self._query_inprogress:
                self._query_inprogress = True
                nfvi.nfvi_get_kube_host_upgrade_list(
                    self._get_kube_host_upgrade_list_callback()
                )
            return True
        return False

    def apply(self):
        """Kube Upgrade Kubelet."""

        from nfv_vim import directors

        DLOG.info("Step (%s) apply to hostnames (%s)." % (self._name, self._host_names))
        host_director = directors.get_host_director()
        operation = host_director.kube_upgrade_hosts_kubelet(
            self._host_names, self._force
        )
        if operation.is_inprogress():
            return strategy.STRATEGY_STEP_RESULT.WAIT, ""
        elif operation.is_failed():
            return strategy.STRATEGY_STEP_RESULT.FAILED, operation.reason

        return strategy.STRATEGY_STEP_RESULT.SUCCESS, ""


class WaitKubernetesUpgradeHealthy(AbstractStrategyStep):
    """Wait for the kubernetes upgrade to be healthy - Strategy Step."""

    def __init__(
        self,
        timeout_in_secs=180,
        first_query_delay_in_secs=15,
        alarm_ignore_list=None,
    ):
        super().__init__(
            STRATEGY_STEP_NAME.KUBE_WAIT_UPGRADE_HEALTHY,
            timeout_in_secs=timeout_in_secs,
        )
        self._first_query_delay_in_secs = first_query_delay_in_secs
        self._wait_time = 0
        self._query_inprogress = False
        self._alarm_ignore_list = alarm_ignore_list or KUBE_UPGRADE_START_ALARM_IGNORE

    @coroutine
    def _query_health_callback(self):
        """Query Health Callback."""

        response = yield
        DLOG.debug("Query-Health callback response=%s." % response)

        self._query_inprogress = False

        if response["completed"]:
            if "result-data" not in response:
                result = strategy.STRATEGY_STEP_RESULT.FAILED
                self.stage.step_complete(
                    result, "Kubernetes upgrade health check missing result-data"
                )
                return
            health_data = response["result-data"]
            if isinstance(health_data, dict):
                health_str = json.dumps(health_data)
            else:
                health_str = str(health_data)
            if "[Fail]" in health_str:
                DLOG.info(
                    "Kubernetes upgrade health check has failures: %s" % health_data
                )
            else:
                result = strategy.STRATEGY_STEP_RESULT.SUCCESS
                self.stage.step_complete(result, "")
        else:
            result = strategy.STRATEGY_STEP_RESULT.FAILED
            self.stage.step_complete(
                result,
                response.get("reason")
                or "Unknown error while trying kubernetes upgrade health check, "
                "check /var/log/nfv-vim.log for more information.",
            )

    def apply(self):
        """Wait for kubernetes upgrade to be healthy."""

        DLOG.info("Step (%s) apply." % self._name)
        return strategy.STRATEGY_STEP_RESULT.WAIT, ""

    def handle_event(self, event, event_data=None):
        """Handle Host events to trigger periodic polling."""

        from nfv_vim import nfvi

        DLOG.debug("Step (%s) handle event (%s)." % (self._name, event))

        if event == STRATEGY_EVENT.HOST_AUDIT:
            if 0 == self._wait_time:
                self._wait_time = timers.get_monotonic_timestamp_in_ms()

            now_ms = timers.get_monotonic_timestamp_in_ms()
            secs_expired = (now_ms - self._wait_time) // 1000
            if (
                self._first_query_delay_in_secs <= secs_expired
                and not self._query_inprogress
            ):
                self._query_inprogress = True
                nfvi.nfvi_get_kube_upgrade_health(
                    self._alarm_ignore_list, self._query_health_callback()
                )
            return True

        return False

    def from_dict(self, data):
        """Returns the step object initialized using the given dictionary."""

        super().from_dict(data)
        self._first_query_delay_in_secs = data["first_query_delay_in_secs"]
        self._wait_time = 0
        self._query_inprogress = False
        self._alarm_ignore_list = data.get(
            "alarm_ignore_list", KUBE_UPGRADE_START_ALARM_IGNORE
        )
        return self

    def as_dict(self):
        """Represent the wait kubernetes upgrade healthy step as a dictionary."""

        data = super().as_dict()
        data["first_query_delay_in_secs"] = self._first_query_delay_in_secs
        data["alarm_ignore_list"] = self._alarm_ignore_list
        return data

    def timeout(self):
        """Strategy Step Timeout Override."""

        result, _ = super().timeout()
        reason = "Kubernetes upgrade did not become healthy before timeout"
        return result, reason
