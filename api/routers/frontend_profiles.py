"""
Frontend Profiles Router - FastAPI People/Profile Management

Handles people/entity CRUD operations for the web UI.
Migrated from Flask profiles.py blueprint.

Routes:
- GET /get_people - List all people in current project
- GET /get_person/{person_id} - Get single person
- POST /add_person - Create new person
- POST /update_person/{person_id} - Update person
- POST /delete_person/{person_id} - Delete person
- POST /zip_user_files/{person_id} - Download person files as ZIP
- GET /profile_editor - Profile editor page
- GET /person/{person_id}/explore - File explorer
- POST /person/{person_id}/upload - Upload files
"""

import hashlib
import io
import logging
import os
import re
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates

from api.dependencies import get_neo4j_handler, get_app_config
from api.routers.frontend import get_current_project, PROJECT_ROOT, TEMPLATES_DIR
from neo4j_handler import Neo4jHandler

logger = logging.getLogger("basset_hound.frontend.profiles")

router = APIRouter(tags=["Frontend Profiles"])

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


def is_image_file(filename: str) -> bool:
    """Check if file is an allowed image type."""
    return os.path.splitext(filename)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


# =============================================================================
# People List/Get Routes
# =============================================================================

@router.get("/get_people")
async def get_people(
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
):
    """
    Get all people in the current project.
    """
    project_ctx = get_current_project()

    if not project_ctx["safe_name"]:
        return []

    people = neo4j_handler.get_all_people(project_ctx["safe_name"])
    return people


@router.get("/get_person/{person_id}")
async def get_person(
    person_id: str,
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
):
    """
    Get a single person by ID.
    """
    project_ctx = get_current_project()

    if not project_ctx["safe_name"]:
        raise HTTPException(status_code=404, detail="No project selected")

    person = neo4j_handler.get_person(project_ctx["safe_name"], person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    return person


# =============================================================================
# Person CRUD Routes
# =============================================================================

@router.post("/add_person")
async def add_person(
    request: Request,
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
    config: dict = Depends(get_app_config),
):
    """
    Add a new person to the current project.

    Handles form data with file uploads.
    """
    project_ctx = get_current_project()

    if not project_ctx["safe_name"]:
        return RedirectResponse(url="/", status_code=302)

    # Generate person ID
    person_id = str(uuid4())

    # Prepare person data
    person_data = {
        "id": person_id,
        "created_at": datetime.now().isoformat(),
        "profile": {}
    }

    # Create directories
    person_files_dir = PROJECT_ROOT / "projects" / project_ctx["id"] / "people" / person_id / "files"
    person_reports_dir = PROJECT_ROOT / "projects" / project_ctx["id"] / "people" / person_id / "reports"
    person_files_dir.mkdir(parents=True, exist_ok=True)
    person_reports_dir.mkdir(parents=True, exist_ok=True)

    # Parse form data
    form_data = await request.form()

    # Extract entity_type from form data (default to "person" for backwards compatibility)
    entity_type = form_data.get("entity_type", "person")
    person_data["entity_type"] = entity_type

    # Process form data by section
    for section in config.get("sections", []):
        section_id = section["id"]
        person_data["profile"][section_id] = {}

        for field in section.get("fields", []):
            field_id = field["id"]
            field_key_prefix = f"{section_id}.{field_id}"

            if field.get("type") == "file":
                # Handle file uploads
                stored_files = []
                for key in form_data:
                    if key.startswith(field_key_prefix):
                        uploaded_file = form_data[key]
                        if hasattr(uploaded_file, 'filename') and uploaded_file.filename:
                            # Skip non-image files for profile pictures
                            if section_id == "profile" and field_id == "profile_picture":
                                if not is_image_file(uploaded_file.filename):
                                    continue

                            # Generate unique file ID
                            file_id = hashlib.sha256(os.urandom(32)).hexdigest()[:12]
                            filename = f"{file_id}_{uploaded_file.filename}"

                            file_path = person_files_dir / filename
                            content = await uploaded_file.read()
                            with open(file_path, "wb") as f:
                                f.write(content)

                            file_data = {
                                "id": file_id,
                                "name": uploaded_file.filename,
                                "path": filename,
                                "section_id": section_id,
                                "field_id": field_id,
                                "full_path": str(file_path),
                                "person_id": person_id
                            }
                            stored_files.append(file_data)

                if stored_files:
                    person_data["profile"][section_id][field_id] = stored_files if field.get("multiple") else stored_files[0]
            else:
                # Handle regular form fields
                field_data = _process_field_data(form_data, section_id, field, person_id)
                if field_data is not None:
                    person_data["profile"][section_id][field_id] = field_data

    # Create person in Neo4j
    person = neo4j_handler.create_person(project_ctx["safe_name"], person_data)

    if not person:
        return RedirectResponse(url="/dashboard", status_code=302)

    return RedirectResponse(url="/dashboard", status_code=302)


def _process_field_data(form_data, section_id: str, field: dict, person_id: str = None):
    """Process form field data for a specific field."""
    field_key = f"{section_id}.{field['id']}"
    is_multiple = field.get("multiple", False)

    # Special handling for comment fields
    if field.get("type") == "comment":
        values = [v for k, v in form_data.items() if k == field_key and v.strip()]
        return values if is_multiple else (values[0] if values else None)

    if "components" in field:
        return _process_component_field(form_data, field, field_key, person_id)

    values = [str(v) for k, v in form_data.items() if k.startswith(field_key) and str(v).strip()]
    return values if is_multiple else (values[0] if values else None)


def _process_component_field(form_data, field: dict, field_key: str, person_id: str = None):
    """Process complex component fields."""
    person_id = person_id or "unknown"
    components = field.get("components", [])
    field_instances = defaultdict(dict)

    # Process regular form fields
    for key, value in form_data.items():
        if not key.startswith(field_key):
            continue

        parts = key.split('.')
        if len(parts) < 3:
            continue

        component_part = parts[2]
        match = re.match(r"(\w+)_([0-9]+)(?:\.([0-9]+))?", component_part)
        if not match:
            continue

        component_id = match.group(1)
        field_index = match.group(2)

        value_str = str(value).strip()
        if not value_str:
            continue

        component_cfg = next((c for c in components if c["id"] == component_id), None)
        if not component_cfg:
            continue

        is_multiple = component_cfg.get("multiple", False)

        if is_multiple:
            field_instances[field_index].setdefault(component_id, []).append(value_str)
        else:
            field_instances[field_index][component_id] = value_str

    # Final aggregation
    instances = [entry for entry in field_instances.values() if entry]
    return instances if field.get("multiple") else (instances[0] if instances else None)


@router.post("/update_person/{person_id}")
async def update_person(
    person_id: str,
    request: Request,
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
    config: dict = Depends(get_app_config),
):
    """
    Update an existing person.

    Handles both JSON API requests and form submissions.
    """
    project_ctx = get_current_project()

    if not project_ctx["id"]:
        raise HTTPException(status_code=404, detail="No project ID")
    if not project_ctx["safe_name"]:
        raise HTTPException(status_code=404, detail="No project safe name")

    # Get existing person
    person = neo4j_handler.get_person(project_ctx["safe_name"], person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Handle JSON API requests
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        updated_data = await request.json()
        updated_person = neo4j_handler.update_person(project_ctx["safe_name"], person_id, updated_data)
        return {"success": bool(updated_person)}

    # Handle form submission
    form_data = await request.form()
    updated_data = {"profile": {}}

    # Extract entity_type from form data if provided
    entity_type = form_data.get("entity_type")
    if entity_type:
        updated_data["entity_type"] = entity_type

    for section in config.get("sections", []):
        section_id = section["id"]
        updated_data["profile"][section_id] = {}

        for field in section.get("fields", []):
            field_id = field["id"]
            field_key_prefix = f"{section_id}.{field_id}"

            if field.get("type") == "file":
                # Check for new file uploads
                has_new_files = any(
                    key.startswith(field_key_prefix) and hasattr(form_data[key], 'filename') and form_data[key].filename
                    for key in form_data
                )

                # Keep existing files if no new ones uploaded
                if not has_new_files:
                    existing = person.get("profile", {}).get(section_id, {}).get(field_id)
                    if existing:
                        updated_data["profile"][section_id][field_id] = existing
                    continue

                # Process new file uploads
                stored_files = []
                person_dir = PROJECT_ROOT / "projects" / project_ctx["id"] / "people" / person_id / "files"
                person_dir.mkdir(parents=True, exist_ok=True)

                for key in form_data:
                    if key.startswith(field_key_prefix):
                        uploaded_file = form_data[key]
                        if hasattr(uploaded_file, 'filename') and uploaded_file.filename:
                            # Skip non-image files for profile pictures
                            if section_id == "profile" and field_id == "profile_picture":
                                if not is_image_file(uploaded_file.filename):
                                    continue

                            file_id = hashlib.sha256(os.urandom(32)).hexdigest()[:12]
                            filename = f"{file_id}_{uploaded_file.filename}"
                            file_path = person_dir / filename

                            content = await uploaded_file.read()
                            with open(file_path, "wb") as f:
                                f.write(content)

                            file_data = {
                                "id": file_id,
                                "name": uploaded_file.filename,
                                "path": filename,
                                "section_id": section_id,
                                "field_id": field_id,
                                "full_path": str(file_path),
                                "person_id": person_id
                            }
                            stored_files.append(file_data)

                if stored_files:
                    updated_data["profile"][section_id][field_id] = stored_files if field.get("multiple") else stored_files[0]
            else:
                field_data = _process_field_data(form_data, section_id, field, person_id)
                if field_data is not None:
                    updated_data["profile"][section_id][field_id] = field_data

    # Update person in Neo4j
    updated_person = neo4j_handler.update_person(project_ctx["safe_name"], person_id, updated_data)

    if not updated_person:
        return {"success": False}

    return {"success": True}


@router.post("/delete_person/{person_id}")
async def delete_person(
    person_id: str,
    request: Request,
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
):
    """
    Delete a person from the current project.
    """
    project_ctx = get_current_project()

    if not project_ctx["safe_name"]:
        raise HTTPException(status_code=404, detail="No project selected")

    success = neo4j_handler.delete_person(project_ctx["safe_name"], person_id)

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        return {"success": success}

    return RedirectResponse(url="/dashboard", status_code=302)


# =============================================================================
# File Management Routes
# =============================================================================

@router.post("/zip_user_files/{person_id}")
async def zip_user_files(
    person_id: str,
    request: Request,
    neo4j_handler: Neo4jHandler = Depends(get_neo4j_handler),
):
    """
    Create a ZIP file of person's files and reports.
    """
    project_ctx = get_current_project()

    if not project_ctx["safe_name"]:
        raise HTTPException(status_code=404, detail="No project selected")

    # Get markdown content from request body
    body = await request.body()
    markdown_content = body.decode('utf-8')

    person = neo4j_handler.get_person(project_ctx["safe_name"], person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Directories to include
    person_root = PROJECT_ROOT / "projects" / project_ctx["id"] / "people" / person_id
    files_dir = person_root / "files"
    reports_dir = person_root / "reports"

    # Create in-memory ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add markdown report at root
        zipf.writestr(f"profile_report_{person_id}.md", markdown_content)

        # Add files directory
        if files_dir.exists():
            for file_path in files_dir.rglob("*"):
                if file_path.is_file():
                    arcname = f"files/{file_path.relative_to(files_dir)}"
                    zipf.write(file_path, arcname=arcname)

        # Add reports directory
        if reports_dir.exists():
            for file_path in reports_dir.rglob("*"):
                if file_path.is_file():
                    arcname = f"reports/{file_path.relative_to(reports_dir)}"
                    zipf.write(file_path, arcname=arcname)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=profile_{person_id}_report.zip"
        }
    )


@router.get("/profile_editor", response_class=HTMLResponse)
async def profile_editor(
    request: Request,
    config: dict = Depends(get_app_config),
):
    """
    Profile editor page.

    Note: This template may not exist yet - returns 404 if missing.
    """
    template_path = TEMPLATES_DIR / "profile_editor.html"
    if not template_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Profile editor template not found. This feature may not be implemented yet."
        )
    return templates.TemplateResponse("profile_editor.html", {"request": request, "config": config})


@router.get("/person/{person_id}/explore")
async def explore_person_files(
    person_id: str,
    request: Request,
    path: str = "/",
):
    """
    Explore person's files and folders.

    Returns directory listing and tree structure.
    """
    project_ctx = get_current_project()

    if not project_ctx["id"]:
        raise HTTPException(status_code=404, detail="No project selected")

    safe_rel_path = path.strip('/')
    person_root = PROJECT_ROOT / "projects" / project_ctx["id"] / "people" / person_id
    abs_path = person_root / safe_rel_path

    try:
        # Ensure root and subfolders exist
        if not person_root.exists():
            (person_root / "files").mkdir(parents=True, exist_ok=True)
            (person_root / "reports").mkdir(parents=True, exist_ok=True)

        # Security check
        if not str(abs_path.resolve()).startswith(str(person_root.resolve())):
            raise HTTPException(status_code=400, detail="Invalid path")

        entries = []
        tree = []

        if abs_path.exists():
            for item in sorted(abs_path.iterdir()):
                stat = item.stat()
                entry = {
                    "name": item.name,
                    "path": str(item.relative_to(person_root)),
                    "date": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                }
                if item.is_dir():
                    entry["type"] = "folder"
                else:
                    entry["type"] = "file"
                    entry["url"] = f"/projects/{project_ctx['id']}/people/{person_id}/{entry['path']}"
                    entry["id"] = ""
                entries.append(entry)

        def build_tree(base_path: Path, rel_path: str = '') -> list:
            nodes = []
            if not base_path.exists():
                return nodes
            for item in sorted(base_path.iterdir()):
                node_path = f"{rel_path}/{item.name}".strip('/')
                if item.is_dir():
                    nodes.append({
                        "name": item.name,
                        "type": "folder",
                        "path": node_path,
                        "open": node_path == safe_rel_path,
                        "children": build_tree(item, node_path) if node_path == safe_rel_path else []
                    })
                else:
                    nodes.append({
                        "name": item.name,
                        "type": "file",
                        "path": node_path,
                        "url": f"/projects/{project_ctx['id']}/people/{person_id}/{node_path}"
                    })
            return nodes

        tree = build_tree(person_root)

        return {"entries": entries, "tree": tree}

    except Exception as e:
        logger.error(f"Error in explore_person_files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/person/{person_id}/upload")
async def upload_person_file(
    person_id: str,
    request: Request,
    path: str = "/",
):
    """
    Upload files to person's files directory.
    """
    project_ctx = get_current_project()

    if not project_ctx["id"]:
        raise HTTPException(status_code=404, detail="No project selected")

    safe_rel_path = path.strip('/')
    person_root = PROJECT_ROOT / "projects" / project_ctx["id"] / "people" / person_id
    files_root = person_root / "files"
    target_dir = person_root / safe_rel_path

    # Security check - only allow uploads to files folder
    if not str(target_dir.resolve()).startswith(str(files_root.resolve())):
        raise HTTPException(status_code=400, detail="Uploads only allowed in 'files' folder")

    target_dir.mkdir(parents=True, exist_ok=True)

    form_data = await request.form()
    uploaded_files = []

    for key in form_data:
        if key == "files":
            files = form_data.getlist("files")
            for file in files:
                if hasattr(file, 'filename') and file.filename:
                    file_id = hashlib.sha256(os.urandom(32)).hexdigest()[:12]
                    filename = f"{file_id}_{file.filename}"
                    file_path = target_dir / filename

                    content = await file.read()
                    with open(file_path, "wb") as f:
                        f.write(content)

                    uploaded_files.append({
                        "id": file_id,
                        "name": file.filename,
                        "path": filename
                    })

    return {"success": True, "files": uploaded_files}
