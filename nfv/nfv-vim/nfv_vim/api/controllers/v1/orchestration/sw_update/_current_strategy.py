#
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import pecan
from pecan import rest
from six.moves import http_client as httplib
from wsme import types as wsme_types
import wsmeext.pecan as wsme_pecan

from nfv_common import debug
from nfv_vim.api._link import Link
from nfv_vim.api.controllers.v1.orchestration.sw_update._sw_update_strategy import CurrentStrategyAPI

DLOG = debug.debug_get_logger('nfv_vim.api.current_strategy')


class StrategyDescription(wsme_types.Base):
    """
    Current Strategy Description
    """
    id = wsme_types.text
    links = wsme_types.wsattr([Link], name='links')

    @classmethod
    def convert(cls):
        url = pecan.request.host_url

        description = StrategyDescription()
        description.id = "current-strategy"
        description.links = [
            Link.make_link('self', url, 'orchestration/current-strategy'),
            Link.make_link('strategy', url, 'orchestration/current-strategy/strategy')]
        return description


class StrategyAPI(rest.RestController):
    """
    Current Strategy Rest API
    """
    @pecan.expose()
    def _lookup(self, key, *remainder):
        if 'strategy' == key:
            return CurrentStrategyAPI(), remainder
        else:
            pecan.abort(httplib.NOT_FOUND)

    @wsme_pecan.wsexpose(StrategyDescription)
    def get(self):
        # NOTE: The reason why convert() is being called for every
        #       request is because we need to get the host url from
        #       the request object to make the links.
        return StrategyDescription.convert()
