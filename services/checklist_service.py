import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ChecklistService:
    """Service layer for checklist management."""
    
    def __init__(self, schema_dir: Path, template_dir: Path):
        self._schema_dir = schema_dir
        self._template_dir = template_dir
        self._manifest_cache = None
    
    def _load_manifest(self) -> list[dict]:
        """Load manifest with caching."""
        if self._manifest_cache is None:
            manifest_path = self._schema_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    self._manifest_cache = json.loads(
                        manifest_path.read_text(encoding="utf-8")
                    )
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Failed to load manifest: {e}")
                    self._manifest_cache = []
            else:
                self._manifest_cache = []
        return self._manifest_cache
    
    def invalidate_cache(self):
        """Invalidate manifest cache."""
        self._manifest_cache = None
    
    @lru_cache(maxsize=32)
    def get_all_checklists(self) -> list[dict]:
        """Get all checklists from manifest."""
        return self._load_manifest()
    
    def get_checklist_by_slug(self, slug: str) -> Optional[dict]:
        """Get a specific checklist by slug."""
        manifest = self._load_manifest()
        for entry in manifest:
            if entry.get("slug") == slug:
                return entry
        return None
    
    def get_schema(self, slug: str) -> Optional[dict]:
        """Get checklist schema."""
        entry = self.get_checklist_by_slug(slug)
        if not entry:
            return None
        
        schema_path = entry.get("schema_path")
        if not schema_path:
            return None
        
        full_path = Path(schema_path)
        if not full_path.is_absolute():
            full_path = self._schema_dir.parent / schema_path
        
        if full_path.exists():
            try:
                return json.loads(full_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load schema for {slug}: {e}")
        return None
    
    def get_template(self, slug: str) -> Optional[dict]:
        """Get checklist template."""
        entry = self.get_checklist_by_slug(slug)
        if not entry:
            return None
        
        template_path = entry.get("template_path")
        if not template_path:
            return {"metadata": {}, "sections": [], "summary": {}}
        
        full_path = Path(template_path)
        if not full_path.is_absolute():
            full_path = self._schema_dir.parent / template_path
        
        if full_path.exists():
            try:
                return json.loads(full_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load template for {slug}: {e}")
        
        return {"metadata": {}, "sections": [], "summary": {}}
    
    def validate_submission(self, payload: dict) -> tuple[bool, str]:
        """Validate checklist submission payload."""
        if not payload:
            return False, "Payload is required"
        
        # Check required top-level keys
        for key in ["metadata", "sections", "summary"]:
            if key not in payload:
                return False, f"Missing required key: {key}"
        
        # Validate metadata
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            return False, "Metadata must be a dictionary"
        
        # Validate sections
        sections = payload.get("sections", [])
        if not isinstance(sections, list):
            return False, "Sections must be a list"
        
        for idx, section in enumerate(sections):
            if not isinstance(section, dict):
                return False, f"Section {idx} must be a dictionary"
            if "title" not in section:
                return False, f"Section {idx} missing title"
            if "items" not in section:
                return False, f"Section {idx} missing items"
        
        # Validate summary
        summary = payload.get("summary", {})
        if not isinstance(summary, dict):
            return False, "Summary must be a dictionary"
        
        return True, ""


def create_checklist_service(schema_dir: Path, template_dir: Path) -> ChecklistService:
    """Factory function to create ChecklistService."""
    return ChecklistService(schema_dir, template_dir)