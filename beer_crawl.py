from flask import Blueprint, request, jsonify
from src.models.beer_crawl import db, UserPreferences, Bar, CrawlGroup, GroupMember, CrawlSession
from datetime import datetime, timedelta
import random
import os

# Group size configuration
MIN_GROUP_SIZE = int(os.environ.get('MIN_GROUP_SIZE', 3))
MAX_GROUP_SIZE = int(os.environ.get('MAX_GROUP_SIZE', 5))

beer_crawl_bp = Blueprint('beer_crawl', __name__)

@beer_crawl_bp.route('/signup', methods=['POST'])
def signup():
    """User signup with preferences"""
    try:
        data = request.get_json()
        
        # Check if user already exists
        existing_user = UserPreferences.query.filter_by(
            whatsapp_number=data.get('whatsapp_number')
        ).first()
        
        if existing_user:
            return jsonify({'error': 'User already exists'}), 400
        
        user = UserPreferences(
            whatsapp_number=data.get('whatsapp_number'),
            preferred_area=data.get('preferred_area'),
            preferred_group_type=data.get('preferred_group_type'),
            gender=data.get('gender'),
            age_range=data.get('age_range')
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@beer_crawl_bp.route('/find-group', methods=['POST'])
def find_group():
    """Find or create a group for the user"""
    try:
        data = request.get_json()
        whatsapp_number = data.get('whatsapp_number')
        
        user = UserPreferences.query.filter_by(whatsapp_number=whatsapp_number).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Look for existing groups that match user preferences
        matching_groups = CrawlGroup.query.filter_by(
            group_type=user.preferred_group_type,
            area=user.preferred_area,
            status='forming'
        ).filter(CrawlGroup.current_members < CrawlGroup.max_members).all()
        
        if matching_groups:
            # Join existing group
            group = matching_groups[0]
            
            # Check if user is already in this group
            existing_membership = GroupMember.query.filter_by(
                group_id=group.id,
                user_id=user.id,
                is_active=True
            ).first()
            
            if not existing_membership:
                member = GroupMember(group_id=group.id, user_id=user.id)
                group.current_members += 1
                db.session.add(member)
                db.session.commit()
        else:
            # Create new group
            group = CrawlGroup(
                group_type=user.preferred_group_type,
                area=user.preferred_area,
                current_members=1
            )
            db.session.add(group)
            db.session.flush()  # Get the group ID
            
            member = GroupMember(group_id=group.id, user_id=user.id)
            db.session.add(member)
            db.session.commit()
        
        return jsonify({
            'message': f'Found group with {group.current_members} members',
            'group': group.to_dict(),
            'ready_to_start': group.current_members >= MIN_GROUP_SIZE
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@beer_crawl_bp.route('/groups/<int:group_id>/start', methods=['POST'])
def start_group(group_id):
    """Start the crawl for a group"""
    try:
        group = CrawlGroup.query.get_or_404(group_id)
        
        if group.current_members < MIN_GROUP_SIZE:
            return jsonify({'error': f'Need at least {MIN_GROUP_SIZE} members to start'}), 400
        
        # Find bars in the area
        bars = Bar.query.filter_by(area=group.area, is_active=True).all()
        if not bars:
            return jsonify({'error': 'No bars available in this area'}), 400
        
        # Select first bar randomly
        first_bar = random.choice(bars)
        
        # Update group status
        group.status = 'active'
        group.start_time = datetime.utcnow()
        group.current_bar_id = first_bar.id
        
        # Create first session
        session = CrawlSession(
            group_id=group.id,
            bar_id=first_bar.id,
            start_time=datetime.utcnow() + timedelta(minutes=30),  # 30 min from now
            status='scheduled'
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'message': 'Group started successfully',
            'group': group.to_dict(),
            'first_bar': first_bar.to_dict(),
            'meeting_time': session.start_time.isoformat(),
            'map_link': f'https://maps.google.com/?q={first_bar.latitude},{first_bar.longitude}'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@beer_crawl_bp.route('/groups/<int:group_id>/next-bar', methods=['POST'])
def next_bar(group_id):
    """Move group to next bar"""
    try:
        group = CrawlGroup.query.get_or_404(group_id)
        
        # Get bars in the area excluding current bar
        bars = Bar.query.filter_by(area=group.area, is_active=True).filter(
            Bar.id != group.current_bar_id
        ).all()
        
        if not bars:
            return jsonify({'error': 'No more bars available'}), 400
        
        # Select next bar
        next_bar = random.choice(bars)
        group.current_bar_id = next_bar.id
        
        # Create next session
        session = CrawlSession(
            group_id=group.id,
            bar_id=next_bar.id,
            start_time=datetime.utcnow() + timedelta(hours=1),  # 1 hour from now
            status='scheduled'
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'message': 'Next bar selected',
            'bar': next_bar.to_dict(),
            'meeting_time': session.start_time.isoformat(),
            'map_link': f'https://maps.google.com/?q={next_bar.latitude},{next_bar.longitude}'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@beer_crawl_bp.route('/bars', methods=['GET'])
def get_bars():
    """Get all bars"""
    try:
        area = request.args.get('area')
        query = Bar.query.filter_by(is_active=True)
        
        if area:
            query = query.filter_by(area=area)
        
        bars = query.all()
        return jsonify([bar.to_dict() for bar in bars]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@beer_crawl_bp.route('/bars', methods=['POST'])
def add_bar():
    """Add a new bar (for bar owners)"""
    try:
        data = request.get_json()
        
        bar = Bar(
            name=data.get('name'),
            address=data.get('address'),
            area=data.get('area'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            owner_contact=data.get('owner_contact')
        )
        
        db.session.add(bar)
        db.session.commit()
        
        return jsonify({
            'message': 'Bar added successfully',
            'bar': bar.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@beer_crawl_bp.route('/groups/<int:group_id>/status', methods=['GET'])
def get_group_status(group_id):
    """Get current group status"""
    try:
        group = CrawlGroup.query.get_or_404(group_id)
        
        # Get current session
        current_session = CrawlSession.query.filter_by(
            group_id=group_id,
            status='active'
        ).first()
        
        if not current_session:
            current_session = CrawlSession.query.filter_by(
                group_id=group_id,
                status='scheduled'
            ).order_by(CrawlSession.start_time).first()
        
        return jsonify({
            'group': group.to_dict(),
            'current_session': current_session.to_dict() if current_session else None,
            'members_count': group.current_members
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@beer_crawl_bp.route('/groups/<int:group_id>/end', methods=['POST'])
def end_group(group_id):
    """End the crawl session"""
    try:
        group = CrawlGroup.query.get_or_404(group_id)
        group.status = 'completed'
        
        # End all active sessions
        active_sessions = CrawlSession.query.filter_by(
            group_id=group_id,
            status='active'
        ).all()
        
        for session in active_sessions:
            session.status = 'completed'
            session.end_time = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'message': 'Group session ended'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

