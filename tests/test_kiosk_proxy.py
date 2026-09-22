"""Verify the public kiosk proxy preserves authentication and API envelopes."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from flask import Flask, request, jsonify, current_app


class ProxyTests(unittest.TestCase):
    def setUp(self):
        source=Path(__file__).resolve().parents[1]/'controllers/controllers.py'
        tree=ast.parse(source.read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='insert_to_queue')
        fn.decorator_list=[]
        connection=Mock()
        connection.execute.return_value.scalar_one.return_value=1
        context=Mock()
        context.__enter__=Mock(return_value=connection)
        context.__exit__=Mock(return_value=False)
        self.http=Mock()
        scope=dict(request=request,jsonify=jsonify,current_app=current_app,
                   requests=self.http,DASHBOARD_SERVICE_URL='https://dashboard.invalid',text=lambda s:s,
                   db=SimpleNamespace(engine=SimpleNamespace(begin=lambda:context)))
        exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),scope)
        app=Flask(__name__)
        app.add_url_rule('/api/bookingQueue',view_func=scope['insert_to_queue'],methods=['POST'])
        self.client=app.test_client()

    def test_canonical_success_and_bearer_forwarded(self):
        body={'status':'success','data':{'booking_id':5,'user_name':'Player'}}
        self.http.post.return_value=SimpleNamespace(json=lambda:body,status_code=200,headers={})
        response=self.client.post('/api/bookingQueue',json={'console_id':10,'access_code':'123456'},headers={'Authorization':'Bearer linked-token'})
        self.assertEqual(response.json,body)
        self.assertEqual(self.http.post.call_args.kwargs['headers']['Authorization'],'Bearer linked-token')

    def test_rate_limit_status_and_retry_header_forwarded(self):
        self.http.post.return_value=SimpleNamespace(json=lambda:{'status':'error','code':'rate_limited'},status_code=429,headers={'Retry-After':'60'})
        response=self.client.post('/api/bookingQueue',json={'console_id':10,'access_code':'123456'})
        self.assertEqual(response.status_code,429)
        self.assertEqual(response.headers['Retry-After'],'60')

    def test_non_json_upstream_returns_json_502(self):
        self.http.post.return_value=SimpleNamespace(json=Mock(side_effect=ValueError()),status_code=500)
        response=self.client.post('/api/bookingQueue',json={'console_id':10,'access_code':'123456'})
        self.assertEqual(response.status_code,502)
        self.assertEqual(response.json['code'],'upstream_invalid_response')


if __name__=='__main__': unittest.main()
