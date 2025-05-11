from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, send_from_directory
import json
import os
from datetime import datetime
import hashlib
from collections import defaultdict
import yaml
from uuid import uuid4
from config_loader import load_config, initialize_person_data
import pprint
import re
from neo4j_handler import Neo4jHandler

app = Flask(__name__)

# Initialize Neo4j handler
neo4j_handler = Neo4jHandler()

# Load profile configuration
try:
    CONFIG = load_config()
    # Setup schema in Neo4j based on config
    neo4j_handler.setup_schema_from_config(CONFIG)
except Exception as e:
    print(f"Error loading configuration: {e}")
    CONFIG = {"sections": []}

# Global current project (now stored in Neo4j)
current_project_safe_name = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/new_project', methods=['POST'])
def new_project():
    project_name = request.form.get('project_name')
    project_safe_name = slugify(project_name)

    try:
        # Create project in Neo4j
        project = neo4j_handler.create_project(project_name, project_safe_name)
        
        if not project:
            return jsonify({"success": False, "error": "Failed to create project"}), 400

        # Set current project
        global current_project_safe_name, current_project_id
        current_project_safe_name = project_safe_name
        current_project_id = project.get('id')  # Ensure `id` is returned by `create_project`

        # Create project directory using the project ID
        os.makedirs(f'projects/{current_project_id}', exist_ok=True)

        return jsonify({"success": True, "redirect": url_for('dashboard')})
    except Exception as e:
        if "already exists" in str(e):
            return jsonify({"success": False, "error": "A project with this name already exists"}), 400
        return jsonify({"success": False, "error": str(e)}), 500
    
def slugify(value):
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '_', value)

@app.route('/get_projects')
def get_projects():  # Remove self parameter
    try:
        projects = neo4j_handler.get_all_projects()
        return jsonify(projects)
    except Exception as e:
        print(f"Error getting projects: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/set_current_project', methods=['POST'])
def set_current_project():
    if not request.is_json:
        return jsonify({"success": False, "error": "JSON data expected"}), 400
    
    data = request.get_json()
    safe_name = data.get('safe_name')
    
    if not safe_name:
        return jsonify({"success": False, "error": "No project specified"}), 400
    
    project = neo4j_handler.get_project(safe_name)
    if not project:
        return jsonify({"success": False, "error": "Project not found"}), 404
    
    global current_project_safe_name, current_project_id
    current_project_safe_name = safe_name
    current_project_id = project.get('id')
    
    return jsonify({
        "success": True,
        "project_id": current_project_id,  # This is crucial
        "redirect": url_for('dashboard')
    })


@app.route('/dashboard')
def dashboard():
    if not current_project_safe_name:
        return redirect(url_for('index'))
    
    project = neo4j_handler.get_project(current_project_safe_name)
    if not project:
        return redirect(url_for('index'))
    
    return render_template('dashboard.html', 
                        project=project, 
                        config=CONFIG, 
                        person=None,
                        current_project_id=current_project_id)  # Add this line

@app.route('/get_people')
def get_people():
    if not current_project_safe_name:
        return jsonify([])
    
    people = neo4j_handler.get_all_people(current_project_safe_name)
    return jsonify(people)

@app.route('/get_config')
def get_config():
    try:
        config = load_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_person/<string:person_id>')
def get_person(person_id):
    if not current_project_safe_name:
        return jsonify({"error": "No project selected"}), 404
    
    person = neo4j_handler.get_person(current_project_safe_name, person_id)
    if not person:
        return jsonify({"error": "Person not found"}), 404
    
    return jsonify(person)

@app.route('/add_person', methods=['POST'])
def add_person():
    if not current_project_safe_name:
        return redirect(url_for('index'))
    
    # Generate person ID first
    person_id = str(uuid4())
    
    # Prepare person data
    person_data = {
        "id": person_id,  # This ID should be used consistently
        "created_at": datetime.now().isoformat(),
        "profile": {}
    }

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
                    person_data["profile"][section_id][field_id] = stored_files if field.get("multiple") else stored_files[0]
            else:
                field_data = process_field_data(section_id, field)
                if field_data is not None:
                    person_data["profile"][section_id][field_id] = field_data

    # Create person in Neo4j
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

@app.route('/update_person/<person_id>', methods=['POST'])
def update_person(person_id):
    if not current_project_safe_name:
        return "No project selected", 404
    
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

@app.route('/delete_person/<string:person_id>', methods=['POST'])
def delete_person(person_id):
    if not current_project_safe_name:
        return jsonify(error="No project selected"), 404
    
    success = neo4j_handler.delete_person(current_project_safe_name, person_id)
    
    if request.content_type == 'application/json':
        return jsonify(success=success)
    return redirect(url_for('dashboard'))

@app.route('/download_project')
def download_project():
    if not current_project_safe_name:
        return redirect(url_for('index'))
    
    project = neo4j_handler.get_project(current_project_safe_name)
    if not project:
        return redirect(url_for('index'))
    
    filename = f"{project['name'].replace(' ', '_')}.json"
    temp_path = os.path.join('static', 'downloads', filename)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)

    with open(temp_path, 'w') as f:
        json.dump(project, f, indent=4)

    return send_file(temp_path, as_attachment=True)

@app.route('/profile_editor')
def profile_editor():
    return render_template('profile_editor.html', config=CONFIG)

@app.route('/save_config', methods=['POST'])
def save_config():
    if not request.is_json:
        return jsonify({"error": "JSON data expected"}), 400

    config_data = request.json
    if "sections" not in config_data:
        return jsonify({"error": "Invalid configuration format"}), 400

    with open('data_config.yaml', 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)

    global CONFIG
    CONFIG = config_data

    # Update Neo4j schema
    neo4j_handler.setup_schema_from_config(CONFIG)

    return jsonify({"success": True})

# Update the serve_file route to correctly handle ID mismatches

@app.route('/projects/<project_id>/people/<person_id>/files/<filename>')
def serve_file(project_id, person_id, filename):
    """
    Serve a file from the appropriate directory.
    
    This improved version:
    1. First tries the direct path with the provided person_id
    2. If not found, searches through all people in the project for the file
    """
    # Verify the project exists
    if project_id != current_project_id:
        return "Invalid project", 404
    
    # First try the direct path
    direct_path = os.path.join("projects", project_id, "people", person_id, "files", filename)
    if os.path.exists(direct_path):
        directory = os.path.join("projects", project_id, "people", person_id, "files")
        return send_from_directory(directory, filename)
    
    # If not found directly, search through all people in the project
    people = neo4j_handler.get_all_people(current_project_safe_name)
    for person in people:
        if not person or not person.get('profile'):
            continue
            
        # Search through all sections and fields for file references
        for section_id, section_data in person['profile'].items():
            for field_id, field_data in section_data.items():
                if not field_data:
                    continue
                
                # Handle both single file and file arrays
                file_entries = field_data if isinstance(field_data, list) else [field_data]
                
                for entry in file_entries:
                    if isinstance(entry, dict) and entry.get('path') == filename:
                        # Found a matching file reference
                        actual_person_id = entry.get('person_id', person['id'])
                        actual_path = os.path.join("projects", project_id, "people", actual_person_id, "files", filename)
                        
                        if os.path.exists(actual_path):
                            directory = os.path.join("projects", project_id, "people", actual_person_id, "files")
                            return send_from_directory(directory, filename)
    
    # If we reach here, the file wasn't found
    return "File not found", 404

if __name__ == '__main__':
    os.makedirs('projects', exist_ok=True)
    app.run(debug=True)