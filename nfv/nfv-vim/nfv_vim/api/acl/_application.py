#
# Copyright (c) 2016-2023, 2025-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import itertools

from nfv_common import debug

from nfv_vim.api.acl.policies import base
from nfv_vim.api.acl.policies import fw_update_strategy_policy
from nfv_vim.api.acl.policies import kube_rootca_update_strategy_policy
from nfv_vim.api.acl.policies import kube_upgrade_strategy_policy
from nfv_vim.api.acl.policies import sw_patch_strategy_policy
from nfv_vim.api.acl.policies import sw_update_strategy_policy
from nfv_vim.api.acl.policies import sw_upgrade_strategy_policy
from nfv_vim.api.acl.policies import system_config_update_strategy_policy

from nfv_vim.api.acl import policy
from nfv_vim.api import openstack
from platform_util.oidc import oidc_utils

DLOG = debug.debug_get_logger("nfv_vim.api.acl.application")


class AuthenticationApplication(object):
    """Authentication Application."""

    def __init__(self, app):
        self._app = app
        self._token = None
        self._oidc_token_cache = {}  # Persistent OIDC token cache
        self._config = openstack.config_load()
        self._directory = openstack.get_directory(
            self._config, openstack.SERVICE_CATEGORY.PLATFORM
        )

        policy_file_contents = "{}"

        default_rule = base.RuleDefault(
            name="default",
            check_str="rule:admin_in_system_projects",
            description="Base rule.",
        )

        nfv_vim_rules = itertools.chain(
            base.list_rules(),
            sw_update_strategy_policy.list_rules(),
            fw_update_strategy_policy.list_rules(),
            kube_rootca_update_strategy_policy.list_rules(),
            kube_upgrade_strategy_policy.list_rules(),
            sw_patch_strategy_policy.list_rules(),
            sw_upgrade_strategy_policy.list_rules(),
            system_config_update_strategy_policy.list_rules(),
        )
        rules = policy.Rules.load_rules(
            policy_file_contents, default_rule, nfv_vim_rules
        )
        policy.set_rules(rules)

    @staticmethod
    def _get_header_value(env, key, default_value=None):
        env_key = "HTTP_%s" % key.upper().replace("-", "_")
        return env.get(env_key, default_value)

    def _validate_oidc_token(self, oidc_token):
        """Validate OIDC token and return auth context."""

        try:
            # Get token claims
            claims = oidc_utils.get_oidc_token_claims(
                oidc_token, self._oidc_token_cache
            )

            # Parse claims to get username and roles
            auth_info = oidc_utils.parse_oidc_token_claims(
                claims, domain="Default", project="admin"
            )

            return {
                "user": auth_info["username"],
                "project_name": "admin",  # Default project for OIDC
                "domain_name": "Default",  # Default domain name for OIDC
                "roles": auth_info["roles"],
            }

        except ValueError as e:
            DLOG.error("OIDC token validation failed: %s" % str(e))
            return None
        except Exception as e:
            DLOG.exception("Caught OIDC token validation exception err=%s" % (e))
            self._oidc_token_cache = {}
            return None

    def __call__(self, env, start_response):
        # Try Keystone authentication first
        # prioritize over OIDC in case of both headers
        user_token_id = self._get_header_value(env, "X-Auth-Token", None)
        if user_token_id:
            if self._token is None or self._token.is_expired(within_seconds=0):
                self._token = openstack.get_token(self._directory)

            user_token = openstack.validate_token(
                self._directory, self._token, user_token_id
            )
            if user_token is None or user_token.is_expired(within_seconds=0):
                DLOG.error("Keystone authentication failed")
                start_response("403 Forbidden", [])
                return []

            env["auth_context"] = {
                "user": user_token.get_user(),
                "project_name": user_token.get_project_name(),
                "domain_name": user_token.get_project_domain_name(),
                "roles": user_token.get_roles(),
            }
            return self._app(env, start_response)

        # Fall back to OIDC authentication only if no Keystone token
        oidc_token = self._get_header_value(env, "OIDC-Token", None)
        if oidc_token:
            auth_context = self._validate_oidc_token(oidc_token)
            if auth_context:
                DLOG.debug("OIDC authentication successful")
                env["auth_context"] = auth_context
                return self._app(env, start_response)
            else:
                DLOG.error("OIDC authentication failed")

        start_response("403 Forbidden", [])
        return []
