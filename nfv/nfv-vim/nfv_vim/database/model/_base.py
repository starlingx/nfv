#
# Copyright (c) 2015-2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AsDictMixin(object):

    @property
    def data(self):
        data = dict()
        for column in self.__table__.columns:
            data[column.name] = getattr(self, column.name)
        return data

    @data.setter
    def data(self, data):
        for column in list(data.keys()):
            setattr(self, column, data[column])


def get_Base_registry():
    try:
        # SQLAlchemy 1.4 got rid of _decl_class_registry
        # so we need to use the new way if it exists
        # otherwise fail over to the old attribute
        return Base.registry._class_registry
    except AttributeError:  # SQLAlchemy <1.4
        return Base._decl_class_registry


def lookup_class_by_table(table_name):
    for c in list(get_Base_registry().values()):
        if hasattr(c, '__table__'):
            if table_name == str(c.__table__):
                return c
    # TODO(abailey): add an explicit return None
