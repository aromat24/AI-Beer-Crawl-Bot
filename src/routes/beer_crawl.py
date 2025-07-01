from flask import Blueprint, request, jsonify
from ..models.beer_crawl import db, UserPreferences, Bar, CrawlGroup, GroupMember, CrawlSession, GroupStatus
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
        db.session.rollback()
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
        
        # Check if user is already in an active group
        existing_membership = GroupMember.query.join(CrawlGroup).filter(
            GroupMember.user_preferences_id == user.id,
            CrawlGroup.status.in_([GroupStatus.FORMING, GroupStatus.ACTIVE])
        ).first()
        
        if existing_membership:
            return jsonify({
                'group': existing_membership.group.to_dict(),
                'ready_to_start': existing_membership.group.current_members >= existing_membership.group.max_members,
                'message': 'User already in a group'
            }), 200
        
        # Find existing group in same area that's still forming
        available_group = CrawlGroup.query.filter_by(
            area=user.preferred_area,
            status=GroupStatus.FORMING
        ).filter(
            CrawlGroup.current_members < CrawlGroup.max_members
        ).first()
        
        if available_group:
            # Join existing group
            member = GroupMember(
                group_id=available_group.id,
                user_preferences_id=user.id
            )
            db.session.add(member)
            
            available_group.current_members += 1
            
            db.session.commit()
            
            ready_to_start = available_group.current_members >= available_group.max_members
            
            return jsonify({
                'group': available_group.to_dict(),
                'ready_to_start': ready_to_start
            }), 200
        
        else:
            # Create new group
            new_group = CrawlGroup(
                area=user.preferred_area,
                max_members=MAX_GROUP_SIZE,
                current_members=1,
                meeting_time=datetime.now() + timedelta(hours=1)  # Default 1 hour from now
            )
            db.session.add(new_group)
            db.session.flush()  # Get the ID
            
            # Add user as first member and admin
            member = GroupMember(
                group_id=new_group.id,
                user_preferences_id=user.id,
                is_admin=True
            )
            db.session.add(member)
            
            db.session.commit()
            
            return jsonify({
                'group': new_group.to_dict(),
                'ready_to_start': False
            }), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@beer_crawl_bp.route('/groups/<int:group_id>/start', methods=['POST'])
def start_group(group_id):
    """Start a group crawl"""
    try:
        group = CrawlGroup.query.get_or_404(group_id)
        
        if group.status != GroupStatus.FORMING:
            return jsonify({'error': 'Group cannot be started'}), 400
            
        if group.current_members < MIN_GROUP_SIZE:  # Use configurable minimum
            return jsonify({'error': f'Not enough members to start (need at least {MIN_GROUP_SIZE})'}), 400
        
        # Get bars in the area
        bars = Bar.query.filter_by(area=group.area, is_active=True).all()
        if len(bars) < 3:
            return jsonify({'error': 'Not enough bars in area'}), 400
        
        # Select random bars for the crawl
        selected_bars = random.sample(bars, min(5, len(bars)))
        
        # Create crawl sessions
        for i, bar in enumerate(selected_bars):
            session = CrawlSession(
                group_id=group.id,
                bar_id=bar.id,
                order_in_crawl=i + 1,
                is_current=(i == 0)  # First bar is current
            )
            db.session.add(session)
        
        # Update group status
        group.status = GroupStatus.ACTIVE
        group.start_time = datetime.now()
        
        db.session.commit()
        
        # Return first bar info
        first_session = CrawlSession.query.filter_by(
            group_id=group.id, 
            order_in_crawl=1
        ).first()
        
        return jsonify({
            'group': group.to_dict(),
            'first_bar': first_session.bar.to_dict() if first_session else None,
            'meeting_time': group.meeting_time.isoformat() if group.meeting_time else None,
            'map_link': f"https://maps.google.com/?q={first_session.bar.latitude},{first_session.bar.longitude}" if first_session and first_session.bar.latitude else None
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@beer_crawl_bp.route('/groups/<int:group_id>/next-bar', methods=['POST'])
def next_bar(group_id):
    """Move to next bar in crawl"""
    try:
        group = CrawlGroup.query.get_or_404(group_id)
        
        if group.status != GroupStatus.ACTIVE:
            return jsonify({'error': 'Group is not active'}), 400
        
        # Get current session
        current_session = CrawlSession.query.filter_by(
            group_id=group.id,
            is_current=True
        ).first()
        
        if not current_session:
            return jsonify({'error': 'No current session found'}), 400
        
        # Mark current session as ended
        current_session.is_current = False
        current_session.end_time = datetime.now()
        
        # Get next session
        next_session = CrawlSession.query.filter_by(
            group_id=group.id,
            order_in_crawl=current_session.order_in_crawl + 1
        ).first()
        
        if next_session:
            # Move to next bar
            next_session.is_current = True
            next_session.start_time = datetime.now()
            
            db.session.commit()
            
            return jsonify({
                'bar': next_session.bar.to_dict(),
                'meeting_time': (datetime.now() + timedelta(minutes=15)).isoformat(),
                'map_link': f"https://maps.google.com/?q={next_session.bar.latitude},{next_session.bar.longitude}" if next_session.bar.latitude else None,
                'order_in_crawl': next_session.order_in_crawl
            }), 200
        else:
            # No more bars, end the crawl
            group.status = GroupStatus.COMPLETED
            group.end_time = datetime.now()
            
            db.session.commit()
            
            return jsonify({
                'message': 'Crawl completed',
                'group': group.to_dict()
            }), 200
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@beer_crawl_bp.route('/groups/<int:group_id>/status', methods=['GET'])
def group_status(group_id):
    """Get group status"""
    try:
        group = CrawlGroup.query.get_or_404(group_id)
        
        # Get current session
        current_session = CrawlSession.query.filter_by(
            group_id=group.id,
            is_current=True
        ).first()
        
        return jsonify({
            'group': group.to_dict(),
            'current_session': current_session.to_dict() if current_session else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@beer_crawl_bp.route('/groups/<int:group_id>/end', methods=['POST'])
def end_group(group_id):
    """End a group crawl"""
    try:
        group = CrawlGroup.query.get_or_404(group_id)
        
        # Mark current session as ended
        current_session = CrawlSession.query.filter_by(
            group_id=group.id,
            is_current=True
        ).first()
        
        if current_session:
            current_session.is_current = False
            current_session.end_time = datetime.now()
        
        # Update group status
        group.status = GroupStatus.COMPLETED
        group.end_time = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Group ended successfully',
            'group': group.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@beer_crawl_bp.route('/groups', methods=['GET'])
def get_groups():
    """Get groups with optional filtering"""
    try:
        status = request.args.get('status')
        area = request.args.get('area')
        
        query = CrawlGroup.query
        
        if status:
            if status == 'active':
                query = query.filter(CrawlGroup.status.in_([GroupStatus.FORMING, GroupStatus.ACTIVE]))
            else:
                query = query.filter_by(status=GroupStatus(status))
        
        if area:
            query = query.filter_by(area=area)
            
        groups = query.all()
        
        return jsonify([group.to_dict() for group in groups]), 200
        
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
