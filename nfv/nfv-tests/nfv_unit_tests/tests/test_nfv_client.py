#
# Copyright (c) 2023-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import copy
import os
from unittest import mock

from nfv_client import shell

from nfv_unit_tests.tests import testcase


class TestNFVClientShell(testcase.NFVTestCase):

    def setUp(self):
        super(TestNFVClientShell, self).setUp()

    def tearDown(self):
        super(TestNFVClientShell, self).tearDown()

    # -- Failure cases --
    # Each failure case will :
    # - invoke _print_message (as part of exit)
    # - invoke print_usage (to indicate proper arguments)
    # - raise a SystemExit exception
    @mock.patch('argparse.ArgumentParser._print_message')
    @mock.patch('argparse.ArgumentParser.print_usage')
    def _test_shell_bad_or_empty_args(self,
                                      mock_usage=None,
                                      mock_message=None,
                                      shell_args=None):
        self.assertRaises(SystemExit, shell.process_main, shell_args)
        mock_usage.assert_called_once()
        mock_message.assert_called_once()

    # --- Help Cases ----
    # -h will print_help and SystemExit
    @mock.patch('argparse.ArgumentParser.print_help')
    def _test_shell_help(self, mock_help=None, shell_args=None):
        self.assertRaises(SystemExit, shell.process_main, shell_args)
        mock_help.assert_called_once()


class TestNFVClientShellRobustness(TestNFVClientShell):
    # invalid arguments causes process_main to exit
    def test_shell_bad_args(self):
        shell_args = ['invalid-arg', ]
        self._test_shell_bad_or_empty_args(shell_args=shell_args)

    # empty arguments causes process_main to exit
    def test_shell_no_args(self):
        shell_args = []
        self._test_shell_bad_or_empty_args(shell_args=shell_args)


class StrategyMixin(object):

    MOCK_ENV = {
        'OS_AUTH_URL': 'FAKE_OS_AUTH_URL',
        'OS_PROJECT_NAME': 'FAKE_OS_PROJECT_NAME',
        'OS_PROJECT_DOMAIN_NAME': 'FAKE_OS_PROJECT_DOMAIN_NAME',
        'OS_USERNAME': 'FAKE_OS_USERNAME',
        'OS_PASSWORD': 'FAKE_OS_PASSWORD',
        'OS_USER_DOMAIN_NAME': 'FAKE_OS_USER_DOMAIN_NAME',
        'OS_REGION_NAME': 'FAKE_OS_REGION_NAME',
        'OS_INTERFACE': 'FAKE_OS_INTERFACE'
    }

    MOCK_ENV_OVERRIDES = {
        'OS_AUTH_URL': '--os-auth-url=FAKE_OS_AUTH_URL',
        'OS_PROJECT_NAME': '--os-project-name=FAKE_OS_PROJECT_NAME',
        'OS_PROJECT_DOMAIN_NAME':
            '--os-project-domain-name=FAKE_OS_PROJECT_DOMAIN_NAME',
        'OS_USERNAME': '--os-username=FAKE_OS_USERNAME',
        'OS_PASSWORD': '--os-password=FAKE_OS_PASSWORD',
        'OS_USER_DOMAIN_NAME':
            '--os-user-domain-name=FAKE_OS_USER_DOMAIN_NAME',
        'OS_REGION_NAME': '--os-region-name=FAKE_OS_REGION_NAME',
        'OS_INTERFACE': '--os-interface=FAKE_OS_INTERFACE'
    }

    def set_strategy(self, strategy):
        """Invoked by the child class setupmethod to set the strategy"""
        self.strategy = strategy

    def required_create_fields(self):
        """Override in the child class if create has required fields"""
        return []

    def optional_create_fields(self):
        """Override in the child class if create has optional fields"""
        return []

    # -- Show commands --
    # The strategy commands use the same underling sw_update class, but
    # but with different modes
    # Test the show commands are not invoked when env values missing
    @mock.patch('nfv_client.sw_update.show_strategy')
    def _test_shell_show_missing_env(self, mock_show=None, shell_args=None):
        shell.process_main(shell_args)
        mock_show.assert_not_called()

    # Test the show commands are invoked when env values detected
    @mock.patch('nfv_client.sw_update.show_strategy')
    def _test_shell_show(self, mock_show=None, shell_args=None):
        with mock.patch.dict(os.environ, self.MOCK_ENV):
            shell.process_main(shell_args)
        mock_show.assert_called_once()

    @mock.patch('nfv_client.sw_update.show_strategy')
    def _test_shell_show_incomplete_env(self,
                                        mock_show=None,
                                        shell_args=None,
                                        pop_env=None,
                                        expect_fails=True):
        # setup a mostly complete environment
        test_env = copy.copy(self.MOCK_ENV)
        test_env.pop(pop_env)
        with mock.patch.dict(os.environ, test_env):
            shell.process_main(shell_args)
            if expect_fails:
                mock_show.assert_not_called()
            else:
                mock_show.assert_called_once()

    def test_shell_strategy_missing_subcommand(self):
        """Test the strategy fails with a missing subcommand"""
        shell_args = [self.strategy, ]
        self._test_shell_bad_or_empty_args(shell_args=shell_args)

    def test_shell_strategy_invalid_subcommand(self):
        """Test the strategy fails with an invalid subcommand"""
        shell_args = [self.strategy, 'foo']
        self._test_shell_bad_or_empty_args(shell_args=shell_args)

    def test_shell_strategy_help(self):
        """Test the strategy supports the help subcommand"""
        shell_args = [self.strategy, '-h', ]
        self._test_shell_help(shell_args=shell_args)

    def test_shell_strategy_show_incomplete_env(self):
        """Test that if any required env variable is missing, it fails"""
        shell_args = [self.strategy, 'show', ]
        for pop_env in list(self.MOCK_ENV.keys()):
            # OS_PROJECT_DOMAIN_NAME was made optional
            if pop_env == "OS_PROJECT_DOMAIN_NAME":
                continue
            # remove the pop_env variable from the environment
            self._test_shell_show_incomplete_env(shell_args=shell_args,
                                                 pop_env=pop_env)

    def test_shell_strategy_show_env_overrides(self):
        """
        Tests that passing certain values to the CLI override the env and
        that removing that value from the env will not cause failure
        """
        for env_val, override_val in self.MOCK_ENV_OVERRIDES.items():
            shell_args = [override_val, self.strategy, 'show', ]
            self._test_shell_show_incomplete_env(shell_args=shell_args,
                                                 pop_env=env_val,
                                                 expect_fails=False)

    def test_shell_strategy_show(self):
        shell_args = [self.strategy, 'show', ]
        self._test_shell_show(shell_args=shell_args)

    def test_shell_strategy_show_bad_extra_arg(self):
        shell_args = [self.strategy, 'show', '--bad']
        self._test_shell_bad_or_empty_args(shell_args=shell_args)

    def test_shell_strategy_show_debug(self):
        shell_args = ["--debug", self.strategy, 'show']
        self._test_shell_show(shell_args=shell_args)

    def test_shell_strategy_show_details(self):
        shell_args = [self.strategy, 'show', '--details']
        self._test_shell_show(shell_args=shell_args)

    def test_shell_strategy_show_active(self):
        shell_args = [self.strategy, 'show', '--active']
        self._test_shell_show(shell_args=shell_args)

    def test_shell_strategy_show_active_details(self):
        shell_args = [self.strategy, 'show', '--details', '--active']
        self._test_shell_show(shell_args=shell_args)

    # -- Abort command --
    # Test the abort command can be invoked. Requires the env to be set
    @mock.patch('nfv_client.sw_update.abort_strategy')
    def _test_shell_abort(self, mock_abort=None, shell_args=None):
        with mock.patch.dict(os.environ, self.MOCK_ENV):
            shell.process_main(shell_args)
        mock_abort.assert_called_once()

    def test_shell_strategy_abort(self):
        shell_args = [self.strategy, 'abort', '--yes']
        self._test_shell_abort(shell_args=shell_args)

    # -- Apply command --
    # Test the apply command can be invoked. Requires the env to be set
    @mock.patch('nfv_client.sw_update.apply_strategy')
    def _test_shell_apply(self, mock_apply=None, shell_args=None):
        with mock.patch.dict(os.environ, self.MOCK_ENV):
            shell.process_main(shell_args)
        mock_apply.assert_called_once()

    def test_shell_strategy_apply(self):
        shell_args = [self.strategy, 'apply', '--yes']
        self._test_shell_apply(shell_args=shell_args)

    # -- Delete command --
    # Test the delete command can be invoked. Requires the env to be set
    @mock.patch('nfv_client.sw_update.delete_strategy')
    def _test_shell_delete(self, mock_delete=None, shell_args=None):
        with mock.patch.dict(os.environ, self.MOCK_ENV):
            shell.process_main(shell_args)
        mock_delete.assert_called_once()

    def test_shell_strategy_delete(self):
        shell_args = [self.strategy, 'delete']
        self._test_shell_delete(shell_args=shell_args)

    # -- Create command --
    # Test the create command can be invoked. Requires the env to be set
    @mock.patch('nfv_client.sw_update.create_strategy')
    def _test_shell_create(self, mock_create=None, shell_args=None):
        with mock.patch.dict(os.environ, self.MOCK_ENV):
            shell.process_main(shell_args)
        mock_create.assert_called_once()

    # Test the create command can be invoked. Requires the env to be set
    @mock.patch('nfv_client.sw_update.create_strategy')
    def _test_shell_create_with_error(self, mock_create=None, shell_args=None):
        with mock.patch.dict(os.environ, self.MOCK_ENV):
            with mock.patch.object(shell, '_process_exit') as thing:
                shell.process_main(shell_args)
                # Returns the exception passed to _process_exit
                return thing.call_args_list[0][0][0]

    # -- Create command --
    def test_shell_strategy_create(self):
        shell_args = [self.strategy, 'create']
        # create may have 'required' additional fields
        shell_args.extend(self.required_create_fields())
        self._test_shell_create(shell_args=shell_args)

    def test_shell_strategy_create_optional(self):
        shell_args = [self.strategy, 'create']
        # create may have 'required' additional fields and optional ones
        shell_args.extend(self.required_create_fields())
        shell_args.extend(self.optional_create_fields())
        self._test_shell_create(shell_args=shell_args)


class TestCLISwDeployStrategy(TestNFVClientShell,
                             StrategyMixin):
    def setUp(self):
        super(TestCLISwDeployStrategy, self).setUp()
        self.set_strategy('sw-deploy-strategy')

    def required_create_fields(self):
        """Software deploy requires a release for create"""
        return ['starlingx-24.03.1']

    def test_create_missing_both(self):
        shell_args = [self.strategy, 'create']
        e = self._test_shell_create_with_error(shell_args=shell_args)
        assert str(e) == 'Must set release or rollback', e

    def test_create_rollback(self):
        shell_args = [self.strategy, 'create', '--rollback']
        self._test_shell_create(shell_args=shell_args)

    def test_create_with_both(self):
        shell_args = [self.strategy, 'create', 'v123.1', '--rollback']
        e = self._test_shell_create_with_error(shell_args=shell_args)
        assert str(e) == 'Cannot set both release and rollback', e


class TestCLIFwUpdateStrategy(TestNFVClientShell,
                              StrategyMixin):
    def setUp(self):
        super(TestCLIFwUpdateStrategy, self).setUp()
        self.set_strategy('fw-update-strategy')


class TestCLIKubeRootCAUpdateStrategy(TestNFVClientShell,
                                      StrategyMixin):
    def setUp(self):
        super(TestCLIKubeRootCAUpdateStrategy, self).setUp()
        self.set_strategy('kube-rootca-update-strategy')


class TestCLIKubeUpgradeStrategy(TestNFVClientShell,
                                 StrategyMixin):
    def setUp(self):
        super(TestCLIKubeUpgradeStrategy, self).setUp()
        self.set_strategy('kube-upgrade-strategy')

    def required_create_fields(self):
        """Kube Upgrade requires a to-version for create"""
        return ['--to-version=1.2.3']


class TestSystemConfigUpdateStrategy(TestNFVClientShell,
                                     StrategyMixin):
    def setUp(self):
        super(TestSystemConfigUpdateStrategy, self).setUp()
        self.set_strategy('system-config-update-strategy')
