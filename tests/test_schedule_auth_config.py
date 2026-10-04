import importlib.util
from pathlib import Path


def test_schedule_key_is_loaded_from_environment(monkeypatch):
    monkeypatch.setenv('JWT_SECRET_KEY','isolated-test-key-'*4)
    source=Path(__file__).resolve().parents[1]/'app/config.py'
    spec=importlib.util.spec_from_file_location('schedule_config_test',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.Config.JWT_SECRET_KEY=='isolated-test-key-'*4


def test_flask_secret_is_not_used_as_login_signing_key(monkeypatch):
    monkeypatch.delenv('JWT_SECRET_KEY',raising=False)
    monkeypatch.setenv('SECRET_KEY','different-flask-secret-'*4)
    source=Path(__file__).resolve().parents[1]/'app/config.py'
    spec=importlib.util.spec_from_file_location('missing_schedule_config_test',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.Config.JWT_SECRET_KEY is None
