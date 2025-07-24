from models.game import Game
from db.extensions import db
from datetime import datetime

class GameService:
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
