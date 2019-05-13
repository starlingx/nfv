#
# Copyright (C) 2019 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
import abc
import six


@six.add_metaclass(abc.ABCMeta)
class NFVIFaultMgmtAPI(object):
    """
    Abstract NFVI Fault Management API Class Definition
    """
    @abc.abstractproperty
    def name(self):
        """
        Returns the name of plugin
        """
        pass

    @abc.abstractproperty
    def version(self):
        """
        Returns the version of the plugin
        """
        pass

    @abc.abstractproperty
    def provider(self):
        """
        Returns the vendor who created the plugin
        """
        pass

    @abc.abstractproperty
    def signature(self):
        """
        Returns the signature of the plugin
        """
        pass

    @abc.abstractmethod
    def get_openstack_alarms(self, future, callback):
        """
        Get openstack alarms using the plugin
        """
        pass

    @abc.abstractmethod
    def get_openstack_logs(self, future, start_period, end_period, callback):
        """
        Get openstack logs using the plugin
        """
        pass

    @abc.abstractmethod
    def get_openstack_alarm_history(self, future, start_period, end_period, callback):
        """
        Get openstack alarm history using the plugin
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
