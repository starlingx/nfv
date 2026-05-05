#
# Copyright (C) 2019 Intel Corporation
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import abc


class NFVIFaultMgmtAPI(metaclass=abc.ABCMeta):
    """Abstract NFVI Fault Management API Class Definition."""

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
    def get_openstack_alarms(self, future, callback):
        """Get openstack alarms using the plugin."""

    @abc.abstractmethod
    def get_openstack_logs(self, future, start_period, end_period, callback):
        """Get openstack logs using the plugin."""

    @abc.abstractmethod
    def get_openstack_alarm_history(self, future, start_period, end_period, callback):
        """Get openstack alarm history using the plugin."""

    @abc.abstractmethod
    def initialize(self, config_file):
        """Initialize the plugin."""

    @abc.abstractmethod
    def finalize(self):
        """Finalize the plugin."""
