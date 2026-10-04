import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify


def test_daily_cron_commits_each_cafe_without_full_capacity_repair():
    source=Path(__file__).resolve().parents[1]/'controllers/controllers.py'
    node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='cron_extend_slots_for_all_active_cafes')
    node.decorator_list=[]
    service=MagicMock();service.extend_vendor_slot_window.side_effect=[3,RuntimeError('one cafe failed'),2]
    db=MagicMock()
    scope=dict(request=request,jsonify=jsonify,db=db,VendorService=service,dt=datetime,date=date,timedelta=timedelta,
        IST=ZoneInfo('Asia/Kolkata'),_is_valid_cron_request=lambda:True,
        _fetch_active_vendor_ids_for_slots=lambda:[1,2,3],_ensure_vendor_slot_table_exists=MagicMock(),current_app=MagicMock())
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),scope)
    app=Flask(__name__)
    with app.test_request_context(json={}):
        response,status=scope['cron_extend_slots_for_all_active_cafes']()
    assert status==200
    assert response.json['success'] is False
    assert [r['success'] for r in response.json['results']]==[True,False,True]
    assert response.json['inserted_rows_total']==5
    assert db.session.commit.call_count==3 # two cafe commits and final compatibility commit
    assert db.session.rollback.call_count==1
    service.reconcile_vendor_slot_capacity_window.assert_not_called()
