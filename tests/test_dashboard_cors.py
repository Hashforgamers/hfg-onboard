"""Use the app's actual CORS configuration to test dashboard preflight."""
import ast
from pathlib import Path
from flask import Flask
from flask_cors import CORS


def test_operating_hours_preflight_accepts_dashboard_headers():
    source=Path(__file__).resolve().parents[1]/'app/__init__.py'
    tree=ast.parse(source.read_text())
    config=next(node for node in ast.walk(tree) if isinstance(node,ast.Expr)
                and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name)
                and node.value.func.id=='CORS')
    app=Flask(__name__)
    exec(compile(ast.Module(body=[config],type_ignores=[]),str(source),'exec'),{'app':app,'CORS':CORS})
    app.add_url_rule('/api/vendor/41/updateSlot',view_func=lambda:'ok',methods=['POST'])
    response=app.test_client().options('/api/vendor/41/updateSlot',headers={
        'Origin':'https://dashboard.hashforgamers.com',
        'Access-Control-Request-Method':'POST',
        'Access-Control-Request-Headers':'authorization,content-type,x-client-source',
    })
    assert response.status_code==200
    allowed=response.headers['Access-Control-Allow-Headers'].lower()
    assert all(header in allowed for header in ['authorization','content-type','x-client-source'])
    assert response.headers['Access-Control-Allow-Origin']=='https://dashboard.hashforgamers.com'
