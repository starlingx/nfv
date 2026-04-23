#
# Copyright (c) 2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import abc


class NFVISwMgmtAPI(object, metaclass=abc.ABCMeta):
    """
    Abstract NFVI Software Management API Class Definition
    """

    @property
    @abc.abstractmethod
    def name(self):
        """
        Returns the name of plugin
        """
        pass

    @property
    @abc.abstractmethod
    def version(self):
        """
        Returns the version of the plugin
        """
        pass

    @property
    @abc.abstractmethod
    def provider(self):
        """
        Returns the vendor who created the plugin
        """
        pass

    @property
    @abc.abstractmethod
    def signature(self):
        """
        Returns the signature of the plugin
        """
        pass

    @abc.abstractmethod
    def query_updates(self, future, callback):
        """
        Query software updates using the plugin
        """
        pass

    @abc.abstractmethod
    def query_hosts(self, future, callback):
        """
        Query hosts using the plugin
        """
        pass

    @abc.abstractmethod
    def update_host(self, future, host_name, callback):
        """
        Apply a software update to a host using the plugin
        """
        pass

    @abc.abstractmethod
    def update_hosts(self, future, host_names, callback):
        """
        Apply a software update to a list of hosts using the plugin
        """
        pass

    @abc.abstractmethod
    def initialize(self, config_file):
        """
        Initialize the plugin
        """
        pass

    @abc.abstractmethod
    def finalize(self):
        """
        Finalize the plugin
        """
        pass
