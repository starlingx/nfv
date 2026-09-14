# Copyright (c) 2015-2024, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from wsme import types as wsme_types

from nfv_common.helpers import Constant
from nfv_common.helpers import Constants
from nfv_common.helpers import Singleton


class SwUpdateNames(Constants, metaclass=Singleton):
    """Software Update - Name Constants."""

    FW_UPDATE = Constant("fw-update")
    KUBE_ROOTCA_UPDATE = Constant("kube-rootca-update")
    KUBE_UPGRADE = Constant("kube-upgrade")
    SW_UPGRADE = Constant("sw-upgrade")
    SYSTEM_CONFIG_UPDATE = Constant("system-config-update")
    CURRENT_STRATEGY = Constant("current-strategy")


class SwUpdateApplyTypes(Constants, metaclass=Singleton):
    """Software Update - Apply Type Constants."""

    SERIAL = Constant("serial")
    PARALLEL = Constant("parallel")
    IGNORE = Constant("ignore")


class SwUpdateInstanceActionTypes(Constants, metaclass=Singleton):
    """Software Update - Instance Action Type Constants."""

    MIGRATE = Constant("migrate")
    STOP_START = Constant("stop-start")


class SwUpdateActions(Constants, metaclass=Singleton):
    """Software Update - Action Constants."""

    APPLY_ALL = Constant("apply-all")
    APPLY_STAGE = Constant("apply-stage")
    ABORT = Constant("abort")
    ABORT_STAGE = Constant("abort-stage")


class SwUpdateAlarmRestrictionTypes(Constants, metaclass=Singleton):
    """Software Update - Alarm Restriction Type Constants."""

    STRICT = Constant("strict")
    RELAXED = Constant("relaxed")
    PERMISSIVE = Constant("permissive")


# Constant Instantiation
SW_UPDATE_NAME = SwUpdateNames()
SW_UPDATE_APPLY_TYPE = SwUpdateApplyTypes()
SW_UPDATE_INSTANCE_ACTION = SwUpdateInstanceActionTypes()
SW_UPDATE_ACTION = SwUpdateActions()
SW_UPDATE_ALARM_RESTRICTION_TYPES = SwUpdateAlarmRestrictionTypes()


# WSME Types
SwUpdateNames = wsme_types.Enum(
    str,
    SW_UPDATE_NAME.FW_UPDATE,
    SW_UPDATE_NAME.KUBE_ROOTCA_UPDATE,
    SW_UPDATE_NAME.KUBE_UPGRADE,
    SW_UPDATE_NAME.SW_UPGRADE,
    SW_UPDATE_NAME.SYSTEM_CONFIG_UPDATE,
    SW_UPDATE_NAME.CURRENT_STRATEGY,
)
SwUpdateApplyTypes = wsme_types.Enum(
    str,
    SW_UPDATE_APPLY_TYPE.SERIAL,
    SW_UPDATE_APPLY_TYPE.PARALLEL,
    SW_UPDATE_APPLY_TYPE.IGNORE,
)
SwUpdateActions = wsme_types.Enum(
    str,
    SW_UPDATE_ACTION.APPLY_ALL,
    SW_UPDATE_ACTION.APPLY_STAGE,
    SW_UPDATE_ACTION.ABORT,
    SW_UPDATE_ACTION.ABORT_STAGE,
)
SwUpdateInstanceActionTypes = wsme_types.Enum(
    str, SW_UPDATE_INSTANCE_ACTION.MIGRATE, SW_UPDATE_INSTANCE_ACTION.STOP_START
)
SwUpdateAlarmRestrictionTypes = wsme_types.Enum(
    str,
    SW_UPDATE_ALARM_RESTRICTION_TYPES.STRICT,
    SW_UPDATE_ALARM_RESTRICTION_TYPES.RELAXED,
    SW_UPDATE_ALARM_RESTRICTION_TYPES.PERMISSIVE,
)


class FlexibleListType(wsme_types.UserType):
    """A WSME user type that accepts both a list of strings and a single

    string, normalizing the latter to a single-element list.

    This provides backwards compatibility for API callers that send a
    scalar string (e.g., dcmanager from older releases) when the API
    now expects a list.

    The basetype is set to str so that WSME's JSON fromjson dispatcher
    passes the raw JSON value through without type-checking. The
    frombasetype method then normalizes it to a list.
    """

    basetype = str
    name = "list(str)"

    def frombasetype(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            return [value]
        raise ValueError(
            "Expected a string or list of strings, got: %s" % type(value).__name__
        )

    def tobasetype(self, value):
        if value is None:
            return []
        return value

    def validate(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(
                "Expected a list of strings, got: %s" % type(value).__name__
            )
        for item in value:
            if not isinstance(item, str):
                raise ValueError("Expected string items, got: %s" % type(item).__name__)
        return value


FlexibleList = FlexibleListType()
