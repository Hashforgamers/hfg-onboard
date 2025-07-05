# models/booking.py
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from db.extensions import db
from .accessBookingCode import AccessBookingCode

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    game_id = Column(Integer, nullable=False)
    slot_id = Column(Integer, nullable=False)
    status = db.Column(db.String(20), default='pending_verified')  # New field for verification status
    
    access_code_id = Column(Integer, ForeignKey('access_booking_codes.id'), nullable=True)
    access_code_entry = db.relationship('AccessBookingCode', back_populates='bookings')

    def __repr__(self):
        return f"<Booking user_id={self.user_id} game_id={self.game_id}>"

    def to_dict(self):
        return {
            'booking_id': self.id,
            'user_id': self.user_id,
            'status': self.status,
            'slot': self.slot.to_dict_for_booking() if self.slot else None
        }
