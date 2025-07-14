#
# Copyright (c) 2015-2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import String

from nfv_vim.database.model._base import AsDictMixin
from nfv_vim.database.model._base import Base


class Host_v8(AsDictMixin, Base):
    """
    Host Database Table Entry
    Note: Changes are only in nfvi_host_data to replace software_load and target_load with sw_version.
    """
    __tablename__ = 'hosts_v8'

    uuid = Column(String(64), nullable=False, primary_key=True)
    name = Column(String(64), nullable=False)
    personality = Column(String(64), nullable=False)
    state = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    upgrade_inprogress = Column(Boolean, nullable=False)
    recover_instances = Column(Boolean, nullable=False)
    uptime = Column(String(64), nullable=False)
    elapsed_time_in_state = Column(String(64), nullable=False)
    host_services_locked = Column(Boolean, nullable=False)
    nfvi_host_data = Column(String(2048), nullable=False)

    def __repr__(self):
        return "<Host(%r, %r, %r, %r, %r %r)>" % (self.uuid, self.name,
                                                  self.personality, self.state,
                                                  self.action, self.uptime)


class Host_v7(AsDictMixin, Base):
    """
    Host Database Table Entry
    Note: Changes are only in nfvi_host_data to add device_image_update string
    """
    __tablename__ = 'hosts_v7'

    uuid = Column(String(64), nullable=False, primary_key=True)
    name = Column(String(64), nullable=False)
    personality = Column(String(64), nullable=False)
    state = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    upgrade_inprogress = Column(Boolean, nullable=False)
    recover_instances = Column(Boolean, nullable=False)
    uptime = Column(String(64), nullable=False)
    elapsed_time_in_state = Column(String(64), nullable=False)
    host_services_locked = Column(Boolean, nullable=False)
    nfvi_host_data = Column(String(2048), nullable=False)

    def __repr__(self):
        return "<Host(%r, %r, %r, %r, %r %r)>" % (self.uuid, self.name,
                                                  self.personality, self.state,
                                                  self.action, self.uptime)


class Host_v6(AsDictMixin, Base):
    """
    Host Database Table Entry
    Note: Changes are only in nfvi_host_data.
    """
    __tablename__ = 'hosts_v6'

    uuid = Column(String(64), nullable=False, primary_key=True)
    name = Column(String(64), nullable=False)
    personality = Column(String(64), nullable=False)
    state = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    upgrade_inprogress = Column(Boolean, nullable=False)
    recover_instances = Column(Boolean, nullable=False)
    uptime = Column(String(64), nullable=False)
    elapsed_time_in_state = Column(String(64), nullable=False)
    host_services_locked = Column(Boolean, nullable=False)
    nfvi_host_data = Column(String(2048), nullable=False)

    def __repr__(self):
        return "<Host(%r, %r, %r, %r, %r %r)>" % (self.uuid, self.name,
                                                  self.personality, self.state,
                                                  self.action, self.uptime)
