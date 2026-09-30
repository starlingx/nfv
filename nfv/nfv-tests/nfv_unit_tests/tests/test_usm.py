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

        # SwDeployDeleteStep does NOT normalize because it receives either a list
        # (from normal deploys) or a string (release_id from rollback). It must
        # preserve whatever was stored to avoid the rollback "Software release not
        # found" bug.
        self._assert_step_preserves_list(SwDeployDeleteStep)

        self._assert_step_normalizes_string(SwSystemDeployInitStep)
        self._assert_step_preserves_list(SwSystemDeployInitStep)


class TestSwDeployGetMetapackages(BaseTestUsm):
    """Unit tests for the sw_deploy_get_metapackages query."""

    def setUp(self):
        super().setUp()
        self.request_mock = self.mock_get

    def test_pre_upgrade_deploy_queries_correct_endpoint(self):
        response = usm.sw_deploy_get_metapackages(self.token, pre_upgrade_deploy=True)

        self._assert_request("release/metapackage?pre-upgrade-deploy", response)

    def test_all_metapackages_queries_correct_endpoint(self):
        response = usm.sw_deploy_get_metapackages(self.token, pre_upgrade_deploy=False)

        self._assert_request("release/metapackage?all", response)


class TestExtractMetapackageInfo(testcase.NFVTestCase):
    """Unit tests for _extract_metapackage_info helper."""

    def test_extracts_only_relevant_fields(self):
        data = [
            {
                "release_id": "mp1_27.03.0",
                "reboot_required": False,
                "state": "available",
                "component": "mp1",
                "packages": ["pkg-a"],
                "sw_version": "27.03.0",
            }
        ]
        result = usm._extract_metapackage_info(data)

        self.assertEqual(
            result,
            [
                {
                    "release_id": "mp1_27.03.0",
                    "reboot_required": False,
                    "state": "available",
                }
            ],
        )

    def test_filters_by_release_ids(self):
        data = [
            {"release_id": "mp1", "reboot_required": False, "state": "available"},
            {"release_id": "mp2", "reboot_required": True, "state": "available"},
            {"release_id": "mp3", "reboot_required": False, "state": "available"},
        ]
        result = usm._extract_metapackage_info(data, filter_release_ids={"mp1", "mp3"})

        self.assertEqual(len(result), 2)
        ids = {r["release_id"] for r in result}
        self.assertEqual(ids, {"mp1", "mp3"})

    def test_filters_by_state(self):
        data = [
            {"release_id": "mp1", "reboot_required": False, "state": "deploy-selected"},
            {"release_id": "mp2", "reboot_required": True, "state": "available"},
            {"release_id": "mp3", "reboot_required": True, "state": "deploy-selected"},
        ]
        result = usm._extract_metapackage_info(data, filter_states={"deploy-selected"})

        self.assertEqual(len(result), 2)
        ids = {r["release_id"] for r in result}
        self.assertEqual(ids, {"mp1", "mp3"})

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(usm._extract_metapackage_info(None), [])
        self.assertEqual(usm._extract_metapackage_info([]), [])


class TestSwDeployGetUpgradeObjMetapackageRR(BaseTestUsm):
    """Unit tests for metapackage-level reboot_required in sw_deploy_get_upgrade_obj."""

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
        self.mock_metapackages = self._mock_object(usm, "sw_deploy_get_metapackages")

        self.upgrade_obj = nfvi.objects.v1.Upgrade(
            ["starlingx-27.03.0"],
            [],
            {"release_id": "starlingx-27.03.0", "reboot_required": True},
            None,
            None,
        )

        self.precheck_data = {
            "info": "",
            "error": "",
            "warning": "",
            "major_release": True,
            "reboot_required": True,
            "prepatched_iso": False,
            "apply_operation": True,
            "from_release": "26.09.0",
            "to_release": "27.03.0",
            "additional_data": {
                "k8s-1.34.1-controlplane_27.03.0": {
                    "info": "",
                    "warning": "",
                    "error": "",
                    "system_healthy": True,
                }
            },
        }

        self.mock_releases.return_value = self._mock_response(
            [
                {
                    "sw_version": "27.03.0",
                    "release_id": "starlingx-27.03.0",
                    "reboot_required": True,
                    "packages": [],
                }
            ]
        )

    def _make_metapackage(self, release_id, reboot_required):
        """Build a full metapackage API response entry."""

        return {
            "release_id": release_id,
            "reboot_required": reboot_required,
            "component": release_id.rsplit("_", 1)[0],
            "sw_version": "27.03.0",
            "state": "available",
            "packages": [],
            "activation_scripts": [],
        }

    def _expected_stored(self, release_id, reboot_required):
        """Build the filtered dict that should be stored on the Upgrade object."""

        return {
            "release_id": release_id,
            "reboot_required": reboot_required,
            "state": "available",
        }

    def test_pre_upgrade_deploy_fetches_metapackages(self):
        """pre_upgrade_deploy=True triggers the ?pre-upgrade-deploy endpoint."""

        metapackages = [
            self._make_metapackage("k8s-1.34.1-controlplane_27.03.0", False),
            self._make_metapackage("k8s-1.34.8-controlplane_27.03.0", False),
        ]
        self.mock_metapackages.return_value = self._mock_response(metapackages)

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(
            self.token,
            ["starlingx-27.03.0"],
            self.upgrade_obj,
            self.precheck_data,
            pre_upgrade_deploy=True,
        )

        self.mock_metapackages.assert_called_once_with(
            self.token, pre_upgrade_deploy=True
        )
        expected = [
            self._expected_stored("k8s-1.34.1-controlplane_27.03.0", False),
            self._expected_stored("k8s-1.34.8-controlplane_27.03.0", False),
        ]
        self.assertEqual(upgrade_obj.pre_upgrade_metapackages, expected)
        # All metapackages are NRR, so reboot_required should be False
        self.assertFalse(upgrade_obj.reboot_required)

    def test_pre_upgrade_deploy_rr_when_any_metapackage_is_rr(self):
        """reboot_required is True when at least one metapackage is RR."""

        metapackages = [
            self._make_metapackage("k8s-1.34.1-controlplane_27.03.0", False),
            self._make_metapackage("platform_27.03.0", True),
        ]
        self.mock_metapackages.return_value = self._mock_response(metapackages)

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(
            self.token,
            ["starlingx-27.03.0"],
            self.upgrade_obj,
            self.precheck_data,
            pre_upgrade_deploy=True,
        )

        self.assertTrue(upgrade_obj.reboot_required)

    def test_pre_upgrade_deploy_empty_metapackages_falls_back(self):
        """Empty metapackage list falls back to release-level RR."""

        self.mock_metapackages.return_value = self._mock_response([])

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(
            self.token,
            ["starlingx-27.03.0"],
            self.upgrade_obj,
            self.precheck_data,
            pre_upgrade_deploy=True,
        )

        self.assertEqual(upgrade_obj.pre_upgrade_metapackages, [])
        # Falls back to release_info vim_rr (True)
        self.assertTrue(upgrade_obj.reboot_required)

    def test_user_metapackages_fetches_all_endpoint(self):
        """User-specified metapackages trigger the ?all endpoint."""

        all_metapackages = [
            self._make_metapackage("k8s-1.34.1-controlplane_27.03.0", False),
            self._make_metapackage("k8s-1.34.8-controlplane_27.03.0", False),
            self._make_metapackage("platform_27.03.0", True),
        ]
        self.mock_metapackages.return_value = self._mock_response(all_metapackages)

        # User passed specific metapackages (not the main release)
        upgrade_obj = usm.sw_deploy_get_upgrade_obj(
            self.token,
            ["k8s-1.34.1-controlplane_27.03.0", "k8s-1.34.8-controlplane_27.03.0"],
            self.upgrade_obj,
            self.precheck_data,
        )

        self.mock_metapackages.assert_called_once_with(
            self.token, pre_upgrade_deploy=False
        )
        # Only the two user-specified NRR metapackages should be stored
        self.assertEqual(len(upgrade_obj.pre_upgrade_metapackages), 2)
        self.assertFalse(upgrade_obj.reboot_required)

    def test_user_metapackages_rr_when_selected_is_rr(self):
        """User selects an RR metapackage, reboot_required is True."""

        all_metapackages = [
            self._make_metapackage("k8s-1.34.1-controlplane_27.03.0", False),
            self._make_metapackage("platform_27.03.0", True),
        ]
        self.mock_metapackages.return_value = self._mock_response(all_metapackages)

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(
            self.token,
            ["platform_27.03.0"],
            self.upgrade_obj,
            self.precheck_data,
        )

        self.assertTrue(upgrade_obj.reboot_required)

    def test_no_release_filters_by_deploy_selected_state(self):
        """No release specified fetches ?all and filters deploy-selected."""

        all_metapackages = [
            self._make_metapackage("distcloud_26.10.1", False),
            self._make_metapackage("k8s-1.34.1-controlplane_27.03.0", True),
        ]
        # Only the first one is deploy-selected
        all_metapackages[0]["state"] = "deploy-selected"

        self.mock_metapackages.return_value = self._mock_response(all_metapackages)

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(
            self.token,
            None,
            self.upgrade_obj,
            self.precheck_data,
        )

        self.mock_metapackages.assert_called_once_with(
            self.token, pre_upgrade_deploy=False
        )
        # Only the deploy-selected NRR metapackage should be stored
        self.assertEqual(len(upgrade_obj.pre_upgrade_metapackages), 1)
        self.assertEqual(
            upgrade_obj.pre_upgrade_metapackages[0]["release_id"],
            "distcloud_26.10.1",
        )
        self.assertFalse(upgrade_obj.reboot_required)

    def test_no_release_no_deploy_selected_falls_back(self):
        """No release and no deploy-selected metapackages falls back to vim_rr."""

        all_metapackages = [
            self._make_metapackage("k8s-1.34.1-controlplane_27.03.0", False),
        ]
        # None are deploy-selected
        self.mock_metapackages.return_value = self._mock_response(all_metapackages)

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(
            self.token,
            None,
            self.upgrade_obj,
            self.precheck_data,
        )

        self.assertEqual(upgrade_obj.pre_upgrade_metapackages, [])
        # Falls back to release_info vim_rr (True)
        self.assertTrue(upgrade_obj.reboot_required)

    def test_main_release_skips_metapackage_fetch(self):
        """Passing the main release name does not fetch metapackages."""

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(
            self.token,
            ["starlingx-27.03.0"],
            self.upgrade_obj,
            self.precheck_data,
        )

        self.mock_metapackages.assert_not_called()
        self.assertEqual(upgrade_obj.pre_upgrade_metapackages, [])
        # Falls back to release_info vim_rr
        self.assertTrue(upgrade_obj.reboot_required)

    def test_deploy_info_takes_precedence_over_metapackages(self):
        """deploy_info reboot_required takes precedence over metapackage data."""

        metapackages = [
            self._make_metapackage("k8s-1.34.1-controlplane_27.03.0", False),
        ]
        self.mock_metapackages.return_value = self._mock_response(metapackages)

        deploy_info = {
            "to_release": "27.03.0",
            "from_release": "26.09.0",
            "reboot_required": True,
            "state": "host",
            "metapackages": [],
        }
        self.mock_show.return_value = self._mock_response([deploy_info])

        self.mock_releases.return_value = self._mock_response(
            {
                "sw_version": "27.03.0",
                "release_id": "starlingx-27.03.0",
                "reboot_required": True,
                "packages": [],
            }
        )

        upgrade_obj = usm.sw_deploy_get_upgrade_obj(
            self.token,
            ["starlingx-27.03.0"],
            self.upgrade_obj,
            pre_upgrade_deploy=True,
        )

        # deploy_info exists, so its reboot_required takes precedence
        self.assertTrue(upgrade_obj.reboot_required)


class TestUpgradeRebootRequired(testcase.NFVTestCase):
    """Unit tests for the Upgrade.reboot_required property."""

    def _make_metapackage(self, release_id, reboot_required):
        return {
            "release_id": release_id,
            "reboot_required": reboot_required,
        }

    def test_deploy_info_takes_highest_precedence(self):
        """deploy_info reboot_required overrides everything else."""

        upgrade = nfvi.objects.v1.Upgrade(
            ["r1"],
            [],
            {"reboot_required": False, "vim_rr": False},
            {"reboot_required": True},
            None,
            pre_upgrade_metapackages=[
                self._make_metapackage("mp1", False),
            ],
        )

        self.assertTrue(upgrade.reboot_required)

    def test_pre_upgrade_metapackages_all_nrr(self):
        """All NRR metapackages -> reboot_required is False."""

        upgrade = nfvi.objects.v1.Upgrade(
            ["r1"],
            [],
            {"reboot_required": True, "vim_rr": True},
            None,
            None,
            pre_upgrade_metapackages=[
                self._make_metapackage("mp1", False),
                self._make_metapackage("mp2", False),
            ],
        )

        self.assertFalse(upgrade.reboot_required)

    def test_pre_upgrade_metapackages_one_rr(self):
        """At least one RR metapackage -> reboot_required is True."""

        upgrade = nfvi.objects.v1.Upgrade(
            ["r1"],
            [],
            {"reboot_required": False, "vim_rr": False},
            None,
            None,
            pre_upgrade_metapackages=[
                self._make_metapackage("mp1", False),
                self._make_metapackage("mp2", True),
            ],
        )

        self.assertTrue(upgrade.reboot_required)

    def test_empty_pre_upgrade_metapackages_falls_back_to_vim_rr(self):
        """Empty list falls back to release_info vim_rr."""

        upgrade = nfvi.objects.v1.Upgrade(
            ["r1"],
            [],
            {"reboot_required": False, "vim_rr": True},
            None,
            None,
            pre_upgrade_metapackages=[],
        )

        self.assertTrue(upgrade.reboot_required)

    def test_no_pre_upgrade_metapackages_falls_back_to_release_info(self):
        """No metapackages and no deploy_info uses release_info."""

        upgrade = nfvi.objects.v1.Upgrade(
            ["r1"],
            [],
            {"reboot_required": True, "vim_rr": True},
            None,
            None,
        )

        self.assertTrue(upgrade.reboot_required)

    def test_no_release_info_returns_none(self):
        """No release_info and no deploy_info returns None."""

        upgrade = nfvi.objects.v1.Upgrade(
            ["r1"],
            [],
            None,
            None,
            None,
        )

        self.assertIsNone(upgrade.reboot_required)

    def test_update_sets_pre_upgrade_metapackages(self):
        """update() with pre_upgrade_metapackages sets the field."""

        upgrade = nfvi.objects.v1.Upgrade(["r1"], [], None, None, None)
        self.assertEqual(upgrade.pre_upgrade_metapackages, [])

        metapackages = [self._make_metapackage("mp1", True)]
        upgrade.update(
            {"reboot_required": False, "vim_rr": False},
            None,
            None,
            pre_upgrade_metapackages=metapackages,
        )

        self.assertEqual(upgrade.pre_upgrade_metapackages, metapackages)
        self.assertTrue(upgrade.reboot_required)

    def test_update_without_pre_upgrade_metapackages_preserves_existing(self):
        """update() without pre_upgrade_metapackages preserves existing data."""

        metapackages = [self._make_metapackage("mp1", False)]
        upgrade = nfvi.objects.v1.Upgrade(
            ["r1"],
            [],
            None,
            None,
            None,
            pre_upgrade_metapackages=metapackages,
        )

        upgrade.update(
            {"reboot_required": True, "vim_rr": True},
            None,
            None,
        )

        # Existing metapackages should be preserved
        self.assertEqual(upgrade.pre_upgrade_metapackages, metapackages)
        self.assertFalse(upgrade.reboot_required)


class TestComputeVimRR(BaseTestUsm):
    """Unit tests for the _compute_vim_rr helper.

    Validates that the correct range of releases is checked when computing
    vim_rr for patch removal (downgrade) scenarios. The function checks
    [from_release, to_release) — inclusive on from_release (higher version),
    exclusive on to_release (lower version, the target).
    """

    def setUp(self):
        super().setUp()

        self.mock_releases = self._mock_object(usm, "sw_deploy_get_releases")

    def _create_releases(self, *releases):
        """Build a list of release dicts from (sw_version, rr) tuples."""

        return [{"sw_version": ver, "reboot_required": rr} for ver, rr in releases]

    def test_checks_from_inclusive_to_exclusive(self):
        """Only releases in [from, to) are checked (from > to)."""

        releases = self._create_releases(
            ("26.10.0", True),
            ("26.10.1", True),
            ("26.10.2", False),
        )
        self.mock_releases.return_value = self._mock_response(releases)

        # Downgrade from 26.10.2 to 26.10.1: should check only 26.10.2
        result = usm._compute_vim_rr(self.token, "26.10.2", "26.10.1")

        # 26.10.2 is NRR and 26.10.1 is excluded (to_side exclusive)
        self.assertFalse(result)

    def test_detects_rr_in_range(self):
        """RR release in [from, to) makes vim_rr True."""

        releases = self._create_releases(
            ("26.10.0", False),
            ("26.10.1", False),
            ("26.10.2", True),
        )
        self.mock_releases.return_value = self._mock_response(releases)

        # Downgrade from 26.10.2 to 26.10.0: should check 26.10.1 and 26.10.2
        result = usm._compute_vim_rr(self.token, "26.10.2", "26.10.0")

        self.assertTrue(result)

    def test_includes_from_release(self):
        """The from_release (higher version being removed) IS included."""

        releases = self._create_releases(
            ("26.10.0", False),
            ("26.10.1", False),
            ("26.10.2", True),
        )
        self.mock_releases.return_value = self._mock_response(releases)

        result = usm._compute_vim_rr(self.token, "26.10.2", "26.10.1")

        # 26.10.2 is RR and included (from_side inclusive)
        self.assertTrue(result)

    def test_excludes_to_release(self):
        """The to_release (lower version, target) is NOT included."""

        releases = self._create_releases(
            ("26.10.0", False),
            ("26.10.1", True),
            ("26.10.2", False),
        )
        self.mock_releases.return_value = self._mock_response(releases)

        # Downgrade from 26.10.2 to 26.10.1: should check only 26.10.2
        result = usm._compute_vim_rr(self.token, "26.10.2", "26.10.1")

        # 26.10.1 is RR but excluded (to_side exclusive)
        self.assertFalse(result)

    def test_bug_scenario_remove_insvc_patch_over_rr(self):
        """Reproduce the bug: removing INSVC patch when target is RR.

        System state: 26.10.0 (deployed), 26.10.1 (deployed, RR),
        26.10.2 (deployed, INSVC).
        User removes patch 26.10.2 by deploying to 26.10.1.
        Only 26.10.2 is being removed, and it's INSVC, so no reboot needed.
        """

        releases = self._create_releases(
            ("26.10.0", True),
            ("26.10.1", True),
            ("26.10.2", False),
        )
        self.mock_releases.return_value = self._mock_response(releases)

        # Downgrade: from 26.10.2 (current) to 26.10.1 (target)
        result = usm._compute_vim_rr(self.token, "26.10.2", "26.10.1")

        # Only 26.10.2 is being removed, and it's NRR
        self.assertFalse(result)

    def test_remove_rr_patch(self):
        """Removing a RR patch should detect reboot needed.

        System state: 26.10.0 (deployed), 26.10.1 (deployed, RR).
        User removes 26.10.1 by deploying to 26.10.0.
        """

        releases = self._create_releases(
            ("26.10.0", True),
            ("26.10.1", True),
        )
        self.mock_releases.return_value = self._mock_response(releases)

        result = usm._compute_vim_rr(self.token, "26.10.1", "26.10.0")

        self.assertTrue(result)

    def test_remove_multiple_patches_one_rr(self):
        """Removing multiple patches where one is RR should detect reboot.

        System state: 26.10.0 (deployed), 26.10.1 (deployed, RR),
        26.10.2 (deployed, INSVC).
        User removes both by deploying to 26.10.0.
        """

        releases = self._create_releases(
            ("26.10.0", True),
            ("26.10.1", True),
            ("26.10.2", False),
        )
        self.mock_releases.return_value = self._mock_response(releases)

        result = usm._compute_vim_rr(self.token, "26.10.2", "26.10.0")

        # 26.10.1 is RR and in the removal range
        self.assertTrue(result)

    def test_returns_none_on_api_failure(self):
        """API failure returns None to allow fallback."""

        self.mock_releases.side_effect = Exception("API error")

        result = usm._compute_vim_rr(self.token, "26.10.2", "26.10.1")

        self.assertIsNone(result)

    def test_no_releases_returns_false(self):
        """No releases at all -> False (no RR found)."""

        self.mock_releases.return_value = self._mock_response([])

        result = usm._compute_vim_rr(self.token, "26.10.2", "26.10.1")

        self.assertFalse(result)

    def test_releases_outside_range_ignored(self):
        """Releases outside the from/to range should not affect the result."""

        releases = self._create_releases(
            ("26.09.0", True),
            ("26.10.0", False),
            ("26.10.1", False),
            ("26.10.2", False),
            ("27.03.0", True),
        )
        self.mock_releases.return_value = self._mock_response(releases)

        # Downgrade from 26.10.2 to 26.10.1: only 26.10.2 is in range
        result = usm._compute_vim_rr(self.token, "26.10.2", "26.10.1")

        self.assertFalse(result)
