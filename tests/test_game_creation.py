"""Exercise catalog creation against the actual Game columns and a SQL database."""
import ast
from datetime import datetime
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from urllib.parse import urlparse
import uuid

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, Float, Date, Boolean, DateTime, text


class GameCreationTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.context = app.app_context()
        self.context.push()
        self.addCleanup(self.context.pop)
        self.db = SQLAlchemy(app)
        # Use production columns without loading unrelated vendor model relationships.
        tree = ast.parse(Path('models/game.py').read_text())
        model = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        model.body = [n for n in model.body if not (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'vendor_games' for t in n.targets))]
        scope = dict(globals(), db=self.db)
        exec(compile(ast.Module(body=[model], type_ignores=[]), 'game-model', 'exec'), scope)
        self.Game = scope['Game']
        self.db.create_all()
        self.db.session.execute(text('CREATE TABLE console_catalog (id INTEGER PRIMARY KEY, display_name TEXT, is_active BOOLEAN)'))
        self.db.session.execute(text('CREATE TABLE game_console_catalog (game_id INTEGER, console_catalog_id INTEGER, source_platform TEXT)'))
        self.db.session.execute(text("INSERT INTO console_catalog VALUES (1, 'PlayStation', true), (2, 'Xbox', true)"))
        self.db.session.commit()
        service = next(n for n in ast.parse(Path('services/game_service.py').read_text()).body if isinstance(n, ast.ClassDef))
        create = next(n for n in service.body if isinstance(n, ast.FunctionDef) and n.name == 'create_game')
        create.decorator_list = []
        scope.update(redis_client=Mock(scan_iter=Mock(return_value=[])), current_app=app)
        exec(compile(ast.Module(body=[create], type_ignores=[]), 'create-game', 'exec'), scope)
        self.create = scope['create_game']

    def test_artwork_and_platforms_survive_reload(self):
        game = self.create(name=' Grand Theft Auto VI ', cover_image_url='https://example.com/cover.jpg', console_catalog_ids=[1, 2, 1])
        game_id = game.id
        self.db.session.expire_all()
        saved = self.db.session.get(self.Game, game_id)
        self.assertEqual(saved.name, 'Grand Theft Auto VI')
        self.assertEqual(saved.image_url, 'https://example.com/cover.jpg')
        self.assertEqual(saved.platform, 'PlayStation')
        self.assertTrue(saved.slug.startswith('grand-theft-auto-vi-'))
        self.assertEqual(self.db.session.execute(text('SELECT COUNT(*) FROM game_console_catalog')).scalar(), 2)

    def test_unknown_platform_does_not_leave_a_game(self):
        with self.assertRaises(ValueError):
            self.create(name='Bad platform', console_catalog_ids=[1, 999])
        self.assertEqual(self.Game.query.count(), 0)

    def test_invalid_input_is_rejected(self):
        for values in ({'name': ' '}, {'name': 'Game', 'cover_image_url': 'javascript:alert(1)'}, {'name': 'Game', 'console_catalog_ids': [True]}, {'name': 'Game', 'release_date': 'invalid'}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.create(**values)
        self.assertEqual(self.Game.query.count(), 0)

    def test_legacy_create_call_uses_supported_model_columns(self):
        game = self.create(name='Legacy game', developer='Studio', publisher='Publisher', screenshots=['image'])
        self.assertIsNotNone(game.id)


if __name__ == '__main__':
    unittest.main()
