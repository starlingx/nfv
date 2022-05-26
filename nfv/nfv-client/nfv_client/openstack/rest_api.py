#
# Copyright (c) 2016-2021 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import json
from six.moves import http_client as httplib
from six.moves import urllib


def request(token_id, method, api_cmd, api_cmd_headers=None,
            api_cmd_payload=None, timeout_in_secs=40):
    """
    Make a rest-api request
    Note: Using a default timeout of 40 seconds. The VIM's internal handling
    of these requests times out after 30 seconds - we want that to happen
    first (if possible).
    """
    headers_per_hop = ['connection', 'keep-alive', 'proxy-authenticate',
                       'proxy-authorization', 'te', 'trailers',
                       'transfer-encoding', 'upgrade']

    try:
        request_info = urllib.request.Request(api_cmd)
        request_info.get_method = lambda: method
        if token_id is not None:
            request_info.add_header("X-Auth-Token", token_id)
        request_info.add_header("Accept", "application/json")

        if api_cmd_headers is not None:
            for header_type, header_value in list(api_cmd_headers.items()):
                request_info.add_header(header_type, header_value)

        if api_cmd_payload is not None:
            request_info.data = api_cmd_payload.encode()

        url_request = urllib.request.urlopen(request_info,
                                             timeout=timeout_in_secs)

        headers = list()  # list of tuples
        for key, value in url_request.info().items():
            if key not in headers_per_hop:
                cap_key = '-'.join((ck.capitalize() for ck in key.split('-')))
                headers.append((cap_key, value))

        response_raw = url_request.read()

        # python2 the reponse may be an empty string
        # python3 the response may be an empty byte string
        if response_raw == "" or response_raw == b"":
            response = dict()
        else:
            response = json.loads(response_raw)

        url_request.close()

        return response

    except urllib.error.HTTPError as e:
        headers = list()
        response_raw = dict()

        if e.fp is not None:
            headers = list()  # list of tuples
            for key, value in e.fp.info().items():
                if key not in headers_per_hop:
                    cap_key = '-'.join((ck.capitalize()
                                        for ck in key.split('-')))
                    headers.append((cap_key, value))

            response_raw = e.fp.read()

        if httplib.FOUND == e.code:
            return response_raw

        elif httplib.NOT_FOUND == e.code:
            return None

        elif httplib.CONFLICT == e.code:
            raise Exception("Operation failed: conflict detected")

        elif httplib.FORBIDDEN == e.code:
            raise Exception("Authorization failed")

        # Attempt to get the reason for the http error from the response
        reason = ''
        for header, value in headers:
            if 'Content-Type' == header:
                if 'application/json' == value.split(';')[0]:
                    try:
                        response = json.loads(response_raw)
                        message = response.get('faultstring', None)
                        if message is not None:
                            reason = str(message.rstrip('.'))
                            print("Operation failed: %s" % reason)
                            break

                    except ValueError:
                        pass

        print("Rest-API status=%s, %s, %s, headers=%s, payload=%s, response=%s"
              % (e.code, method, api_cmd, api_cmd_headers, api_cmd_payload,
                 response_raw))
        raise

    except urllib.error.URLError as e:
        print("Rest-API status=ERR, %s, %s, headers=%s, payload=%s"
              % (method, api_cmd, api_cmd_headers, api_cmd_payload,))
        raise
