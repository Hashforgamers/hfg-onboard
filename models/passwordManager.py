from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, foreign
from db.extensions import db
from sqlalchemy.ext.declarative import declared_attr

class PasswordManager(db.Model):
    __tablename__ = 'password_manager'

    id = Column(Integer, primary_key=True)
    userid = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)

    # Parent relationship columns (generic, no ForeignKey constraint)
    parent_id = Column(Integer, nullable=False)
    parent_type = Column(String(50), nullable=False)

    # Polymorphic setup for distinguishing between Vendor and User
    @declared_attr
    def __mapper_args__(cls):
        return {
            'polymorphic_on': cls.parent_type,
            'polymorphic_identity': 'password_manager'
        }

    # Relationships to Vendor and User using polymorphism
    @declared_attr
    def vendor(cls):
        return relationship(
            'Vendor',
            primaryjoin="and_(foreign(PasswordManager.parent_id) == Vendor.id, PasswordManager.parent_type == 'vendor')",
            back_populates='password'
        )

    def __repr__(self):
        return f"PasswordManager(id={self.id}, userid='{self.userid}')"
