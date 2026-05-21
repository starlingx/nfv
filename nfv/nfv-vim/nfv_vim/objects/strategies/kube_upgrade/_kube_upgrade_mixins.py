#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_common import debug
from nfv_common.helpers import coroutine
from nfv_vim.strategy._strategy_stages import KUBE_STAGE_PREFIXES

DLOG = debug.debug_get_logger("nfv_vim.objects.strategies.kube_upgrade")


class KubeUpgradeMixin:
    """Mixin for objects that need to audit Kubernetes Upgrade status."""

    def _init_kube_upgrade_state(self):
        self._kube_upgrade = None
        self._kube_upgrade_hosts = []
        self._alarm_context = None

    @coroutine
    def nfvi_kube_upgrade_callback(self, timer_id):
        """Audit Kube Upgrade Callback"""
        from nfv_vim import strategy

        response = yield

        if response["completed"]:
            DLOG.debug("Audit-Kube-Upgrade callback, response=%s." % response)
            last_state = self._kube_upgrade.state if self._kube_upgrade else None
            self._kube_upgrade = response["result-data"]
            current_state = self._kube_upgrade.state if self._kube_upgrade else None
            if last_state != current_state:
                self.handle_event(
                    strategy.STRATEGY_EVENT.KUBE_UPGRADE_CHANGED, self._kube_upgrade
                )
        else:
            DLOG.error(
                "Audit-Kube-Upgrade callback, not completed, response=%s." % response
            )

        self._nfvi_audit_inprogress = False

    @coroutine
    def nfvi_kube_host_upgrade_list_callback(self, timer_id):
        """Audit Kube Host Upgrade Callback"""
        from nfv_vim import strategy

        response = yield

        if response["completed"]:
            DLOG.debug("Audit-Kube-Host-Upgrade callback, response=%s." % response)
            self._kube_upgrade_hosts = response["result-data"]
            # todo(abailey): this needs to detect the change
            self.handle_event(
                strategy.STRATEGY_EVENT.KUBE_HOST_UPGRADE_CHANGED, self._kube_upgrade
            )
        else:
            DLOG.error(
                "Audit-Kube-Upgrade callback, not completed, response=%s." % response
            )

        self._nfvi_audit_inprogress = False

    def _is_kube_upgrade_active(self):
        """Check if the current executing stage is a Kubernetes Upgrade stage."""
        if (
            self.strategy is None
            or getattr(self.strategy, "kube_to_version", None) is None
        ):
            return False

        phase = self.strategy.apply_phase
        current_stage_index = phase.current_stage
        if current_stage_index < len(phase.stages):
            stage = phase.stages[current_stage_index]
            if any(
                stage.name.startswith(prefix.value) for prefix in KUBE_STAGE_PREFIXES
            ):
                return True

        return False
