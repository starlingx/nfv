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
    KUBE_ROOTCA_UPDATING_PODS_TRUSTBOTHCAS = 'updating-pods-trust-both-cas'
    KUBE_ROOTCA_UPDATED_PODS_TRUSTBOTHCAS = 'updated-pods-trust-both-cas'
    KUBE_ROOTCA_UPDATING_PODS_TRUSTBOTHCAS_FAILED = 'updating-pods-trust-both-cas-failed'
    KUBE_ROOTCA_UPDATING_PODS_TRUSTNEWCA = 'updating-pods-trust-new-ca'
    KUBE_ROOTCA_UPDATED_PODS_TRUSTNEWCA = 'updated-pods-trust-new-ca'
    KUBE_ROOTCA_UPDATING_PODS_TRUSTNEWCA_FAILED = 'updating-pods-trust-new-ca-failed'
    KUBE_ROOTCA_UPDATE_COMPLETED = 'update-completed'
    KUBE_ROOTCA_UPDATE_ABORTED = 'update-aborted'

    KUBE_ROOTCA_UPDATING_HOST_TRUSTBOTHCAS = 'updating-host-trust-both-cas'
    KUBE_ROOTCA_UPDATED_HOST_TRUSTBOTHCAS = 'updated-host-trust-both-cas'
    KUBE_ROOTCA_UPDATING_HOST_TRUSTBOTHCAS_FAILED = 'updating-host-trust-both-cas-failed'
    KUBE_ROOTCA_UPDATING_HOST_UPDATECERTS = 'updating-host-update-certs'
    KUBE_ROOTCA_UPDATED_HOST_UPDATECERTS = 'updated-host-update-certs'
    KUBE_ROOTCA_UPDATING_HOST_UPDATECERTS_FAILED = 'updating-host-update-certs-failed'
    KUBE_ROOTCA_UPDATING_HOST_TRUSTNEWCA = 'updating-host-trust-new-ca'
    KUBE_ROOTCA_UPDATED_HOST_TRUSTNEWCA = 'updated-host-trust-new-ca'
    KUBE_ROOTCA_UPDATING_HOST_TRUSTNEWCA_FAILED = 'updating-host-trust-new-ca-failed'


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
                 host_id,   # this ID is not the same as the sysinv ID
                 hostname,
                 target_rootca_cert,
                 effective_rootca_cert,
                 state,
                 created_at,
                 updated_at):
        super(KubeRootcaHostUpdate, self).__init__('1.0.0')
        self.update(
            dict(host_id=host_id,
                 hostname=hostname,
                 target_rootca_cert=target_rootca_cert,
                 effective_rootca_cert=effective_rootca_cert,
                 state=state,
                 created_at=created_at,
                 updated_at=updated_at)
        )
