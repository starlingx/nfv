#
# Copyright (c) 2016-2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import six

from nfv_common.helpers import Constant
from nfv_common.helpers import Constants
from nfv_common.helpers import Singleton

from nfv_vim.nfvi.objects.v1._object import ObjectData


@six.add_metaclass(Singleton)
class KubeUpgradeState(Constants):
    """
    Kube Upgrade State Constants
    These values are copied from sysinv/common/kubernetes.py
    """

    KUBE_UPGRADE_STARTED = Constant('upgrade-started')
    KUBE_UPGRADE_DOWNLOADING_IMAGES = Constant('downloading-images')
    KUBE_UPGRADE_DOWNLOADING_IMAGES_FAILED = Constant('downloading-images-failed')
    KUBE_UPGRADE_DOWNLOADED_IMAGES = Constant('downloaded-images')
    KUBE_UPGRADING_FIRST_MASTER = Constant('upgrading-first-master')
    KUBE_UPGRADING_FIRST_MASTER_FAILED = Constant('upgrading-first-master-failed')
    KUBE_UPGRADED_FIRST_MASTER = Constant('upgraded-first-master')
    KUBE_UPGRADING_NETWORKING = Constant('upgrading-networking')
    KUBE_UPGRADING_NETWORKING_FAILED = Constant('upgrading-networking-failed')
    KUBE_UPGRADED_NETWORKING = Constant('upgraded-networking')
    KUBE_UPGRADING_SECOND_MASTER = Constant('upgrading-second-master')
    KUBE_UPGRADING_SECOND_MASTER_FAILED = Constant('upgrading-second-master-failed')
    KUBE_UPGRADED_SECOND_MASTER = Constant('upgraded-second-master')
    KUBE_UPGRADING_KUBELETS = Constant('upgrading-kubelets')
    KUBE_UPGRADE_COMPLETE = Constant('upgrade-complete')


# Kube Upgrade Constant Instantiation
KUBE_UPGRADE_STATE = KubeUpgradeState()


class KubeHostUpgrade(ObjectData):
    """
    NFVI Kube Host Upgrade Object
    """
    def __init__(self,
                 host_id,
                 host_uuid,
                 target_version,
                 control_plane_version,
                 kubelet_version,
                 status):
        super(KubeHostUpgrade, self).__init__('1.0.0')
        self.update(
            dict(host_id=host_id,
                 host_uuid=host_uuid,
                 target_version=target_version,
                 control_plane_version=control_plane_version,
                 kubelet_version=kubelet_version,
                 status=status
            )
        )


class KubeUpgrade(ObjectData):
    """
    NFVI Kube Upgrade Object
    """
    def __init__(self, state, from_version, to_version):
        super(KubeUpgrade, self).__init__('1.0.0')
        self.update(
            dict(state=state,
                 from_version=from_version,
                 to_version=to_version
            )
        )


class KubeVersion(ObjectData):
    """
    NFVI Kube Version Object
    """
    def __init__(self,
                 kube_version,
                 state,
                 target,
                 upgrade_from,
                 downgrade_to,
                 applied_patches,
                 available_patches):
        super(KubeVersion, self).__init__('1.0.0')
        self.update(
            dict(kube_version=kube_version,
                 state=state,
                 target=target,
                 upgrade_from=upgrade_from,
                 downgrade_to=downgrade_to,
                 applied_patches=applied_patches,
                 available_patches=available_patches
            )
        )
