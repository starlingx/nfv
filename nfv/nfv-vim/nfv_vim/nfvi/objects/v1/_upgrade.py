#
# Copyright (c) 2016-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_vim.nfvi.objects.v1._object import ObjectData
import software.states as usm_states
from tsconfig.tsconfig import SW_VERSION


def is_major_release(to_release, from_release):
    """Determine if this is a major release software deployment

    Major release if major or minor version changed:
    eg. 10.11.12 -> (11.1.1 or 10.12.1)
    """

    return to_release.split(".")[:2] != from_release.split(".")[:2]


class Upgrade(ObjectData):
    """
    NFVI Upgrade Object
    """
    def __init__(self, release, release_info, deploy_info, hosts_info):
        super(Upgrade, self).__init__('1.0.0')
        self.update(dict(release=release,
                         release_info=release_info,
                         deploy_info=deploy_info,
                         hosts_info=hosts_info))

    @property
    def release_state(self):
        if not self.release_info:
            return None

        return self.release_info["state"]

    @property
    def deploy_state(self):
        if not self.deploy_info:
            return None

        return self.deploy_info["state"]

    @property
    def reboot_required(self):
        if not self.release_info:
            return None

        return self.release_info["reboot_required"]

    @property
    def sw_version(self):
        if not self.release_info:
            return None

        return self.release_info["sw_version"]

    @property
    def from_release(self):
        if not self.deploy_info:
            return None

        return self.deploy_info["from_release"]

    @property
    def to_release(self):
        if not self.deploy_info:
            return None

        return self.deploy_info["to_release"]

    @property
    def major_release(self):
        if self.deploy_info:
            return is_major_release(self.from_release, self.to_release)
        elif self.release_info:
            # On DX systems, SW_VERSION will not be accurate if only one host has be deployed.
            # Therefore, it should only be used when a deployment is not in progress.
            return is_major_release(SW_VERSION, self.sw_version)

    @property
    def is_available(self):
        return self.release_state == usm_states.AVAILABLE

    @property
    def is_unavailable(self):
        return self.release_state == usm_states.UNAVAILABLE

    @property
    def is_deploying(self):
        return self.release_state == usm_states.DEPLOYING

    @property
    def is_deployed(self):
        return self.release_state == usm_states.DEPLOYED

    @property
    def is_committed(self):
        return self.release_state == usm_states.COMMITTED

    @property
    def is_starting(self):
        return self.deploy_state == usm_states.DEPLOY_STATES.START.value

    @property
    def is_start_done(self):
        return self.deploy_state == usm_states.DEPLOY_STATES.START_DONE.value

    @property
    def is_start_failed(self):
        return self.deploy_state == usm_states.DEPLOY_STATES.START_FAILED.value

    @property
    def is_deploying_hosts(self):
        return self.deploy_state == usm_states.DEPLOY_STATES.HOST.value

    @property
    def is_deploying_hosts_done(self):
        return self.deploy_state == usm_states.DEPLOY_STATES.HOST_DONE.value

    @property
    def is_deploying_hosts_failed(self):
        return self.deploy_state == usm_states.DEPLOY_STATES.HOST_FAILED.value

    @property
    def is_activating(self):
        return self.deploy_state == usm_states.DEPLOY_STATES.ACTIVATE.value

    @property
    def is_activate_done(self):
        return self.deploy_state == usm_states.DEPLOY_STATES.ACTIVATE_DONE.value

    @property
    def is_activate_failed(self):
        return self.deploy_state == usm_states.DEPLOY_STATES.ACTIVATE_FAILED.value

    @property
    def is_deploy_completed(self):
        return self.deploy_state == usm_states.DEPLOY_STATES.COMPLETED.value

    def is_host_deployed(self, hostname):
        if not self.hosts_info:
            return None

        for v in self.hosts_info:
            if v["hostname"] == hostname:
                return v["host_state"] == usm_states.DEPLOY_HOST_STATES.DEPLOYED.value
