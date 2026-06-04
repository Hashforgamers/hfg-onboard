from models.game import Game
from db.extensions import db, redis_client
from datetime import datetime
from services.cloudinary_services import CloudinaryGameImageService
from flask import current_app
from sqlalchemy import text
import json
import os

class GameService:
    DISCOVERY_CACHE_TTL_SECONDS = int(os.getenv("GAME_DISCOVERY_CACHE_TTL_SECONDS", "300"))
    POPULAR_EVENT_WEIGHTS = {
        "booking_success": 10,
        "booking_start": 6,
        "result_view": 4,
        "click": 3,
        "view": 1,
        "search": 1,
    }

    @staticmethod
    def _normalize_limit(limit, default=20, maximum=50):
        try:
            return max(1, min(int(limit or default), maximum))
        except Exception:
            return default

    @staticmethod
    def _normalize_offset(cursor):
        try:
            return max(0, int(cursor or 0))
        except Exception:
            return 0

    @staticmethod
    def _safe_int(value):
        try:
            if value in (None, ""):
                return None
            return int(value)
        except Exception:
            return None

    @staticmethod
    def _safe_float(value, scale=6):
        try:
            if value in (None, ""):
                return None
            return round(float(value), scale)
        except Exception:
            return None

    @staticmethod
    def _game_card(row):
        return {
            "id": row["id"],
            "slug": row["slug"],
            "name": row["name"],
            "genre": row["genre"],
            "platform": row["platform"],
            "image_url": row["image_url"],
            "multiplayer": bool(row["multiplayer"]) if row["multiplayer"] is not None else False,
            "average_rating": float(row["average_rating"] or 0),
            "rawg_rating": float(row["rawg_rating"] or 0),
            "console_catalog": {
                "id": row["console_catalog_id"],
                "slug": row["console_slug"],
                "display_name": row["console_display_name"],
                "family": row["console_family"],
                "icon": row["console_icon"],
            } if row["console_catalog_id"] else None,
            "popularity_score": float(row["popularity_score"] or 0),
        }

    @staticmethod
    def _cache_get(cache_key):
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            return None
        return None

    @staticmethod
    def _cache_set(cache_key, payload, ttl=None):
        try:
            redis_client.setex(cache_key, int(ttl or GameService.DISCOVERY_CACHE_TTL_SECONDS), json.dumps(payload))
        except Exception:
            pass

    @staticmethod
    def list_discovery_platforms(include_empty=False):
        cache_key = f"games:platforms:v1:{bool(include_empty)}"
        cached = GameService._cache_get(cache_key)
        if cached:
            return cached

        where_clause = "WHERE cc.is_active = true"
        if not include_empty:
            where_clause += " AND COALESCE(gc.game_count, 0) > 0"
        rows = db.session.execute(text(f"""
            WITH game_counts AS (
                SELECT console_catalog_id, COUNT(DISTINCT game_id) AS game_count
                FROM game_console_catalog
                WHERE is_active = true
                GROUP BY console_catalog_id
            )
            SELECT
                cc.id,
                cc.slug,
                cc.display_name,
                cc.family,
                cc.icon,
                cc.input_mode,
                cc.supports_multiplayer,
                cc.default_capacity,
                cc.controller_policy,
                COALESCE(gc.game_count, 0) AS game_count
            FROM console_catalog cc
            LEFT JOIN game_counts gc ON gc.console_catalog_id = cc.id
            {where_clause}
            ORDER BY COALESCE(gc.game_count, 0) DESC, cc.display_name ASC
        """)).mappings().all()

        payload = {
            "platforms": [
                {
                    "id": row["id"],
                    "slug": row["slug"],
                    "display_name": row["display_name"],
                    "family": row["family"],
                    "icon": row["icon"],
                    "input_mode": row["input_mode"],
                    "supports_multiplayer": bool(row["supports_multiplayer"]),
                    "default_capacity": row["default_capacity"],
                    "controller_policy": row["controller_policy"],
                    "game_count": int(row["game_count"] or 0),
                }
                for row in rows
            ]
        }
        GameService._cache_set(cache_key, payload, ttl=600)
        return payload

    @staticmethod
    def search_discovery_games(q=None, console_slug=None, console_catalog_id=None, limit=20, cursor=None):
        limit = GameService._normalize_limit(limit)
        offset = GameService._normalize_offset(cursor)
        normalized_query = str(q or "").strip().lower()
        normalized_console_slug = str(console_slug or "").strip().lower()
        catalog_id = GameService._safe_int(console_catalog_id)

        cache_payload = {
            "q": normalized_query,
            "console_slug": normalized_console_slug,
            "console_catalog_id": catalog_id,
            "limit": limit,
            "offset": offset,
        }
        cache_key = f"games:search:v1:{json.dumps(cache_payload, sort_keys=True, separators=(',', ':'))}"
        cached = GameService._cache_get(cache_key)
        if cached:
            return cached

        where = ["gcc.is_active = true", "cc.is_active = true"]
        params = {
            "q": normalized_query or None,
            "console_slug": normalized_console_slug or None,
            "console_catalog_id": catalog_id,
            "limit": limit + 1,
            "offset": offset,
        }
        if normalized_query:
            where.append("(LOWER(g.name) LIKE CONCAT('%', :q, '%') OR LOWER(COALESCE(g.slug, '')) LIKE CONCAT('%', :q, '%'))")
        if catalog_id is not None:
            where.append("cc.id = :console_catalog_id")
        elif normalized_console_slug:
            where.append("cc.slug = :console_slug")

        rows = db.session.execute(text(f"""
            SELECT
                g.id,
                g.slug,
                g.name,
                g.genre,
                g.platform,
                g.image_url,
                g.multiplayer,
                g.average_rating,
                g.rawg_rating,
                cc.id AS console_catalog_id,
                cc.slug AS console_slug,
                cc.display_name AS console_display_name,
                cc.family AS console_family,
                cc.icon AS console_icon,
                gcc.popularity_score
            FROM game_console_catalog gcc
            JOIN games g ON g.id = gcc.game_id
            JOIN console_catalog cc ON cc.id = gcc.console_catalog_id
            WHERE {" AND ".join(where)}
            ORDER BY gcc.popularity_score DESC, COALESCE(g.average_rating, g.rawg_rating, 0) DESC, g.name ASC
            LIMIT :limit OFFSET :offset
        """), params).mappings().all()

        result_rows = rows[:limit]
        payload = {
            "games": [GameService._game_card(row) for row in result_rows],
            "count": len(result_rows),
            "next_cursor": str(offset + limit) if len(rows) > limit else None,
            "filters": {
                "q": normalized_query or None,
                "console_slug": normalized_console_slug or None,
                "console_catalog_id": catalog_id,
                "limit": limit,
            },
        }
        GameService._cache_set(cache_key, payload)
        return payload

    @staticmethod
    def get_popular_discovery_games(console_slug=None, console_catalog_id=None, city=None, limit=20):
        limit = GameService._normalize_limit(limit)
        normalized_console_slug = str(console_slug or "").strip().lower()
        normalized_city = str(city or "").strip().lower()
        catalog_id = GameService._safe_int(console_catalog_id)
        weights = GameService.POPULAR_EVENT_WEIGHTS

        cache_payload = {
            "console_slug": normalized_console_slug,
            "console_catalog_id": catalog_id,
            "city": normalized_city,
            "limit": limit,
        }
        cache_key = f"games:popular:v1:{json.dumps(cache_payload, sort_keys=True, separators=(',', ':'))}"
        cached = GameService._cache_get(cache_key)
        if cached:
            return cached

        where = ["gcc.is_active = true", "cc.is_active = true"]
        params = {
            "console_slug": normalized_console_slug or None,
            "console_catalog_id": catalog_id,
            "city": normalized_city or None,
            "limit": limit,
            "booking_success_weight": weights["booking_success"],
            "booking_start_weight": weights["booking_start"],
            "result_view_weight": weights["result_view"],
            "click_weight": weights["click"],
            "view_weight": weights["view"],
            "search_weight": weights["search"],
        }
        if catalog_id is not None:
            where.append("cc.id = :console_catalog_id")
        elif normalized_console_slug:
            where.append("cc.slug = :console_slug")

        rows = db.session.execute(text(f"""
            WITH event_scores AS (
                SELECT
                    game_id,
                    console_catalog_id,
                    SUM(CASE event_type
                        WHEN 'booking_success' THEN :booking_success_weight
                        WHEN 'booking_start' THEN :booking_start_weight
                        WHEN 'result_view' THEN :result_view_weight
                        WHEN 'click' THEN :click_weight
                        WHEN 'view' THEN :view_weight
                        WHEN 'search' THEN :search_weight
                        ELSE 0
                    END) AS event_score
                FROM game_discovery_events
                WHERE created_at >= NOW() - INTERVAL '7 days'
                  AND game_id IS NOT NULL
                  AND (:city IS NULL OR LOWER(COALESCE(city, '')) = :city)
                GROUP BY game_id, console_catalog_id
            )
            SELECT
                g.id,
                g.slug,
                g.name,
                g.genre,
                g.platform,
                g.image_url,
                g.multiplayer,
                g.average_rating,
                g.rawg_rating,
                cc.id AS console_catalog_id,
                cc.slug AS console_slug,
                cc.display_name AS console_display_name,
                cc.family AS console_family,
                cc.icon AS console_icon,
                (COALESCE(es.event_score, 0) + COALESCE(gcc.popularity_score, 0)) AS popularity_score
            FROM game_console_catalog gcc
            JOIN games g ON g.id = gcc.game_id
            JOIN console_catalog cc ON cc.id = gcc.console_catalog_id
            LEFT JOIN event_scores es
              ON es.game_id = g.id
             AND es.console_catalog_id = cc.id
            WHERE {" AND ".join(where)}
            ORDER BY (COALESCE(es.event_score, 0) + COALESCE(gcc.popularity_score, 0)) DESC,
                     COALESCE(g.average_rating, g.rawg_rating, 0) DESC,
                     g.name ASC
            LIMIT :limit
        """), params).mappings().all()

        payload = {
            "games": [GameService._game_card(row) for row in rows],
            "count": len(rows),
            "filters": {
                "console_slug": normalized_console_slug or None,
                "console_catalog_id": catalog_id,
                "city": normalized_city or None,
                "limit": limit,
            },
        }
        GameService._cache_set(cache_key, payload)
        return payload

    @staticmethod
    def record_discovery_event(data):
        event_type = str(data.get("event_type") or "").strip().lower()
        if event_type not in GameService.POPULAR_EVENT_WEIGHTS:
            raise ValueError("Invalid event_type")

        game_id = GameService._safe_int(data.get("game_id"))
        console_catalog_id = GameService._safe_int(data.get("console_catalog_id"))
        console_slug = str(data.get("console_slug") or data.get("platform_type") or "").strip().lower() or None
        city = str(data.get("city") or "").strip().lower() or None
        pincode = str(data.get("pincode") or "").strip() or None
        search_query = str(data.get("search_query") or data.get("q") or "").strip() or None
        game_name = str(data.get("game_name") or "").strip() or None
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}

        if game_id and not game_name:
            game = db.session.get(Game, game_id)
            game_name = game.name if game else None

        if console_catalog_id is None and console_slug:
            row = db.session.execute(
                text("SELECT id FROM console_catalog WHERE slug = :slug"),
                {"slug": console_slug},
            ).mappings().first()
            console_catalog_id = row["id"] if row else None

        db.session.execute(text("""
            INSERT INTO game_discovery_events (
                user_id,
                session_id,
                game_id,
                game_name,
                console_catalog_id,
                console_slug,
                city,
                pincode,
                lat,
                lng,
                event_type,
                search_query,
                metadata
            )
            VALUES (
                :user_id,
                :session_id,
                :game_id,
                :game_name,
                :console_catalog_id,
                :console_slug,
                :city,
                :pincode,
                :lat,
                :lng,
                :event_type,
                :search_query,
                CAST(:metadata AS jsonb)
            )
        """), {
            "user_id": GameService._safe_int(data.get("user_id")),
            "session_id": str(data.get("session_id") or "")[:128] or None,
            "game_id": game_id,
            "game_name": game_name,
            "console_catalog_id": console_catalog_id,
            "console_slug": console_slug,
            "city": city,
            "pincode": pincode,
            "lat": GameService._safe_float(data.get("lat")),
            "lng": GameService._safe_float(data.get("lng")),
            "event_type": event_type,
            "search_query": search_query,
            "metadata": json.dumps(metadata),
        })
        db.session.commit()

        return {
            "success": True,
            "event_type": event_type,
            "game_id": game_id,
            "console_catalog_id": console_catalog_id,
        }

    @staticmethod
    def create_game(
        name,
        description=None,
        release_date=None,
        developer=None,
        publisher=None,
        genre=None,
        cover_image_url=None,
        screenshots=None,
        average_rating=0.0,
        trailer_url=None,
        multiplayer=False,
        esrb_rating=None,
    ):
        if not name:
            raise ValueError("Game name is required.")

        # Convert release_date from string to date if necessary
        release_date_obj = None
        if release_date:
            try:
                # Expecting ISO format: 'YYYY-MM-DD' or similar
                release_date_obj = datetime.strptime(release_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("release_date must be in 'YYYY-MM-DD' format.")

        # Validate screenshots is JSON-serializable or None
        if screenshots and not isinstance(screenshots, (list, dict)):
            raise ValueError("screenshots must be a JSON serializable list or dict.")

        # Create Game object
        game = Game(
            name=name,
            description=description,
            release_date=release_date_obj,
            developer=developer,
            publisher=publisher,
            genre=genre,
            cover_image_url=cover_image_url,
            screenshots=screenshots,
            average_rating=average_rating,
            trailer_url=trailer_url,
            multiplayer=multiplayer,
            esrb_rating=esrb_rating,
        )

        try:
            db.session.add(game)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to create game: {str(e)}")

        return game
    
    # new game service with cloudinary

    @staticmethod
    def create_game_with_cover_image(
        name,
        cover_image_file=None,
        description=None,
        release_date=None,
        developer=None,
        publisher=None,
        genre=None,
        screenshots=None,
        average_rating=0.0,
        trailer_url=None,
        multiplayer=False,
        esrb_rating=None,
    ):
        """
        Create game with Cloudinary cover image upload
        """
        if not name:
            raise ValueError("Game name is required.")

        cover_image_url = None
        
        # Upload cover image to Cloudinary if provided
        if cover_image_file:
            try:
                from services.cloudinary_services import CloudinaryGameImageService
                upload_result = CloudinaryGameImageService.upload_game_cover_image(
                    cover_image_file, 
                    name
                )
                
                if upload_result['success']:
                    cover_image_url = upload_result['url']
                    current_app.logger.info(f"Cover image uploaded for game '{name}': {cover_image_url}")
                else:
                    current_app.logger.warning(f"Failed to upload cover image: {upload_result['error']}")
            except ImportError:
                current_app.logger.warning("Cloudinary service not available")

        # Create game using existing create_game method
        return GameService.create_game(
            name=name,
            description=description,
            release_date=release_date,
            developer=developer,
            publisher=publisher,
            genre=genre,
            cover_image_url=cover_image_url,  # Cloudinary URL
            screenshots=screenshots,
            average_rating=average_rating,
            trailer_url=trailer_url,
            multiplayer=multiplayer,
            esrb_rating=esrb_rating,
        )
