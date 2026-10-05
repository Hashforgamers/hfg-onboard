import ast
from pathlib import Path
from flask import Flask,request,jsonify,current_app
from types import SimpleNamespace
import pytest
import requests
import os

source=Path(__file__).resolve().parents[1]/'controllers/super_admin_controller.py'
node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='preview_notification_context')
node.decorator_list=[]
scope=dict(request=request,jsonify=jsonify,current_app=current_app,os=os)
exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),scope)


@pytest.mark.parametrize('status,expected',[(405,'Deploy'),(404,'Deploy'),(401,'SUPER_ADMIN_API_KEY'),(403,'SUPER_ADMIN_API_KEY'),(200,'')])
def test_upstream_errors_identify_required_fix(monkeypatch,status,expected):
    calls=[]
    monkeypatch.setenv('USER_ONBOARD_BACKEND_URL','https://hfg-user-onboard.onrender.com/api/')
    def post(url,**kwargs):
        calls.append(url)
        return SimpleNamespace(status_code=status,json=lambda:dict(success=True,data={'title':'Test','message':'Test'}))
    monkeypatch.setattr(requests,'post',post)
    app=Flask(__name__)
    app.add_url_rule('/preview',view_func=scope['preview_notification_context'],methods=['POST'])
    response=app.test_client().post('/preview',json={'context':'Example'})
    assert calls==['https://hfg-user-onboard.onrender.com/api/admin/notification-context/preview']
    if expected:
        assert response.status_code==503
        assert expected in response.json['message']
    else: assert response.status_code==200 and response.json['success']
