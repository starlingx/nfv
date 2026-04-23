#
# Copyright (c) 2025-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import testtools

from nfv_vim.api.acl._application import AuthenticationApplication
from unittest import mock


class TestAuthenticationApplication(testtools.TestCase):

    def setUp(self):
        super(TestAuthenticationApplication, self).setUp()
        with mock.patch("nfv_vim.api.openstack.config_load"), mock.patch(
            "nfv_vim.api.openstack.get_directory"
        ), mock.patch("nfv_vim.api.acl.policy.set_rules"):
            self.app = AuthenticationApplication(mock.Mock())

    @mock.patch("nfv_vim.api.openstack.get_token")
    @mock.patch("nfv_vim.api.openstack.validate_token")
    def test_call_keystone_auth_success(self, mock_validate, mock_get_token):
        # Setup mocks
        mock_token = mock.Mock()
        mock_token.is_expired.return_value = False
        mock_token.get_user.return_value = "testuser"
        mock_token.get_project_name.return_value = "testproject"
        mock_token.get_project_domain_name.return_value = "Default"
        mock_token.get_roles.return_value = ["admin"]

        mock_validate.return_value = mock_token
        mock_get_token.return_value = mock.Mock()

        env = {"HTTP_X_AUTH_TOKEN": "keystone-token"}
        start_response = mock.Mock()

        self.app._app = mock.Mock(return_value=["response"])
        result = self.app(env, start_response)

        self.assertEqual(result, ["response"])
        self.assertIn("auth_context", env)
        self.assertEqual(env["auth_context"]["user"], "testuser")

    @mock.patch("nfv_vim.api.openstack.get_token")
    @mock.patch("nfv_vim.api.openstack.validate_token")
    def test_call_keystone_auth_expired_token(self, mock_validate, mock_get_token):
        mock_token = mock.Mock()
        mock_token.is_expired.return_value = True
        mock_validate.return_value = mock_token
        mock_get_token.return_value = mock.Mock()

        env = {"HTTP_X_AUTH_TOKEN": "expired-token"}
        start_response = mock.Mock()

        result = self.app(env, start_response)

        self.assertEqual(result, [])
        start_response.assert_called_with("403 Forbidden", [])

    @mock.patch("nfv_vim.api.openstack.validate_token")
    def test_call_oidc_auth_success(self, mock_validate):
        # No keystone token, use OIDC
        mock_validate.return_value = None

        with mock.patch.object(self.app, "_validate_oidc_token") as mock_oidc:
            mock_oidc.return_value = {
                "user": "oidcuser",
                "project_name": "admin",
                "domain_name": "Default",
                "roles": ["member"],
            }

            env = {"HTTP_OIDC_TOKEN": "oidc-token"}
            start_response = mock.Mock()
            self.app._app = mock.Mock(return_value=["oidc-response"])

            result = self.app(env, start_response)

            self.assertEqual(result, ["oidc-response"])
            self.assertIn("auth_context", env)
            self.assertEqual(env["auth_context"]["user"], "oidcuser")

    def test_call_oidc_auth_failed(self):
        with mock.patch.object(self.app, "_validate_oidc_token") as mock_oidc:
            mock_oidc.return_value = None

            env = {"HTTP_OIDC_TOKEN": "invalid-oidc-token"}
            start_response = mock.Mock()

            result = self.app(env, start_response)

            self.assertEqual(result, [])
            start_response.assert_called_with("403 Forbidden", [])

    def test_call_no_auth_token(self):
        env = {}
        start_response = mock.Mock()

        result = self.app(env, start_response)

        self.assertEqual(result, [])
        start_response.assert_called_with("403 Forbidden", [])

    @mock.patch("nfv_vim.api.openstack.get_token")
    @mock.patch("nfv_vim.api.openstack.validate_token")
    def test_call_keystone_priority_over_oidc(self, mock_validate, mock_get_token):
        # Both tokens present, keystone should take priority
        mock_token = mock.Mock()
        mock_token.is_expired.return_value = False
        mock_token.get_user.return_value = "keystoneuser"
        mock_token.get_project_name.return_value = "project"
        mock_token.get_project_domain_name.return_value = "Default"
        mock_token.get_roles.return_value = ["admin"]

        mock_validate.return_value = mock_token
        mock_get_token.return_value = mock.Mock()

        env = {"HTTP_X_AUTH_TOKEN": "keystone-token", "HTTP_OIDC_TOKEN": "oidc-token"}
        start_response = mock.Mock()
        self.app._app = mock.Mock(return_value=["keystone-response"])

        result = self.app(env, start_response)

        self.assertEqual(result, ["keystone-response"])
        self.assertEqual(env["auth_context"]["user"], "keystoneuser")

    @mock.patch("platform_util.oidc.oidc_utils.get_oidc_token_claims")
    @mock.patch("platform_util.oidc.oidc_utils.parse_oidc_token_claims")
    def test_validate_oidc_token_success(self, mock_parse, mock_claims):
        mock_claims.return_value = {"sub": "user123", "preferred_username": "testuser"}
        mock_parse.return_value = {
            "username": "testuser",
            "roles": ["admin", "member", "reader"],
        }

        result = self.app._validate_oidc_token("valid-token")

        self.assertEqual(result["user"], "testuser")
        self.assertEqual(result["project_name"], "admin")
        self.assertEqual(result["domain_name"], "Default")
        self.assertEqual(result["roles"], ["admin", "member", "reader"])

    @mock.patch("platform_util.oidc.oidc_utils.get_oidc_token_claims")
    def test_validate_oidc_token_invalid(self, mock_claims):
        mock_claims.side_effect = ValueError("Invalid token")

        result = self.app._validate_oidc_token("invalid-token")

        self.assertIsNone(result)
