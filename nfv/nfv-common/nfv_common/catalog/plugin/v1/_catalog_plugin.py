#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from abc import ABCMeta
from abc import abstractmethod


class CatalogPlugin(metaclass=ABCMeta):
    """Abstract Catalog Plugin Class Definition."""

    @property
    @abstractmethod
    def name(self):
        """The name of plugin."""

    @property
    @abstractmethod
    def version(self):
        """The versions of the plugin."""

    @property
    @abstractmethod
    def provider(self):
        """Vendor created the plugin."""

    @property
    @abstractmethod
    def signature(self):
        """Signature of the plugin."""

    @abstractmethod
    def read_vnf_descriptor(self, vnfd_id, vnf_vendor, vnf_version):
        """Read a particular vnf descriptor."""

    @abstractmethod
    def initialize(self, version):
        """Initialize the plugin."""

    @abstractmethod
    def finalize(self):
        """Finalize the plugin."""
