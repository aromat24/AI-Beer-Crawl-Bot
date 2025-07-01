from . import db
from datetime import datetime
from enum import Enum

class GroupStatus(Enum):
    FORMING = "forming"
    ACTIVE = "active" 
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class UserPreferences(db.Model):
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    whatsapp_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    preferred_area = db.Column(db.String(100), nullable=False)
    preferred_group_type = db.Column(db.String(50), default='mixed')
    gender = db.Column(db.String(10))
    age_range = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    group_memberships = db.relationship('GroupMember', back_populates='user_preferences')
    
    def to_dict(self):
        return {
            'id': self.id,
            'whatsapp_number': self.whatsapp_number,
            'preferred_area': self.preferred_area,
            'preferred_group_type': self.preferred_group_type,
            'gender': self.gender,
            'age_range': self.age_range,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Bar(db.Model):
    __tablename__ = 'bars'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    area = db.Column(db.String(100), nullable=False, index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    owner_contact = db.Column(db.String(100))
    capacity = db.Column(db.Integer, default=50)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    crawl_sessions = db.relationship('CrawlSession', back_populates='bar')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'area': self.area,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'owner_contact': self.owner_contact,
            'capacity': self.capacity,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CrawlGroup(db.Model):
    __tablename__ = 'crawl_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    area = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.Enum(GroupStatus), default=GroupStatus.FORMING, index=True)
    max_members = db.Column(db.Integer, default=5)
    current_members = db.Column(db.Integer, default=0)
    whatsapp_group_id = db.Column(db.String(100))
    meeting_time = db.Column(db.DateTime)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = db.relationship('GroupMember', back_populates='group', cascade='all, delete-orphan')
    sessions = db.relationship('CrawlSession', back_populates='group', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'area': self.area,
            'status': self.status.value if self.status else None,
            'max_members': self.max_members,
            'current_members': self.current_members,
            'whatsapp_group_id': self.whatsapp_group_id,
            'meeting_time': self.meeting_time.isoformat() if self.meeting_time else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'members': [member.to_dict() for member in self.members] if hasattr(self, 'members') else []
        }

class GroupMember(db.Model):
    __tablename__ = 'group_members'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('crawl_groups.id'), nullable=False)
    user_preferences_id = db.Column(db.Integer, db.ForeignKey('user_preferences.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Relationships
    group = db.relationship('CrawlGroup', back_populates='members')
    user_preferences = db.relationship('UserPreferences', back_populates='group_memberships')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('group_id', 'user_preferences_id', name='unique_group_member'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'user_preferences_id': self.user_preferences_id,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'is_admin': self.is_admin,
            'user': self.user_preferences.to_dict() if self.user_preferences else None
        }

class CrawlSession(db.Model):
    __tablename__ = 'crawl_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('crawl_groups.id'), nullable=False)
    bar_id = db.Column(db.Integer, db.ForeignKey('bars.id'), nullable=False)
    order_in_crawl = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    is_current = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    group = db.relationship('CrawlGroup', back_populates='sessions')
    bar = db.relationship('Bar', back_populates='crawl_sessions')
    
    # Unique constraint for current session per group
    __table_args__ = (
        db.Index('idx_group_order', 'group_id', 'order_in_crawl'),
        db.Index('idx_group_current', 'group_id', 'is_current'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'bar_id': self.bar_id,
            'order_in_crawl': self.order_in_crawl,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'is_current': self.is_current,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'bar': self.bar.to_dict() if self.bar else None
        }
