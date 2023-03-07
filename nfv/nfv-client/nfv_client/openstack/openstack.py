#
# Copyright (c) 2016-2022 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import json
from six.moves import urllib

from nfv_client.openstack.objects import Token


class OpenStackServices(object):
    """
    OpenStack Services Constants
    """
    VIM = 'vim'


class OpenStackServiceTypes(object):
    """
    OpenStack Service Types Constants
    """
    NFV = 'nfv'


SERVICE = OpenStackServices()
SERVICE_TYPE = OpenStackServiceTypes()


def get_token(auth_uri, project_name, project_domain_name, username, password,
              user_domain_name):
    """
    Ask OpenStack for a token
    """
    try:
        # handle auth_uri re-direct (300)
        urllib.request.urlopen(auth_uri)
    except urllib.error.HTTPError as e:
        if e.code == 300:
            auth_uri = e.headers['location']
            if auth_uri.endswith('/'):
                auth_uri = auth_uri[:-1]

    try:
        url = auth_uri + "/auth/tokens"

        request_info = urllib.request.Request(url)
        request_info.add_header("Content-Type", "application/json")
        request_info.add_header("Accept", "application/json")

        payload = json.dumps(
            {"auth": {
                "identity": {
                    "methods": [
                        "password"
                    ],
                    "password": {
                        "user": {
                            "name": username,
                            "password": password,
                            "domain": {"name": user_domain_name}
                        }
                    }
                },
                "scope": {
                    "project": {
                        "name": project_name,
                        "domain": {"name": project_domain_name}
                    }}}})

        request_info.data = payload.encode()

        request = urllib.request.urlopen(request_info, timeout=30)
        # Identity API v3 returns token id in X-Subject-Token
        # response header.
        token_id = request.headers.get('X-Subject-Token')
        response = json.loads(request.read())
        request.close()
        return Token(response, token_id)

    except urllib.error.HTTPError as e:
        print(e)
        return None

    except urllib.error.URLError as e:
        print(e)
        return None
