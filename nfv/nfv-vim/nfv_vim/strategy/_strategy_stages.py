#
# Copyright (c) 2015-2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import six

from nfv_common import debug
from nfv_common.helpers import Constant
from nfv_common.helpers import Constants
from nfv_common.helpers import Singleton
from nfv_common import strategy

DLOG = debug.debug_get_logger('nfv_vim.strategy.stage')


@six.add_metaclass(Singleton)
class StrategyStageNames(Constants):
    """
    Strategy Stage Names
    """
    # patch stages
    SW_PATCH_QUERY = Constant('sw-patch-query')
    SW_PATCH_CONTROLLERS = Constant('sw-patch-controllers')
    SW_PATCH_STORAGE_HOSTS = Constant('sw-patch-storage-hosts')
    SW_PATCH_SWIFT_HOSTS = Constant('sw-patch-swift-hosts')
    SW_PATCH_WORKER_HOSTS = Constant('sw-patch-worker-hosts')
    # upgrade stages
    SW_UPGRADE_QUERY = Constant('sw-upgrade-query')
    SW_UPGRADE_START = Constant('sw-upgrade-start')
    SW_UPGRADE_CONTROLLERS = Constant('sw-upgrade-controllers')
    SW_UPGRADE_STORAGE_HOSTS = Constant('sw-upgrade-storage-hosts')
    SW_UPGRADE_WORKER_HOSTS = Constant('sw-upgrade-worker-hosts')
    SW_UPGRADE_COMPLETE = Constant('sw-upgrade-complete')
    # firmware update stages
    FW_UPDATE_QUERY = Constant('fw-update-query')
    FW_UPDATE_HOSTS_QUERY = Constant('fw-update-hosts-query')
    FW_UPDATE_HOST_QUERY = Constant('fw-update-host-query')
    FW_UPDATE_WORKER_HOSTS = Constant('fw-update-worker-hosts')
    # kube root ca update stages
    KUBE_ROOTCA_UPDATE_CERT = Constant('kube-rootca-update-cert')
    KUBE_ROOTCA_UPDATE_COMPLETE = Constant('kube-rootca-update-complete')
    KUBE_ROOTCA_UPDATE_HOSTS_TRUSTBOTHCAS = \
        Constant('kube-rootca-update-hosts-trustbothcas')
    KUBE_ROOTCA_UPDATE_HOSTS_TRUSTNEWCA = \
        Constant('kube-rootca-update-hosts-trustnewca')
    KUBE_ROOTCA_UPDATE_HOSTS_UPDATECERTS = \
        Constant('kube-rootca-update-hosts-updatecerts')
    KUBE_ROOTCA_UPDATE_PODS_TRUSTBOTHCAS = \
        Constant('kube-rootca-update-pods-trustbothcas')
    KUBE_ROOTCA_UPDATE_PODS_TRUSTNEWCA = \
        Constant('kube-rootca-update-pods-trustnewca')
    KUBE_ROOTCA_UPDATE_QUERY = Constant('kube-rootca-update-query')
    KUBE_ROOTCA_UPDATE_START = Constant('kube-rootca-update-start')
    # kube upgrade stages
    KUBE_UPGRADE_QUERY = Constant('kube-upgrade-query')
    KUBE_UPGRADE_START = Constant('kube-upgrade-start')
    KUBE_UPGRADE_DOWNLOAD_IMAGES = Constant('kube-upgrade-download-images')
    KUBE_UPGRADE_FIRST_CONTROL_PLANE = \
        Constant('kube-upgrade-first-control-plane')
    KUBE_UPGRADE_NETWORKING = Constant('kube-upgrade-networking')
    KUBE_UPGRADE_SECOND_CONTROL_PLANE = \
        Constant('kube-upgrade-second-control-plane')
    KUBE_UPGRADE_PATCH = Constant('kube-upgrade-patch')
    KUBE_UPGRADE_KUBELETS_CONTROLLERS = \
       Constant('kube-upgrade-kubelets-controllers')
    KUBE_UPGRADE_KUBELETS_WORKERS = Constant('kube-upgrade-kubelets-workers')
    KUBE_UPGRADE_COMPLETE = Constant('kube-upgrade-complete')
    KUBE_UPGRADE_CLEANUP = Constant('kube-upgrade-cleanup')


# Constant Instantiation
STRATEGY_STAGE_NAME = StrategyStageNames()


def strategy_stage_rebuild_from_dict(data):
    """
    Returns the strategy stage object initialized using the given dictionary
    """
    from nfv_vim.strategy._strategy_steps import strategy_step_rebuild_from_dict

    steps = list()
    for step_data in data['steps']:
        step = strategy_step_rebuild_from_dict(step_data)
        steps.append(step)

    stage_obj = object.__new__(strategy.StrategyStage)
    stage_obj.from_dict(data, steps)
    return stage_obj
