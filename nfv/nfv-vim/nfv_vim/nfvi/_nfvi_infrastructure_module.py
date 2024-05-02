#
# Copyright (c) 2015-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from nfv_common import debug

from nfv_vim.nfvi._nfvi_infrastructure_plugin import NFVIInfrastructurePlugin

DLOG = debug.debug_get_logger('nfv_vim.nfvi.nfvi_infrastructure_module')

_infrastructure_plugin = None


def nfvi_get_datanetworks(host_uuid, callback):
    """
    Get host data network information
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_datanetworks',
                                                  host_uuid,
                                                  callback=callback)
    return cmd_id


def nfvi_get_system_info(callback):
    """
    Get information about the system
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_system_info',
                                                  callback=callback)
    return cmd_id


def nfvi_get_system_state(callback):
    """
    Get the state of the system
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_system_state',
                                                  callback=callback)
    return cmd_id


def nfvi_get_hosts(callback):
    """
    Get a list of hosts
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_hosts',
                                                  callback=callback)
    return cmd_id


def nfvi_get_host(host_uuid, host_name, callback):
    """
    Get host details
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_host',
                                                  host_uuid, host_name,
                                                  callback=callback)
    return cmd_id


def nfvi_get_deployment_host(host_name, callback):
    """
    Get host resource from deployment namespace
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_deployment_host',
                                                  host_name,
                                                  callback=callback)
    return cmd_id


def nfvi_list_deployment_hosts(callback):
    """
    Get host resource from deployment namespace
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('list_deployment_hosts',
                                                  callback=callback)
    return cmd_id


def nfvi_get_system_config_unlock_request(host_names, callback):
    """
    Get host unlock request from deployment namespace
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_system_config_unlock_request',
                                                  host_names,
                                                  callback=callback)
    return cmd_id


def nfvi_get_host_devices(host_uuid, host_name, callback):
    """
    Get host device list details
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_host_devices',
                                                  host_uuid, host_name,
                                                  callback=callback)
    return cmd_id


def nfvi_get_host_device(host_uuid, host_name, device_uuid, device_name, callback):
    """
    Get host device details
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_host_device',
                                                  host_uuid, host_name,
                                                  device_uuid, device_name,
                                                  callback=callback)
    return cmd_id


def nfvi_host_device_image_update(host_uuid, host_name, callback):
    """
    Update host device image
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('host_device_image_update',
                                                  host_uuid, host_name,
                                                  callback=callback)
    return cmd_id


def nfvi_host_device_image_update_abort(host_uuid, host_name, callback):
    """
    Abort host device image update
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('host_device_image_update_abort',
                                                  host_uuid, host_name,
                                                  callback=callback)
    return cmd_id


def nfvi_kube_host_cordon(host_uuid, host_name, force, callback):
    """
    Kube Host Upgrade Cordon
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_host_cordon',
        host_uuid,
        host_name,
        force,
        callback=callback)
    return cmd_id


def nfvi_kube_host_uncordon(host_uuid, host_name, force, callback):
    """
    Kube Host Upgrade Uncordon
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_host_uncordon',
        host_uuid,
        host_name,
        force,
        callback=callback)
    return cmd_id


def nfvi_kube_host_upgrade_control_plane(host_uuid, host_name, force, callback):
    """
    Kube Host Upgrade Control Plane
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_host_upgrade_control_plane',
        host_uuid,
        host_name,
        force,
        callback=callback)
    return cmd_id


def nfvi_kube_host_upgrade_kubelet(host_uuid, host_name, force, callback):
    """
    Kube Host Upgrade Kubelet
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_host_upgrade_kubelet',
        host_uuid,
        host_name,
        force,
        callback=callback)
    return cmd_id


def nfvi_kube_rootca_update_abort(callback):
    """Kube RootCA Update - Abort"""
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_rootca_update_abort',
        callback=callback)
    return cmd_id


def nfvi_kube_rootca_update_complete(callback):
    """Kube RootCA Update - Complete"""
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_rootca_update_complete',
        callback=callback)
    return cmd_id


def nfvi_kube_rootca_update_generate_cert(expiry_date, subject, callback):
    """Kube RootCA Update - Generate Cert"""
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_rootca_update_generate_cert',
        expiry_date=expiry_date,
        subject=subject,
        callback=callback)
    return cmd_id


def nfvi_kube_rootca_update_host(host_uuid, host_name, update_type,
                                 in_progress_state, completed_state,
                                 failed_state, callback):
    """Kube RootCA Update - Host"""
    cmd_id = _infrastructure_plugin.invoke_plugin('kube_rootca_update_host',
                                                  host_uuid,
                                                  host_name,
                                                  update_type,
                                                  in_progress_state,
                                                  completed_state,
                                                  failed_state,
                                                  callback=callback)
    return cmd_id


# todo(abailey): Similar in-progress/complete/failed handling as used for hosts
# would protect stalled pod states from blocking orchestration
def nfvi_kube_rootca_update_pods(phase, callback):
    """Kube RootCA Update - Pods for a particular phase"""
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_rootca_update_pods',
        phase,
        callback=callback)
    return cmd_id


def nfvi_kube_rootca_update_start(force, alarm_ignore_list, callback):
    """Kube RootCA Update - Start"""
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_rootca_update_start',
        force=force,
        alarm_ignore_list=alarm_ignore_list,
        callback=callback)
    return cmd_id


def nfvi_kube_rootca_update_upload_cert(cert_file, callback):
    """Kube RootCA Update - Upload Cert"""
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_rootca_update_upload_cert',
        cert_file=cert_file,
        callback=callback)
    return cmd_id


def nfvi_kube_upgrade_abort(callback):
    """Kube Upgrade - Abort"""
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_upgrade_abort',
        callback=callback)
    return cmd_id


def nfvi_kube_upgrade_cleanup(callback):
    """
    Kube Upgrade Cleanup
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_upgrade_cleanup',
        callback=callback)
    return cmd_id


def nfvi_kube_upgrade_complete(callback):
    """
    Kube Upgrade Complete
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_upgrade_complete',
        callback=callback)
    return cmd_id


def nfvi_kube_upgrade_download_images(callback):
    """
    Kube Upgrade Download Images
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_upgrade_download_images',
        callback=callback)
    return cmd_id


def nfvi_kube_upgrade_networking(callback):
    """
    Kube Upgrade Networking
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('kube_upgrade_networking',
                                                  callback=callback)
    return cmd_id


def nfvi_kube_upgrade_storage(callback):
    """
    Kube Upgrade Storage
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('kube_upgrade_storage',
                                                  callback=callback)
    return cmd_id


def nfvi_kube_upgrade_start(to_version, force, alarm_ignore_list, callback):
    """
    Kube Upgrade Start
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_upgrade_start',
        to_version=to_version,
        force=force,
        alarm_ignore_list=alarm_ignore_list,
        callback=callback)
    return cmd_id


def nfvi_kube_pre_application_update(callback):
    """
    Kube Upgrade Pre Application Update
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_pre_application_update',
        callback=callback)
    return cmd_id


def nfvi_kube_post_application_update(callback):
    """
    Kube Upgrade Post Application Update
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'kube_post_application_update',
        callback=callback)
    return cmd_id


def nfvi_get_kube_host_upgrade_list(callback):
    """
    Get kube host upgrade list
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_kube_host_upgrade_list',
                                                  callback=callback)
    return cmd_id


def nfvi_get_kube_rootca_host_update_list(callback):
    """
    Get kube rootca update host list
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'get_kube_rootca_host_update_list',
        callback=callback)
    return cmd_id


def nfvi_get_kube_rootca_update(callback):
    """
    Get kube rootca update
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_kube_rootca_update',
                                                  callback=callback)
    return cmd_id


def nfvi_get_kube_upgrade(callback):
    """
    Get kube upgrade
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_kube_upgrade',
                                                  callback=callback)
    return cmd_id


def nfvi_get_kube_version_list(callback):
    """
    Get kube version list
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_kube_version_list',
                                                  callback=callback)
    return cmd_id


def nfvi_get_upgrade(release, callback):
    """
    Get Software deploy
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_upgrade',
                                                  release,
                                                  callback=callback)
    return cmd_id


def nfvi_sw_deploy_precheck(release, callback):
    """
    Software deploy precheck
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('sw_deploy_precheck',
                                                  release,
                                                  callback=callback)
    return cmd_id


def nfvi_upgrade_start(release, callback):
    """
    Software deploy start
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('sw_deploy_start',
                                                  release,
                                                  callback=callback)
    return cmd_id


def nfvi_upgrade_activate(release, callback):
    """
    Software deploy activate
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('sw_deploy_activate',
                                                  release,
                                                  callback=callback)
    return cmd_id


def nfvi_upgrade_complete(release, callback):
    """
    Software deploy complete
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('sw_deploy_complete',
                                                  release,
                                                  callback=callback)
    return cmd_id


def nfvi_disable_container_host_services(host_uuid, host_name,
                                         host_personality, host_offline,
                                         callback):
    """
    Disable container services on a host
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'disable_host_services',
        host_uuid, host_name, host_personality, host_offline,
        callback=callback)
    return cmd_id


def nfvi_enable_container_host_services(host_uuid, host_name,
                                        host_personality,
                                        callback):
    """
    Enable container services on a host
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'enable_host_services',
        host_uuid, host_name, host_personality,
        callback=callback)
    return cmd_id


def nfvi_delete_container_host_services(host_uuid, host_name,
                                        host_personality,
                                        callback):
    """
    Delete container services on a host
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'delete_host_services',
        host_uuid, host_name, host_personality,
        callback=callback)
    return cmd_id


def nfvi_notify_host_services_enabled(host_uuid, host_name, callback):
    """
    Notify host services are enabled
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'notify_host_services_enabled', host_uuid, host_name,
        callback=callback)
    return cmd_id


def nfvi_notify_host_services_disabled(host_uuid, host_name, callback):
    """
    Notify host services are disabled
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'notify_host_services_disabled', host_uuid, host_name,
        callback=callback)
    return cmd_id


def nfvi_notify_host_services_disable_extend(host_uuid, host_name, callback):
    """
    Notify host services disable extend timeout
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'notify_host_services_disable_extend', host_uuid, host_name,
        callback=callback)
    return cmd_id


def nfvi_notify_host_services_disable_failed(host_uuid, host_name,
                                             reason, callback):
    """
    Notify host services disable failed
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'notify_host_services_disable_failed', host_uuid, host_name,
        reason, callback=callback)
    return cmd_id


def nfvi_notify_host_services_deleted(host_uuid, host_name, callback):
    """
    Notify host services have been deleted
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'notify_host_services_deleted', host_uuid, host_name,
        callback=callback)
    return cmd_id


def nfvi_notify_host_services_delete_failed(host_uuid, host_name,
                                            reason, callback):
    """
    Notify host services delete failed
    """
    cmd_id = _infrastructure_plugin.invoke_plugin(
        'notify_host_services_delete_failed', host_uuid, host_name,
        reason, callback=callback)
    return cmd_id


def nfvi_notify_host_failed(host_uuid, host_name, host_personality, callback):
    """
    Notify host is failed
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('notify_host_failed',
                                                  host_uuid, host_name,
                                                  host_personality,
                                                  callback=callback)
    return cmd_id


def nfvi_lock_host(host_uuid, host_name, callback):
    """
    Lock a host
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('lock_host', host_uuid,
                                                  host_name, callback=callback)
    return cmd_id


def nfvi_unlock_host(host_uuid, host_name, callback):
    """
    Unlock a host
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('unlock_host', host_uuid,
                                                  host_name, callback=callback)
    return cmd_id


def nfvi_reboot_host(host_uuid, host_name, callback):
    """
    Reboot a host
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('reboot_host', host_uuid,
                                                  host_name, callback=callback)
    return cmd_id


def nfvi_upgrade_host(host_uuid, host_name, callback):
    """
    Upgrade a host
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('upgrade_host', host_uuid,
                                                  host_name, callback=callback)
    return cmd_id


def nfvi_swact_from_host(host_uuid, host_name, callback):
    """
    Swact from a host
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('swact_from_host', host_uuid,
                                                  host_name, callback=callback)
    return cmd_id


def nfvi_get_alarms(callback):
    """
    Get alarms
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_alarms', callback=callback)
    return cmd_id


def nfvi_get_logs(start_period, end_period, callback):
    """
    Get logs
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_logs', start_period,
                                                  end_period, callback=callback)
    return cmd_id


def nfvi_get_alarm_history(start_period, end_period, callback):
    """
    Get logs
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_alarm_history', start_period,
                                                  end_period, callback=callback)
    return cmd_id


def nfvi_get_terminating_pods(host_name, callback):
    """
    Get terminating pods
    """
    cmd_id = _infrastructure_plugin.invoke_plugin('get_terminating_pods',
                                                  host_name, callback=callback)
    return cmd_id


def nfvi_register_host_add_callback(callback):
    """
    Register for host add notifications
    """
    _infrastructure_plugin.invoke_plugin('register_host_add_callback',
                                         callback=callback)


def nfvi_register_host_action_callback(callback):
    """
    Register for host action notifications
    """
    _infrastructure_plugin.invoke_plugin('register_host_action_callback',
                                         callback=callback)


def nfvi_register_host_state_change_callback(callback):
    """
    Register for host state change notifications
    """
    _infrastructure_plugin.invoke_plugin('register_host_state_change_callback',
                                         callback=callback)


def nfvi_register_host_get_callback(callback):
    """
    Register for host get notifications
    """
    _infrastructure_plugin.invoke_plugin('register_host_get_callback',
                                         callback=callback)


def nfvi_register_host_upgrade_callback(callback):
    """
    Register for host upgrade notifications
    """
    _infrastructure_plugin.invoke_plugin('register_host_upgrade_callback',
                                         callback=callback)


def nfvi_register_host_update_callback(callback):
    """
    Register for host update notifications
    """
    _infrastructure_plugin.invoke_plugin('register_host_update_callback',
                                         callback=callback)


def nfvi_register_host_notification_callback(callback):
    """
    Register for host notifications
    """
    _infrastructure_plugin.invoke_plugin('register_host_notification_callback',
                                         callback=callback)


def nfvi_register_sw_update_get_callback(callback):
    """
    Register for software update get notifications
    """
    _infrastructure_plugin.invoke_plugin('register_sw_update_get_callback',
                                         callback=callback)


def nfvi_infrastructure_initialize(config, pool):
    """
    Initialize the NFVI infrastructure package
    """
    global _infrastructure_plugin

    _infrastructure_plugin = NFVIInfrastructurePlugin(config['namespace'], pool)
    _infrastructure_plugin.initialize(config['config_file'])


def nfvi_infrastructure_finalize():
    """
    Finalize the NFVI infrastructure package
    """
    if _infrastructure_plugin is not None:
        _infrastructure_plugin.finalize()
