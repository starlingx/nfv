#
# Copyright (c) 2015-2016,2025 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import subprocess

from nfv_vim.database._database import database_create
from nfv_vim.database._database import database_get


def database_dump_data(filename):
    """
    Dump database data to a file
    """
    database = database_get()
    database.dump_data(filename)


def database_load_data(filename):
    """
    Load database data from a file
    """
    database = database_get()
    database.load_data(filename)


def database_migrate_data():
    """
    Migrate database data
    """
    database = database_get()
    database.migrate_data()


def database_initialize(config):
    """
    Initialize the database package
    """
    database_create(config['database_dir'])


def database_finalize(config=None):
    """
    Finalize the database package
    """
    database = database_get()
    database.end_session()
    if config:
        subprocess.call(["sync", config['database_dir']])
