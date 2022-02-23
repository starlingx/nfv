#
# Copyright (c) 2015-2016, 2022 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from pecan import hooks
import re
from six.moves.urllib.parse import urlparse
import time

from nfv_common import config
from nfv_common import debug
from nfv_common import tcp

from nfv_common.helpers import Object


DLOG = debug.debug_get_logger('nfv_vim.api')


class VimConnectionMgmt(object):
    """
    VIM Connection Management
    """
    def __init__(self):
        super(VimConnectionMgmt, self).__init__()

        self._connections = list()

    def open_connection(self):
        """
        Open a connection to the VIM
        """
        connection = tcp.TCPConnection(config.CONF['vim-api']['rpc_host'],
                                       config.CONF['vim-api']['rpc_port'])
        connection.connect(config.CONF['vim']['rpc_host'],
                           config.CONF['vim']['rpc_port'])
        self._connections.append(connection)
        return connection

    def close_connection(self, connection):
        """
        Close a connection to the VIM
        """
        if connection in self._connections:
            self._connections.remove(connection)

        connection.close()

    def close_connections(self):
        """
        Close all connections to the VIM
        """
        for connection in self._connections:
            connection.close()


class ConnectionHook(hooks.PecanHook):
    """
    Connection Hook
    """
    def __init__(self):
        super(ConnectionHook, self).__init__()

    def before(self, state):
        state.request.vim = VimConnectionMgmt()

    def after(self, state):
        try:
            getattr(state.request, 'vim')

        except AttributeError:
            pass

        else:
            if state.request.vim is not None:
                state.request.vim.close_connections()


class ContextHook(hooks.PecanHook):
    """
    Context Hook
    """
    def __init__(self, acl_public_routes):
        super(ContextHook, self).__init__()
        self.acl_public_routes = acl_public_routes

    def before(self, state):
        auth_token = state.request.headers.get('X-Auth-Token', None)
        state.request.context = Object(auth_token=auth_token)


class AuditLoggingHook(hooks.PecanHook):
    """
        Performs audit logging of all Fault Manager
        ["POST", "PUT", "PATCH", "DELETE"] REST requests.
    """

    def __init__(self):
        self.log_methods = ["POST", "PUT", "PATCH", "DELETE"]

    def before(self, state):
        state.request.start_time = time.time()

    def __after(self, state):

        method = state.request.method
        if method not in self.log_methods:
            return

        now = time.time()
        try:
            elapsed = now - state.request.start_time
        except AttributeError:
            DLOG.info("Start time is not in request, setting it to 0.")
            elapsed = 0

        environ = state.request.environ
        server_protocol = environ["SERVER_PROTOCOL"]

        response_content_length = state.response.content_length

        user_id = state.request.headers.get('X-User-Id')
        user_name = state.request.headers.get('X-User', user_id)
        tenant_id = state.request.headers.get('X-Tenant-Id')
        tenant = state.request.headers.get('X-Tenant', tenant_id)
        domain_name = state.request.headers.get('X-User-Domain-Name')

        url_path = urlparse(state.request.path_qs).path

        def json_post_data(rest_state):
            if 'form-data' in rest_state.request.headers.get('Content-Type'):
                return " POST: {}".format(rest_state.request.params)
            if not hasattr(rest_state.request, 'json'):
                return ""
            return " POST: {}".format(rest_state.request.json)

        # Filter password from log
        filtered_json = re.sub(r'{[^{}]*(passwd_hash|community|password)[^{}]*},*',
                               '',
                               json_post_data(state))

        log_data = \
            "{} \"{} {} {}\" status: {} len: {} time: {}{} host:{}" \
            " agent:{} user: {} tenant: {} domain: {}".format(
                state.request.remote_addr,
                state.request.method,
                url_path,
                server_protocol,
                state.response.status_int,
                response_content_length,
                elapsed,
                filtered_json,
                state.request.host,
                state.request.user_agent,
                user_name,
                tenant,
                domain_name)

        DLOG.info("{}".format(log_data))

    def after(self, state):
        try:
            self.__after(state)
        except Exception:
            # Logging and then swallowing exception to ensure
            # rest service does not fail even if audit logging fails
            DLOG.exception("Exception in AuditLoggingHook on event 'after'")

    def on_error(self, state, e):
        DLOG.exception("Exception in AuditLoggingHook passed to event 'on_error': " + str(e))
