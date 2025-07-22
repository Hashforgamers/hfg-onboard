# routes/vendor_games.py

from flask import Blueprint, request, jsonify
from services.supported_game_service import SupportedGameService
from models.supportedGame import PlatformEnum
from models.game import Game
from services.game_service import GameService

vendor_games_bp = Blueprint('vendor_games', __name__)

# Add a supported game for a vendor
@vendor_games_bp.route('/vendors/<int:vendor_id>/supported-games', methods=['POST'])
def add_supported_game(vendor_id):
    data = request.get_json()
    game_id = data.get('game_id')
    platform = data.get('platform')
    is_famous = data.get('is_famous', False)

    # Validate platform value
    if platform not in [e.value for e in PlatformEnum]:
        return jsonify({'message': 'Invalid platform.'}), 400

    try:
        sg = SupportedGameService.add_supported_game(
            vendor_id, game_id, platform, is_famous
        )
        return jsonify({
            'message': 'Supported game added',
            'supported_game': {
                'id': sg.id,
                'game_id': sg.game_id,
                'platform': sg.platform,
                'is_famous': sg.is_famous
            }
        }), 201
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 400

# Remove a supported game for a vendor
@vendor_games_bp.route('/vendors/<int:vendor_id>/supported-games', methods=['DELETE'])
def delete_supported_game(vendor_id):
    data = request.get_json()
    game_id = data.get('game_id')
    platform = data.get('platform')

    if platform not in [e.value for e in PlatformEnum]:
        return jsonify({'message': 'Invalid platform.'}), 400

    try:
        SupportedGameService.remove_supported_game(
            vendor_id, game_id, platform
        )
        return jsonify({'message': 'Supported game removed'}), 200
    except ValueError as ve:
        return jsonify({'message': str(ve)}), 404

# List all supported games for a vendor
@vendor_games_bp.route('/vendors/<int:vendor_id>/supported-games', methods=['GET'])
def list_supported_games(vendor_id):
    supported = SupportedGameService.list_vendor_supported_games(vendor_id)
    return jsonify({
        'supported_games': [
            {
                'id': sg.id,
                'game_id': sg.game_id,
                'game_name': sg.game.name,
                'platform': sg.platform,
                'is_famous': sg.is_famous
            } for sg in supported
        ]
    }), 200

# List all vendors for a given game (and optional platform)
@vendor_games_bp.route('/games/<int:game_id>/vendors', methods=['GET'])
def list_vendors_for_game(game_id):
    platform = request.args.get('platform')
    if platform and platform not in [e.value for e in PlatformEnum]:
        return jsonify({'message': 'Invalid platform.'}), 400

    supported = SupportedGameService.list_game_vendors(game_id, platform)
    return jsonify({
        'vendors': [
            {
                'vendor_id': sg.vendor_id,
                'vendor_name': sg.vendor.cafe_name,
                'platform': sg.platform
            } for sg in supported
        ]
    }), 200

@vendor_games_bp.route('/games', methods=['POST'])
def create_game():
    data = request.get_json()
    try:
        game = GameService.create_game(
            name=data.get('name'),
            description=data.get('description'),
            release_date=data.get('release_date'),
            developer=data.get('developer'),
            publisher=data.get('publisher'),
            genre=data.get('genre'),
            cover_image_url=data.get('cover_image_url'),
            screenshots=data.get('screenshots'),
            average_rating=data.get('average_rating'),
            trailer_url=data.get('trailer_url'),
            multiplayer=data.get('multiplayer'),
            esrb_rating=data.get('esrb_rating'),
        )
        return jsonify({"message": "Game created", "game": game.to_dict()}), 201
    except Exception as e:
        return jsonify({"message": str(e)}), 400

@vendor_games_bp.route('/games/batch', methods=['POST'])
def create_games_batch():
    data = request.get_json()

    if not isinstance(data, list):
        return jsonify({"message": "Expected a list of games"}), 400

    created_games = []
    errors = []

    for idx, game_data in enumerate(data):
        try:
            game = GameService.create_game(
                name=game_data.get('name'),
                description=game_data.get('description'),
                release_date=game_data.get('release_date'),
                developer=game_data.get('developer'),
                publisher=game_data.get('publisher'),
                genre=game_data.get('genre'),
                cover_image_url=game_data.get('cover_image_url'),
                screenshots=game_data.get('screenshots'),
                average_rating=game_data.get('average_rating'),
                trailer_url=game_data.get('trailer_url'),
                multiplayer=game_data.get('multiplayer'),
                esrb_rating=game_data.get('esrb_rating'),
            )
            created_games.append(game.to_dict())
        except Exception as e:
            errors.append({
                "index": idx,
                "game_name": game_data.get('name'),
                "error": str(e)
            })

    response_payload = {
        "created_games": created_games,
        "errors": errors
    }

    status_code = 201 if not errors else 207  # 207: Multi-Status indicates partial success

    return jsonify(response_payload), status_code

@vendor_games_bp.route('/games', methods=['GET'])
def get_all_games():
    try:
        games = Game.query.all()
        return jsonify({
            "games": [game.to_dict() for game in games]
        }), 200
    except Exception as e:
        return jsonify({"message": f"Failed to fetch games: {str(e)}"}), 500
