import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import unittest

class DocumentReviewTests(unittest.TestCase):
    def setUp(self):
        source=Path('services/super_admin_service.py').read_text()
        cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='SuperAdminService')
        fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='verify_documents')
        fn.decorator_list=[]
        self.document=Mock()
        self.document.query.filter.return_value.all.return_value=[]
        scope={'Document':self.document}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'review','exec'),scope)
        self.verify=scope['verify_documents']
    def test_invalid_ids_never_query_database(self):
        for ids in [[],['1'],[True],[-1],[None]]:
            self.assertFalse(self.verify(1,ids)[0])
        self.document.query.filter.assert_not_called()
    def test_partial_or_foreign_document_batch_is_rejected(self):
        doc=SimpleNamespace(status='unverified')
        self.document.query.filter.return_value.all.return_value=[doc]
        self.assertEqual(self.verify(1,[1,2]),(False,'Every document must belong to this cafe'))
        self.assertEqual(doc.status,'unverified')
