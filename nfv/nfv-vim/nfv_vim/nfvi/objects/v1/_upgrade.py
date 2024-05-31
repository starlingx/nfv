#
# Copyright (c) 2016-2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from enum import Enum

from nfv_vim.nfvi.objects.v1._object import ObjectData


# Enums from https://opendev.org/starlingx/update/src/branch/master/software/software/states.py
class RELEASE_STATES(Enum):
    AVAILABLE = 'available'
    UNAVAILABLE = 'unavailable'
    DEPLOYING = 'deploying'
    DEPLOYED = 'deployed'
    REMOVING = 'removing'
    COMMITTED = 'committed'


class DEPLOY_STATES(Enum):
    START = 'start'
    START_DONE = 'start-done'
    START_FAILED = 'start-failed'

    HOST = 'host'
    HOST_DONE = 'host-done'
    HOST_FAILED = 'host-failed'

    ACTIVATE = 'activate'
    ACTIVATE_DONE = 'activate-done'
    ACTIVATE_FAILED = 'activate-failed'

    ABORT = 'abort'
    ABORT_DONE = 'abort-done'


class DEPLOY_HOST_STATES(Enum):
    DEPLOYED = 'deployed'
    DEPLOYING = 'deploying'
    FAILED = 'failed'
    PENDING = 'pending'


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
    def is_available(self):
        return self.release_state == RELEASE_STATES.AVAILABLE.value

    @property
    def is_deployed(self):
        return self.release_state == RELEASE_STATES.DEPLOYED.value

    @property
    def is_committed(self):
        return self.release_state == RELEASE_STATES.COMMITTED.value

    @property
    def is_starting(self):
        return self.deploy_state == DEPLOY_STATES.START.value

    @property
    def is_start_done(self):
        return self.deploy_state == DEPLOY_STATES.START_DONE.value

    @property
    def is_start_failed(self):
        return self.deploy_state == DEPLOY_STATES.START_FAILED.value

    @property
    def is_deploying_hosts(self):
        return self.deploy_state == DEPLOY_STATES.HOST.value

    @property
    def is_deploy_hosts_done(self):
        return self.deploy_state == DEPLOY_STATES.HOST_DONE.value

    @property
    def is_deploy_hosts_failed(self):
        return self.deploy_state == DEPLOY_STATES.HOST_FAILED.value

    @property
    def is_activating(self):
        return self.deploy_state == DEPLOY_STATES.ACTIVATE.value

    @property
    def is_activate_done(self):
        return self.deploy_state == DEPLOY_STATES.ACTIVATE_DONE.value

    @property
    def is_activate_failed(self):
        return self.deploy_state == DEPLOY_STATES.ACTIVATE_FAILED.value
