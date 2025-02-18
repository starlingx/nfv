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

ADMIN_IN_SYSTEM_PROJECTS = 'admin_in_system_projects'
READER_OR_OPERATOR_IN_SYSTEM_PROJECTS = 'reader_or_operator_in_system_projects'


class RuleDefault(object):
    """Class used to represent a policy rule.

    :param name: The name of the policy.
    :param check_str: The string that represents the policy.
    :param description: A brief description of the policy.
    """
    def __init__(self, name, check_str, description):
        self.name = name
        self.check_str = check_str
        self.description = description


base_rules = [
    RuleDefault(
        name='default',
        check_str='rule:admin_in_system_projects',
        description="Default. Admin in system projects, similar to the old behavior",
    ),
    RuleDefault(
        name=ADMIN_IN_SYSTEM_PROJECTS,
        check_str='role:admin and (project_name:admin or ' +
                  'project_name:services)',
        description="Generic rule for set-style requests",
    ),
    RuleDefault(
        name=READER_OR_OPERATOR_IN_SYSTEM_PROJECTS,
        check_str='(role:reader or role:operator) and (project_name:admin or ' +
                  'project_name:services)',
        description="Generic rule for get-style requests",
    )
]


def list_rules():
    return base_rules
