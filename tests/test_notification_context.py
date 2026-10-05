import ast
from pathlib import Path
import pytest

SOURCE=Path(__file__).resolve().parents[1]/'services/notification_context.py'
node=next(n for n in ast.parse(SOURCE.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='validate_notification_context')
scope={}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),scope)
validate=scope['validate_notification_context']
GOOD=dict(context='Promote squad bookings. No discounts.',enabled=True,fallback_title='Game with your squad',fallback_message='Explore nearby gaming cafes.')


def test_valid_context_and_pause():
    assert validate(GOOD)==GOOD
    assert validate(dict(GOOD,enabled=False))['enabled'] is False


@pytest.mark.parametrize('changes',[{'context':''},{'context':'x'*6001},{'enabled':'false'},{'fallback_title':'x'*81},{'fallback_message':''}])
def test_invalid_context(changes):
    with pytest.raises(ValueError): validate(dict(GOOD,**changes))


def test_rejects_non_object():
    with pytest.raises(ValueError): validate([])
