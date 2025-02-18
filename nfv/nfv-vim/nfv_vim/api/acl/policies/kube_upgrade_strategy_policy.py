# Copyright (c) 2022 Wind River Systems, Inc.
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

from nfv_vim.api.acl.policies import base

POLICY_ROOT = 'nfv_api:kube_upgrade_strategy:%s'


kube_upgrade_strategy_rules = [
    base.RuleDefault(
        name=POLICY_ROOT % 'add',
        check_str='rule:' + base.ADMIN_IN_SYSTEM_PROJECTS,
        description="Add a kube_upgrade_strategy",
    ),
    base.RuleDefault(
        name=POLICY_ROOT % 'delete',
        check_str='rule:' + base.ADMIN_IN_SYSTEM_PROJECTS,
        description="Delete a kube_upgrade_strategy",
    ),
    base.RuleDefault(
        name=POLICY_ROOT % 'get',
        check_str='rule:' + base.READER_OR_OPERATOR_IN_SYSTEM_PROJECTS,
        description="Get a kube_upgrade_strategy",
    )
]


def list_rules():
    return kube_upgrade_strategy_rules
