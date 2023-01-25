#
# Copyright (c) 2015-2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from setuptools import setup

setup(
    name='nfv_scenario_tests',
    description='NFV Scenario Tests',
    version='1.0.0',
    license='Apache-2.0',
    platforms=['any'],
    provides=['nfv_scenario_tests'],
    data_files=['./config.ini'],
    packages=['nfv_scenario_tests.tests'],
    package_dir={'nfv_scenario_tests.tests': 'tests'},
    scripts=['main.py']
)
