import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import unittest
import requests


class CatalogProxyTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / 'services/super_admin_service.py'
        tree = ast.parse(source.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'SuperAdminService')
        fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_subscription_catalog_request')
        fn.decorator_list = []
        self.http = SimpleNamespace(request=Mock(), RequestException=requests.RequestException)
        self.service = SimpleNamespace(_admin_proxy_headers=lambda: {'x-admin-key': 'server-only'}, _dashboard_service_url=lambda: 'https://dashboard.invalid')
        scope = dict(requests=self.http, SuperAdminService=self.service)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), 'exec'), scope)
        self.call = scope[fn.name]

    def respond(self, status, body):
        self.http.request.return_value = SimpleNamespace(status_code=status, json=lambda: body)

    def test_catalog_and_auth_forwarding(self):
        self.respond(200, {'models': [{'code': 'base'}]})
        self.assertEqual(self.call('GET'), (True, [{'code': 'base'}]))
        args = self.http.request.call_args.kwargs
        self.assertEqual(args['headers']['x-admin-key'], 'server-only')
        self.assertFalse(args['allow_redirects'])

    def test_missing_key_does_not_send_request(self):
        self.service._admin_proxy_headers = lambda: {}
        self.assertEqual(self.call('GET')[1]['status'], 503)
        self.http.request.assert_not_called()

    def test_auth_error_is_actionable_and_sanitized(self):
        self.respond(401, {'error': 'private upstream output'})
        ok, error = self.call('GET')
        self.assertFalse(ok)
        self.assertIn('matching SUPER_ADMIN_API_KEY', error['message'])
        self.assertNotIn('private', error['message'])

    def test_unavailable_and_malformed(self):
        for status, body in [(404, {}), (500, {}), (302, {}), (200, []), (200, {})]:
            with self.subTest(status=status, body=body):
                self.respond(status, body)
                self.assertEqual(self.call('GET')[1]['status'], 502)
        self.http.request.side_effect = requests.Timeout()
        self.assertEqual(self.call('GET')[1]['status'], 503)

    def test_validation_is_preserved(self):
        self.respond(400, {'message': 'Invalid monthly price'})
        self.assertEqual(self.call('PUT', payload={'models': []}), (False, {'message': 'Invalid monthly price', 'status': 400}))
