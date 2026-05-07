import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SubmissionService:
    """Service layer for handling checklist submissions."""
    
    def __init__(self, submission_dir: Path, active_dir: Path, processor_module=None):
        self._submission_dir = submission_dir
        self._active_dir = active_dir
        self._processor = processor_module
    
    def save_submission(self, slug: str, category: str, payload: dict,
                       operator_name: str, operator_id: str) -> tuple[bool, str, Optional[dict]]:
        """
        Save a checklist submission.
        
        Returns: (success, error_message, saved_data)
        """
        try:
            # Create directory
            cat_slug = self._sanitize_filename_part(category, "general_checklist")
            checklist_dir = self._submission_dir / cat_slug / slug
            checklist_dir.mkdir(parents=True, exist_ok=True)
            self._active_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract metadata
            shift = payload.get("metadata", {}).get("shift", "no_shift")
            saved_at = datetime.now()
            
            # Generate batch number
            submission_count = sum(
                1 for path in checklist_dir.glob("*.json") 
                if path.is_file() and not path.name.startswith("~$")
            )
            next_checklist_index = submission_count + 1
            batch_no = ((next_checklist_index - 1) // 6) + 1
            checklist_no = ((next_checklist_index - 1) % 6) + 1
            
            # Build filename
            sanitized_shift = self._sanitize_filename_part(shift, "no_shift").upper()
            sanitized_operator = self._sanitize_filename_part(operator_name, "unknown")
            timestamp = saved_at.strftime("%Y%m%d_%H%M%S")
            
            filename = f"B{batch_no:03d}_({checklist_no})_{slug}_{sanitized_shift}_{sanitized_operator}_{timestamp}.json"
            
            # Add operator info to payload
            if "summary" not in payload:
                payload["summary"] = {}
            
            payload["summary"]["set_up_done_by"] = operator_name
            payload["summary"]["set_up_done_by_oe"] = f"{operator_name} ({operator_id})"
            payload["summary"]["submit_time"] = saved_at.strftime("%Y-%m-%d %H:%M:%S")
            payload["summary"]["verify_status"] = "Pending"
            
            # Auto-fill date if not provided
            if "metadata" in payload and not payload["metadata"].get("date"):
                payload["metadata"]["date"] = saved_at.strftime("%Y-%m-%d")
            
            # Save JSON
            save_path = checklist_dir / filename
            save_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            
            saved_data = {
                "filename": filename,
                "batch": f"B{batch_no:03d}",
                "sequence": checklist_no,
                "timestamp": saved_at.isoformat()
            }
            
            # Process to Excel
            if self._processor:
                try:
                    relative_path = f"{cat_slug}/{slug}/{filename}"
                    self._processor.process_submission_to_excel(relative_path)
                    saved_data["excel_processed"] = True
                except Exception as e:
                    logger.error(f"Excel processing failed: {e}")
                    saved_data["excel_processed"] = False
                    saved_data["excel_error"] = str(e)
            
            return True, "", saved_data
            
        except Exception as e:
            logger.error(f"Failed to save submission: {e}")
            return False, str(e), None
    
    def get_pending_submissions(self) -> list[dict]:
        """Get all pending submissions."""
        submissions = []
        
        if not self._submission_dir.exists():
            return submissions
        
        for root, _, files in os.walk(self._submission_dir):
            for filename in files:
                if filename.endswith(".json") and not filename.startswith("~$"):
                    try:
                        parts = filename.split("_")
                        if len(parts) >= 7:
                            current_slug = Path(root).name
                            submissions.append({
                                "filename": filename,
                                "batch": parts[0],
                                "sequence": parts[1].replace("(", "").replace(")", ""),
                                "slug": current_slug,
                                "shift": parts[3],
                                "operator": parts[4],
                                "time": f"{parts[5]} {parts[6].replace('.json', '')}"
                            })
                    except Exception as e:
                        logger.error(f"Failed to parse filename {filename}: {e}")
        
        submissions.sort(key=lambda x: x.get("time", ""), reverse=True)
        return submissions
    
    def _sanitize_filename_part(self, value: str, fallback: str) -> str:
        """Sanitize a string for use in filename."""
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").strip()).strip("_").lower()
        return cleaned or fallback


def create_submission_service(submission_dir: Path, active_dir: Path, 
                             processor_module=None) -> SubmissionService:
    """Factory function to create SubmissionService."""
    return SubmissionService(submission_dir, active_dir, processor_module)