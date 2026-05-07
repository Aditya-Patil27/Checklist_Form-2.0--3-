import pytest
import json
import tempfile
import os
from pathlib import Path

# Import the application components for testing
import sys
sys.path.insert(0, '.')

from services.user_service import UserService
from services.checklist_service import ChecklistService
from services.submission_service import SubmissionService


class TestUserService:
    """Tests for UserService."""
    
    @pytest.fixture
    def temp_users_file(self):
        """Create a temporary users file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            temp_path = f.name
        yield Path(temp_path)
        os.unlink(temp_path)
    
    def test_create_user(self, temp_users_file):
        """Test user creation with hashed password."""
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        service = UserService(temp_users_file, bcrypt)
        
        user = service.create_user(
            name="Test User",
            employee_id="TEST001",
            password="testpass123",
            role="Operator"
        )
        
        assert user is not None
        assert user["name"] == "Test User"
        assert user["employee_id"] == "TEST001"
        assert user["role"] == "Operator"
    
    def test_authenticate_success(self, temp_users_file):
        """Test successful authentication."""
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        service = UserService(temp_users_file, bcrypt)
        
        service.create_user(
            name="Test User",
            employee_id="TEST001",
            password="testpass123",
            role="Operator"
        )
        
        user = service.authenticate("TEST001", "testpass123")
        assert user is not None
        assert user["employee_id"] == "TEST001"
    
    def test_authenticate_failure(self, temp_users_file):
        """Test failed authentication with wrong password."""
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        service = UserService(temp_users_file, bcrypt)
        
        service.create_user(
            name="Test User",
            employee_id="TEST001",
            password="testpass123",
            role="Operator"
        )
        
        user = service.authenticate("TEST001", "wrongpass")
        assert user is None
    
    def test_duplicate_user(self, temp_users_file):
        """Test that duplicate user creation fails."""
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        service = UserService(temp_users_file, bcrypt)
        
        service.create_user(
            name="Test User",
            employee_id="TEST001",
            password="testpass123",
            role="Operator"
        )
        
        duplicate = service.create_user(
            name="Another User",
            employee_id="TEST001",
            password="pass456",
            role="Operator"
        )
        
        assert duplicate is None


class TestChecklistService:
    """Tests for ChecklistService."""
    
    @pytest.fixture
    def schema_dir(self, tmp_path):
        """Create a temporary schema directory."""
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        
        # Create manifest
        manifest = [
            {"slug": "test-checklist", "title": "Test", "category": "Test"}
        ]
        (schema_dir / "manifest.json").write_text(json.dumps(manifest))
        
        return schema_dir
    
    def test_get_all_checklists(self, schema_dir):
        """Test getting all checklists."""
        service = ChecklistService(schema_dir, schema_dir)
        
        checklists = service.get_all_checklists()
        assert len(checklists) == 1
        assert checklists[0]["slug"] == "test-checklist"
    
    def test_get_checklist_by_slug(self, schema_dir):
        """Test getting checklist by slug."""
        service = ChecklistService(schema_dir, schema_dir)
        
        checklist = service.get_checklist_by_slug("test-checklist")
        assert checklist is not None
        assert checklist["slug"] == "test-checklist"
    
    def test_validate_submission_valid(self, schema_dir):
        """Test validation with valid submission."""
        service = ChecklistService(schema_dir, schema_dir)
        
        valid_payload = {
            "metadata": {"date": "2026-01-01"},
            "sections": [{"title": "Test", "items": []}],
            "summary": {}
        }
        
        is_valid, error = service.validate_submission(valid_payload)
        assert is_valid is True
        assert error == ""
    
    def test_validate_submission_missing_keys(self, schema_dir):
        """Test validation with missing keys."""
        service = ChecklistService(schema_dir, schema_dir)
        
        invalid_payload = {
            "metadata": {"date": "2026-01-01"}
            # Missing "sections" and "summary"
        }
        
        is_valid, error = service.validate_submission(invalid_payload)
        assert is_valid is False
        assert "sections" in error or "summary" in error
    
    def test_validate_submission_empty(self, schema_dir):
        """Test validation with empty payload."""
        service = ChecklistService(schema_dir, schema_dir)
        
        is_valid, error = service.validate_submission({})
        assert is_valid is False


class TestSubmissionService:
    """Tests for SubmissionService."""
    
    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Create temporary directories."""
        submission_dir = tmp_path / "submissions"
        active_dir = tmp_path / "active"
        submission_dir.mkdir()
        active_dir.mkdir()
        return submission_dir, active_dir
    
    def test_save_submission(self, temp_dirs):
        """Test saving a submission."""
        submission_dir, active_dir = temp_dirs
        service = SubmissionService(submission_dir, active_dir)
        
        payload = {
            "metadata": {"date": "2026-01-01", "shift": "A"},
            "sections": [{"title": "Test", "items": []}],
            "summary": {"set_up_done_by": "Test User"}
        }
        
        success, error, saved_data = service.save_submission(
            slug="test",
            category="Test",
            payload=payload,
            operator_name="Test User",
            operator_id="TEST001",
            machine_id="MACH001"
        )
        
        assert success is True
        assert saved_data is not None
        assert "filename" in saved_data
    
    def test_get_pending_submissions(self, temp_dirs):
        """Test getting pending submissions."""
        submission_dir, active_dir = temp_dirs
        
        # Create a test submission file
        test_dir = submission_dir / "test_category" / "test"
        test_dir.mkdir(parents=True)
        (test_dir / "B001_(1)_test_A_user_20260101_120000.json").write_text("{}")
        
        service = SubmissionService(submission_dir, active_dir)
        submissions = service.get_pending_submissions()
        
        assert len(submissions) == 1
        assert submissions[0]["batch"] == "B001"


class TestIntegration:
    """Integration tests for the full application."""
    
    def test_app_creation(self):
        """Test that app can be created."""
        from app import create_app
        app = create_app("testing")
        assert app is not None
        assert app.config["TESTING"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])