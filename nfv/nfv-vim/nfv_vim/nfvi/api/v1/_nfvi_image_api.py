#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import abc


class NFVIImageAPI(object, metaclass=abc.ABCMeta):
    """
    Abstract NFVI Image API Class Definition
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
    def get_images(self, future, paging, callback):
        """
        Get a list of images using the plugin
        """
        pass

    @abc.abstractmethod
    def create_image(
        self,
        future,
        image_name,
        image_description,
        image_attributes,
        image_data_url,
        callback,
    ):
        """
        Create an image using the plugin
        """
        pass

    @abc.abstractmethod
    def delete_image(self, future, image_uuid, callback):
        """
        Delete an image using the plugin
        """
        pass

    @abc.abstractmethod
    def update_image(
        self, future, image_uuid, image_description, image_attributes, callback
    ):
        """
        Update an image using the plugin
        """
        pass

    @abc.abstractmethod
    def get_image(self, future, image_uuid, callback):
        """
        Get an image using the plugin
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
