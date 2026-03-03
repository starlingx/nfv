#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import copy

from unittest import mock

from nfv_plugins.nfvi_plugins.openstack import usm
from nfv_unit_tests.tests import testcase
from nfv_vim import nfvi
from nfv_vim.strategy._strategy_steps import SwDeployDeleteStep
from nfv_vim.strategy._strategy_steps import SwDeployPrecheckStep
from nfv_vim.strategy._strategy_steps import SwSystemDeployInitStep
from nfv_vim.strategy._strategy_steps import UpgradeActivateStep
from nfv_vim.strategy._strategy_steps import UpgradeCompleteStep
from nfv_vim.strategy._strategy_steps import UpgradeStartStep
from nfv_vim.strategy._utils import normalize_release


class BaseTestUsm(testcase.NFVTestCase):
    """Base test class for usm file."""

    def setUp(self):
        super().setUp()

        self.token = mock.MagicMock()
        self.mock_post = self._mock_object(usm, "_api_post")
        self.mock_get = self._mock_object(usm, "_api_get")
        self.mock_delete = self._mock_object(usm, "_api_delete")
        self.mock_usm_api_cmd = self._mock_object(
            usm, "_usm_api_cmd", side_effect=lambda _, endpoint: endpoint
        )
        self.request_mock = self.mock_post

    # TODO(rlima): this method should be placed in NFVTestCase class, but doing so
    # would require a change in tox.ini to add the -e flag to the test dependency
    # install to enable it to identify the file change. This subsequently causes several
    # pylint issues to resolve.
    def _mock_object(self, target, attribute, wraps=None, **kwargs):
        """Mock a specified target's attribute and return the mock object"""

        mock_patch_object = mock.patch.object(target, attribute, wraps=wraps, **kwargs)
        self.addCleanup(mock_patch_object.stop)

        return mock_patch_object.start()

    def _mock_response(self, response):
        """Mock the response from the usm module."""

        mock_response = mock.MagicMock()
        mock_response.result_data = response
        return mock_response

    def _assert_request(self, url, response, data=None, timeout=None):
        """Asserts a request has the expected url, response and data.

        Each test class has a self.request_mock object defined to represent the type
        of request being made, e.g. get, post, delete. Based on that, the validation
        will check the necessary fields.
        """

        self.mock_usm_api_cmd.assert_called_once_with(self.token, url)
        self.assertEqual(response, self.request_mock.return_value)

        if self.request_mock in [self.mock_post, self.mock_delete]:
            expected_args = [self.token, url]
            expected_kwargs = {}

            if self.request_mock == self.mock_post:
                expected_args.append(data)
            if timeout:
                expected_kwargs["timeout_in_secs"] = timeout

            self.request_mock.assert_called_once_with(*expected_args, **expected_kwargs)


class TestSwDeployGetReleases(BaseTestUsm):
    """Unit tests for the sw_deploy_get_releases query URI construction."""

    def setUp(self):
        super().setUp()
        self.request_mock = self.mock_get

    def test_sw_deploy_get_releases_succeeds_without_release_id(self):
        response = usm.sw_deploy_get_releases(self.token)

        self._assert_request("release", response)

    def test_sw_deploy_get_releases_succeeds_with_release_id(self):
        response = usm.sw_deploy_get_releases(self.token, "starlingx-13")

        self._assert_request("release/starlingx-13", response)


class TestSwDeployShow(BaseTestUsm):
    """Unit tests for the sw_deploy_show query."""

    def setUp(self):
        super().setUp()
        self.request_mock = self.mock_get

    def test_sw_deploy_show_succeeds(self):
        response = usm.sw_deploy_show(self.token)

        self._assert_request("deploy", response)


class TestSwDeployHostList(BaseTestUsm):
    """Unit tests for the sw_deploy_host_list query."""

    def setUp(self):
        super().setUp()
        self.request_mock = self.mock_get

    def test_sw_deploy_host_list_succeeds(self):
        response = usm.sw_deploy_host_list(self.token)

        self._assert_request("deploy_host", response)


class TestSwDeployPrecheck(BaseTestUsm):
    """Unit tests for the sw_deploy_precheck payload construction."""

    def test_sw_deploy_precheck_succeeds(self):
        response = usm.sw_deploy_precheck(self.token, ["r1", "r2"])

        self._assert_request("deploy/precheck", response, {"releases": ["r1", "r2"]})

    def test_sw_deploy_precheck_succeeds_with_force_and_snapshot(self):
        response = usm.sw_deploy_precheck(self.token, ["r1"], force=True, snapshot=True)

        self._assert_request(
            "deploy/precheck",
            response,
            {"releases": ["r1"], "force": True, "options": ["snapshot=true"]},
        )

    def test_sw_deploy_precheck_succeeds_with_pre_upgrade_deploy(self):
        response = usm.sw_deploy_precheck(self.token, ["r1"], pre_upgrade_deploy=True)

        self._assert_request(
            "deploy/precheck",
            response,
            {"releases": ["r1"], "pre_upgrade_deploy": True},
        )

    def test_sw_deploy_precheck_succeeds_with_omitted_pre_upgrade_deploy(self):
        response = usm.sw_deploy_precheck(self.token, ["r1"], pre_upgrade_deploy=False)

        self._assert_request(
            "deploy/precheck",
            response,
            {"releases": ["r1"]},
        )


class TestSwDeployStart(BaseTestUsm):
    """Unit tests for the sw_deploy_start payload construction."""

    def test_sw_deploy_start_succeeds(self):
        response = usm.sw_deploy_start(self.token, ["r1", "r2"])

        self._assert_request(
            "deploy/start",
            response,
            {"releases": ["r1", "r2"]},
            usm.REST_API_DEPLOY_START_TIMEOUT,
        )

    def test_sw_deploy_start_succeeds_with_force_and_snapshot(self):
        response = usm.sw_deploy_start(self.token, ["r1"], force=True, snapshot=True)

        self._assert_request(
            "deploy/start",
            response,
            {"releases": ["r1"], "force": True, "options": ["snapshot=true"]},
            usm.REST_API_DEPLOY_START_TIMEOUT,
        )

    def test_sw_deploy_start_succeeds_with_pre_upgrade_deploy(self):
        response = usm.sw_deploy_start(self.token, ["r1"], pre_upgrade_deploy=True)

        self._assert_request(
            "deploy/start",
            response,
            {"releases": ["r1"], "pre_upgrade_deploy": True},
            usm.REST_API_DEPLOY_START_TIMEOUT,
        )

    def test_sw_deploy_start_succeeds_with_omitted_pre_upgrade_deploy(self):
        response = usm.sw_deploy_start(self.token, ["r1"], pre_upgrade_deploy=False)

        self._assert_request(
            "deploy/start",
            response,
            {"releases": ["r1"]},
            usm.REST_API_DEPLOY_START_TIMEOUT,
        )


class TestSwDeployExecute(BaseTestUsm):
    """Unit tests for the sw_deploy_execute request."""

    def test_sw_deploy_execute_succeeds(self):
        response = usm.sw_deploy_execute(self.token, "controller-0")

        self._assert_request(
            "deploy_host/controller-0", response, {}, usm.REST_API_DEPLOY_HOST_TIMEOUT
        )


class TestSwDeployRollback(BaseTestUsm):
    """Unit tests for the sw_deploy_rollback request."""

    def test_sw_deploy_rollback_succeeds(self):
        response = usm.sw_deploy_rollback(self.token, "controller-0")

        self._assert_request("deploy_host/controller-0/rollback", response, {})


class TestSwDeployActivate(BaseTestUsm):
    """Unit tests for the sw_deploy_activate request."""

    def test_sw_deploy_activate_succeeds(self):
        response = usm.sw_deploy_activate(self.token)

        self._assert_request("deploy/activate", response, {})


class TestSwDeployComplete(BaseTestUsm):
    """Unit tests for the sw_deploy_complete request."""

    def test_sw_deploy_complete_succeeds(self):
        response = usm.sw_deploy_complete(self.token)

        self._assert_request("deploy/complete", response, {})


class TestSwDeployDelete(BaseTestUsm):
    """Unit tests for the sw_deploy_delete request."""

    def setUp(self):
        super().setUp()
        self.request_mock = self.mock_delete

    def test_sw_deploy_delete_succeeds(self):
        response = usm.sw_deploy_delete(self.token)

        self._assert_request(
            "deploy", response, timeout=usm.REST_API_DEPLOY_DELETE_TIMEOUT
        )


class TestSwDeployAbort(BaseTestUsm):
    """Unit tests for the sw_deploy_abort request."""

    def test_sw_deploy_abort_succeeds(self):
        response = usm.sw_deploy_abort(self.token)

        self._assert_request("deploy/abort", response, {})


class TestSwDeployActivateRollback(BaseTestUsm):
    """Unit tests for the sw_deploy_activate_rollback request."""

    def test_sw_deploy_activate_rollback_succeeds(self):
        response = usm.sw_deploy_activate_rollback(self.token)

        self._assert_request("deploy/activate_rollback", response, {})


class TestSwSystemDeployInit(BaseTestUsm):
    """Unit tests for the sw_system_deploy_init request."""

    def test_sw_system_deploy_init_succeeds(self):
        response = usm.sw_system_deploy_init(self.token, "starlingx-13")

        self._assert_request("system_deploy/starlingx-13/init", response, {})

    def test_sw_system_deploy_init_succeeds_with_kube_version(self):
        response = usm.sw_system_deploy_init(self.token, "starlingx-13", "1.35.2")

        self._assert_request(
            "system_deploy/starlingx-13/init", response, {"kube_version": "1.35.2"}
        )


class TestSwSystemDeployDelete(BaseTestUsm):
    """Unit tests for the sw_system_deploy_delete request."""

    def setUp(self):
        super().setUp()
        self.request_mock = self.mock_delete

    def test_sw_system_deploy_delete_succeeds(self):
        response = usm.sw_system_deploy_delete(self.token)

        self._assert_request("system_deploy", response, {})


class TestSwSystemDeployShow(BaseTestUsm):
    """Unit tests for the sw_system_deploy_show request."""

    def setUp(self):
        super().setUp()
        self.request_mock = self.mock_get

    def test_sw_system_deploy_show_succeeds(self):
        response = usm.sw_system_deploy_show(self.token)

        self._assert_request("system_deploy", response, {})


class TestRetrieveReleaseData(BaseTestUsm):
    """Unit tests for retrieve_release_data."""

    def test_upgrade_when_target_greater_than_source(self):
        for to_release, from_release in [
            ("26.09", "25.09"),
            ("26.09", "24.09.100"),
            ("26.09.0", "25.09.500"),
            ("26.09.200", "25.09.500"),
            ("26.09.300", "25.09.200"),
            ("26.09.300", "25.09"),
            ("11.0.0", "9.0.0"),
            ("11.100.0", "9.0.0"),
            ("11.0.0", "9.100.0"),
        ]:
            upgrade, downgrade = usm._retrieve_release_data(to_release, from_release)
            self.assertTrue(upgrade)
            self.assertFalse(downgrade)

    def test_downgrade_when_target_lower_than_source(self):
        for to_release, from_release in [
            ("25.09", "26.09"),
            ("24.09.100", "26.09"),
            ("25.09.500", "26.09.0"),
            ("25.09.500", "26.09.200"),
            ("25.09.200", "26.09.300"),
            ("25.09", "26.09.300"),
            ("9.0.0", "11.0.0"),
            ("9.0.0", "11.100.0"),
            ("9.100.0", "11.0.0"),
        ]:
            upgrade, downgrade = usm._retrieve_release_data(to_release, from_release)
            self.assertFalse(upgrade)
            self.assertTrue(downgrade)

        upgrade, downgrade = usm._retrieve_release_data("25.09", "26.09")
        self.assertFalse(upgrade)
        self.assertTrue(downgrade)


class TestRetrieveReleaseInfo(BaseTestUsm):
    """Unit tests for retrieve_release_info."""

    def setUp(self):
        super().setUp()

        releases = [
            {"sw_version": "25.09", "release_id": "starlingx-25.09.0"},
            {"sw_version": "26.09", "release_id": "starlingx-26.09.0"},
        ]

        self.mock_sw_deploy_get_releases = self._mock_object(
            usm, "sw_deploy_get_releases"
        )
        self.mock_sw_deploy_get_releases.return_value = self._mock_response(releases)

    def test_returns_release_matching_sw_version(self):
        release = usm._retrieve_release_info(self.token, "26.09")

        self.assertEqual(release["release_id"], "starlingx-26.09.0")

    def test_raises_environment_error_when_no_match(self):
        # When the release information is not found, the next() will raise a
        # StopIteration exception that is converted to an EnvironmentError
        error = self.assertRaises(
            EnvironmentError, usm._retrieve_release_info, self.token, "99.99"
        )
        self.assertEqual(str(error), "Software release not found: 99.99")


class TestSwDeployGetUpgradeObj(BaseTestUsm):
    """Unit tests for sw_deploy_get_upgrade_obj."""

    def setUp(self):
        super().setUp()

        self.mock_show = self._mock_object(
            usm, "sw_deploy_show", return_value=self._mock_response(None)
        )
        self.mock_hosts = self._mock_object(
            usm, "sw_deploy_host_list", return_value=self._mock_response([])
        )
        self.mock_system = self._mock_object(
            usm, "sw_system_deploy_show", return_value=self._mock_response([])
        )
        self.mock_releases = self._mock_object(usm, "sw_deploy_get_releases")

        self.upgrade_obj = nfvi.objects.v1.Upgrade(
            ["26.09"],
            ["distcloud", "k8s"],
            {"release_id": "starlingx-13"},
            None,
            None,
        )
        self.mock_releases.return_value = self._mock_response(
            [
                {
                    "sw_version": "26.09",
                    "release_id": "starlingx-13",
                    "reboot_required": True,
                    "packages": [],
                },
                {
                    "sw_version": "26.09.1000",
                    "release_id": "starlingx-13.1",
                    "reboot_required": True,
                    "packages": [],
                },
            ]
        )
        self.precheck_data = {
            "info": "",
            "error": "",
            "warning": "",
            "major_release": False,
            "reboot_required": False,
            "prepatched_iso": False,
            "apply_operation": True,
            "from_release": "26.09.0",
            "to_release": "26.09.1000",
            "additional_data": {
                "k8s-v1.35.2_26.09.1000": {
                    "info": "",
                    "warning": "",
                    "error": "",
                    "system_healthy": True,
                }
            },
        }
        self.deploy_info = {
            "to_release": "26.09",
            "from_release": "25.09",
            "reboot_required": True,
            "state": "host",
            "metapackages": [["distcloud", "1000", "26.09.1000"]],
        }

    def _create_release(self, sw_version, release_id, reboot_required=True):
        return {
            "sw_version": sw_version,
            "release_id": release_id,
            "reboot_required": reboot_required,
            "state": "deploying",
            "packages": ["pkg-a", "pkg-b"],
        }

    def test_sw_deploy_get_upgrade_obj_uses_precheck_data(self):
        """The precheck path fills metapackages and refreshes release info."""

        # The precheck is executed as the last step of the strategy build. Because of
        # this, the upgrade_obj will exist.
        upgrade_obj = usm.sw_deploy_get_upgrade_obj(
            self.token, ["26.09"], self.upgrade_obj, self.precheck_data
        )

        self.assertEqual(upgrade_obj.metapackages, ["k8s-v1.35.2_26.09.1000"])
        self.assertEqual(upgrade_obj.release_info["release_id"], "starlingx-13.1")
        self.assertEqual(upgrade_obj.release_info["packages_count"], 0)
        self.assertTrue(upgrade_obj.release_info["upgrade"])
        self.assertFalse(upgrade_obj.release_info["downgrade"])
        self.assertTrue(upgrade_obj.release_info["vim_rr"])
        self.assertNotIn("packages", upgrade_obj.release_info)

    def test_sw_deploy_get_upgrade_obj_raises_environment_error(self):
        self.precheck_data["to_release"] = "10.0.0"

        exception = self.assertRaises(
            EnvironmentError,
            usm.sw_deploy_get_upgrade_obj,
            self.token,
            ["99.99"],
            self.upgrade_obj,
            self.precheck_data,
        )
        self.assertEqual(
            str(exception),
            f"Software release not found: {self.precheck_data['to_release']}",
        )

    def test_sw_deploy_get_upgrade_obj_refresh_obj_with_deploy(self):
        """An active deployment refreshes the known release by its id."""

        self.mock_show.return_value = self._mock_response([self.deploy_info])

        # This scenario will run the releases query for a specified release id,
        # returning only a single entry rather than a list.
        self.mock_releases.return_value = self._mock_response(
            {
                "sw_version": "26.09",
                "release_id": "starlingx-13",
                "reboot_required": True,
                "packages": [],
            }
        )

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(
            self.token, ["26.09"], self.upgrade_obj
        )

        self.mock_releases.assert_called_once_with(self.token, "starlingx-13")
        self.assertEqual(upgrade_obj.deploy_info, self.deploy_info)
        self.assertTrue(upgrade_obj.release_info["upgrade"])

    def test_sw_deploy_get_upgrade_obj_builds_metapackages_when_in_progress(self):
        """A fresh strategy on an in-progress deploy retrieves metapackages."""

        self.mock_show.return_value = self._mock_response([self.deploy_info])

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(self.token, ["26.09"], None)

        self.assertEqual(upgrade_obj.release, ["26.09"])
        self.assertEqual(upgrade_obj.release_id, "starlingx-13")
        self.assertEqual(upgrade_obj.metapackages, ["distcloud_26.09.1000"])
        self.assertTrue(upgrade_obj.release_info["upgrade"])
        self.assertEqual(upgrade_obj.deploy_info, self.deploy_info)

    def test_sw_deploy_get_upgrade_obj_without_metapackages_when_in_progress(self):
        """A deploy in progress whose payload lacks 'metapackages' must default to [].

        Regression test: after a VIM restart during upgrade, the upgrade_obj might be
        None when upgrading to latest release. In this scenario, the 'software deploy
        show' may not include the metapackages key, which previously raised a KeyError.
        """

        deploy_info = copy.deepcopy(self.deploy_info)
        del deploy_info["metapackages"]
        self.mock_show.return_value = self._mock_response([deploy_info])

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(self.token, ["26.09"], None)

        self.assertEqual(upgrade_obj.release, ["26.09"])
        self.assertEqual(upgrade_obj.release_id, "starlingx-13")
        self.assertEqual(upgrade_obj.metapackages, [])
        self.assertTrue(upgrade_obj.release_info["upgrade"])
        self.assertEqual(upgrade_obj.deploy_info, deploy_info)

    def test_sw_deploy_get_upgrade_obj_with_none_metapackages_when_in_progress(self):
        """A deploy in progress with 'metapackages' set to None must default to [].

        Complements the missing-key regression test by covering the case where
        the key exists but carries a None value, which would break the list
        comprehension with a TypeError if not guarded.
        """

        deploy_info = copy.deepcopy(self.deploy_info)
        deploy_info["metapackages"] = None
        self.mock_show.return_value = self._mock_response([deploy_info])

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(self.token, ["26.09"], None)

        self.assertEqual(upgrade_obj.metapackages, [])
        self.assertEqual(upgrade_obj.deploy_info, deploy_info)

    def test_sw_deploy_get_upgrade_obj_minimal_return(self):
        """With no data available, a minimal Upgrade object is returned."""

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(self.token, ["26.09"], None)

        self.assertEqual(upgrade_obj.release, ["26.09"])
        self.assertIsNone(upgrade_obj.release_id)
        self.assertEqual(upgrade_obj.metapackages, [])
        self.assertIsNone(upgrade_obj.release_info)
        self.assertIsNone(upgrade_obj.deploy_info)
        self.mock_releases.assert_not_called()


class TestNormalizeRelease(testcase.NFVTestCase):
    """Unit tests for the normalize_release helper.

    Prior to the componentization feature the software deploy release was
    persisted as a single string. With componentization, it must be handled as a
    list of string, so values restored from strategies created with the old
    code need to be normalized with normalize_release.
    """

    def test_normalize_release_string_value_normalizes_to_list(self):
        self.assertEqual(normalize_release("24.03.1"), ["24.03.1"])

    def test_normalize_release_list_is_preserved(self):
        self.assertEqual(normalize_release(["24.03.1"]), ["24.03.1"])

    def test_normalize_release_multi_item_list_is_preserved(self):
        self.assertEqual(
            normalize_release(["24.03.1", "24.03.2"]), ["24.03.1", "24.03.2"]
        )

    def test_normalize_release_empty_list_is_preserved(self):
        self.assertEqual(normalize_release([]), [])

    def test_normalize_release_none_is_preserved(self):
        self.assertIsNone(normalize_release(None))


class TestStepReleaseNormalization(testcase.NFVTestCase):
    """Verify every step that normalizes its release normalizes a legacy string.

    A step persisted by a pre-componentization VIM stores the release as a bare
    string. On load, from_dict must normalize it back to the list format.
    """

    def _assert_step_normalizes_string(self, step_class):
        # A step built with the new list format serializes the list unchanged.
        step = step_class(release=["24.03.1"])
        self.assertEqual(step.as_dict()["release"], ["24.03.1"])

        # Simulate a step persisted as a bare string and confirm from_dict
        # normalizes it back to the list format.
        data = step.as_dict()
        data["release"] = "24.03.1"
        normalized = step_class(release=None).from_dict(data)
        self.assertEqual(normalized.as_dict()["release"], ["24.03.1"])

    def _assert_step_preserves_list(self, step_class):
        step = step_class(release=["24.03.1", "24.03.2"])
        normalized = step_class(release=None).from_dict(step.as_dict())
        self.assertEqual(normalized.as_dict()["release"], ["24.03.1", "24.03.2"])

    def test_normalize_release_through_steps(self):
        self._assert_step_normalizes_string(SwDeployPrecheckStep)
        self._assert_step_preserves_list(SwDeployPrecheckStep)

        self._assert_step_normalizes_string(UpgradeStartStep)
        self._assert_step_preserves_list(UpgradeStartStep)

        self._assert_step_normalizes_string(UpgradeActivateStep)
        self._assert_step_preserves_list(UpgradeActivateStep)

        self._assert_step_normalizes_string(UpgradeCompleteStep)
        self._assert_step_preserves_list(UpgradeCompleteStep)

        self._assert_step_normalizes_string(SwDeployDeleteStep)
        self._assert_step_preserves_list(SwDeployDeleteStep)

        self._assert_step_normalizes_string(SwSystemDeployInitStep)
        self._assert_step_preserves_list(SwSystemDeployInitStep)
