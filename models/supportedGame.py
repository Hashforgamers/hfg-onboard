# models/supportedGame.py
from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from db.extensions import db
from sqlalchemy import Enum
import enum

class PlatformEnum(enum.Enum):
    pc = 'pc'
    ps = 'ps'
    vr = 'vr'
    xbox = 'xbox'

class SupportedGame(db.Model):
    __tablename__ = 'supported_games'
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=False)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    platform = Column(Enum(PlatformEnum), nullable=False)
    is_famous = Column(Boolean, default=False)

    vendor = relationship('Vendor', back_populates='supported_games')
    game = relationship('Game', back_populates='supported_by')
