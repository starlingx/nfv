#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_common.helpers import Constant
from nfv_common.helpers import Constants
from nfv_common.helpers import Singleton
from nfv_vim.nfvi.objects.v1._object import ObjectData


class AlarmSeverity(Constants, metaclass=Singleton):
    """Alarm Severity Constants."""

    NONE = Constant("")
    MINOR = Constant("minor")
    MAJOR = Constant("major")
    CRITICAL = Constant("critical")


# Alarm Constant Instantiation
ALARM_SEVERITY = AlarmSeverity()


class Alarm(ObjectData):
    """NFVI Alarm Object."""

    def __init__(
        self,
        alarm_uuid,
        alarm_id,
        entity_instance_id,
        severity,
        reason_text,
        timestamp,
        mgmt_affecting,
    ):
        super().__init__("1.0.0")
        self.update(
            {
                "alarm_uuid": alarm_uuid,
                "alarm_id": alarm_id,
                "entity_instance_id": entity_instance_id,
                "severity": severity,
                "reason_text": reason_text,
                "timestamp": timestamp,
                "mgmt_affecting": mgmt_affecting,
            }
        )
