import json
import logging
import os
import re
from functools import wraps

from flask import Flask, jsonify, render_template, request, session, redirect, url_for, current_app
from flask_cors import CORS
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Length, Optional
from flask_bcrypt import Bcrypt

# Import configuration
from config import get_config

# Import services
from services import (
    create_user_service,
    create_checklist_service,
    create_submission_service
)

# Import processor for Excel processing
try:
    import processor as processor_module
except ImportError:
    processor_module = None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app(config_name=None):
    """Application factory pattern."""
    app = Flask(__name__)
    
    # Load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    # Initialize extensions
    CORS(app, supports_credentials=True, origins=app.config.get("CORS_ORIGINS", ["http://127.0.0.1:5000"]))
    bcrypt = Bcrypt(app)
    
    # Initialize services
    app.user_service = create_user_service(app.config["USERS_FILE"])
    app.checklist_service = create_checklist_service(
        app.config["SCHEMA_DIR"],
        app.config["TEMPLATE_DIR"]
    )
    app.submission_service = create_submission_service(
        app.config["SUBMISSION_DIR"],
        app.config["ACTIVE_DIR"],
        processor_module
    )
    
    # Register routes
    register_routes(app, bcrypt)
    
    # Error handlers
    register_error_handlers(app)
    
    return app


def register_routes(app, bcrypt):
    """Register all routes."""
    
    # ============ AUTH DECORATORS ============
    
    def login_required(f):
        """Decorator to protect routes that require authentication."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("login_page"))
            return f(*args, **kwargs)
        return decorated_function
    
    def role_required(*allowed_roles):
        """Decorator to protect routes that require specific roles."""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if "user" not in session:
                    return redirect(url_for("login_page"))
                user_role = session["user"].get("role")
                if user_role not in allowed_roles:
                    return jsonify({"error": "Access denied"}), 403
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def build_user_session(user):
        """Build user session dict - DRY helper."""
        return {
            "name": user.get("name"),
            "employee_id": user.get("employee_id"),
            "role": user.get("role"),
            "assigned_checklists": user.get("assigned_checklists", [])
        }
    
    # ============ PAGE ROUTES ============
    
    @app.route("/")
    def home():
        return render_template("login.html")
    
    @app.route("/login", methods=["GET", "POST"])
    def login_page():
        if request.method == "POST":
            data = request.form
            employee_id = data.get("employee_id", "").strip()
            password = data.get("password", "")
            
            user = app.user_service.authenticate(employee_id, password)
            if user:
                session["user"] = build_user_session(user)
                role = user.get("role")
                if role == "Admin":
                    return redirect(url_for("admin_page"))
                elif role == "Supervisor":
                    return redirect(url_for("supervisor_page"))
                else:
                    return redirect(url_for("operator_page"))
            else:
                return render_template("login.html", error="Invalid credentials")
        
        return render_template("login.html")
    
    @app.route("/api/login", methods=["POST"])
    def api_login():
        """API endpoint for login."""
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid request"}), 400
        
        employee_id = data.get("employee_id", "").strip()
        password = data.get("password", "")
        
        if not employee_id or not password:
            return jsonify({"error": "Employee ID and password are required"}), 400
        
        user = app.user_service.authenticate(employee_id, password)
        if not user:
            return jsonify({"error": "Invalid Employee ID or password"}), 401
        
        session["user"] = build_user_session(user)
        
        return jsonify({
            "message": "Login successful",
            "name": user.get("name"),
            "employee_id": user.get("employee_id"),
            "role": user.get("role"),
            "assigned_checklists": user.get("assigned_checklists", [])
        })
    
    @app.route("/logout")
    def logout():
        """Logout route - clears session."""
        session.clear()
        return redirect(url_for("login_page"))
    
    @app.route("/register", methods=["GET", "POST"])
    def register_page():
        if request.method == "POST":
            data = request.form
            name = data.get("name", "").strip()
            employee_id = data.get("employee_id", "").strip()
            password = data.get("password", "")
            role = data.get("role", "Operator")
            assigned = data.getlist("assigned_checklists")
            
            if not name or not employee_id or not password:
                return render_template("register.html", error="All fields required")
            
            result = app.user_service.create_user(
                name, employee_id, password, role, assigned
            )
            
            if result:
                return render_template("register.html", success="Registered successfully!")
            else:
                return render_template("register.html", error="Employee ID already exists")
        
        return render_template("register.html")
    
    @app.route("/api/register", methods=["POST"])
    def api_register():
        """API endpoint for registration."""
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid request"}), 400
        
        name = data.get("name", "").strip()
        employee_id = data.get("employee_id", "").strip()
        password = data.get("password", "")
        role = data.get("role", "Operator")
        assigned_checklists = data.get("assigned_checklists", [])
        
        if not name or not employee_id or not password:
            return jsonify({"error": "Name, Employee ID, and password are required"}), 400
        
        result = app.user_service.create_user(
            name, employee_id, password, role, assigned_checklists
        )
        
        if result:
            return jsonify({
                "message": "Registration successful",
                "employee_id": employee_id
            })
        return jsonify({"error": "Employee ID already exists"}), 400
    
    @app.route("/admin")
    @login_required
    @role_required("Admin")
    def admin_page():
        return render_template("admin.html")
    
    @app.route("/supervisor")
    @login_required
    @role_required("Admin", "Supervisor")
    def supervisor_page():
        return render_template("supervisor.html")
    
    @app.route("/operator")
    @login_required
    def operator_page():
        return render_template("operator.html")
    
    @app.route("/forms/<slug>")
    @login_required
    def form_page(slug: str):
        entry = app.checklist_service.get_checklist_by_slug(slug)
        if not entry:
            return "Checklist not found", 404
        return render_template("form.html", checklist_slug=slug, checklist=entry)
    
    @app.route("/dashboard")
    @login_required
    def supervisor_dashboard():
        return render_template("supervisor.html")
    
    # ============ CHECKLIST APIs ============
    
    @app.route("/api/checklists")
    def api_all_checklists():
        return jsonify(app.checklist_service.get_all_checklists())
    
    @app.route("/api/manifest")
    def api_manifest():
        return jsonify(app.checklist_service.get_all_checklists())
    
    @app.route("/api/checklists/<slug>")
    def api_checklist(slug: str):
        schema = app.checklist_service.get_schema(slug)
        if schema is None:
            return jsonify({"error": "Checklist not found"}), 404
        return jsonify(schema)
    
    @app.route("/api/templates/<slug>")
    def api_template(slug: str):
        template = app.checklist_service.get_template(slug)
        return jsonify(template)
    
    @app.route("/api/checklists/<slug>/save", methods=["POST"])
    @login_required
    def save_checklist(slug: str):
        entry = app.checklist_service.get_checklist_by_slug(slug)
        if not entry:
            return jsonify({"error": "Checklist not found"}), 404
        
        payload = request.get_json(silent=True)
        
        # Validate submission
        is_valid, error_msg = app.checklist_service.validate_submission(payload)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        operator_name = session.get("user", {}).get("name", "Unknown")
        operator_id = session.get("user", {}).get("employee_id", "Unknown")
        
        success, error, saved_data = app.submission_service.save_submission(
            slug=slug,
            category=entry.get("category", "General Checklist"),
            payload=payload,
            operator_name=operator_name,
            operator_id=operator_id
        )
        
        if not success:
            return jsonify({"error": f"Failed to save: {error}"}), 500
        
        response = {
            "message": "Checklist saved successfully.",
            "saved_file": saved_data.get("filename") if saved_data else None
        }
        
        if saved_data and not saved_data.get("excel_processed", True):
            response["warning"] = "Saved but Excel processing failed"
        
        return jsonify(response)
    
    # ============ SUPERVISOR APIs ============
    
    @app.route("/api/supervisor/pending")
    def get_pending_submissions():
        return jsonify(app.submission_service.get_pending_submissions())
    
    @app.route("/api/supervisor/preview/<batch_id>/<slug>")
    @login_required
    @role_required("Admin", "Supervisor")
    def preview_excel(batch_id, slug):
        from processor import get_excel_preview
        try:
            preview_data = get_excel_preview(batch_id, slug)
            if preview_data is None:
                return jsonify({"error": "No Excel file found"}), 404
            return jsonify(preview_data)
        except Exception as e:
            logger.error(f"Preview error: {e}")
            return jsonify({"error": f"Preview error: {str(e)}"}), 500
    
    @app.route("/api/checklists/approve", methods=["POST"])
    @login_required
    @role_required("Admin", "Supervisor")
    def approve_checklist():
        data = request.json or {}
        batch = data.get("batch_id")
        seq = data.get("sequence")
        approver = session.get("user", {}).get("name", data.get("approver", "Supervisor"))
        slug = data.get("slug")
        
        template_name = app.config.get("WORKBOOK_MAP", {}).get(slug, "FMS.xlsx")
        
        if not batch or not seq or not slug:
            return jsonify({"error": "Missing required fields"}), 400
        
        try:
            from processor import add_supervisor_approval
            result = add_supervisor_approval(batch, seq, approver, slug, template_name)
            
            if "Error" in result:
                return jsonify({"error": result}), 500
                
            return jsonify({"message": result})
        except Exception as e:
            logger.error(f"Approval error: {e}")
            return jsonify({"error": f"Approval failed: {str(e)}"}), 500


def register_error_handlers(app):
    """Register error handlers."""
    
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request"}), 400
    
    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized"}), 401
    
    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "Forbidden"}), 403
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal error: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ============ APP INITIALIZATION ============

# Workaround for older Werkzeug versions
try:
    import werkzeug
    if not hasattr(werkzeug, "__version__"):
        werkzeug.__version__ = "3"
except ImportError:
    pass

# Add WORKBOOK_MAP to config
WORKBOOK_MAP = {
    "fms": "FMS.xlsx",
    "fms_checklist": "FMS.xlsx",
    "7_fms": "FMS.xlsx",
    "fan_motor_assembly_balancing": "FanMotorAB.xlsx",
    "5_fan_motor_assembly": "FanMotorAB.xlsx",
    "leak_testing": "LeakTesting.xlsx",
    "2_dlt": "LeakTesting.xlsx",
    "module_assembly_testing": "ModuleAssembly.xlsx",
    "3_module_assly": "ModuleAssembly.xlsx",
    "wheel_crimping": "Wheel crimping.xlsx",
    "1_ep6_crimping_startup": "1. EP6 CRIMPING STARTUP.xlsx",
    "1b_clinching": "1B. CLINCHING.xlsx",
    "4_ep6_final_testing_startup": "4. EP6 FINAL TESTING STARTUP.xlsx",
    "6_balancing": "6. BALANCING.xlsx",
    "8_ep6_firewall_startup": "8. EP6 FIREWALL STARTUP.xlsx",
}

if __name__ == "__main__":
    app = create_app()
    app.config["WORKBOOK_MAP"] = WORKBOOK_MAP
    app.run(host="127.0.0.1", port=5000, debug=True)