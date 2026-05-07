import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional
from flask_bcrypt import Bcrypt

logger = logging.getLogger(__name__)

_bcrypt = None


def get_bcrypt() -> Bcrypt:
    global _bcrypt
    if _bcrypt is None:
        _bcrypt = Bcrypt()
    return _bcrypt


class UserService:
    """Service layer for user management."""
    
    def __init__(self, users_file: Path, bcrypt_instance: Optional[Bcrypt] = None):
        self._users_file = users_file
        self._bcrypt = bcrypt_instance or get_bcrypt()
        self._users_cache = None
    
    def _load_users(self) -> list[dict]:
        """Load users from file with caching."""
        if self._users_cache is None:
            if self._users_file.exists():
                try:
                    self._users_cache = json.loads(
                        self._users_file.read_text(encoding="utf-8")
                    )
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Failed to load users: {e}")
                    self._users_cache = []
            else:
                self._users_cache = []
        return self._users_cache
    
    def _save_users(self, users: list[dict]) -> bool:
        """Save users to file."""
        try:
            self._users_file.write_text(
                json.dumps(users, indent=2),
                encoding="utf-8"
            )
            self._users_cache = users
            return True
        except IOError as e:
            logger.error(f"Failed to save users: {e}")
            return False
    
    def invalidate_cache(self):
        """Invalidate users cache."""
        self._users_cache = None
    
    def authenticate(self, employee_id: str, password: str) -> Optional[dict]:
        """Authenticate user with employee_id and password."""
        if not employee_id or not password:
            return None
        
        users = self._load_users()
        for user in users:
            if user.get("employee_id") == employee_id:
                stored_hash = user.get("password_hash") or user.get("password")
                if self._bcrypt.check_password_hash(stored_hash, password):
                    return self._serialize_user(user)
                # Fallback for old plaintext passwords (migration)
                if user.get("password") == password:
                    return self._serialize_user(user)
        return None
    
    def get_user_by_id(self, employee_id: str) -> Optional[dict]:
        """Get user by employee_id."""
        users = self._load_users()
        for user in users:
            if user.get("employee_id") == employee_id:
                return self._serialize_user(user)
        return None
    
    def create_user(self, name: str, employee_id: str, password: str, 
                    role: str = "Operator", assigned_checklists: list = None) -> Optional[dict]:
        """Create a new user with hashed password."""
        if not name or not employee_id or not password:
            return None
        
        users = self._load_users()
        
        # Check if user exists
        if any(u.get("employee_id") == employee_id for u in users):
            return None
        
        # Hash password
        password_hash = self._bcrypt.generate_password_hash(password).decode("utf-8")
        
        new_user = {
            "name": name,
            "employee_id": employee_id,
            "password_hash": password_hash,
            "role": role,
            "assigned_checklists": assigned_checklists or []
        }
        
        users.append(new_user)
        
        if self._save_users(users):
            return self._serialize_user(new_user)
        return None
    
    def _serialize_user(self, user: dict) -> dict:
        """Remove sensitive data from user dict."""
        serialized = user.copy()
        serialized.pop("password", None)
        serialized.pop("password_hash", None)
        return serialized


def create_user_service(users_file: Path) -> UserService:
    """Factory function to create UserService."""
    return UserService(users_file)