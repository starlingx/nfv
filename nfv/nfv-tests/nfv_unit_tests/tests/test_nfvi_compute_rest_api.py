#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import http.client as httplib
import json
import sys
from unittest import mock

from nfv_common import timers
from nfv_unit_tests.tests import testcase

sys.modules["fm_core"] = mock.Mock()

# pylint: disable-next=C0413
from nfv_plugins.nfvi_plugins.nfvi_compute_api import (  # noqa: H306,E402
    NFVIComputeAPI,
)

# pylint: disable-next=C0413
from nfv_plugins.nfvi_plugins.openstack.rest_api import (  # noqa: H306,E402
    RestAPIRequestDispatcher,
)

INSTANCE_UUID = "deadbeef-dead-beef-dead-beefdeadbeef"
TENANT_UUID = "11111111111111111111111111111111"
ACTION_PATH = "/v2.1/%s/servers/%s/action" % (TENANT_UUID, INSTANCE_UUID)

# The status line is emitted as HTTP/1.0 because RestAPIServer assigns the
# handler's 'protocol' attribute while http.server reads 'protocol_version'.
# That pre-existing mismatch is out of scope here, so the tests assert the
# version that is actually produced.
HTTP_VERSION = "HTTP/1.0"


class FakeSocketFile:
    """A wfile/rfile stand-in that retains everything written to it.

    io.BytesIO discards its buffer on close, and the delayed-response path
    closes wfile, so the bytes on the wire have to be recorded separately.
    """

    def __init__(self, data=b"", raise_on_write=False):
        self.data = data
        self.written = b""
        self.closed = False
        self.raise_on_write = raise_on_write

    def read(self, amount=None):
        if amount is None:
            amount = len(self.data)
        result = self.data[:amount]
        self.data = self.data[amount:]
        return result

    def write(self, data):
        if self.raise_on_write:
            raise BrokenPipeError("connection reset by peer")
        self.written += data
        return len(data)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        pass

    def close(self):
        self.closed = True


def make_dispatcher(path=ACTION_PATH, body=b""):
    """Build a dispatcher without running the socket-bound lifecycle.

    BaseHTTPRequestHandler.__init__ reads and dispatches a request as a side
    effect of construction, so the object is built directly and given only
    the attributes the response path touches.
    """
    dispatcher = object.__new__(RestAPIRequestDispatcher)
    dispatcher._is_shutdown = False
    dispatcher._response_delayed = False
    dispatcher._headers_ended = False
    dispatcher.path = path
    dispatcher.command = "POST"
    dispatcher.request_version = "HTTP/1.1"
    dispatcher.requestline = "POST %s HTTP/1.1" % path
    dispatcher.client_address = ("127.0.0.1", 45678)
    dispatcher.headers = {"content-length": str(len(body))}
    dispatcher.rfile = FakeSocketFile(body)
    dispatcher.wfile = FakeSocketFile()
    dispatcher.request = mock.Mock()
    return dispatcher


class TestNFVIComputeRestAPI(testcase.NFVTestCase):
    """Verify that the compute rest-api error paths put bytes on the wire."""

    def setUp(self):
        super().setUp()
        # send_response logs the request line to stderr via log_message.
        patcher = mock.patch.object(RestAPIRequestDispatcher, "log_request")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.plugin_api = NFVIComputeAPI()

    @staticmethod
    def status_line(http_status_code):
        """Build the status line the dispatcher is expected to emit."""

        return (
            "%s %d %s\r\n"
            % (HTTP_VERSION, http_status_code, httplib.responses[http_status_code])
        ).encode()

    def assert_single_header_terminator(self, dispatcher):
        """Assert the header block was terminated exactly once."""

        self.assertEqual(1, dispatcher.wfile.written.count(b"\r\n\r\n"))

    def assert_json_error_body(self, dispatcher, fault_name, http_status_code, message):
        """Assert a nova compatible JSON error body was written."""

        header_block, _, http_body = dispatcher.wfile.written.partition(b"\r\n\r\n")
        self.assertIn(b"Content-Type: application/json", header_block)
        self.assertIn(
            ("Content-Length: %d" % len(http_body)).encode(),
            header_block,
        )
        self.assertEqual(
            {fault_name: {"code": http_status_code, "message": message}},
            json.loads(http_body),
        )

    # -----------------------------------------------------------------------
    # Non-delayed error paths.
    # -----------------------------------------------------------------------

    def test_instance_action_not_found_writes_response(self):
        """A 404 for an unknown instance reaches the wire with a json body."""

        self.plugin_api.register_instance_action_callback(
            lambda instance_uuid, action_data: False
        )
        dispatcher = make_dispatcher(body=b'{"pause": {}}')

        self.plugin_api.instance_action_rest_api_post_handler(dispatcher)

        err_msg = "Instance %s could not be found." % INSTANCE_UUID
        self.assertTrue(
            dispatcher.wfile.written.startswith(self.status_line(httplib.NOT_FOUND))
        )
        self.assert_single_header_terminator(dispatcher)
        self.assert_json_error_body(
            dispatcher, "itemNotFound", httplib.NOT_FOUND, err_msg
        )
        # The bookkeeping is released and the socket teardown is left to
        # finish(), which the caller of the handler has not reached yet.
        self.assertEqual({}, self.plugin_api._requests)
        self.assertEqual(0, len(self.plugin_api._request_times))
        self.assertFalse(dispatcher.wfile.closed)

    def test_instance_action_no_action_writes_response(self):
        """A body carrying no action produces a 400 on the wire."""

        dispatcher = make_dispatcher(body=b"{}")

        self.plugin_api.instance_action_rest_api_post_handler(dispatcher)

        err_msg = "No server action specified"
        self.assertTrue(
            dispatcher.wfile.written.startswith(self.status_line(httplib.BAD_REQUEST))
        )
        self.assert_single_header_terminator(dispatcher)
        self.assert_json_error_body(
            dispatcher, "badRequest", httplib.BAD_REQUEST, err_msg
        )

    def test_instance_action_empty_body_writes_response(self):
        """An empty request body produces a bodyless 204 on the wire."""

        dispatcher = make_dispatcher(body=b"")

        self.plugin_api.instance_action_rest_api_post_handler(dispatcher)

        self.assertTrue(
            dispatcher.wfile.written.startswith(self.status_line(httplib.NO_CONTENT))
        )
        self.assert_single_header_terminator(dispatcher)
        # A 204 must not carry a message body.
        self.assertTrue(dispatcher.wfile.written.endswith(b"\r\n\r\n"))
        self.assertNotIn(b"Content-Type", dispatcher.wfile.written)

    def test_instance_action_invalid_url_writes_response(self):
        """The invalid-url early return produces a 400 on the wire."""

        dispatcher = make_dispatcher(
            path="/v2.1/%s/servers/%s" % (TENANT_UUID, INSTANCE_UUID),
            body=b'{"pause": {}}',
        )

        self.plugin_api.instance_action_rest_api_post_handler(dispatcher)

        err_msg = "Invalid url, expecting a server action request"
        self.assertTrue(
            dispatcher.wfile.written.startswith(self.status_line(httplib.BAD_REQUEST))
        )
        self.assert_single_header_terminator(dispatcher)
        self.assert_json_error_body(
            dispatcher, "badRequest", httplib.BAD_REQUEST, err_msg
        )
        # The early return happens before any request bookkeeping.
        self.assertEqual({}, self.plugin_api._requests)

    def test_instance_action_client_disconnect_is_not_fatal(self):
        """A client that disconnects mid-response does not raise."""

        self.plugin_api.register_instance_action_callback(
            lambda instance_uuid, action_data: False
        )
        dispatcher = make_dispatcher(body=b'{"pause": {}}')
        dispatcher.wfile = FakeSocketFile(raise_on_write=True)

        # The write failure is logged and swallowed rather than escaping into
        # http.server, which would log a traceback for every dropped client.
        self.plugin_api.instance_action_rest_api_post_handler(dispatcher)

        self.assertEqual(b"", dispatcher.wfile.written)
        # The bookkeeping is still released, so the request does not leak.
        self.assertEqual({}, self.plugin_api._requests)
        self.assertEqual(0, len(self.plugin_api._request_times))

    # -----------------------------------------------------------------------
    # Delayed-response paths. These cannot be driven from a live system
    # unless an instance is known to the vim, so they are only covered here.
    # -----------------------------------------------------------------------

    def _register_delayed_request(self, request_uuid, age_in_ms=0):
        """Register a request that is awaiting a delayed response."""

        dispatcher = make_dispatcher(body=b'{"pause": {}}')
        dispatcher.response_delayed()
        self.plugin_api._requests[request_uuid] = dispatcher
        self.plugin_api._request_times.append(
            (request_uuid, timers.get_monotonic_timestamp_in_ms() - age_in_ms)
        )
        return dispatcher

    def test_max_concurrent_requests_writes_response(self):
        """The max-concurrent 503 reaches the wire and releases the socket."""

        dispatcher = self._register_delayed_request("request-503")
        self.plugin_api._max_concurrent_action_requests = 0

        self.plugin_api._ageout_action_requests()

        self.assertTrue(
            dispatcher.wfile.written.startswith(
                self.status_line(httplib.SERVICE_UNAVAILABLE)
            )
        )
        self.assert_single_header_terminator(dispatcher)
        self.assertEqual({}, self.plugin_api._requests)
        # On the delayed path finish() has already returned without cleaning
        # up, so done() has to release the socket itself.
        self.assertTrue(dispatcher.wfile.closed)
        self.assertTrue(dispatcher._is_shutdown)

    def test_ageout_auto_accept_writes_response(self):
        """The ageout 202 reaches the wire and releases the socket."""

        wait_in_ms = self.plugin_api._max_action_request_wait_in_secs * 1000
        dispatcher = self._register_delayed_request(
            "request-202", age_in_ms=wait_in_ms + 1000
        )

        self.plugin_api._ageout_action_requests()

        self.assertTrue(
            dispatcher.wfile.written.startswith(self.status_line(httplib.ACCEPTED))
        )
        self.assert_single_header_terminator(dispatcher)
        self.assertEqual({}, self.plugin_api._requests)
        self.assertTrue(dispatcher.wfile.closed)
        self.assertTrue(dispatcher._is_shutdown)

    def test_action_request_complete_relays_nova_response(self):
        """A relayed nova response is not corrupted by the added end_headers."""

        dispatcher = self._register_delayed_request("request-200")
        http_body = b'{"server": {}}'

        self.plugin_api._action_request_complete(
            "request-200",
            httplib.OK,
            http_headers=[
                ("Server", "suppressed"),
                ("Date", "suppressed"),
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(http_body))),
            ],
            http_body=http_body,
        )

        header_block, _, written_body = dispatcher.wfile.written.partition(b"\r\n\r\n")
        self.assert_single_header_terminator(dispatcher)
        self.assertEqual(http_body, written_body)
        self.assertIn(b"Content-Type: application/json", header_block)
        self.assertNotIn(b"Server: suppressed", header_block)
        self.assertTrue(dispatcher.wfile.closed)

    def test_action_request_complete_writes_headers_before_body(self):
        """A body is never written ahead of the header block.

        A relayed response can carry a body without headers, and the header
        flush moved into done(), so the flush has to happen before the body
        rather than after it.
        """

        dispatcher = self._register_delayed_request("request-500")
        http_body = b'{"computeFault": {}}'

        self.plugin_api._action_request_complete(
            "request-500",
            httplib.INTERNAL_SERVER_ERROR,
            http_headers=None,
            http_body=http_body,
        )

        header_block, _, written_body = dispatcher.wfile.written.partition(b"\r\n\r\n")
        self.assert_single_header_terminator(dispatcher)
        self.assertTrue(
            header_block.startswith(
                self.status_line(httplib.INTERNAL_SERVER_ERROR).rstrip(b"\r\n")
            )
        )
        self.assertEqual(http_body, written_body)


class TestRestAPIRequestDispatcher(testcase.NFVTestCase):
    """Verify the dispatcher-level response finalisation."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(RestAPIRequestDispatcher, "log_request")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_done_flushes_buffered_headers(self):
        """done() writes the headers that send_response only buffered."""

        dispatcher = make_dispatcher()
        dispatcher.send_response(httplib.NOT_FOUND)
        # In python3 send_response only appends to the header buffer.
        self.assertEqual(b"", dispatcher.wfile.written)

        dispatcher.done()

        self.assertTrue(dispatcher.wfile.written.startswith(b"HTTP/1.0 404 "))
        self.assertTrue(dispatcher.wfile.written.endswith(b"\r\n\r\n"))

    def test_done_does_not_close_socket_when_not_delayed(self):
        """done() leaves the socket to finish() on the non-delayed path."""

        dispatcher = make_dispatcher()
        dispatcher.send_response(httplib.NOT_FOUND)

        dispatcher.done()

        self.assertFalse(dispatcher.wfile.closed)
        self.assertFalse(dispatcher._is_shutdown)
        dispatcher.request.shutdown.assert_not_called()

        # finish() is what tears the socket down, once http.server is done
        # with wfile.
        dispatcher.finish()

        self.assertTrue(dispatcher.wfile.closed)
        self.assertTrue(dispatcher._is_shutdown)

    def test_done_closes_socket_when_delayed(self):
        """done() releases the socket on the delayed path, where finish() will not."""

        dispatcher = make_dispatcher()
        dispatcher.response_delayed()
        dispatcher.send_response(httplib.SERVICE_UNAVAILABLE)

        dispatcher.done()

        self.assertTrue(dispatcher.wfile.written.startswith(b"HTTP/1.0 503 "))
        self.assertTrue(dispatcher.wfile.closed)
        self.assertTrue(dispatcher._is_shutdown)

        # finish() early-returns on this path and must not double up.
        dispatcher.finish()

        self.assertEqual(1, dispatcher.request.shutdown.call_count)

    def test_end_headers_is_idempotent(self):
        """An explicit end_headers() followed by done() does not corrupt the body."""

        dispatcher = make_dispatcher()
        http_body = b'{"itemNotFound": {}}'
        dispatcher.send_response(httplib.NOT_FOUND)
        dispatcher.send_header("Content-Type", "application/json")
        dispatcher.send_header("Content-Length", str(len(http_body)))
        dispatcher.end_headers()
        dispatcher.wfile.write(http_body)

        dispatcher.done()

        self.assertEqual(1, dispatcher.wfile.written.count(b"\r\n\r\n"))
        self.assertTrue(dispatcher.wfile.written.endswith(http_body))

    def test_end_headers_after_shutdown_writes_nothing(self):
        """end_headers() is inert once the socket has been released."""

        dispatcher = make_dispatcher()
        dispatcher.response_delayed()
        dispatcher.send_response(httplib.ACCEPTED)
        dispatcher.done()
        written = dispatcher.wfile.written

        dispatcher.end_headers()
        dispatcher.done()

        self.assertEqual(written, dispatcher.wfile.written)

    def test_send_header_suppresses_server_header(self):
        """The Server header is still suppressed through the new flush path."""

        dispatcher = make_dispatcher()
        dispatcher.send_response(httplib.OK)
        dispatcher.send_header("Server", "should-not-appear")

        dispatcher.done()

        self.assertNotIn(b"should-not-appear", dispatcher.wfile.written)
        self.assertIn(b"Date: ", dispatcher.wfile.written)
