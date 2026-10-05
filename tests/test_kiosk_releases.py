import ast
import re
from pathlib import Path
from urllib.parse import urlsplit
import pytest

source=Path(__file__).resolve().parents[1]/'services/kiosk_releases.py'
tree=ast.parse(source.read_text())
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_release')
scope={'re':re,'urlsplit':urlsplit}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),scope)
validate=scope['validate_release']
BUILD='https://github.com/zeyan-ansari/hashdashpc/actions/runs/37220882347/artifacts/11309578734'
ASSET='https://github.com/zeyan-ansari/hashdashpc/releases/download/v1.2.0/HashDash.exe'


def test_actions_link_can_be_saved_as_draft_reference():
    assert validate({'version':'1.2.0','source_url':BUILD})['download_url']==''


def test_release_installer_can_be_saved():
    assert validate({'version':'1.2.0','source_url':BUILD,'download_url':ASSET})['download_url']==ASSET


@pytest.mark.parametrize('url',[BUILD,'javascript:alert(1)','https://github.com.evil.test/app.exe','https://user:pass@github.com/a/b/releases/download/v1/app.exe',ASSET+'?token=secret'])
def test_rejects_non_installer_and_credential_links(url):
    with pytest.raises(ValueError):validate({'version':'1.2.0','source_url':BUILD,'download_url':url})


def test_rejects_missing_version():
    with pytest.raises(ValueError):validate({'source_url':BUILD})


@pytest.mark.parametrize('available',[False,True])
def test_activation_preserves_current_version_when_download_is_private(monkeypatch,available):
    from flask import Flask,jsonify,current_app
    from types import SimpleNamespace
    import requests
    controller=source.parents[1]/'controllers/super_admin_controller.py'
    activation=next(n for n in ast.parse(controller.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='activate_kiosk_release')
    activation.decorator_list=[]
    calls=[]
    class Session:
        def execute(self,sql,params=None):
            calls.append(str(sql))
            return SimpleNamespace(scalar=lambda:ASSET)
        def rollback(self): calls.append('ROLLBACK')
        def commit(self): calls.append('COMMIT')
    class Asset:
        status_code=200 if available else 404
        headers={'Content-Type':'application/octet-stream'}
        def __enter__(self): return self
        def __exit__(self,*args): pass
    monkeypatch.setattr(requests,'head',lambda *args,**kwargs:Asset())
    scope={'db':SimpleNamespace(session=Session()),'jsonify':jsonify,'current_app':current_app}
    exec(compile(ast.Module(body=[activation],type_ignores=[]),str(controller),'exec'),scope)
    with Flask(__name__).app_context():
        result=scope['activate_kiosk_release'](7)
        if available:
            assert result.json['success'] is True
            assert calls[-1]=='COMMIT'
            assert len([sql for sql in calls if sql.startswith('UPDATE')])==2
        else:
            assert result[1]==400
            assert 'ROLLBACK' in calls
            assert not any(sql.startswith('UPDATE') for sql in calls)
    assert calls[0].startswith('LOCK TABLE')
