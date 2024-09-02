#
# Copyright (c) 2016-2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import json

from nfv_vim import objects

from nfv_vim.database import model

from nfv_vim.database._database import database_get


def database_sw_update_add(sw_update_obj):
    """
    Add a software update object to the database
    """
    db = database_get()
    session = db.session()
    query = session.query(model.SoftwareUpdate)
    sw_update = query.filter(model.SoftwareUpdate.uuid ==
                             sw_update_obj.uuid).first()
    if not sw_update:
        sw_update = model.SoftwareUpdate()
        sw_update.uuid = sw_update_obj.uuid
        sw_update.sw_update_type = sw_update_obj.sw_update_type
        if sw_update_obj.strategy is None:
            sw_update.strategy_data = json.dumps(dict())
        else:
            sw_update.strategy_data = json.dumps(sw_update_obj.strategy.as_dict())
        session.add(sw_update)
    else:
        if sw_update_obj.strategy is None:
            sw_update.strategy_data = json.dumps(dict())
        else:
            sw_update.strategy_data = json.dumps(sw_update_obj.strategy.as_dict())
    db.commit()


def database_sw_update_delete(sw_update_uuid):
    """
    Delete a software update object from the database
    """
    db = database_get()
    session = db.session()
    query = session.query(model.SoftwareUpdate)
    query.filter(model.SoftwareUpdate.uuid == sw_update_uuid).delete()
    session.commit()


def database_sw_update_get_list():
    """
    Fetch all the software update objects from the database
    """
    db = database_get()
    session = db.session()
    query = session.query(model.SoftwareUpdate)

    sw_update_objs = list()
    for sw_update in query.all():
        strategy_data = json.loads(sw_update.strategy_data)
        if objects.SW_UPDATE_TYPE.SW_PATCH == sw_update.sw_update_type:
            sw_patch_obj = objects.SwPatch(sw_update.uuid, strategy_data)
            sw_update_objs.append(sw_patch_obj)
        elif objects.SW_UPDATE_TYPE.SW_UPGRADE == sw_update.sw_update_type:
            sw_upgrade_obj = objects.SwUpgrade(sw_update.uuid, strategy_data)
            sw_update_objs.append(sw_upgrade_obj)
        elif objects.SW_UPDATE_TYPE.FW_UPDATE == sw_update.sw_update_type:
            fw_update_obj = objects.FwUpdate(sw_update.uuid, strategy_data)
            sw_update_objs.append(fw_update_obj)
        elif objects.SW_UPDATE_TYPE.KUBE_ROOTCA_UPDATE == sw_update.sw_update_type:
            kube_rootca_obj = objects.KubeRootcaUpdate(sw_update.uuid,
                                                        strategy_data)
            sw_update_objs.append(kube_rootca_obj)
        elif objects.SW_UPDATE_TYPE.KUBE_UPGRADE == sw_update.sw_update_type:
            kube_upgrade_obj = objects.KubeUpgrade(sw_update.uuid,
                                                   strategy_data)
            sw_update_objs.append(kube_upgrade_obj)
        elif objects.SW_UPDATE_TYPE.SYSTEM_CONFIG_UPDATE == sw_update.sw_update_type:
            system_config_update_obj = objects.SystemConfigUpdate(sw_update.uuid,
                                                                  strategy_data)
            sw_update_objs.append(system_config_update_obj)
    return sw_update_objs


def database_sw_update_exists():
    """
    Check if any software update strategy exists in the database
    """
    db = database_get()
    session = db.session()
    query = session.query(model.SoftwareUpdate)

    # Return True if any record exists, False otherwise
    return session.query(query.exists()).scalar()
