"""Run with GAME_SEARCH_TEST_DATABASE_URL pointing to a disposable PostgreSQL DB."""
import ast
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

from sqlalchemy import create_engine, text


@unittest.skipUnless(os.getenv('GAME_SEARCH_TEST_DATABASE_URL'), 'PostgreSQL test URL not configured')
class GameSearchPostgresTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(os.environ['GAME_SEARCH_TEST_DATABASE_URL'])
        self.addCleanup(engine.dispose)
        connection = engine.connect()
        self.addCleanup(connection.close)
        transaction = connection.begin()
        self.addCleanup(transaction.rollback)
        # Temporary tables isolate this fixture from persistent application data.
        for statement in [
            '''CREATE TEMP TABLE games (id INT, slug TEXT, name TEXT, genre TEXT, platform TEXT,
                image_url TEXT, multiplayer BOOLEAN, average_rating FLOAT, rawg_rating FLOAT)''',
            '''CREATE TEMP TABLE console_catalog (id INT, slug TEXT, display_name TEXT,
                family TEXT, icon TEXT, is_active BOOLEAN)''',
            '''CREATE TEMP TABLE game_console_catalog (game_id INT, console_catalog_id INT,
                popularity_score FLOAT, is_active BOOLEAN)''',
            "INSERT INTO games (id, slug, name) VALUES (1, 'gta-6', 'Grand Theft Auto VI'), (2, 'portal', 'Portal')",
            "INSERT INTO console_catalog (id, slug, display_name, is_active) VALUES (1, 'playstation', 'PlayStation', true)",
            'INSERT INTO game_console_catalog VALUES (1, 1, 0, true), (2, 1, 0, true)',
        ]:
            connection.execute(text(statement))
        source = Path(__file__).resolve().parents[1] / 'services/game_service.py'
        service = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'GameService')
        names = {'_normalize_limit', '_normalize_offset', '_safe_int', '_game_card', 'search_discovery_games'}
        service.body = [n for n in service.body if isinstance(n, ast.FunctionDef) and n.name in names]
        scope = {'text': text, 'json': json, 'db': SimpleNamespace(session=connection)}
        exec(compile(ast.Module(body=[service], type_ignores=[]), str(source), 'exec'), scope)
        self.service = scope['GameService']
        self.service._cache_get = staticmethod(lambda *args: None)
        self.service._cache_set = staticmethod(lambda *args: None)

    def test_search_by_name_with_psycopg_server_parameters(self):
        result = self.service.search_discovery_games(q=' Grand Theft Auto VI ')
        self.assertEqual([g['id'] for g in result['games']], [1])

    def test_slug_search(self):
        self.assertEqual(self.service.search_discovery_games(q='GTA-6')['count'], 1)

    def test_empty_search_and_pagination(self):
        result = self.service.search_discovery_games(limit=1)
        self.assertEqual(result['next_cursor'], '1')
        page = self.service.search_discovery_games(limit=1, cursor=result['next_cursor'])
        self.assertEqual(page['games'][0]['name'], 'Portal')
        self.assertIsNone(page['next_cursor'])

    def test_no_match_and_platform_filter(self):
        self.assertEqual(self.service.search_discovery_games(q='missing')['count'], 0)
        self.assertEqual(self.service.search_discovery_games(q='Grand', console_slug='xbox')['count'], 0)
