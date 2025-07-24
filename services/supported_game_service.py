# services/supported_game_service.py

from models.supportedGame import SupportedGame, PlatformEnum
from models.vendor import Vendor
from models.game import Game
from db.extensions import db

class SupportedGameService:
    @staticmethod
    def add_supported_game(vendor_id, game_id, platform, is_famous=False):
        vendor = Vendor.query.get(vendor_id)
        game = Game.query.get(game_id)
        if not vendor:
            raise ValueError("Vendor not found")
        if not game:
            raise ValueError("Game not found")
        
        # Prevent duplicate entry
        exists = SupportedGame.query.filter_by(
            vendor_id=vendor_id, game_id=game_id, platform=platform
        ).first()
        if exists:
            raise ValueError("This game is already supported by the vendor on this platform.")

        sg = SupportedGame(
            vendor_id=vendor_id,
            game_id=game_id,
            platform=platform,
            is_famous=is_famous
        )
        db.session.add(sg)
        db.session.commit()
        return sg

    @staticmethod
    def remove_supported_game(vendor_id, game_id, platform):
        sg = SupportedGame.query.filter_by(
            vendor_id=vendor_id, game_id=game_id, platform=platform
        ).first()
        if not sg:
            raise ValueError("This supported game entry does not exist.")
        db.session.delete(sg)
        db.session.commit()

    @staticmethod
    def list_vendor_supported_games(vendor_id):
        supported = (
            SupportedGame.query.filter_by(vendor_id=vendor_id)
            .join(Game)
            .all()
        )
        return supported

    @staticmethod
    def list_game_vendors(game_id, platform=None):
        q = SupportedGame.query.filter_by(game_id=game_id)
        if platform:
            q = q.filter_by(platform=platform)
        return q.all()
