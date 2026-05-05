#
# Copyright (c) 2015-2016, 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
NFVI_OPENSTACK_LOG = "/var/log/nfvi-openstack.log"


def _log_write_log(error, msg, *args, **kwargs):
    """Low-Level log write."""

    def timestamp_str(timestamp_data):
        return timestamp_data.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def log_info(msg, *args, **kwargs):
    """Log at the info level."""

    _log_write_log(False, msg, *args, **kwargs)


def log_error(msg, *args, **kwargs):
    """Log at the error level."""

    _log_write_log(True, msg, *args, **kwargs)
