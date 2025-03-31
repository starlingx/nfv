#
# Copyright (c) 2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import json

from nfv_vim.database import model

from nfv_common import debug

DLOG = debug.debug_get_logger('nfv_vim.database')


def _migrate_hosts_v7_to_v8(session, hosts_v7, hosts_v8):
    """
    Replace software_load, target_load with sw_version
    """
    if 0 == len(hosts_v8):
        for host_v7 in hosts_v7:
            host_v8 = model.Host_v8()
            host_v8.data = host_v7.data
            nfvi_host_data = json.loads(host_v7.nfvi_host_data)
            nfvi_host_data['sw_version'] = None
            nfvi_host_data.pop('software_load', None)
            nfvi_host_data.pop('target_load', None)
            host_v8.nfvi_host_data = json.dumps(nfvi_host_data)
            session.add(host_v8)


def _migrate_hosts_v6_to_v7(session, hosts_v6, hosts_v7):
    """
    Migrate host_v6 table to host_v7 table
    """
    if 0 == len(hosts_v7):
        for host_v6 in hosts_v6:
            host_v7 = model.Host_v7()
            host_v7.data = host_v6.data
            nfvi_host_data = json.loads(host_v6.nfvi_host_data)
            nfvi_host_data['device_image_update'] = None
            host_v7.nfvi_host_data = json.dumps(nfvi_host_data)
            session.add(host_v7)


def migrate_tables(session, table_names):
    """
    Migrate database tables
    """
    if 'hosts_v6' in table_names and 'hosts_v7' in table_names:
        hosts_v6_query = session.query(model.Host_v6)
        hosts_v6 = hosts_v6_query.all()
        hosts_v7_query = session.query(model.Host_v7)
        hosts_v7 = hosts_v7_query.all()
        _migrate_hosts_v6_to_v7(session, hosts_v6, hosts_v7)
        hosts_v6_query.delete()
    if 'hosts_v7' in table_names and 'hosts_v8' in table_names:
        hosts_v7_query = session.query(model.Host_v7)
        hosts_v7 = hosts_v7_query.all()
        hosts_v8_query = session.query(model.Host_v8)
        hosts_v8 = hosts_v8_query.all()
        _migrate_hosts_v7_to_v8(session, hosts_v7, hosts_v8)
        hosts_v7_query.delete()
