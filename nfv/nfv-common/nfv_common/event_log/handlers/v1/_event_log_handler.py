#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import abc


class EventLogHandler(metaclass=abc.ABCMeta):
    """Abstract Event Log Handler Class Definition."""

    @property
    @abc.abstractmethod
    def name(self):
        """The name of handler."""

    @property
    @abc.abstractmethod
    def version(self):
        """The versions of the handler."""

    @property
    @abc.abstractmethod
    def provider(self):
        """Who created the handler."""

    @property
    @abc.abstractmethod
    def signature(self):
        """Signature of the handler."""

    @abc.abstractmethod
    def log(self, log_data):
        """Log an event via the handler."""

    @abc.abstractmethod
    def initialize(self, config_file):
        """Initialize the handler."""

    @abc.abstractmethod
    def finalize(self):
        """Finalize the handler."""
