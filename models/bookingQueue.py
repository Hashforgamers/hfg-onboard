from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from . import db

class BookingQueue(db.Model):
    __tablename__ = 'booking_queue'

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=True)
    console_id = Column(Integer, nullable=False)
    game_id = Column(Integer, ForeignKey('available_games.id'), nullable=False)
    vendor_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=True)
    status = Column(String(20), default='queued')  # queued, started, completed
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)

    # Relationships
    booking = relationship('Booking', backref='queue_entries')
    game = relationship('AvailableGame', backref='queue_entries')
