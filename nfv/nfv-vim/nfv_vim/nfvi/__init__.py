#
# Copyright (c) 2015-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import nfv_vim.nfvi.api  # noqa: F401
import nfv_vim.nfvi.objects  # noqa: F401

from nfv_vim.nfvi._nfvi_block_storage_module import (  # noqa: F401
    nfvi_block_storage_plugin_disabled
)
from nfv_vim.nfvi._nfvi_block_storage_module import (  # noqa: F401
    nfvi_get_volume_snapshots
)
from nfv_vim.nfvi._nfvi_block_storage_module import nfvi_create_volume  # noqa: F401
from nfv_vim.nfvi._nfvi_block_storage_module import nfvi_delete_volume  # noqa: F401
from nfv_vim.nfvi._nfvi_block_storage_module import nfvi_get_volume  # noqa: F401
from nfv_vim.nfvi._nfvi_block_storage_module import nfvi_get_volumes  # noqa: F401
from nfv_vim.nfvi._nfvi_block_storage_module import nfvi_update_volume  # noqa: F401

from nfv_vim.nfvi._nfvi_compute_module import (  # noqa: F401
    nfvi_cold_migrate_confirm_instance
)
from nfv_vim.nfvi._nfvi_compute_module import (  # noqa: F401
    nfvi_cold_migrate_revert_instance
)
from nfv_vim.nfvi._nfvi_compute_module import (  # noqa: F401
    nfvi_delete_compute_host_services
)
from nfv_vim.nfvi._nfvi_compute_module import (  # noqa: F401
    nfvi_disable_compute_host_services
)
from nfv_vim.nfvi._nfvi_compute_module import (  # noqa: F401
    nfvi_enable_compute_host_services
)
from nfv_vim.nfvi._nfvi_compute_module import (  # noqa: F401
    nfvi_notify_compute_host_disabled
)
from nfv_vim.nfvi._nfvi_compute_module import (  # noqa: F401
    nfvi_notify_compute_host_enabled
)
from nfv_vim.nfvi._nfvi_compute_module import (  # noqa: F401
    nfvi_query_compute_host_services
)
from nfv_vim.nfvi._nfvi_compute_module import (  # noqa: F401
    nfvi_register_instance_action_callback
)
from nfv_vim.nfvi._nfvi_compute_module import (  # noqa: F401
    nfvi_register_instance_action_change_callback
)
from nfv_vim.nfvi._nfvi_compute_module import (  # noqa: F401
    nfvi_register_instance_delete_callback
)
from nfv_vim.nfvi._nfvi_compute_module import (  # noqa: F401
    nfvi_register_instance_state_change_callback
)
from nfv_vim.nfvi._nfvi_compute_module import nfvi_cold_migrate_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_compute_plugin_disabled  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_create_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_create_instance_type  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_delete_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_delete_instance_type  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_evacuate_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_fail_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_get_host_aggregates  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_get_hypervisor  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_get_hypervisors  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_get_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_get_instance_groups  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_get_instance_type  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_get_instance_types  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_get_instances  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_live_migrate_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_pause_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_reboot_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_rebuild_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_reject_instance_action  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_resize_confirm_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_resize_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_resize_revert_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_resume_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_start_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_stop_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_suspend_instance  # noqa: F401
from nfv_vim.nfvi._nfvi_compute_module import nfvi_unpause_instance  # noqa: F401

from nfv_vim.nfvi._nfvi_defs import NFVI_ERROR_CODE  # noqa: F401

from nfv_vim.nfvi._nfvi_fault_mgmt_module import (  # noqa: F401
    nfvi_fault_mgmt_plugin_disabled
)
from nfv_vim.nfvi._nfvi_fault_mgmt_module import (  # noqa: F401
    nfvi_get_openstack_alarm_history
)
from nfv_vim.nfvi._nfvi_fault_mgmt_module import nfvi_get_openstack_alarms  # noqa: F401
from nfv_vim.nfvi._nfvi_fault_mgmt_module import nfvi_get_openstack_logs  # noqa: F401

from nfv_vim.nfvi._nfvi_guest_module import (  # noqa: F401
    nfvi_create_guest_host_services
)
from nfv_vim.nfvi._nfvi_guest_module import (  # noqa: F401
    nfvi_delete_guest_host_services
)
from nfv_vim.nfvi._nfvi_guest_module import (  # noqa: F401
    nfvi_disable_guest_host_services
)
from nfv_vim.nfvi._nfvi_guest_module import (  # noqa: F401
    nfvi_enable_guest_host_services
)
from nfv_vim.nfvi._nfvi_guest_module import (  # noqa: F401
    nfvi_register_guest_services_action_notify_callback
)
from nfv_vim.nfvi._nfvi_guest_module import (  # noqa: F401
    nfvi_register_guest_services_alarm_notify_callback
)
from nfv_vim.nfvi._nfvi_guest_module import (  # noqa: F401
    nfvi_register_guest_services_query_callback
)
from nfv_vim.nfvi._nfvi_guest_module import (  # noqa: F401
    nfvi_register_guest_services_state_notify_callback
)
from nfv_vim.nfvi._nfvi_guest_module import (  # noqa: F401
    nfvi_register_host_services_query_callback
)
from nfv_vim.nfvi._nfvi_guest_module import nfvi_guest_plugin_disabled  # noqa: F401
from nfv_vim.nfvi._nfvi_guest_module import nfvi_guest_services_create  # noqa: F401
from nfv_vim.nfvi._nfvi_guest_module import nfvi_guest_services_delete  # noqa: F401
from nfv_vim.nfvi._nfvi_guest_module import nfvi_guest_services_notify  # noqa: F401
from nfv_vim.nfvi._nfvi_guest_module import nfvi_guest_services_query  # noqa: F401
from nfv_vim.nfvi._nfvi_guest_module import nfvi_guest_services_set  # noqa: F401
from nfv_vim.nfvi._nfvi_guest_module import nfvi_guest_services_vote  # noqa: F401
from nfv_vim.nfvi._nfvi_guest_module import nfvi_query_guest_host_services  # noqa: F401

from nfv_vim.nfvi._nfvi_identity_module import nfvi_get_tenants  # noqa: F401

from nfv_vim.nfvi._nfvi_image_module import nfvi_create_image  # noqa: F401
from nfv_vim.nfvi._nfvi_image_module import nfvi_delete_image  # noqa: F401
from nfv_vim.nfvi._nfvi_image_module import nfvi_get_image  # noqa: F401
from nfv_vim.nfvi._nfvi_image_module import nfvi_get_images  # noqa: F401
from nfv_vim.nfvi._nfvi_image_module import nfvi_image_plugin_disabled  # noqa: F401
from nfv_vim.nfvi._nfvi_image_module import nfvi_update_image  # noqa: F401

from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_delete_container_host_services
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_disable_container_host_services
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_enable_container_host_services
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_get_alarm_history
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_get_kube_host_upgrade_list
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_get_kube_rootca_host_update_list
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_get_kube_rootca_update
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_get_kube_version_list
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_get_system_config_unlock_request
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_get_terminating_pods
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_host_device_image_update
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_host_device_image_update_abort
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_host_uncordon
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_host_upgrade_control_plane
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_host_upgrade_kubelet
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_post_application_update
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_pre_application_update
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_rootca_update_abort
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_rootca_update_complete
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_rootca_update_generate_cert
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_rootca_update_host
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_rootca_update_pods
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_rootca_update_start
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_upgrade_abort
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_upgrade_cleanup
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_upgrade_complete
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_upgrade_download_images
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_upgrade_networking
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_upgrade_start
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_kube_upgrade_storage
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_list_deployment_hosts
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_notify_host_failed
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_notify_host_services_delete_failed
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_notify_host_services_deleted
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_notify_host_services_disable_extend
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_notify_host_services_disable_failed
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_notify_host_services_disabled
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_notify_host_services_enabled
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_register_host_action_callback
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_register_host_add_callback
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_register_host_get_callback
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_register_host_notification_callback
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_register_host_state_change_callback
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_register_host_update_callback
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_register_host_upgrade_callback
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_register_sw_update_get_callback
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_sw_deploy_activate_rollback
)
from nfv_vim.nfvi._nfvi_infrastructure_module import (  # noqa: F401
    nfvi_sw_deploy_precheck
)
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_deploy_delete  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_get_alarms  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_get_datanetworks  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_get_host  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_get_host_device  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_get_host_devices  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_get_hosts  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_get_kube_upgrade  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_get_logs  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_get_system_info  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_get_system_state  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_get_upgrade  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_kube_host_cordon  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_lock_host  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_reboot_host  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_sw_deploy_abort  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_swact_from_host  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_unlock_host  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_upgrade_activate  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_upgrade_complete  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_upgrade_host  # noqa: F401
from nfv_vim.nfvi._nfvi_infrastructure_module import nfvi_upgrade_start  # noqa: F401

from nfv_vim.nfvi._nfvi_module import nfvi_finalize  # noqa: F401
from nfv_vim.nfvi._nfvi_module import nfvi_initialize  # noqa: F401
from nfv_vim.nfvi._nfvi_module import nfvi_reinitialize  # noqa: F401

from nfv_vim.nfvi._nfvi_network_module import (  # noqa: F401
    nfvi_add_network_to_dhcp_agent
)
from nfv_vim.nfvi._nfvi_network_module import (  # noqa: F401
    nfvi_delete_network_host_services
)
from nfv_vim.nfvi._nfvi_network_module import (  # noqa: F401
    nfvi_enable_network_host_services
)
from nfv_vim.nfvi._nfvi_network_module import (  # noqa: F401
    nfvi_notify_network_host_disabled
)
from nfv_vim.nfvi._nfvi_network_module import (  # noqa: F401
    nfvi_query_network_host_services
)
from nfv_vim.nfvi._nfvi_network_module import (  # noqa: F401
    nfvi_remove_network_from_dhcp_agent
)
from nfv_vim.nfvi._nfvi_network_module import (  # noqa: F401
    nfvi_remove_router_from_agent
)
from nfv_vim.nfvi._nfvi_network_module import nfvi_add_router_to_agent  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_create_network  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_create_subnet  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_delete_network  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_delete_subnet  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_get_agent_routers  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_get_dhcp_agent_networks  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_get_network  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_get_network_agents  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_get_networks  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_get_physical_network  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_get_router_ports  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_get_subnet  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_get_subnets  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_network_plugin_disabled  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_update_network  # noqa: F401
from nfv_vim.nfvi._nfvi_network_module import nfvi_update_subnet  # noqa: F401

from nfv_vim.nfvi._nfvi_sw_mgmt_module import nfvi_sw_mgmt_apply_updates  # noqa: F401
from nfv_vim.nfvi._nfvi_sw_mgmt_module import nfvi_sw_mgmt_query_hosts  # noqa: F401
from nfv_vim.nfvi._nfvi_sw_mgmt_module import nfvi_sw_mgmt_query_updates  # noqa: F401
from nfv_vim.nfvi._nfvi_sw_mgmt_module import nfvi_sw_mgmt_update_host  # noqa: F401
from nfv_vim.nfvi._nfvi_sw_mgmt_module import nfvi_sw_mgmt_update_hosts  # noqa: F401
