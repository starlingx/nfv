#
# Copyright (c) 2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import kubernetes
from kubernetes.client.rest import ApiException
from six.moves import http_client as httplib

from nfv_common import debug
from nfv_common.helpers import Result

DLOG = debug.debug_get_logger('nfv_plugins.nfvi_plugins.clients.kubernetes_client')


def get_client():
    kubernetes.config.load_kube_config('/etc/kubernetes/admin.conf')

    # Workaround: Turn off SSL/TLS verification
    c = kubernetes.client.Configuration()
    c.verify_ssl = False
    kubernetes.client.Configuration.set_default(c)

    return kubernetes.client.CoreV1Api()


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
        body = {"spec": {"taints": updated_taints}}
        response = kube_client.patch_node(node_name, body)

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
        response = kube_client.delete_node(node_name, body)
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
