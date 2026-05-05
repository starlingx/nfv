#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import abc


class NFVIIdentityAPI(metaclass=abc.ABCMeta):
    """Abstract NFVI Identity API Class Definition."""

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
    def get_tenants(self, future, callback):
        """Get a list of tenants using the plugin."""

    @abc.abstractmethod
    def initialize(self, config_file):
        """Initialize the plugin."""

    @abc.abstractmethod
    def finalize(self):
        """Finalize the plugin."""
