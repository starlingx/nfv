#
# Copyright (c) 2018-2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from fm_api import constants as fm_constants
from fm_api import fm_api
import kubernetes

from kubernetes import __version__ as K8S_MODULE_VERSION
from kubernetes.client.models.v1_container_image import V1ContainerImage
from kubernetes.client.rest import ApiException
from six.moves import http_client as httplib

from nfv_common import debug
from nfv_common.helpers import Result

K8S_MODULE_MAJOR_VERSION = int(K8S_MODULE_VERSION.split('.', maxsplit=1)[0])

fmapi = fm_api.FaultAPIs()

DLOG = debug.debug_get_logger('nfv_plugins.nfvi_plugins.clients.kubernetes_client')


# https://github.com/kubernetes-client/python/issues/895
# If a container image contains no tag or digest, node
# related requests sent via python Kubernetes client will be
# returned with exception because python Kubernetes client
# deserializes the ContainerImage response from kube-apiserver
# and it fails the validation due to the empty image name.
#
# Implement this workaround to replace the V1ContainerImage.names
# in the python Kubernetes client to bypass the "none image"
# check because the error is not from kubernetes.
#
# This workaround should be removed when we update to
# kubernetes client v22
def names(self, names):
    """Monkey patch V1ContainerImage with this to set the names."""
    self._names = names


# Replacing address of "names" in V1ContainerImage
# with the "names" defined above
V1ContainerImage.names = V1ContainerImage.names.setter(names)  # pylint: disable=assignment-from-no-return


def get_client():
    kubernetes.config.load_kube_config('/etc/kubernetes/admin.conf')

    # Workaround: Turn off SSL/TLS verification
    if K8S_MODULE_MAJOR_VERSION < 12:
        c = kubernetes.client.Configuration()
    else:
        c = kubernetes.client.Configuration().get_default_copy()
    c.verify_ssl = False
    kubernetes.client.Configuration.set_default(c)

    return kubernetes.client.CoreV1Api()


def get_kubertnetes_https_client():
    """
    Get Kubernetes client with HTTPS enabled
    """
    kubernetes.config.load_kube_config('/etc/kubernetes/admin.conf')

    if K8S_MODULE_MAJOR_VERSION < 12:
        c = kubernetes.client.Configuration()
    else:
        c = kubernetes.client.Configuration().get_default_copy()
    kubernetes.client.Configuration.set_default(c)
    return kubernetes.client


def get_customobjects_api_instance():
    """
    Get a custom objects API instance
    """
    client = get_kubertnetes_https_client()
    return client.CustomObjectsApi()


def raise_alarm(node_name):

    entity_instance_id = "%s=%s" % (fm_constants.FM_ENTITY_TYPE_HOST,
            node_name)
    fault = fm_api.Fault(
        alarm_id=fm_constants.FM_ALARM_ID_USM_NODE_TAINTED,
        alarm_state=fm_constants.FM_ALARM_STATE_SET,
        entity_type_id=fm_constants.FM_ENTITY_TYPE_HOST,
        entity_instance_id=entity_instance_id,
        severity=fm_constants.FM_ALARM_SEVERITY_MAJOR,
        reason_text=("Node tainted."),
        alarm_type=fm_constants.FM_ALARM_TYPE_7,
        probable_cause=fm_constants.ALARM_PROBABLE_CAUSE_8,
        proposed_repair_action=("Execute 'kubectl taint nodes %s services=disabled:NoExecute-'. "
            "If it fails, Execute 'system host-lock %s' followed by 'system host-unlock %s'. "
            "If issue still persists, contact next level of support."
            % (node_name, node_name, node_name)),
        service_affecting=True)
    DLOG.info("Raising alarm %s on %s " % (fm_constants.FM_ALARM_ID_USM_NODE_TAINTED, node_name))
    fmapi.set_fault(fault)


def clear_alarm(node_name):

    entity_instance_id = "%s=%s" % (fm_constants.FM_ENTITY_TYPE_HOST,
            node_name)
    DLOG.info("Clearing alarm %s on %s " % (fm_constants.FM_ALARM_ID_USM_NODE_TAINTED, node_name))
    fmapi.clear_fault(fm_constants.FM_ALARM_ID_USM_NODE_TAINTED, entity_instance_id)


def taint_node(node_name, effect, key, value):
    """
    Apply a taint to a node
    """
    # Get the client.
    kube_client = get_client()
    # Retrieve the node to access any existing taints.
    try:
        response = kube_client.read_node(node_name)
    except ApiException as e:
        if e.status == httplib.NOT_FOUND:
            # In some cases we may attempt to taint a node that exists in
            # the VIM, but not yet in kubernetes (e.g. when the node is first
            # being configured). Ignore the failure.
            DLOG.info("Not tainting node %s because it doesn't exist" %
                      node_name)
            return
        else:
            raise

    add_taint = True
    taints = response.spec.taints
    if taints is not None:
        for taint in taints:
            # Taints must be unique by key and effect
            if taint.key == key and taint.effect == effect:
                add_taint = False
                if taint.value != value:
                    msg = ("Duplicate value - key: %s effect: %s "
                           "value: %s new value %s" % (key, effect,
                                                       taint.value, value))
                    DLOG.error(msg)
                    raise Exception(msg)
                else:
                    # This taint already exists
                    break

    if add_taint:
        DLOG.info("Adding %s=%s:%s taint to node %s" % (key, value, effect,
                                                        node_name))
        # Preserve any existing taints
        if taints is not None:
            body = {"spec": {"taints": taints}}
        else:
            body = {"spec": {"taints": []}}
        # Add our new taint
        new_taint = {"key": key, "value": value, "effect": effect}
        body["spec"]["taints"].append(new_taint)
        response = kube_client.patch_node(node_name, body)
        # Clear taint node alarm if tainting is successful.
        # Alarm not cleared if taint is already present in the system
        # or the node is under configuration.
        clear_alarm(node_name)

    return Result(response)


def untaint_node(node_name, effect, key):
    """
    Remove a taint from a node
    """
    # Get the client.
    kube_client = get_client()

    # Retrieve the node to access any existing taints.
    response = kube_client.read_node(node_name)

    remove_taint = False
    taints = response.spec.taints
    if taints is not None:
        for taint in taints:
            # Taints must be unique by key and effect
            if taint.key == key and taint.effect == effect:
                remove_taint = True
                break

    if remove_taint:
        DLOG.info("Removing %s:%s taint from node %s" % (key, effect,
                                                         node_name))
        # Preserve any existing taints
        updated_taints = [taint for taint in taints if taint.key != key or
                          taint.effect != effect]
        DLOG.info("Updated taints %s" % (updated_taints))
        body = {"spec": {"taints": updated_taints}}
        response = kube_client.patch_node(node_name, body)
        check_taints = kube_client.read_node(node_name)
        taints = check_taints.spec.taints
        DLOG.info("Existing taint %s" % (taints))
        if taints is not None:
            for taint in taints:
                if (taint.key == key and taint.effect == effect):
                    DLOG.info("Removing %s:%s taint from node %s failed" % (key,
                        effect, node_name))
                    raise_alarm(node_name)
                    break
            else:
                # Taint removed successfully. If there are multiple taints
                # on the system, removing the 'services' taint will clear the alarm.
                clear_alarm(node_name)
        else:
            # If there is only 'services' taint on the system , then removing the taint
            # should clear the alarm.
            clear_alarm(node_name)

    return Result(response)


def delete_node(node_name):
    """
    Delete a node
    """
    # Get the client.
    kube_client = get_client()

    # Delete the node
    body = kubernetes.client.V1DeleteOptions()

    try:
        if K8S_MODULE_MAJOR_VERSION < 12:
            response = kube_client.delete_node(node_name, body)
        else:
            response = kube_client.delete_node(node_name, body=body)
    except ApiException as e:
        if e.status == httplib.NOT_FOUND:
            # In some cases we may attempt to delete a node that exists in
            # the VIM, but not yet in kubernetes (e.g. when the node is first
            # being configured). Ignore the failure.
            DLOG.info("Not deleting node %s because it doesn't exist" %
                      node_name)
            return
        else:
            raise

    return Result(response)


def mark_all_pods_not_ready(node_name, reason):
    """
    Mark all pods on a node as not ready
    Note: It would be preferable to mark the node as not ready and have
    kubernetes then mark the pods as not ready, but this is not supported.
    """
    # Get the client.
    kube_client = get_client()

    # Retrieve the pods on the specified node.
    response = kube_client.list_namespaced_pod(
        "", field_selector="spec.nodeName=%s" % node_name)

    pods = response.items
    if pods is not None:
        for pod in pods:
            for condition in pod.status.conditions:
                if condition.type == "Ready":
                    if condition.status != "False":
                        # Update the Ready status to False
                        body = {"status":
                                {"conditions":
                                 [{"type": "Ready",
                                   "status": "False",
                                   "reason": reason,
                                   }]}}
                        try:
                            DLOG.debug(
                                "Marking pod %s in namespace %s not ready" %
                                (pod.metadata.name, pod.metadata.namespace))
                            kube_client.patch_namespaced_pod_status(
                                pod.metadata.name, pod.metadata.namespace, body)
                        except ApiException:
                            DLOG.exception(
                                "Failed to update status for pod %s in "
                                "namespace %s" % (pod.metadata.name,
                                                  pod.metadata.namespace))
                    break
    return


def get_terminating_pods(node_name):
    """
    Get all pods on a node that are terminating
    """
    # Get the client.
    kube_client = get_client()

    # Retrieve the pods on the specified node.
    response = kube_client.list_namespaced_pod(
        "", field_selector="spec.nodeName=%s" % node_name)

    terminating_pods = list()
    pods = response.items
    if pods is not None:
        for pod in pods:
            # The presence of the deletion_timestamp indicates the pod is
            # terminating.
            if pod.metadata.deletion_timestamp is not None:
                terminating_pods.append(pod.metadata.name)

    return Result(','.join(terminating_pods))


def get_namespaced_custom_object(name, plural, group, version, namespace):
    """
    Get a custom resource object in a namespace
    """
    # Get a CustomObjectsApi instance
    api_instance = get_customobjects_api_instance()

    try:
        resource = api_instance.get_namespaced_custom_object(
            group=group,
            version=version,
            name=name,
            namespace=namespace,
            plural=plural
        )
        return Result(resource)
    except ApiException as e:
        DLOG.exception(
            "Failed to get object %s from namespace %s, "
            "reason: %s" % (name, namespace, e.reason))
        return None


def get_deployment_host(name):
    """
    Get a host in the deployment namespace
    """
    # Get a CustomObjectsApi instance
    api_instance = get_customobjects_api_instance()

    try:
        resource = api_instance.get_namespaced_custom_object(
            group='starlingx.windriver.com',
            version='v1',
            name=name,
            namespace='deployment',
            plural='hosts'
        )
        unlock_request = resource.get('status').get('strategyRequired')
        result = {'name': name, 'unlock_request': unlock_request}
        return Result(result)
    except ApiException as e:
        DLOG.exception(
            "Failed to get object %s from namespace deployment, "
            "reason: %s" % (name, e.reason))
        return None


def list_namespaced_custom_objects(plural, group, version, namespace):
    """
    List custom resource objects in a namespace
    """
    # Get a CustomObjectsApi instance
    api_instance = get_customobjects_api_instance()

    try:
        resources = api_instance.list_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural
        )
        return Result(resources)
    except ApiException as e:
        DLOG.exception(
            "Failed to list objects %s from namespace %s, "
            "reason: %s" % (plural, namespace, e.reason))
        return None


def list_deployment_hosts():
    """
    List hosts in a deployment namespace
    """
    # Get a CustomObjectsApi instance
    api_instance = get_customobjects_api_instance()

    try:
        resources = api_instance.list_namespaced_custom_object(
            group='starlingx.windriver.com',
            version='v1',
            namespace='deployment',
            plural='hosts'
        )

        if not resources:
            return None

        results = list()
        for resource in resources.get('items'):
            name = resource.get('metadata').get('name')
            unlock_request = resource.get('status').get('strategyRequired')
            results.append({'name': name,
                            'unlock_request': unlock_request})

        return Result(results)
    except ApiException as e:
        DLOG.exception(
            "Failed to list hosts from deployment namespace, "
            "reason: %s" % e.reason)
        return None


def get_namespaced_running_pods(namespace, name):
    """
    Get running pods in a namespace
    """
    api_instance = get_client()

    try:
        response = api_instance.list_namespaced_pod(
            namespace=namespace,
            field_selector="status.phase=Running",)
    except ApiException as e:
        DLOG.exception(
            "Failed to list pods from namespace %s, "
            "reason: %s" % (namespace, e.reason))
        return None

    pods = response.items
    found = list()
    if pods is not None:
        for pod in pods:
            if name in pod.metadata.name:
                found.append(pod.metadata.name)

    return Result(','.join(found))
