#
# Copyright (c) 2015-2016, 2025-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

from nfv_common.helpers import Constant
from nfv_common.helpers import Constants
from nfv_common.helpers import Singleton


class StrategyApplyTypes(Constants, metaclass=Singleton):
    """
    Strategy - Apply Type Constants
    """
    SERIAL = Constant('serial')
    PARALLEL = Constant('parallel')
    IGNORE = Constant('ignore')


class StrategyAlarmRestrictionTypes(Constants, metaclass=Singleton):
    """
    Strategy - Alarm Restriction Type Constants
    """
    STRICT = Constant('strict')
    RELAXED = Constant('relaxed')
    PERMISSIVE = Constant('permissive')


class StrategyPhases(Constants, metaclass=Singleton):
    """
    Strategy - Phase Constants
    """
    INITIAL = Constant('initial')
    BUILD = Constant('build')
    APPLY = Constant('apply')
    ABORT = Constant('abort')


class StrategyStates(Constants, metaclass=Singleton):
    """
    Strategy - State Constants
    """
    INITIAL = Constant('initial')
    BUILDING = Constant('building')
    BUILD_FAILED = Constant('build-failed')
    BUILD_TIMEOUT = Constant('build-timeout')
    READY_TO_APPLY = Constant('ready-to-apply')
    APPLYING = Constant('applying')
    APPLY_FAILED = Constant('apply-failed')
    APPLY_TIMEOUT = Constant('apply-timeout')
    APPLIED = Constant('applied')
    ABORTING = Constant('aborting')
    ABORT_FAILED = Constant('abort-failed')
    ABORT_TIMEOUT = Constant('abort-timeout')
    ABORTED = Constant('aborted')


# Constant Instantiation
STRATEGY_APPLY_TYPE = StrategyApplyTypes()
STRATEGY_ALARM_RESTRICTION_TYPES = StrategyAlarmRestrictionTypes()
STRATEGY_PHASE = StrategyPhases()
STRATEGY_STATE = StrategyStates()
