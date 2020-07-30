#
# Copyright (c) 2015-2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import six

from nfv_common.helpers import Constant
from nfv_common.helpers import Singleton


@six.add_metaclass(Singleton)
class EventNames(object):
    """
    Strategy - Event Name Constants
    """
    HOST_LOCK_FAILED = Constant('host-lock-failed')
    HOST_UNLOCK_FAILED = Constant('host-unlock-failed')
    HOST_REBOOT_FAILED = Constant('host-reboot-failed')
    HOST_UPGRADE_FAILED = Constant('host-upgrade-failed')
    HOST_FW_UPDATE_FAILED = Constant('host-fw-update-failed')
    HOST_FW_UPDATE_ABORT_FAILED = Constant('host-fw-update-abort-failed')
    HOST_SWACT_FAILED = Constant('host-swact-failed')
    HOST_STATE_CHANGED = Constant('host-state-changed')
    HOST_AUDIT = Constant('host-audit')
    INSTANCE_STATE_CHANGED = Constant('instance-state-chagned')
    INSTANCE_AUDIT = Constant('instance-audit')
    DISABLE_HOST_SERVICES_FAILED = Constant('disable-host-services-failed')
    ENABLE_HOST_SERVICES_FAILED = Constant('enable-host-services-failed')
    MIGRATE_INSTANCES_FAILED = Constant('migrate-instances-failed')


# Constants
STRATEGY_EVENT = EventNames()


@six.add_metaclass(Singleton)
class FirmwareUpdateLabels(object):
    """
    Firmware Update Labels
    """
    # Host image update pending key label : True / False
    DEVICE_IMAGE_NEEDS_FIRMWARE_UPDATE = Constant('needs_firmware_update')

    # Device Image Status
    DEVICE_IMAGE_UPDATE_NULL = Constant('')
    DEVICE_IMAGE_UPDATE_PENDING = Constant('pending')
    DEVICE_IMAGE_UPDATE_IN_PROGRESS = Constant('in-progress')
    DEVICE_IMAGE_UPDATE_COMPLETED = Constant('completed')
    DEVICE_IMAGE_UPDATE_FAILED = Constant('failed')
    DEVICE_IMAGE_UPDATE_IN_PROGRESS_ABORTED = Constant('in-progress-aborted')

FW_UPDATE_LABEL = FirmwareUpdateLabels()
