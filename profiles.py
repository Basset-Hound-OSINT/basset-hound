from flask import Blueprint, request, jsonify, redirect, url_for, render_template, current_app, send_file, send_from_directory
import os
import hashlib
from uuid import uuid4
from datetime import datetime
from collections import defaultdict
import re
import io
import zipfile
import zipfile
import io


profiles_bp = Blueprint('profiles', __name__)


@profiles_bp.route('/get_people')
def get_people():
    neo4j_handler = current_app.config['NEO4J_HANDLER']
    current_project_safe_name = current_app.config.get('CURRENT_PROJECT_SAFE_NAME')
    if not current_project_safe_name:
        return jsonify([])
    people = neo4j_handler.get_all_people(current_project_safe_name)
    return jsonify(people)


@profiles_bp.route('/get_person/<string:person_id>')
def get_person(person_id):
    neo4j_handler = current_app.config['NEO4J_HANDLER']
    current_project_safe_name = current_app.config.get('CURRENT_PROJECT_SAFE_NAME')
    if not current_project_safe_name:
        return jsonify({"error": "No project selected"}), 404
    
    person = neo4j_handler.get_person(current_project_safe_name, person_id)
    if not person:
        return jsonify({"error": "Person not found"}), 404
    
    return jsonify(person)

@profiles_bp.route('/add_person', methods=['POST'])
def add_person():
    neo4j_handler = current_app.config['NEO4J_HANDLER']
    current_project_safe_name = current_app.config.get('CURRENT_PROJECT_SAFE_NAME')
    if not current_project_safe_name:
        return redirect(url_for('index'))
    
    # Generate person ID ONCE
    person_id = str(uuid4())
    
    # Prepare person data
    person_data = {
        "id": person_id,
        "created_at": datetime.now().isoformat(),
        "profile": {}
    }

    # Create both files and reports directories
    current_project_id = current_app.config.get('CURRENT_PROJECT_ID')
    person_files_dir = os.path.join("projects", current_project_id, "people", person_id, "files")
    person_reports_dir = os.path.join("projects", current_project_id, "people", person_id, "reports")
    os.makedirs(person_files_dir, exist_ok=True)
    os.makedirs(person_reports_dir, exist_ok=True)

    CONFIG = current_app.config['CONFIG']
    # Process form data
    for section in CONFIG["sections"]:
        section_id = section["id"]
        person_data["profile"][section_id] = {}
        
        for field in section["fields"]:
            field_id = field["id"]
            field_key_prefix = f"{section_id}.{field_id}"

            if field.get("type") == "file":
                files = [f for k, f in request.files.items() if k.startswith(field_key_prefix)]
                stored_files = []
                
                for uploaded_file in files:
                    if uploaded_file and uploaded_file.filename:
                        # Skip non-image files for profile pictures
                        if section_id == "profile" and field_id == "profile_picture":
                            if not is_image_file(uploaded_file.filename):
                                continue

                        # Generate unique file ID
                        file_id = str(hashlib.sha256(os.urandom(32)).hexdigest()[:12])
                        filename = f"{file_id}_{uploaded_file.filename}"
                        
                        # Use the correct person_dir created above
                        file_path = os.path.join(person_files_dir, filename)
                        file_data = {
                            "id": file_id,
                            "name": uploaded_file.filename,
                            "path": filename,
                            "section_id": section_id,
                            "field_id": field_id,
                            "full_path": file_path,
                            "person_id": person_id
                        }
                        uploaded_file.save(file_path)

                        # Handle associated comments
                        if "components" in field:
                            for component in field["components"]:
                                if component["type"] == "comment":
                                    index_match = re.search(rf"{field_key_prefix}_(\d+)", uploaded_file.filename)
                                    index = index_match.group(1) if index_match else "0"
                                    comment_key = f"{field_key_prefix}.{component['id']}_{index}"
                                    comment_value = request.form.get(comment_key, "").strip()
                                    if comment_value:
                                        file_data[component["id"]] = comment_value

                        stored_files.append(file_data)

                if stored_files:
                    person_data["profile"][section_id][field_id] = stored_files if field.get("multiple") else stored_files[0]
            else:
                # Always pass person_id to helper
                field_data = process_field_data(section_id, field, person_id)
                if field_data is not None:
                    person_data["profile"][section_id][field_id] = field_data

    # Create person in Neo4j (do NOT generate a new ID in Neo4j handler!)
    person = neo4j_handler.create_person(current_project_safe_name, person_data)
    
    if not person:
        return redirect(url_for('dashboard'))
    
    return redirect(url_for('dashboard'))

def process_field_data(section_id, field, person_id=None):
    form_data = request.form
    field_key = f"{section_id}.{field['id']}"
    is_multiple = field.get("multiple", False)
    
    # Special handling for comment fields
    if field.get("type") == "comment":
        values = [v for k, v in form_data.items() if k == field_key and v.strip()]
        return values if is_multiple else (values[0] if values else None)

    if "components" in field:
        return process_component_field(field, field_key, person_id)

    values = [v for k, v in form_data.items() if k.startswith(field_key) and v.strip()]
    return values if is_multiple else (values[0] if values else None)

def process_component_field(field, field_key, person_id=None):
    person_id = person_id or "unknown"
    components = field.get("components", [])
    field_instances = defaultdict(dict)

    # Process regular form fields
    for key, value in request.form.items():
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

        value = value.strip()
        if not value:
            continue

        component_cfg = next((c for c in components if c["id"] == component_id), None)
        if not component_cfg:
            continue

        is_multiple = component_cfg.get("multiple", False)

        if is_multiple:
            field_instances[field_index].setdefault(component_id, []).append(value)
        else:
            field_instances[field_index][component_id] = value

    # Process file components
    for key, uploaded_file in request.files.items():
        if not key.startswith(field_key):
            continue

        parts = key.split('.')
        if len(parts) < 3:
            continue

        component_part = parts[2]
        match = re.match(r"(\w+)_([0-9]+)", component_part)
        if not match:
            continue

        component_id = match.group(1)
        field_index = match.group(2)

        component_cfg = next((c for c in components if c["id"] == component_id and c["type"] == "file"), None)
        if not component_cfg or not uploaded_file.filename:
            continue

        file_id = str(hashlib.sha256(os.urandom(32)).hexdigest()[:12])
        filename = f"{file_id}_{uploaded_file.filename}"
        current_project_safe_name = current_app.config.get('CURRENT_PROJECT_SAFE_NAME')
        person_dir = os.path.join("projects", current_project_safe_name, "people", person_id)
        os.makedirs(person_dir, exist_ok=True)
        file_path = os.path.join(person_dir, filename)
        uploaded_file.save(file_path)

        file_data = {
            "id": file_id,
            "name": uploaded_file.filename,
            "path": filename
        }

        # Attach comments to the file
        for comp in components:
            if comp["type"] == "comment":
                comment_key = f"{field_key}.{comp['id']}_{field_index}"
                comment_value = request.form.get(comment_key, "").strip()
                if comment_value:
                    file_data[comp["id"]] = comment_value

        field_instances[field_index][component_id] = file_data

    # Final aggregation
    instances = [entry for entry in field_instances.values() if entry]
    return instances if field.get("multiple") else (instances[0] if instances else None)

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

def is_image_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@profiles_bp.route('/update_person/<person_id>', methods=['POST'])
def update_person(person_id):
    neo4j_handler = current_app.config['NEO4J_HANDLER']
    current_project_safe_name = current_app.config.get('CURRENT_PROJECT_SAFE_NAME')
    current_project_id = current_app.config.get('CURRENT_PROJECT_ID')
    if not current_project_id:
        return "No project ID", 404
    if not current_project_safe_name:
        return "No project safe name", 404
    
    # Get existing person data
    person = neo4j_handler.get_person(current_project_safe_name, person_id)
    if not person:
        return "Person not found", 404

    # Handle JSON API requests
    if request.is_json:
        updated_data = request.get_json()
        updated_person = neo4j_handler.update_person(current_project_safe_name, person_id, updated_data)
        return jsonify(success=bool(updated_person))

    # Handle form submission
    updated_data = {
        "profile": {}
    }

    CONFIG = current_app.config['CONFIG']
    for section in CONFIG["sections"]:
        section_id = section["id"]
        updated_data["profile"][section_id] = {}
        
        for field in section["fields"]:
            field_id = field["id"]
            field_key_prefix = f"{section_id}.{field_id}"
            
            if field.get("type") == "file":
                files = [f for k, f in request.files.items() if k.startswith(field_key_prefix)]
                stored_files = []
                
                # Keep existing files if no new ones uploaded
                if not files and section_id in person["profile"] and field_id in person["profile"][section_id]:
                    updated_data["profile"][section_id][field_id] = person["profile"][section_id][field_id]
                    continue
                
                for uploaded_file in files:
                    if uploaded_file and uploaded_file.filename:
                        # Skip non-image files for profile pictures
                        if section_id == "profile" and field_id == "profile_picture":
                            if not is_image_file(uploaded_file.filename):
                                continue

                        # Generate unique file ID
                        file_id = str(hashlib.sha256(os.urandom(32)).hexdigest()[:12])
                        filename = f"{file_id}_{uploaded_file.filename}"
                        
                        # Create person's directory if it doesn't exist
                        person_dir = os.path.join("projects", current_project_id, "people", person_id, "files")
                        os.makedirs(person_dir, exist_ok=True)

                        # In both add_person and update_person routes, update the file path construction:
                        file_path = os.path.join("projects", current_project_id, "people", person_id, "files", filename)
                        file_data = {
                            "id": file_id,
                            "name": uploaded_file.filename,
                            "path": filename,  # Just store the filename, not the full path
                            "section_id": section_id,
                            "field_id": field_id,
                            "full_path": file_path,
                            "person_id": person_id
                        }
                        uploaded_file.save(file_path)

                        # Handle associated comments
                        if "components" in field:
                            for component in field["components"]:
                                if component["type"] == "comment":
                                    index_match = re.search(rf"{field_key_prefix}_(\d+)", uploaded_file.filename)
                                    index = index_match.group(1) if index_match else "0"
                                    comment_key = f"{field_key_prefix}.{component['id']}_{index}"
                                    comment_value = request.form.get(comment_key, "").strip()
                                    if comment_value:
                                        file_data[component["id"]] = comment_value

                        stored_files.append(file_data)

                if stored_files:
                    updated_data["profile"][section_id][field_id] = stored_files if field.get("multiple") else stored_files[0]
            else:
                field_data = process_field_data(section_id, field, person_id)
                if field_data is not None:
                    updated_data["profile"][section_id][field_id] = field_data

    # Update person in Neo4j
    updated_person = neo4j_handler.update_person(current_project_safe_name, person_id, updated_data)
    
    if not updated_person:
        return jsonify(success=False), 400
    
    return jsonify(success=True)

@profiles_bp.route('/delete_person/<string:person_id>', methods=['POST'])
def delete_person(person_id):
    neo4j_handler = current_app.config['NEO4J_HANDLER']
    current_project_safe_name = current_app.config.get('CURRENT_PROJECT_SAFE_NAME')

    if not current_project_safe_name:
        return jsonify(error="No project selected"), 404
    
    success = neo4j_handler.delete_person(current_project_safe_name, person_id)
    
    if request.content_type == 'application/json':
        return jsonify(success=success)
    return redirect(url_for('dashboard'))

@profiles_bp.route('/zip_user_files/<person_id>', methods=['POST'])
def zip_user_files(person_id):
    neo4j_handler = current_app.config['NEO4J_HANDLER']
    current_project_safe_name = current_app.config.get('CURRENT_PROJECT_SAFE_NAME')
    current_project_id = current_app.config.get('CURRENT_PROJECT_ID')

    if not current_project_safe_name:
        return "No project selected", 404

    # Get the markdown content from the request body
    markdown_content = request.data.decode('utf-8')
    person = neo4j_handler.get_person(current_project_safe_name, person_id)
    if not person:
        return "Person not found", 404

    # Find all files for this person
    files_dir = os.path.join("projects", current_project_id, "people", person_id, "files")
    file_paths = []
    if os.path.exists(files_dir):
        for fname in os.listdir(files_dir):
            fpath = os.path.join(files_dir, fname)
            if os.path.isfile(fpath):
                file_paths.append(fpath)

    # Create an in-memory zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        # Add the markdown report
        zipf.writestr(f"profile_report_{person_id}.md", markdown_content)
        # Add all files
        for fpath in file_paths:
            arcname = os.path.basename(fpath)
            zipf.write(fpath, arcname=arcname)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"profile_{person_id}_report.zip"
    )
# Update the serve_file route to correctly handle ID mismatches

@profiles_bp.route('/profile_editor')
def profile_editor():
    CONFIG = current_app.config['CONFIG']
    return render_template('profile_editor.html', config=CONFIG)

@profiles_bp.route('/person/<person_id>/explore')
def explore_person_files(person_id):
    current_project_id = current_app.config.get('CURRENT_PROJECT_ID')
    if not current_project_id:
        return jsonify({"error": "No project selected"}), 404

    rel_path = request.args.get('path', '/')
    safe_rel_path = rel_path.strip('/')

    person_root = os.path.join("projects", current_project_id, "people", person_id)
    abs_path = os.path.join(person_root, safe_rel_path)

    try:
        # --- Ensure root and subfolders exist ---
        abs_person_root = os.path.abspath(person_root)
        if not os.path.exists(abs_person_root):
            os.makedirs(os.path.join(abs_person_root, "files"), exist_ok=True)
            os.makedirs(os.path.join(abs_person_root, "reports"), exist_ok=True)

        abs_abs_path = os.path.abspath(abs_path)
        if not abs_abs_path.startswith(abs_person_root):
            return jsonify({"error": "Invalid path"}), 400

        entries = []
        tree = []

        if os.path.exists(abs_abs_path):
            for name in sorted(os.listdir(abs_abs_path)):
                full_path = os.path.join(abs_abs_path, name)
                stat = os.stat(full_path)
                entry = {
                    "name": name,
                    "path": os.path.relpath(full_path, abs_person_root),
                    "date": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                }
                if os.path.isdir(full_path):
                    entry["type"] = "folder"
                else:
                    entry["type"] = "file"
                    entry["url"] = f"/projects/{current_project_id}/people/{person_id}/{entry['path']}".replace("\\", "/")
                    entry["id"] = ""
                entries.append(entry)

        def build_tree(base_path, rel_path=''):
            nodes = []
            for name in sorted(os.listdir(base_path)):
                full_path = os.path.join(base_path, name)
                node_path = os.path.join(rel_path, name)
                if os.path.isdir(full_path):
                    nodes.append({
                        "name": name,
                        "type": "folder",
                        "path": node_path.replace("\\", "/"),
                        "open": node_path.strip('/') == safe_rel_path,
                        "children": build_tree(full_path, node_path) if node_path.strip('/') == safe_rel_path else []
                    })
                else:
                    nodes.append({
                        "name": name,
                        "type": "file",
                        "path": node_path.replace("\\", "/"),
                        "url": f"/projects/{current_project_id}/people/{person_id}/{node_path.replace('\\', '/')}"
                    })
            return nodes

        tree = build_tree(abs_person_root)

        return jsonify({
            "entries": entries,
            "tree": tree
        })
    except Exception as e:
        print(f"Error in explore_person_files: {e}")
        return jsonify({"error": str(e)}), 500
    
@profiles_bp.route('/person/<person_id>/upload', methods=['POST'])
def upload_person_file(person_id):
    current_project_id = current_app.config.get('CURRENT_PROJECT_ID')
    if not current_project_id:
        return jsonify({"error": "No project selected"}), 404

    rel_path = request.args.get('path', '/')
    safe_rel_path = rel_path.strip('/')

    person_root = os.path.join("projects", current_project_id, "people", person_id)
    files_root = os.path.join(person_root, "files")
    target_dir = os.path.join(person_root, safe_rel_path)
    abs_files_root = os.path.abspath(files_root)
    abs_target_dir = os.path.abspath(target_dir)

    # Only allow uploads to the files folder or its subfolders
    if not abs_target_dir.startswith(abs_files_root):
        return jsonify({"error": "Uploads only allowed in 'files' folder"}), 400

    os.makedirs(abs_target_dir, exist_ok=True)

    uploaded_files = []
    for file in request.files.getlist('files'):
        if file and file.filename:
            # Generate unique file ID
            file_id = str(hashlib.sha256(os.urandom(32)).hexdigest()[:12])
            filename = f"{file_id}_{file.filename}"
            file_path = os.path.join(abs_target_dir, filename)
            file.save(file_path)
            uploaded_files.append({
                "id": file_id,
                "name": file.filename,
                "path": filename
            })

    return jsonify({"success": True, "files": uploaded_files})