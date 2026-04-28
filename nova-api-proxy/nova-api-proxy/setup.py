# Copyright (c) 2015, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from setuptools import find_packages
from setuptools import setup

setup(
    name="api_proxy",
    description="Nova REST API Proxy",
    version="1.0.0",
    license="Apache-2.0",
    platforms=["any"],
    provides="nova_api_proxy",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "nova-api-proxy = nova_api_proxy.api_proxy:main",
        ],
    },
)
