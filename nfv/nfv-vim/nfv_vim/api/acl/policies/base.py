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

ADMIN_OR_CONFIGURATOR = 'admin_or_configurator'
READER_OR_OPERATOR_OR_CONFIGURATOR = 'reader_or_operator_or_configurator'


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
        description='Default. Admin in system projects, similar to the old behavior',
    ),
    RuleDefault(
        name=ADMIN_OR_CONFIGURATOR,
        check_str='(role:admin or role:configurator) and ' +
                  '(project_name:admin or project_name:services)',
        description='admin or configurator in system projects',
    ),
    RuleDefault(
        name=READER_OR_OPERATOR_OR_CONFIGURATOR,
        check_str='(role:reader or role:operator or role:configurator) and ' +
                  '(project_name:admin or project_name:services)',
        description='reader,operator,configurator in system projects',
    )
]


def list_rules():
    return base_rules
