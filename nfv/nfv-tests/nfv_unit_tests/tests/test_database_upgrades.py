#
# Copyright (c) 2016-2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import os
import shutil
import subprocess
import tempfile

from nfv_vim import database
from nfv_vim import tables

from nfv_unit_tests.tests import testcase


class TestNFVDatabaseUpgrade(testcase.NFVTestCase):

    def setUp(self):
        super(TestNFVDatabaseUpgrade, self).setUp()
        root_dir = os.environ['VIRTUAL_ENV']
        # create a directory to hold the DB, randomly named, under the tox env
        self.db_dir = tempfile.mkdtemp(dir=root_dir)

    def tearDown(self):
        super(TestNFVDatabaseUpgrade, self).tearDown()
        shutil.rmtree(self.db_dir)

    def test_nfv_vim_database_upgrade_from_19_12(self):
        """
        Test VIM database upgrades from stx 19_12
        """
        root_dir = os.environ['VIRTUAL_ENV']
        # stage some old data
        devnull = open(os.devnull, 'w')
        try:
            vim_cmd = ("nfv-vim-manage db-load-data -d %s "
                       "-f %s/nfv_vim_db_stx_19.12" % (self.db_dir, root_dir))

            subprocess.check_call([vim_cmd], shell=True, stderr=devnull)
        except subprocess.CalledProcessError:
            raise

        # migrate the old data
        config = dict()
        config['database_dir'] = self.db_dir
        database.database_initialize(config)
        database.database_migrate_data()
        tables.tables_initialize()
