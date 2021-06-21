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
class KubeRootcaUpdateState(Constants):
    """
    Kube RootCA Update State Constants
    These values are copied from sysinv/common/kubernetes.py
    """
    KUBE_ROOTCA_UPDATE_STARTED = Constant('update-started')
    KUBE_ROOTCA_UPDATE_CERT_UPLOADED = Constant('update-new-rootca-cert-uploaded')
    KUBE_ROOTCA_UPDATE_CERT_GENERATED = Constant('update-new-rootca-cert-generated')
    KUBE_ROOTCA_UPDATING_PODS_TRUSTBOTHCAS = Constant('updating-pods-trustBothCAs')
    KUBE_ROOTCA_UPDATED_PODS_TRUSTBOTHCAS = Constant('updated-pods-trustBothCAs')
    KUBE_ROOTCA_UPDATING_PODS_TRUSTBOTHCAS_FAILED = Constant('updating-pods-trustBothCAs-failed')
    KUBE_ROOTCA_UPDATING_PODS_TRUSTNEWCA = Constant('updating-pods-trustNewCA')
    KUBE_ROOTCA_UPDATED_PODS_TRUSTNEWCA = Constant('updated-pods-trustNewCA')
    KUBE_ROOTCA_UPDATING_PODS_TRUSTNEWCA_FAILED = Constant('updating-pods-trustNewCA-failed')
    KUBE_ROOTCA_UPDATE_COMPLETED = Constant('update-completed')
    KUBE_ROOTCA_UPDATING_HOST_TRUSTBOTHCAS = Constant('updating-host-trustBothCAs')
    KUBE_ROOTCA_UPDATED_HOST_TRUSTBOTHCAS = Constant('updated-host-trustBothCAs')
    KUBE_ROOTCA_UPDATING_HOST_TRUSTBOTHCAS_FAILED = Constant('updating-host-trustBothCAs-failed')
    KUBE_ROOTCA_UPDATING_HOST_UPDATECERTS = Constant('updating-host-updateCerts')
    KUBE_ROOTCA_UPDATED_HOST_UPDATECERTS = Constant('updated-host-updateCerts')
    KUBE_ROOTCA_UPDATING_HOST_UPDATECERTS_FAILED = Constant('updating-host-updateCerts-failed')
    KUBE_ROOTCA_UPDATING_HOST_TRUSTNEWCA = Constant('updating-host-trustNewCA')
    KUBE_ROOTCA_UPDATED_HOST_TRUSTNEWCA = Constant('updated-host-trustNewCA')
    KUBE_ROOTCA_UPDATING_HOST_TRUSTNEWCA_FAILED = Constant('updating-host-trustNewCA-failed')


# Kube Upgrade Constant Instantiation
KUBE_ROOTCA_UPDATE_STATE = KubeRootcaUpdateState()


class KubeRootcaUpdate(ObjectData):
    """
    NFVI Kube RootCA Update Object
    """
    def __init__(self, state):
        super(KubeRootcaUpdate, self).__init__('1.0.0')
        self.update(
            dict(state=state)
        )


class KubeRootcaHostUpdate(ObjectData):
    """
    NFVI Kube RootCA Host Update Object
    """
    def __init__(self,
                 host_id,
                 hostname,
                 target_rootca_cert,
                 effective_rootca_cert,
                 state):
        super(KubeRootcaHostUpdate, self).__init__('1.0.0')
        self.update(
            dict(host_id=host_id,
                 hostname=hostname,
                 target_rootca_cert=target_rootca_cert,
                 effective_rootca_cert=effective_rootca_cert,
                 state=state)
        )
