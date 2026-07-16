#
# Copyright (c) 2015-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_common.helpers import Constant
from nfv_common.helpers import Constants
from nfv_common.helpers import Singleton


class StrategyStepNames(Constants, metaclass=Singleton):
    """Strategy Step Names."""

    SYSTEM_STABILIZE = Constant("system-stabilize")
    LOCK_HOSTS = Constant("lock-hosts")
    UNLOCK_HOSTS = Constant("unlock-hosts")
    REBOOT_HOSTS = Constant("reboot-hosts")
    SW_DEPLOY_DO_NOTHING = Constant("sw-deploy-do-nothing")
    UPGRADE_HOSTS = Constant("upgrade-hosts")
    SW_DEPLOY_PRECHECK = Constant("sw-deploy-precheck")
    START_UPGRADE = Constant("start-upgrade")
    ACTIVATE_UPGRADE = Constant("activate-upgrade")
    SW_DEPLOY_ABORT = Constant("sw-deploy-abort")
    SW_DEPLOY_ACTIVATE_ROLLBACK = Constant("sw-deploy-activate-rollback")
    COMPLETE_UPGRADE = Constant("complete-upgrade")
    SW_DEPLOY_DELETE = Constant("deploy-delete")
    SW_SYSTEM_DEPLOY_INIT = Constant("sw-system-deploy-init")
    SW_SYSTEM_DEPLOY_DELETE = Constant("sw-system-deploy-delete")
    SWACT_HOSTS = Constant("swact-hosts")
    FW_UPDATE_HOSTS = Constant("fw-update-hosts")
    FW_UPDATE_ABORT_HOSTS = Constant("fw-update-abort-hosts")
    MIGRATE_INSTANCES = Constant("migrate-instances")
    MIGRATE_INSTANCES_FROM_HOST = Constant("migrate-instances-from-host")
    STOP_INSTANCES = Constant("stop-instances")
    START_INSTANCES = Constant("start-instances")
    QUERY_ALARMS = Constant("query-alarms")
    WAIT_DATA_SYNC = Constant("wait-data-sync")
    WAIT_ALARMS_CLEAR = Constant("wait-alarms-clear")
    QUERY_FW_UPDATE_HOST = Constant("query-fw-update-host")
    QUERY_UPGRADE = Constant("query-upgrade")
    DISABLE_HOST_SERVICES = Constant("disable-host-services")
    ENABLE_HOST_SERVICES = Constant("enable-host-services")
    # kube rootca update steps
    KUBE_ROOTCA_UPDATE_ABORT = Constant("kube-rootca-update-abort")
    KUBE_ROOTCA_UPDATE_COMPLETE = Constant("kube-rootca-update-complete")
    KUBE_ROOTCA_UPDATE_GENERATE_CERT = Constant("kube-rootca-update-generate-cert")
    KUBE_ROOTCA_UPDATE_HOST_TRUSTBOTHCAS = Constant(
        "kube-rootca-update-host-trustbothcas"
    )
    KUBE_ROOTCA_UPDATE_HOST_TRUSTNEWCA = Constant("kube-rootca-update-host-trustnewca")
    KUBE_ROOTCA_UPDATE_HOST_UPDATECERTS = Constant(
        "kube-rootca-update-host-update-certs"
    )
    KUBE_ROOTCA_UPDATE_PODS_TRUSTBOTHCAS = Constant(
        "kube-rootca-update-pods-trustbothcas"
    )
    KUBE_ROOTCA_UPDATE_PODS_TRUSTNEWCA = Constant("kube-rootca-update-pods-trustnewca")
    KUBE_ROOTCA_UPDATE_START = Constant("kube-rootca-update-start")
    QUERY_KUBE_ROOTCA_UPDATE = Constant("query-kube-rootca-update")
    QUERY_KUBE_ROOTCA_HOST_UPDATES = Constant("query-kube-rootca-host-updates")
    # kube upgrade steps
    WAIT_KUBE_CONTROL_PLANE_PODS_READY = Constant("wait-kube-control-plane-pods-ready")
    APPLY_PATCHES = Constant("apply-patches")
    QUERY_KUBE_HOST_UPGRADE = Constant("query-kube-host-upgrade")
    QUERY_KUBE_UPGRADE = Constant("query-kube-upgrade")
    QUERY_KUBE_VERSIONS = Constant("query-kube-versions")
    KUBE_HOST_CORDON = Constant("kube-host-cordon")
    KUBE_HOST_UNCORDON = Constant("kube-host-uncordon")
    KUBE_UPGRADE_ABORT = Constant("kube-upgrade-abort")
    KUBE_UPGRADE_START = Constant("kube-upgrade-start")
    KUBE_UPGRADE_CLEANUP = Constant("kube-upgrade-cleanup")
    KUBE_UPGRADE_CLEANUP_ABORTED = Constant("kube-upgrade-cleanup-aborted")
    KUBE_UPGRADE_COMPLETE = Constant("kube-upgrade-complete")
    KUBE_UPGRADE_DOWNLOAD_IMAGES = Constant("kube-upgrade-download-images")
    KUBE_UPGRADE_NETWORKING = Constant("kube-upgrade-networking")
    KUBE_UPGRADE_STORAGE = Constant("kube-upgrade-storage")
    KUBE_HOST_UPGRADE_CONTROL_PLANE = Constant("kube-host-upgrade-control-plane")
    KUBE_HOST_UPGRADE_KUBELET = Constant("kube-host-upgrade-kubelet")
    KUBE_PRE_APPLICATION_UPDATE = Constant("kube-pre-application-update")
    KUBE_POST_APPLICATION_UPDATE = Constant("kube-post-application-update")
    # system config update specific steps
    QUERY_SYSTEM_CONFIG_UPDATE_HOSTS = Constant("query-system-config-update-hosts")
    SYSTEM_CONFIG_UPDATE_HOSTS = Constant("system-config-update-hosts")
    # Retryable swact failure classifications
    HOST_SWACT_RETRY_CONFIG_NOT_APPLIED = Constant(
        "host-swact-retry-config-not-applied"
    )
    HOST_SWACT_RETRY_APPLY_IN_PROGRESS = Constant("host-swact-retry-apply-in-progress")


# Constant Instantiation
STRATEGY_STEP_NAME = StrategyStepNames()
