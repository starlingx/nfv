#
# Copyright (c) 2016-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_vim.nfvi.objects.v1._object import ObjectData

# USM states
USM_ABORTING = 'aborting'
USM_AVAILABLE = 'available'
USM_COMMITTED = 'committed'
USM_DEPLOYED = 'deployed'
USM_DEPLOYING_ACTIVATE = 'deploying-activate'
USM_DEPLOYING_COMPLETE = 'deploying-complete'
USM_DEPLOYING_HOST = 'deploying-host'
USM_DEPLOYING_START = 'deploying-start'
USM_REMOVING = 'removing'
USM_UNAVAILABLE = 'unavailable'
USM_UNKNOWN = 'n/a'
USM_REBOOT_REQUIRED = "Y"


class Upgrade(ObjectData):
    """
    NFVI Upgrade Object
    """
    def __init__(self, release, release_info, hosts_info):
        super(Upgrade, self).__init__('1.0.0')
        self.update(dict(release=release,
                         release_info=release_info,
                         hosts_info=hosts_info))

    @property
    def state(self):
        if self.release_info is None:
            return None

        return self.release_info["state"]

    @property
    def reboot_required(self):
        if self.release_info is None:
            return None

        return self.release_info["reboot_required"] == USM_REBOOT_REQUIRED

    @property
    def is_available(self):
        return self.state == USM_AVAILABLE

    @property
    def is_deployed(self):
        return self.state == USM_DEPLOYED

    @property
    def is_commited(self):
        return self.state == USM_COMMITTED

    @property
    def is_started(self):
        return self.state == USM_DEPLOYING_START

    @property
    def is_activated(self):
        return self.state == USM_DEPLOYING_ACTIVATE

    def is_host_deployed(self, hostname):
        """Return if hostname is deployed

        If is missing it is assumed not deployed.
        """

        if self.hosts_info is None:
            return False

        if hostname not in self.hosts_info:
            raise EnvironmentError(f"{hostname} does not exist on system")

        return self.hosts_info[hostname]["state"] == USM_DEPLOYED
