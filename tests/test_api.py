"""
Test suite for the Mergington High School API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities
import copy


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original activities
    original = copy.deepcopy(activities)
    
    # Reset to a clean state with test data
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 2,  # Small capacity for testing full activity
            "participants": ["john@mergington.edu"]
        }
    })
    
    yield
    
    # Restore original after test
    activities.clear()
    activities.update(original)


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_index(self, client):
        """Test that root path redirects to static index page"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_activity_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)
    
    def test_activity_participants_count(self, client):
        """Test that participants are returned correctly"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert len(chess_club["participants"]) == 2
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_duplicate_participant(self, client):
        """Test signing up a student who is already registered"""
        # First signup
        response1 = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Attempt duplicate signup
        response2 = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_full_activity(self, client):
        """Test signup when activity is at max capacity"""
        # Fill up the Gym Class (max 2, currently has 1)
        response1 = client.post(
            "/activities/Gym Class/signup?email=student1@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Try to add one more when full
        response2 = client.post(
            "/activities/Gym Class/signup?email=student2@mergington.edu"
        )
        assert response2.status_code == 400
        assert "full" in response2.json()["detail"].lower()
    
    def test_signup_with_special_characters_in_name(self, client):
        """Test signup with URL encoding for activity name"""
        # Create activity with space (which gets URL encoded)
        response = client.post(
            "/activities/Programming%20Class/signup?email=coder@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify signup worked
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "coder@mergington.edu" in activities_data["Programming Class"]["participants"]


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "michael@mergington.edu" in data["message"]
        assert "Removed" in data["message"] or "removed" in data["message"].lower()
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_not_signed_up(self, client):
        """Test unregistering a student who isn't signed up"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notsignedup@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
    
    def test_unregister_and_signup_again(self, client):
        """Test that a student can sign up again after unregistering"""
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # Unregister
        response1 = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response1.status_code == 200
        
        # Sign up again
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify they're back in the list
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity]["participants"]


class TestIntegrationScenarios:
    """Integration tests for complex user scenarios"""
    
    def test_multiple_students_signup_and_unregister(self, client):
        """Test multiple students signing up and unregistering"""
        activity = "Programming Class"
        
        # Initial state
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Sign up 3 students
        students = [
            "alice@mergington.edu",
            "bob@mergington.edu",
            "charlie@mergington.edu"
        ]
        
        for student in students:
            response = client.post(f"/activities/{activity}/signup?email={student}")
            assert response.status_code == 200
        
        # Verify all are signed up
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        assert len(participants) == initial_count + 3
        for student in students:
            assert student in participants
        
        # Unregister one student
        response = client.delete(f"/activities/{activity}/unregister?email={students[1]}")
        assert response.status_code == 200
        
        # Verify the count decreased
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        assert len(participants) == initial_count + 2
        assert students[1] not in participants
    
    def test_activity_capacity_management(self, client):
        """Test that activity capacity is properly enforced"""
        activity = "Gym Class"
        
        # Get current state (should have 1 participant, max 2)
        response = client.get("/activities")
        data = response.json()[activity]
        current_count = len(data["participants"])
        max_capacity = data["max_participants"]
        spots_left = max_capacity - current_count
        
        # Fill remaining spots
        for i in range(spots_left):
            response = client.post(
                f"/activities/{activity}/signup?email=student{i}@mergington.edu"
            )
            assert response.status_code == 200
        
        # Verify it's now full
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        assert len(participants) == max_capacity
        
        # Try to add one more (should fail)
        response = client.post(
            f"/activities/{activity}/signup?email=overflow@mergington.edu"
        )
        assert response.status_code == 400
        
        # Unregister someone
        response = client.delete(
            f"/activities/{activity}/unregister?email={participants[0]}"
        )
        assert response.status_code == 200
        
        # Now there should be space again
        response = client.post(
            f"/activities/{activity}/signup?email=nowworks@mergington.edu"
        )
        assert response.status_code == 200
