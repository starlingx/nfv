#
# Copyright (c) 2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#

import kubernetes
from kubernetes.client.rest import ApiException
from unittest import mock

from nfv_plugins.nfvi_plugins.clients import kubernetes_client

from nfv_unit_tests.tests import testcase


def mock_load_kube_config(path):
    return


def exchange_json_to_V1Node(body):
    node = kubernetes.client.V1Node()

    # exchange taints only.
    if 'spec' not in body:
        return node

    node.spec = kubernetes.client.V1NodeSpec()
    if 'taints' not in body['spec']:
        return node

    node.spec.taints = []
    for taint in body['spec']['taints']:
        if type(taint) is kubernetes.client.models.v1_taint.V1Taint:
            node.spec.taints.append(taint)
            continue

        if 'key' in taint and 'effect' in taint:
            taintBody = kubernetes.client.V1Taint(taint['effect'], taint['key'])
            if 'value' in taint:
                taintBody.value = taint['value']
            node.spec.taints.append(taintBody)

    return node


@mock.patch('kubernetes.config.load_kube_config', mock_load_kube_config)
class TestNFVPluginsK8SNodeTaint(testcase.NFVTestCase):

    test_node_name = 'testNode'
    test_key1 = 'testKey1'
    test_value1 = 'testValue1'
    test_key2 = 'testKey2'
    test_value2 = 'testValue2'

    def setUp(self):
        super(TestNFVPluginsK8SNodeTaint, self).setUp()
        self.test_node_repo = {}
        self.setup_node_repo(self.test_node_name)

        def mock_patch_node(obj, node_name, body):
            if node_name in self.test_node_repo:
                self.test_node_repo[node_name] = exchange_json_to_V1Node(body)
            else:
                raise ApiException
            return self.test_node_repo[node_name]

        self.mocked_patch_node = mock.patch(
            'kubernetes.client.CoreV1Api.patch_node', mock_patch_node)
        self.mocked_patch_node.start()

        def mock_read_node(obj, node_name):
            if node_name in self.test_node_repo:
                return self.test_node_repo[node_name]
            else:
                raise ApiException

        self.mocked_read_node = mock.patch(
            'kubernetes.client.CoreV1Api.read_node', mock_read_node)
        self.mocked_read_node.start()

    def tearDown(self):
        super(TestNFVPluginsK8SNodeTaint, self).tearDown()
        self.mocked_patch_node.stop()
        self.mocked_read_node.stop()
        self.node_repo_clear()

    def check_taint_exist(self, node_name, effect, key, value):
        try:
            kube_client = kubernetes_client.get_client()
            response = kube_client.read_node(node_name)
        except ApiException:
            return False

        taints = response.spec.taints
        if taints is not None:
            for taint in taints:
                if (taint.key == key and
                    taint.effect == effect and
                    taint.value == value):
                    return True
        return False

    def setup_node_repo(self, node_name):
        body = kubernetes.client.V1Node()
        body.spec = kubernetes.client.V1NodeSpec()
        body.spec.taints = []

        self.test_node_repo[node_name] = body

    def node_repo_clear(self):
        self.test_node_repo.clear()

    def test_when_add_taint_and_get_then_get_it(self):
        assert self.check_taint_exist(self.test_node_name,
                                      'NoExecute',
                                      self.test_key1,
                                      self.test_value1) is False
        kubernetes_client.taint_node(self.test_node_name,
                                     'NoExecute',
                                     self.test_key1,
                                     self.test_value1)
        assert self.check_taint_exist(self.test_node_name,
                                      'NoExecute',
                                      self.test_key1,
                                      self.test_value1) is True

    def test_when_add_two_taints_and_get_then_get_them(self):
        assert self.check_taint_exist(self.test_node_name,
                                      'NoExecute',
                                      self.test_key1,
                                      self.test_value1) is False
        assert self.check_taint_exist(self.test_node_name,
                                      'NoExecute',
                                      self.test_key2,
                                      self.test_value2) is False

        kubernetes_client.taint_node(self.test_node_name,
                                     'NoExecute',
                                     self.test_key2,
                                     self.test_value2)
        kubernetes_client.taint_node(self.test_node_name,
                                     'NoExecute',
                                     self.test_key1,
                                     self.test_value1)

        assert self.check_taint_exist(self.test_node_name,
                                      'NoExecute',
                                      self.test_key1,
                                      self.test_value1) is True
        assert self.check_taint_exist(self.test_node_name,
                                      'NoExecute',
                                      self.test_key2,
                                      self.test_value2) is True

    def test_when_delete_exist_taint_and_get_then_get_none(self):
        kubernetes_client.taint_node(self.test_node_name,
                                     'NoExecute',
                                     self.test_key1,
                                     self.test_value1)
        assert self.check_taint_exist(self.test_node_name,
                                      'NoExecute',
                                      self.test_key1,
                                      self.test_value1) is True
        kubernetes_client.untaint_node(self.test_node_name,
                                       'NoExecute',
                                       self.test_key1)
        assert self.check_taint_exist(self.test_node_name,
                                      'NoExecute',
                                      self.test_key1,
                                      self.test_value1) is False

    def test_when_delete_no_exist_taint_and_get_then_get_none(self):
        assert self.check_taint_exist(self.test_node_name,
                                      'NoExecute',
                                      self.test_key1,
                                      self.test_value1) is False
        kubernetes_client.untaint_node(self.test_node_name,
                                       'NoExecute',
                                       self.test_key1)
        assert self.check_taint_exist(self.test_node_name,
                                      'NoExecute',
                                      self.test_key1,
                                      self.test_value1) is False

    def test_when_add_taint_twice_and_delete_it_and_get_then_get_none(self):
        kubernetes_client.taint_node(self.test_node_name,
                                     'NoSchedule',
                                     self.test_key1,
                                     self.test_value1)
        kubernetes_client.taint_node(self.test_node_name,
                                     'NoSchedule',
                                     self.test_key1,
                                     self.test_value1)
        assert self.check_taint_exist(self.test_node_name,
                                      'NoSchedule',
                                      self.test_key1,
                                      self.test_value1) is True

        kubernetes_client.untaint_node(self.test_node_name,
                                       'NoSchedule',
                                       self.test_key1)
        assert self.check_taint_exist(self.test_node_name,
                                      'NoSchedule',
                                      self.test_key1,
                                      self.test_value1) is False


@mock.patch('kubernetes.config.load_kube_config', mock_load_kube_config)
class TestNFVPluginsK8SMarkAllPodsNotReady(testcase.NFVTestCase):

    list_namespaced_pod_result = kubernetes.client.V1PodList(
        api_version="v1",
        items=[
            kubernetes.client.V1Pod(
                api_version="v1",
                kind="Pod",
                metadata=kubernetes.client.V1ObjectMeta(
                    name="test-pod-not-ready",
                    namespace="test-namespace-1"),
                status=kubernetes.client.V1PodStatus(
                    conditions=[
                        kubernetes.client.V1PodCondition(
                            status="True",
                            type="Initialized"),
                        kubernetes.client.V1PodCondition(
                            status="False",
                            type="Ready"),
                        kubernetes.client.V1PodCondition(
                            status="True",
                            type="ContainersReady"),
                        kubernetes.client.V1PodCondition(
                            status="True",
                            type="PodScheduled"),
                    ]
                )
            ),
            kubernetes.client.V1Pod(
                api_version="v1",
                kind="Pod",
                metadata=kubernetes.client.V1ObjectMeta(
                    name="test-pod-ready",
                    namespace="test-namespace-1"),
                status=kubernetes.client.V1PodStatus(
                    conditions=[
                        kubernetes.client.V1PodCondition(
                            status="True",
                            type="Initialized"),
                        kubernetes.client.V1PodCondition(
                            status="True",
                            type="Ready"),
                        kubernetes.client.V1PodCondition(
                            status="True",
                            type="ContainersReady"),
                        kubernetes.client.V1PodCondition(
                            status="True",
                            type="PodScheduled"),
                    ]
                )
            ),
            kubernetes.client.V1Pod(
                api_version="v1",
                kind="Pod",
                metadata=kubernetes.client.V1ObjectMeta(
                    name="test-pod-no-ready-status",
                    namespace="test-namespace-1"),
                status=kubernetes.client.V1PodStatus(
                    conditions=[
                        kubernetes.client.V1PodCondition(
                            status="True",
                            type="Initialized"),
                        kubernetes.client.V1PodCondition(
                            status="True",
                            type="ContainersReady"),
                        kubernetes.client.V1PodCondition(
                            status="True",
                            type="PodScheduled"),
                    ]
                )
            ),
        ]
    )

    def setUp(self):
        super(TestNFVPluginsK8SMarkAllPodsNotReady, self).setUp()

        def mock_list_namespaced_pod(obj, namespace, field_selector=""):
            return self.list_namespaced_pod_result

        self.mocked_list_namespaced_pod = mock.patch(
            'kubernetes.client.CoreV1Api.list_namespaced_pod',
            mock_list_namespaced_pod)
        self.mocked_list_namespaced_pod.start()

        self.mock_patch_namespaced_pod_status = mock.Mock()
        self.mocked_patch_namespaced_pod_status = mock.patch(
            'kubernetes.client.CoreV1Api.patch_namespaced_pod_status',
            self.mock_patch_namespaced_pod_status)
        self.mocked_patch_namespaced_pod_status.start()

    def tearDown(self):
        super(TestNFVPluginsK8SMarkAllPodsNotReady, self).tearDown()

        self.mocked_list_namespaced_pod.stop()
        self.mocked_patch_namespaced_pod_status.stop()

    def test_mark_pods(self):

        kubernetes_client.mark_all_pods_not_ready("test_node", "test_reason")

        self.mock_patch_namespaced_pod_status.assert_called_with(
            "test-pod-ready", "test-namespace-1", mock.ANY)
        self.mock_patch_namespaced_pod_status.assert_called_once()


@mock.patch('kubernetes.config.load_kube_config', mock_load_kube_config)
class TestNFVPluginsK8SGetTerminatingPods(testcase.NFVTestCase):

    list_namespaced_pod_result = {
        'test-node-1': kubernetes.client.V1PodList(
            api_version="v1",
            items=[
                kubernetes.client.V1Pod(
                    api_version="v1",
                    kind="Pod",
                    metadata=kubernetes.client.V1ObjectMeta(
                        name="test-pod-not-terminating",
                        namespace="test-namespace-1",
                        deletion_timestamp=None)
                ),
                kubernetes.client.V1Pod(
                    api_version="v1",
                    kind="Pod",
                    metadata=kubernetes.client.V1ObjectMeta(
                        name="test-pod-terminating",
                        namespace="test-namespace-1",
                        deletion_timestamp="2019-10-03T16:54:25Z")
                ),
                kubernetes.client.V1Pod(
                    api_version="v1",
                    kind="Pod",
                    metadata=kubernetes.client.V1ObjectMeta(
                        name="test-pod-not-terminating-2",
                        namespace="test-namespace-1",
                        deletion_timestamp=None)
                )
            ]
        ),
        'test-node-2': kubernetes.client.V1PodList(
            api_version="v1",
            items=[
                kubernetes.client.V1Pod(
                    api_version="v1",
                    kind="Pod",
                    metadata=kubernetes.client.V1ObjectMeta(
                        name="test-pod-not-terminating",
                        namespace="test-namespace-1",
                        deletion_timestamp=None)
                ),
                kubernetes.client.V1Pod(
                    api_version="v1",
                    kind="Pod",
                    metadata=kubernetes.client.V1ObjectMeta(
                        name="test-pod-not-terminating-2",
                        namespace="test-namespace-1",
                        deletion_timestamp=None)
                )
            ]
        ),
        'test-node-3': kubernetes.client.V1PodList(
            api_version="v1",
            items=[
                kubernetes.client.V1Pod(
                    api_version="v1",
                    kind="Pod",
                    metadata=kubernetes.client.V1ObjectMeta(
                        name="test-pod-not-terminating",
                        namespace="test-namespace-1",
                        deletion_timestamp=None)
                ),
                kubernetes.client.V1Pod(
                    api_version="v1",
                    kind="Pod",
                    metadata=kubernetes.client.V1ObjectMeta(
                        name="test-pod-terminating",
                        namespace="test-namespace-1",
                        deletion_timestamp="2019-10-03T16:54:25Z")
                ),
                kubernetes.client.V1Pod(
                    api_version="v1",
                    kind="Pod",
                    metadata=kubernetes.client.V1ObjectMeta(
                        name="test-pod-terminating-2",
                        namespace="test-namespace-1",
                        deletion_timestamp="2019-10-03T16:55:25Z")
                )
            ]
        )
    }

    def setUp(self):
        super(TestNFVPluginsK8SGetTerminatingPods, self).setUp()

        def mock_list_namespaced_pod(obj, namespace, field_selector=""):
            node_name = field_selector.split('spec.nodeName=', 1)[1]
            return self.list_namespaced_pod_result[node_name]

        self.mocked_list_namespaced_pod = mock.patch(
            'kubernetes.client.CoreV1Api.list_namespaced_pod',
            mock_list_namespaced_pod)
        self.mocked_list_namespaced_pod.start()

    def tearDown(self):
        super(TestNFVPluginsK8SGetTerminatingPods, self).tearDown()

        self.mocked_list_namespaced_pod.stop()

    def test_get_terminating_with_terminating(self):

        result = kubernetes_client.get_terminating_pods("test-node-1")

        assert result.result_data == 'test-pod-terminating'

    def test_get_terminating_no_terminating(self):

        result = kubernetes_client.get_terminating_pods("test-node-2")

        assert result.result_data == ''

    def test_get_terminating_with_two_terminating(self):

        result = kubernetes_client.get_terminating_pods("test-node-3")

        assert result.result_data == \
               'test-pod-terminating,test-pod-terminating-2'
