# Copyright (c) 2016-2024, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# TODO(rlima): this disables flake8 in the whole file as there is no
# way to suppress a specific warning.
# flake8: noqa
from nfv_client.sw_update._sw_update import ALARM_RESTRICTIONS_PERMISSIVE
from nfv_client.sw_update._sw_update import ALARM_RESTRICTIONS_RELAXED
from nfv_client.sw_update._sw_update import ALARM_RESTRICTIONS_STRICT
from nfv_client.sw_update._sw_update import APPLY_TYPE_IGNORE
from nfv_client.sw_update._sw_update import APPLY_TYPE_PARALLEL
from nfv_client.sw_update._sw_update import APPLY_TYPE_SERIAL
from nfv_client.sw_update._sw_update import CMD_NAME_FW_UPDATE
from nfv_client.sw_update._sw_update import CMD_NAME_KUBE_ROOTCA_UPDATE
from nfv_client.sw_update._sw_update import CMD_NAME_KUBE_UPGRADE
from nfv_client.sw_update._sw_update import CMD_NAME_SW_DEPLOY
from nfv_client.sw_update._sw_update import CMD_NAME_SYSTEM_CONFIG_UPDATE
from nfv_client.sw_update._sw_update import INSTANCE_ACTION_MIGRATE
from nfv_client.sw_update._sw_update import INSTANCE_ACTION_STOP_START
from nfv_client.sw_update._sw_update import STRATEGY_NAME_FW_UPDATE
from nfv_client.sw_update._sw_update import STRATEGY_NAME_KUBE_ROOTCA_UPDATE
from nfv_client.sw_update._sw_update import STRATEGY_NAME_KUBE_UPGRADE
from nfv_client.sw_update._sw_update import STRATEGY_NAME_SW_DEPLOY
from nfv_client.sw_update._sw_update import STRATEGY_NAME_SW_UPGRADE
from nfv_client.sw_update._sw_update import STRATEGY_NAME_SYSTEM_CONFIG_UPDATE
from nfv_client.sw_update._sw_update import abort_strategy
from nfv_client.sw_update._sw_update import apply_strategy
from nfv_client.sw_update._sw_update import create_strategy
from nfv_client.sw_update._sw_update import delete_strategy
from nfv_client.sw_update._sw_update import show_strategy
