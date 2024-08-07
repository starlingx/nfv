#!/bin/bash
#
# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2019 Intel Corporation
#

# devstack/plugin.sh
# Triggers specific functions to install and configure stx-nfv

echo_summary "stx-nfv devstack plugin.sh called: $1/$2"

# check for service enabled
if is_service_enabled nfv; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of service source
        echo_summary "Installing stx-nfv"
        install_nfv

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        echo_summary "Configuring stx-nfv"
        configure_nfv

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        echo_summary "Starting stx-nfv"
        start_nfv
    fi

    if [[ "$1" == "unstack" ]]; then
        echo_summary "Shutdown stx-nfv"
        stop_nfv
    fi

    if [[ "$1" == "clean" ]]; then
        echo_summary "Clean stx-nfv"
        cleanup_nfv
    fi
fi
