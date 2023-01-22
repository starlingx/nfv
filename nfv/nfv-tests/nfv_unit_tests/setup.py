#
# Copyright (c) 2015-2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from setuptools import setup

setup(
    name='nfv_unit_tests',
    description='NFV Unit Tests',
    version='1.0.0',
    license='Apache-2.0',
    platforms=['any'],
    provides=['nfv_unit_tests'],
    packages=['nfv_unit_tests.tests'],
    package_dir={'nfv_unit_tests.tests': 'tests'}
)
