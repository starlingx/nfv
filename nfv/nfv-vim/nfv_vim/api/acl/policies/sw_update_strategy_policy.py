# Copyright (c) 2022,2025 Wind River Systems, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0
#
# "SwUpdateStrategyActionAPI" need to handle the post "controller api method"
#  common to all 5 apply and aborts "sw-manager commands"
#
# FwUpdateStrategyAPI
# KubeRootcaUpdateStrategyAPI
# KubeUpgradeStrategyAPI
# SwPatchStrategyAPI
# SwUpgradeStrategyAPI
#
# those 5 classes needs to handle get_all, post, delete "controller api methods"
# for show, create, delete "sw-manager commands" respectively
#
# There are 5 sw-manager commands and 6 controller api classes.
# We need 6 policy classes because the 5 controller api classes handle 3/5
# of their commands and inherit from this 6th class to handle the other 2.
# This policy class is for "SwUpdateStrategyActionAPI"

from nfv_vim.api.acl.policies import base

POLICY_ROOT = 'nfv_api:sw_update_strategy:%s'


sw_update_strategy_rules = [
    # this rule handles the 'apply' and 'abort' commands, both of which
    # comes into the controller as 'post' requests.
    base.RuleDefault(
        name=POLICY_ROOT % 'post',
        check_str='rule:' + base.ADMIN_OR_CONFIGURATOR,
        description="Apply sw_update_strategy",
    )
]


def list_rules():
    return sw_update_strategy_rules
