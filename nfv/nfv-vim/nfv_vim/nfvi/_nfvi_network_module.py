#
# Copyright (c) 2015-2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_common import debug

from nfv_vim.nfvi._nfvi_network_plugin import NFVINetworkPlugin

DLOG = debug.debug_get_logger('nfv_vim.nfvi.nfvi_network_module')

_network_plugin = None


def nfvi_network_plugin_disabled():
    """
    Get network plugin disabled status
    """
    return (_network_plugin is None)


def nfvi_get_networks(paging, callback):
    """
    Get a list of networks
    """
    cmd_id = _network_plugin.invoke_plugin('get_networks', paging,
                                           callback=callback)
    return cmd_id


def nfvi_create_network(network_name, network_type, segmentation_id,
                        physical_network, shared, callback):
    """
    Create a network
    """
    cmd_id = _network_plugin.invoke_plugin('create_network', network_name,
                                           network_type, segmentation_id,
                                           physical_network, shared,
                                           callback=callback)
    return cmd_id


def nfvi_update_network(network_uuid, shared, callback):
    """
    Update a network
    """
    cmd_id = _network_plugin.invoke_plugin('update_network', network_uuid,
                                           shared, callback=callback)
    return cmd_id


def nfvi_delete_network(network_id, callback):
    """
    Delete a network
    """
    cmd_id = _network_plugin.invoke_plugin('delete_network', network_id,
                                           callback=callback)
    return cmd_id


def nfvi_get_network(network_id, callback):
    """
    Get a network
    """
    cmd_id = _network_plugin.invoke_plugin('get_network', network_id,
                                           callback=callback)
    return cmd_id


def nfvi_get_subnets(paging, callback):
    """
    Get a list of subnets
    """
    cmd_id = _network_plugin.invoke_plugin('get_subnets', paging,
                                           callback=callback)
    return cmd_id


def nfvi_create_subnet(network_uuid, subnet_name, ip_version, subnet_ip,
                       subnet_prefix, gateway_ip, dhcp_enabled, callback):
    """
    Create a subnet
    """
    cmd_id = _network_plugin.invoke_plugin('create_subnet', network_uuid,
                                           subnet_name, ip_version, subnet_ip,
                                           subnet_prefix, gateway_ip,
                                           dhcp_enabled, callback=callback)
    return cmd_id


def nfvi_update_subnet(subnet_uuid, gateway_ip, delete_gateway, dhcp_enabled,
                       callback):
    """
    Update a subnet
    """
    cmd_id = _network_plugin.invoke_plugin('update_subnet', subnet_uuid,
                                           gateway_ip, delete_gateway,
                                           dhcp_enabled, callback=callback)
    return cmd_id


def nfvi_delete_subnet(subnet_id, callback):
    """
    Delete a subnet
    """
    cmd_id = _network_plugin.invoke_plugin('delete_subnet', subnet_id,
                                           callback=callback)
    return cmd_id


def nfvi_get_subnet(subnet_id, callback):
    """
    Get a subnet
    """
    cmd_id = _network_plugin.invoke_plugin('get_subnet', subnet_id,
                                           callback=callback)
    return cmd_id


def nfvi_notify_network_host_disabled(host_uuid, host_name, host_personality,
                                      callback):
    """
    Notify network host is disabled
    """
    cmd_id = _network_plugin.invoke_plugin('notify_host_disabled',
                                           host_uuid, host_name,
                                           host_personality,
                                           callback=callback)
    return cmd_id


def nfvi_enable_network_host_services(host_uuid, host_name, host_personality,
                                      callback):
    """
    Enable network services
    """
    cmd_id = _network_plugin.invoke_plugin('enable_host_services',
                                           host_uuid, host_name,
                                           host_personality,
                                           callback=callback)
    return cmd_id


def nfvi_get_network_agents(callback):
    """
    Get network agents of all hosts
    """
    cmd_id = _network_plugin.invoke_plugin('get_network_agents',
                                           callback=callback)
    return cmd_id


def nfvi_get_dhcp_agent_networks(agent_id, callback):
    """
    Get networks hosted on a dhcp agent
    """
    cmd_id = _network_plugin.invoke_plugin('get_dhcp_agent_networks',
                                           agent_id, callback=callback)
    return cmd_id


def nfvi_get_agent_routers(agent_id, callback):
    """
    Get routers hosted on a l3 agent
    """
    cmd_id = _network_plugin.invoke_plugin('get_agent_routers',
                                           agent_id, callback=callback)
    return cmd_id


def nfvi_get_router_ports(router_id, callback):
    """
    Get router port information
    """
    cmd_id = _network_plugin.invoke_plugin('get_router_ports',
                                           router_id, callback=callback)
    return cmd_id


def nfvi_add_network_to_dhcp_agent(agent_id, network_id, callback):
    """
    Add a network to a DHCP agent
    """
    cmd_id = _network_plugin.invoke_plugin('add_network_to_dhcp_agent',
                                           agent_id, network_id, callback=callback)
    return cmd_id


def nfvi_remove_network_from_dhcp_agent(agent_id, network_id, callback):
    """
    Remove a network from a DHCP Agent
    """
    cmd_id = _network_plugin.invoke_plugin('remove_network_from_dhcp_agent',
                                           agent_id, network_id, callback=callback)
    return cmd_id


def nfvi_add_router_to_agent(agent_id, router_id, callback):
    """
    Add a router to an L3 agent
    """
    cmd_id = _network_plugin.invoke_plugin('add_router_to_agent',
                                           agent_id, router_id, callback=callback)
    return cmd_id


def nfvi_remove_router_from_agent(agent_id, router_id, callback):
    """
    Remove a router from an L3 Agent
    """
    cmd_id = _network_plugin.invoke_plugin('remove_router_from_agent',
                                           agent_id, router_id, callback=callback)
    return cmd_id


def nfvi_get_physical_network(network_id, callback):
    """
    Get physical network of a network
    """
    cmd_id = _network_plugin.invoke_plugin('get_physical_network',
                                           network_id, callback=callback)
    return cmd_id


def nfvi_delete_network_host_services(host_uuid, host_name, host_personality,
                                      callback):
    """
    Delete network services
    """
    cmd_id = _network_plugin.invoke_plugin('delete_host_services',
                                           host_uuid, host_name,
                                           host_personality,
                                           callback=callback)
    return cmd_id


def nfvi_query_network_host_services(host_uuid, host_name, host_personality,
                                     check_fully_up,
                                     callback):
    """
    Query network services
    """
    cmd_id = _network_plugin.invoke_plugin('query_host_services',
                                           host_uuid, host_name,
                                           host_personality,
                                           check_fully_up,
                                           callback=callback)
    return cmd_id


def nfvi_network_initialize(config, pool):
    """
    Initialize the NFVI network package
    """
    global _network_plugin

    _network_plugin = NFVINetworkPlugin(config['namespace'], pool)
    _network_plugin.initialize(config['config_file'])


def nfvi_network_finalize():
    """
    Finalize the NFVI network package
    """
    if _network_plugin is not None:
        _network_plugin.finalize()
