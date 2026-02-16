# models/availableGame.py
from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from db.extensions import db

# ✅ Define the association table for many-to-many relationship
available_game_console = Table(
    'available_game_console',
    db.Model.metadata,
    Column('available_game_id', Integer, ForeignKey('available_games.id', ondelete='CASCADE'), primary_key=True),
    Column('console_id', Integer, ForeignKey('consoles.id', ondelete='CASCADE'), primary_key=True)
)

class AvailableGame(db.Model):
    __tablename__ = 'available_games'

    # ✅ Add missing columns
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id', ondelete='CASCADE'), nullable=False, index=True)
    game_name = Column(String(100), nullable=False)
    total_slot = Column(Integer, nullable=False)
    single_slot_price = Column(Integer, nullable=False)

    # Relationships
    vendor = relationship('Vendor', back_populates='available_games')
    slots = relationship('Slot', back_populates='available_game', cascade="all, delete-orphan")
    
    # ✅ Add the missing relationship to Console
    consoles = relationship('Console', secondary=available_game_console, back_populates='available_games')

    def __repr__(self):
        return f"<AvailableGame {self.game_name} vendor_id={self.vendor_id}>"
