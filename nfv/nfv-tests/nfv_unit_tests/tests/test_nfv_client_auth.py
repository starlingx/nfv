#
# Copyright (c) 2025-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import os
from unittest import mock

from nfv_client import shell
from nfv_client.sw_update import _sw_update

from nfv_unit_tests.tests import testcase


class TestNFVClientAuth(testcase.NFVTestCase):
    def setUp(self):
        super(TestNFVClientAuth, self).setUp()

    def tearDown(self):
        super(TestNFVClientAuth, self).tearDown()

    def test_stx_auth_type_default_keystone(self):
        """Test --stx-auth-type defaults to keystone."""

        shell_args = ["sw-deploy-strategy", "show"]
        with mock.patch("nfv_client.sw_update.show_strategy") as mock_show:
            with mock.patch.dict(
                os.environ,
                {
                    "OS_AUTH_URL": "http://test",
                    "OS_PROJECT_NAME": "test",
                    "OS_USERNAME": "test",
                    "OS_PASSWORD": "test",
                    "OS_USER_DOMAIN_NAME": "test",
                    "OS_REGION_NAME": "test",
                    "OS_INTERFACE": "test",
                },
            ):
                shell.process_main(shell_args)
                mock_show.assert_called_once()

    def test_stx_auth_type_explicit_keystone(self):
        """Test --stx-auth-type keystone."""

        shell_args = ["--stx-auth-type=keystone", "sw-deploy-strategy", "show"]
        with mock.patch("nfv_client.sw_update.show_strategy") as mock_show:
            with mock.patch.dict(
                os.environ,
                {
                    "OS_AUTH_URL": "http://test",
                    "OS_PROJECT_NAME": "test",
                    "OS_USERNAME": "test",
                    "OS_PASSWORD": "test",
                    "OS_USER_DOMAIN_NAME": "test",
                    "OS_REGION_NAME": "test",
                    "OS_INTERFACE": "test",
                },
            ):
                shell.process_main(shell_args)
                mock_show.assert_called_once()

    def test_stx_auth_type_oidc(self):
        """Test --stx-auth-type oidc."""

        shell_args = ["--stx-auth-type=oidc", "sw-deploy-strategy", "show"]
        with mock.patch("nfv_client.sw_update.show_strategy") as mock_show:
            with mock.patch.dict(
                os.environ,
                {
                    "OS_AUTH_URL": "http://test",
                    "OS_PROJECT_NAME": "test",
                    "OS_USERNAME": "test",
                    "OS_PASSWORD": "test",
                    "OS_USER_DOMAIN_NAME": "test",
                    "OS_REGION_NAME": "test",
                    "OS_INTERFACE": "test",
                },
            ):
                shell.process_main(shell_args)
                mock_show.assert_called_once()

    def test_stx_auth_type_invalid_choice(self):
        """Test --stx-auth-type with invalid choice fails."""

        shell_args = ["--stx-auth-type=invalid", "sw-deploy-strategy", "show"]
        with mock.patch("argparse.ArgumentParser._print_message"):
            with mock.patch("argparse.ArgumentParser.print_usage"):
                self.assertRaises(SystemExit, shell.process_main, shell_args)

    @mock.patch("nfv_client.sw_update._sw_update.oidc_utils.get_oidc_token")
    def test_get_auth_token_and_url_oidc(self, mock_get_token):
        """Test _get_auth_token_and_url with OIDC."""

        mock_get_token.return_value = "fake_token"

        token_id, url = _sw_update._get_auth_token_and_url(
            "http://192.168.1.1:5000/v3",
            "admin",
            "Default",
            "admin",
            "password",
            "Default",
            "RegionOne",
            "public",
            "oidc",
        )

        self.assertEqual(token_id, "fake_token")
        self.assertIn("4545", url)
        self.assertEqual(url, "https://192.168.1.1:4545")

    @mock.patch("nfv_client.sw_update._sw_update.openstack.get_token")
    def test_get_auth_token_and_url_keystone(self, mock_get_token):
        """Test _get_auth_token_and_url with Keystone."""

        mock_token = mock.Mock()
        mock_token.get_service_url.return_value = "https://test:4545"
        mock_token.get_id.return_value = "fake_token"
        mock_get_token.return_value = mock_token

        token_id, url = _sw_update._get_auth_token_and_url(
            "http://192.168.1.1:5000/v3",
            "admin",
            "Default",
            "admin",
            "password",
            "Default",
            "RegionOne",
            "public",
            "keystone",
        )

        self.assertEqual(token_id, "fake_token")
        self.assertEqual(url, "https://test:4545")
