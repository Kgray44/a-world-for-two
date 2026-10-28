import http.client
import socket
import threading
import unittest

from control_room.redirect import PreviewRedirect, PreviewServer, make_server


class PreviewRedirectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)  # Owned ephemeral test listener; no live port touched.
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={'poll_interval': .01})
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)
        if cls.thread.is_alive():
            raise AssertionError('Owned redirect test listener did not stop')

    def request(self, method='GET', target='/', host=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        try:
            connection.request(method, target, headers={'Host': host or f'127.0.0.1:{self.port}'})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_fixed_loopback_target_preserves_path_and_query_for_get_and_head(self):
        for method in ('GET', 'HEAD'):
            status, headers, body = self.request(method, '/api/overview?view=atlas&name=Rose%20Reach')
            self.assertEqual(status, 307)
            self.assertEqual(headers['Location'], 'http://127.0.0.1:8766/api/overview?view=atlas&name=Rose%20Reach')
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertEqual(headers['Content-Length'], '0')
            self.assertEqual(body, b'')
            self.assertFalse(any(name.lower().startswith('access-control-') for name in headers))

    def test_stale_actions_and_all_other_methods_are_not_forwarded(self):
        for method in ('POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'TRACE', 'CONNECT', 'CUSTOM'):
            with self.subTest(method=method):
                status, headers, body = self.request(method, '/api/server/start')
                self.assertEqual(status, 405)
                self.assertEqual(headers['Allow'], 'GET, HEAD')
                self.assertNotIn('Location', headers)
                self.assertEqual(body, b'')

    def test_only_exact_local_host_and_actual_port_are_accepted(self):
        self.assertEqual(self.request(host=f'localhost:{self.port}')[0], 307)
        for host in ('example.com', f'127.0.0.1:{self.port+1}', 'localhost',
                     f'user@127.0.0.1:{self.port}', f'127.0.0.1:{self.port}.evil'):
            self.assertEqual(self.request(host=host)[0], 400)

    def test_absolute_authority_encoded_controls_and_normalized_targets_refuse(self):
        for target in ('http://user@evil.test/', '//evil.test/', '/%2fevil.test/',
                       '/%5cevil.test/', '/x%0d%0aLocation:evil', '/x%00', '/#atlas', '/bad%zz'):
            with self.subTest(target=target):
                status, headers, body = self.request(target=target)
                self.assertEqual(status, 400)
                self.assertNotIn('Location', headers)
                self.assertEqual(body, b'')
        self.assertEqual(self.request(target='/'+'a'*8192)[0], 400)

    def test_duplicate_or_missing_host_and_expect_continue_fail_closed(self):
        requests = (
            f'GET / HTTP/1.1\r\nHost:127.0.0.1:{self.port}\r\nHost:evil.test\r\n\r\n',
            'GET / HTTP/1.1\r\n\r\n',
            f'POST /api/server/start HTTP/1.1\r\nHost:127.0.0.1:{self.port}\r\nExpect:100-continue\r\nContent-Length:10\r\n\r\n',
        )
        for request in requests:
            with socket.create_connection(('127.0.0.1', self.port), timeout=3) as connection:
                connection.sendall(request.encode('ascii'))
                response = http.client.HTTPResponse(connection)
                response.begin()
                self.assertIn(response.status, (400, 405))
                self.assertIsNone(response.getheader('Location'))
                self.assertEqual(response.read(), b'')

    def test_factory_cannot_bind_public_address_or_redirect_to_itself(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        for value in (8766, 80, -1, True, '0.0.0.0'):
            with self.assertRaises(ValueError):
                make_server(value)
        with self.assertRaises(ValueError):
            PreviewServer(('0.0.0.0', 0), PreviewRedirect)  # Refuses before socket creation.


if __name__ == '__main__':
    unittest.main()
