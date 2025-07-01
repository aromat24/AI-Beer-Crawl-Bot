import pytest
import json
from src.models.beer_crawl import UserPreferences, Bar, CrawlGroup, GroupMember, CrawlSession, GroupStatus
from src.models import db

class TestBeerCrawlAPI:
    """Test suite for Beer Crawl API endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'version' in data

    def test_user_signup(self, client, auth_headers):
        """Test user signup endpoint."""
        user_data = {
            'whatsapp_number': '+1234567890',
            'preferred_area': 'northern quarter',
            'preferred_group_type': 'mixed',
            'gender': 'male',
            'age_range': '25-35'
        }
        
        response = client.post('/api/beer-crawl/signup', 
                             data=json.dumps(user_data), 
                             headers=auth_headers)
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['message'] == 'User registered successfully'
        assert data['user']['whatsapp_number'] == user_data['whatsapp_number']
        
    def test_user_signup_duplicate(self, client, auth_headers):
        """Test duplicate user signup."""
        user_data = {
            'whatsapp_number': '+1234567890',
            'preferred_area': 'northern quarter',
            'preferred_group_type': 'mixed'
        }
        
        # First signup
        client.post('/api/beer-crawl/signup', 
                   data=json.dumps(user_data), 
                   headers=auth_headers)
        
        # Second signup (should fail)
        response = client.post('/api/beer-crawl/signup', 
                             data=json.dumps(user_data), 
                             headers=auth_headers)
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'already exists' in data['error']

    def test_find_group_new_user(self, client, auth_headers):
        """Test finding group for new user (should create new group)."""
        # First, signup a user
        user_data = {
            'whatsapp_number': '+1234567890',
            'preferred_area': 'northern quarter',
            'preferred_group_type': 'mixed'
        }
        
        client.post('/api/beer-crawl/signup', 
                   data=json.dumps(user_data), 
                   headers=auth_headers)
        
        # Then find group
        response = client.post('/api/beer-crawl/find-group', 
                             data=json.dumps({'whatsapp_number': '+1234567890'}), 
                             headers=auth_headers)
        
        assert response.status_code == 201  # New group created
        data = json.loads(response.data)
        assert data['group']['area'] == 'northern quarter'
        assert data['group']['current_members'] == 1
        assert data['ready_to_start'] == False

    def test_find_group_nonexistent_user(self, client, auth_headers):
        """Test finding group for non-existent user."""
        response = client.post('/api/beer-crawl/find-group', 
                             data=json.dumps({'whatsapp_number': '+9999999999'}), 
                             headers=auth_headers)
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'not found' in data['error']

    def test_group_formation(self, client, auth_headers, app):
        """Test complete group formation process."""
        with app.app_context():
            # Create multiple users
            users = [
                {'whatsapp_number': f'+12345678{i:02d}', 'preferred_area': 'northern quarter'}
                for i in range(5)
            ]
            
            group_id = None
            
            for i, user_data in enumerate(users):
                # Signup user
                client.post('/api/beer-crawl/signup', 
                           data=json.dumps(user_data), 
                           headers=auth_headers)
                
                # Find group
                response = client.post('/api/beer-crawl/find-group', 
                                     data=json.dumps({'whatsapp_number': user_data['whatsapp_number']}), 
                                     headers=auth_headers)
                
                data = json.loads(response.data)
                
                if i == 0:
                    # First user creates new group
                    assert response.status_code == 201
                    group_id = data['group']['id']
                else:
                    # Subsequent users join existing group
                    assert response.status_code == 200
                    assert data['group']['id'] == group_id
                
                # Check if group is ready to start
                expected_members = i + 1
                assert data['group']['current_members'] == expected_members
                
                if expected_members >= 5:
                    assert data['ready_to_start'] == True
                else:
                    assert data['ready_to_start'] == False

    def test_start_group(self, client, auth_headers, app):
        """Test starting a group crawl."""
        with app.app_context():
            # Create sample bars
            bars = [
                Bar(name=f"Bar {i}", address=f"Address {i}", area="northern quarter", 
                    latitude=53.4839 + i*0.001, longitude=-2.2374 + i*0.001)
                for i in range(5)
            ]
            
            for bar in bars:
                db.session.add(bar)
            db.session.commit()
            
            # Create a group with enough members
            group = CrawlGroup(area="northern quarter", current_members=5, max_members=5)
            db.session.add(group)
            db.session.commit()
            
            # Start the group
            response = client.post(f'/api/beer-crawl/groups/{group.id}/start')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['group']['status'] == 'active'
            assert 'first_bar' in data
            assert 'meeting_time' in data

    def test_group_progression(self, client, auth_headers, app):
        """Test progressing through bars."""
        with app.app_context():
            # Setup group and bars
            bars = [
                Bar(name=f"Bar {i}", address=f"Address {i}", area="northern quarter", 
                    latitude=53.4839 + i*0.001, longitude=-2.2374 + i*0.001)
                for i in range(3)
            ]
            
            for bar in bars:
                db.session.add(bar)
            
            group = CrawlGroup(area="northern quarter", status=GroupStatus.ACTIVE, current_members=5)
            db.session.add(group)
            db.session.flush()
            
            # Create crawl sessions
            for i, bar in enumerate(bars):
                session = CrawlSession(
                    group_id=group.id,
                    bar_id=bar.id,
                    order_in_crawl=i + 1,
                    is_current=(i == 0)
                )
                db.session.add(session)
            
            db.session.commit()
            
            # Progress to next bar
            response = client.post(f'/api/beer-crawl/groups/{group.id}/next-bar')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'bar' in data
            assert data['order_in_crawl'] == 2

    def test_get_bars(self, client, app):
        """Test getting bars."""
        with app.app_context():
            # Create sample bars
            bars = [
                Bar(name="Northern Bar", address="NQ Address", area="northern quarter"),
                Bar(name="City Bar", address="City Address", area="city centre"),
            ]
            
            for bar in bars:
                db.session.add(bar)
            db.session.commit()
            
            # Get all bars
            response = client.get('/api/beer-crawl/bars')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data) >= 2
            
            # Get bars by area
            response = client.get('/api/beer-crawl/bars?area=northern quarter')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert all(bar['area'] == 'northern quarter' for bar in data)

    def test_get_groups(self, client, app):
        """Test getting groups."""
        with app.app_context():
            # Create sample groups
            groups = [
                CrawlGroup(area="northern quarter", status=GroupStatus.FORMING),
                CrawlGroup(area="city centre", status=GroupStatus.ACTIVE),
                CrawlGroup(area="deansgate", status=GroupStatus.COMPLETED),
            ]
            
            for group in groups:
                db.session.add(group)
            db.session.commit()
            
            # Get all groups
            response = client.get('/api/beer-crawl/groups')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data) >= 3
            
            # Get active groups
            response = client.get('/api/beer-crawl/groups?status=active')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data) >= 1
            assert all(group['status'] in ['forming', 'active'] for group in data)
