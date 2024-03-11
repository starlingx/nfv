#
# Copyright (c) 2015-2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import pecan
from pecan import rest
from six.moves import http_client as httplib
from wsme import types as wsme_types
import wsmeext.pecan as wsme_pecan

from nfv_vim.api._link import Link
from nfv_vim.api.controllers.v1.orchestration.sw_update import FwUpdateAPI
from nfv_vim.api.controllers.v1.orchestration.sw_update import KubeRootcaUpdateAPI
from nfv_vim.api.controllers.v1.orchestration.sw_update import KubeUpgradeAPI
from nfv_vim.api.controllers.v1.orchestration.sw_update import StrategyAPI
from nfv_vim.api.controllers.v1.orchestration.sw_update import SwPatchAPI
from nfv_vim.api.controllers.v1.orchestration.sw_update import SwUpgradeAPI
from nfv_vim.api.controllers.v1.orchestration.sw_update import SystemConfigUpdateAPI


class OrchestrationDescription(wsme_types.Base):
    """
    Orchestration Description
    """
    id = wsme_types.text
    links = wsme_types.wsattr([Link], name='links')

    @classmethod
    def convert(cls):
        url = pecan.request.host_url

        description = OrchestrationDescription()
        description.id = "orchestration"
        description.links = [
            Link.make_link('self', url, 'orchestration'),
            Link.make_link('sw-patch', url, 'orchestration/sw-patch', ''),
            Link.make_link('sw-upgrade', url, 'orchestration/sw-upgrade', ''),
            Link.make_link('system-config-update',
                           url, 'orchestration/system-config-update', ''),
            Link.make_link('kube-rootca-update',
                           url, 'orchestration/kube-rootca-update', ''),
            Link.make_link('kube-upgrade',
                           url, 'orchestration/kube-upgrade', ''),
            Link.make_link('fw-update', url, 'orchestration/fw-update', ''),
            Link.make_link('current-strategy', url, 'orchestration/current-strategy', '')]
        return description


class OrchestrationAPI(rest.RestController):
    """
    Orchestration API
    """
    @pecan.expose()
    def _lookup(self, key, *remainder):
        if 'sw-patch' == key:
            return SwPatchAPI(), remainder
        elif 'sw-upgrade' == key:
            return SwUpgradeAPI(), remainder
        elif 'system-config-update' == key:
            return SystemConfigUpdateAPI(), remainder
        elif 'fw-update' == key:
            return FwUpdateAPI(), remainder
        elif 'kube-rootca-update' == key:
            return KubeRootcaUpdateAPI(), remainder
        elif 'kube-upgrade' == key:
            return KubeUpgradeAPI(), remainder
        elif 'current-strategy' == key:
            return StrategyAPI(), remainder
        else:
            pecan.abort(httplib.NOT_FOUND)

    @wsme_pecan.wsexpose(OrchestrationDescription)
    def get(self):
        # NOTE: The reason why convert() is being called for every
        #       request is because we need to get the host url from
        #       the request object to make the links.
        return OrchestrationDescription.convert()
