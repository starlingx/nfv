#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import abc


class NFVIGuestAPI(metaclass=abc.ABCMeta):
    """Abstract NFVI Guest API Class Definition."""

    @property
    @abc.abstractmethod
    def name(self):
        """Returns the name of plugin."""

    @property
    @abc.abstractmethod
    def version(self):
        """Returns the version of the plugin."""

    @property
    @abc.abstractmethod
    def provider(self):
        """Returns the vendor who created the plugin."""

    @property
    @abc.abstractmethod
    def signature(self):
        """Returns the signature of the plugin."""

    @abc.abstractmethod
    def guest_services_create(
        self, future, instance_uuid, host_name, services, callback
    ):
        """Guest Services Create."""

    @abc.abstractmethod
    def guest_services_set(self, future, instance_uuid, host_name, services, callback):
        """Guest Services Set."""

    @abc.abstractmethod
    def guest_services_delete(self, future, instance_uuid, callback):
        """Guest Services Delete."""

    @abc.abstractmethod
    def guest_services_query(self, future, instance_uuid, callback):
        """Guest Services Query."""

    @abc.abstractmethod
    def guest_services_vote(
        self, future, instance_uuid, host_name, action_type, callback
    ):
        """Guest Services Vote."""

    @abc.abstractmethod
    def guest_services_notify(
        self, future, instance_uuid, host_name, action_type, pre_notification, callback
    ):
        """Guest Services Notify."""

    @abc.abstractmethod
    def disable_host_services(
        self, future, host_uuid, host_name, host_personality, callback
    ):
        """Disable guest services on a host using the plugin."""

    @abc.abstractmethod
    def enable_host_services(
        self, future, host_uuid, host_name, host_personality, callback
    ):
        """Enable guest services on a host using the plugin."""

    @abc.abstractmethod
    def delete_host_services(
        self, future, host_uuid, host_name, host_personality, callback
    ):
        """Delete guest services on a host using the plugin."""

    @abc.abstractmethod
    def create_host_services(
        self, future, host_uuid, host_name, host_personality, callback
    ):
        """Create guest services on a host using the plugin."""

    @abc.abstractmethod
    def query_host_services(
        self, future, host_uuid, host_name, host_personality, callback
    ):
        """Query guest services on a host using the plugin."""

    @abc.abstractmethod
    def register_host_services_query_callback(self, callback):
        """Register for Host Services query."""

    @abc.abstractmethod
    def register_guest_services_query_callback(self, callback):
        """Register for Guest Services query."""

    @abc.abstractmethod
    def register_guest_services_state_notify_callback(self, callback):
        """Register for Guest Services notify service type event."""

    @abc.abstractmethod
    def register_guest_services_alarm_notify_callback(self, callback):
        """Register for Guest Services notify for alarm type event."""

    @abc.abstractmethod
    def initialize(self, config_file):
        """Initialize the plugin."""

    @abc.abstractmethod
    def finalize(self):
        """Finalize the plugin."""
