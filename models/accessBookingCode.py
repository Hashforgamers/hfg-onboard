from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from . import db

class AccessBookingCode(db.Model):
    __tablename__ = 'access_booking_codes'

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey('bookings.id'), nullable=False)
    access_code = Column(String(50), unique=True, nullable=False)

    booking = relationship('Booking', backref='access_code')
