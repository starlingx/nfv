#
# Copyright (c) 2016-2022 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import itertools

from nfv_vim.api.acl.policies import base
from nfv_vim.api.acl.policies import sw_update_strategy_policy
from nfv_vim.api.acl import policy
from nfv_vim.api import openstack


class AuthenticationApplication(object):
    """
    Authentication Application
    """
    header_env_mapping = {'X-Auth-Token': 'HTTP_X_AUTH_TOKEN'}

    def __init__(self, app):
        self._app = app
        self._token = None
        self._config = openstack.config_load()
        self._directory = openstack.get_directory(
            self._config, openstack.SERVICE_CATEGORY.PLATFORM)

        policy_file_contents = "{}"

        default_rule = base.RuleDefault(
            name='default',
            check_str='rule:admin_in_system_projects',
            description="Base rule.",
        )

        nfv_vim_rules = itertools.chain(
            base.list_rules(),
            sw_update_strategy_policy.list_rules()
        )
        rules = policy.Rules.load_rules(policy_file_contents,
            default_rule,
            nfv_vim_rules)
        policy.set_rules(rules)

    @staticmethod
    def _get_header_value(env, key, default_value=None):
        env_key = 'HTTP_%s' % key.upper().replace('-', '_')
        return env.get(env_key, default_value)

    def __call__(self, env, start_response):
        if self._token is None or self._token.is_expired(within_seconds=0):
            self._token = openstack.get_token(self._directory)

        user_token_id = self._get_header_value(env, 'X-Auth-Token', None)
        user_token = openstack.validate_token(self._directory, self._token,
                                              user_token_id)
        if (user_token is None or user_token.is_expired(within_seconds=0)):
            start_response('403 Forbidden', [])
            return []

        env['auth_context'] = {
            'user': user_token.get_user(),
            'project_name': user_token.get_project_name(),
            'domain_name': user_token.get_project_domain_name(),
            'roles': user_token.get_roles()
        }

        return self._app(env, start_response)
