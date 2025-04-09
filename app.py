from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, send_from_directory
import json
import os
from datetime import datetime
import hashlib
from collections import defaultdict
import yaml
from config_loader import load_config, initialize_person_data
import pprint
import re

app = Flask(__name__)

# Load profile configuration
try:
    CONFIG = load_config()
except Exception as e:
    print(f"Error loading configuration: {e}")
    CONFIG = {"sections": []}

# Global current project
current_project = {
    "name": "",
    "start_date": "",
    "people": []
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/new_project', methods=['POST'])
def new_project():
    project_name = request.form.get('project_name')
    project_safe_name = slugify(project_name)

    global current_project
    current_project = {
        "name": project_name,
        "safe_name": project_safe_name,
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "people": []
    }

    os.makedirs(f'projects/{project_safe_name}', exist_ok=True)
    save_project()

    return redirect(url_for('dashboard'))

def slugify(value):
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '_', value)

@app.route('/open_project', methods=['POST'])
def open_project():
    if 'project_file' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['project_file']
    if file.filename == '':
        return redirect(url_for('index'))

    if file:
        global current_project
        current_project = json.load(file)

        # Ensure safe_name is set
        if "safe_name" not in current_project:
            current_project["safe_name"] = slugify(current_project.get("name", "unnamed_project"))

        project_dir = os.path.join("projects", current_project["safe_name"])
        os.makedirs(project_dir, exist_ok=True)

        # Ensure all people have folders and migration fields
        for person in current_project.get("people", []):
            if "id" not in person:
                person["id"] = generate_unique_id()
            if "created_at" not in person:
                person["created_at"] = datetime.now().isoformat()

            person_folder = os.path.join(project_dir, person["id"])
            os.makedirs(person_folder, exist_ok=True)

        return redirect(url_for('dashboard'))


def ensure_person_folders():
    """Ensure every person has a folder in the project directory."""
    if 'safe_name' not in current_project:
        current_project['safe_name'] = slugify(current_project.get('name', 'default_project'))

    project_dir = os.path.join('projects', current_project['safe_name'])

    for person in current_project.get("people", []):
        person_id = person.get("id")
        person_folder = os.path.join(project_dir, person_id)
        if not os.path.exists(person_folder):
            os.makedirs(person_folder)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', project=current_project, config=CONFIG, person=None)

@app.route('/get_people')
def get_people():
    return jsonify(current_project["people"])

@app.route('/get_config')
def get_config():
    try:
        config = load_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_person/<string:person_id>')
def get_person(person_id):
    for person in current_project["people"]:
        if person.get("id") == person_id:
            return jsonify(person)
    return jsonify({"error": "Person not found"}), 404

@app.route('/generate_id')
def generate_id():
    return jsonify({"id": generate_unique_id()})

def generate_unique_id():
    length = 12
    existing_ids = set()

    # Project folder path
    safe_name = current_project.get("safe_name") or slugify(current_project.get("name", "default_project"))
    project_dir = os.path.join("projects", safe_name)


    # 1. Check all folder names (person IDs)
    if os.path.isdir(project_dir):
        for entry in os.listdir(project_dir):
            full_path = os.path.join(project_dir, entry)
            if os.path.isdir(full_path):
                existing_ids.add(entry)

            # 2. Check all file names in each folder (extract prefix before '_')
            elif os.path.isfile(full_path) and "_" in entry:
                prefix = entry.split("_", 1)[0]
                existing_ids.add(prefix)

        # 3. Check files inside each person's folder too
        for person_folder in os.listdir(project_dir):
            folder_path = os.path.join(project_dir, person_folder)
            if os.path.isdir(folder_path):
                for file in os.listdir(folder_path):
                    if "_" in file:
                        prefix = file.split("_", 1)[0]
                        existing_ids.add(prefix)

    # 4. Generate a truly unique ID
    while True:
        new_id = hashlib.sha256(os.urandom(32)).hexdigest()[:length]
        if new_id not in existing_ids:
            return new_id

@app.route('/add_person', methods=['POST'])
def add_person():
    person_id = generate_unique_id()

    if 'safe_name' not in current_project:
        current_project['safe_name'] = slugify(current_project.get('name', 'default_project'))

    person_data = {
        "id": person_id,
        "created_at": datetime.now().isoformat(),
        "profile": {}
    }

    person_dir = os.path.join("projects", current_project["safe_name"], person_id)
    os.makedirs(person_dir, exist_ok=True)

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
                        file_id = generate_unique_id()
                        filename = f"{file_id}_{uploaded_file.filename}"
                        file_path = os.path.join(person_dir, filename)
                        uploaded_file.save(file_path)

                        stored_files.append({
                            "id": file_id,
                            "name": uploaded_file.filename,
                            "path": filename
                        })

                if stored_files:
                    person_data["profile"][section_id][field_id] = stored_files if field.get("multiple") else stored_files[0]

            else:
                field_data = process_field_data(section_id, field)
                if field_data:
                    person_data["profile"][section_id][field_id] = field_data

    current_project["people"].append(person_data)
    save_project()
    return redirect(url_for('dashboard'))

def get_display_name(person):
    name_data = person.get("profile", {}).get("core", {}).get("name", [])
    if isinstance(name_data, list) and name_data:
        first = name_data[0].get("first", "")
        last = name_data[0].get("last", "")
        return f"{first} {last}".strip()
    return "Unnamed"

def process_field_data(section_id, field):
    form_data = request.form
    field_key = f"{section_id}.{field['id']}"
    is_multiple = field.get("multiple", False)

    if "components" in field:
        return process_component_field(field, field_key)

    values = [v for k, v in form_data.items() if k.startswith(field_key) and v.strip()]
    return values if is_multiple else (values[0] if values else None)

def process_component_field(field, field_key):
    components = field.get("components", [])
    field_instances = defaultdict(dict)

    for key, value in request.form.items():
        if not key.startswith(field_key):
            continue

        parts = key.split('.')
        if len(parts) < 3:
            continue

        component_part = parts[2]

        # Match things like: email_0_1 or email_0
        match = re.match(r"(\w+)_([0-9]+)(?:\.([0-9]+))?", component_part)
        if not match:
            continue

        component_id = match.group(1)
        field_index = match.group(2)
        sub_index = match.group(3)

        value = value.strip()
        if not value:
            continue

        component_cfg = next((c for c in components if c["id"] == component_id), None)
        if not component_cfg:
            continue

        is_multiple = component_cfg.get("multiple", False)

        # Store appropriately: single or multiple values
        if is_multiple:
            field_instances[field_index].setdefault(component_id, []).append(value)
        else:
            field_instances[field_index][component_id] = value

    instances = [entry for entry in field_instances.values() if entry]
    return instances if field.get("multiple") else (instances[0] if instances else None)

@app.route('/update_person/<person_id>', methods=['POST'])
def update_person(person_id):
    person = next((p for p in current_project["people"] if p["id"] == person_id), None)
    if not person:
        return "Person not found", 404

    # 🔹 JSON request (e.g., via API)
    if request.is_json:
        incoming = request.get_json().get("profile", {})
        for section_id, fields in incoming.items():
            person["profile"].setdefault(section_id, {})
            for field_id, value in fields.items():
                person["profile"][section_id][field_id] = value

        save_project()
        return jsonify(success=True)

    # 🔹 Form submission (e.g., via UI form)
    print("=== UPDATE PERSON FORM KEYS ===")
    print(list(request.form.keys()))

    for section in CONFIG["sections"]:
        section_id = section["id"]
        person["profile"].setdefault(section_id, {})

        for field in section["fields"]:
            field_id = field["id"]
            field_key = f"{section_id}.{field_id}"
            is_multiple = field.get("multiple", False)

            # Handle file uploads
            if field.get("type") == "file":
                files = [f for k, f in request.files.items() if k.startswith(field_key) and f.filename]
                
                # Keep existing files if no new ones uploaded
                if not files and field_id in person["profile"][section_id]:
                    continue
                    
                stored_files = []
                
                # Retrieve existing files if we have them
                if field_id in person["profile"][section_id]:
                    existing = person["profile"][section_id][field_id]
                    if not isinstance(existing, list):
                        existing = [existing]
                    stored_files.extend(existing)
                
                # Add new files
                for uploaded_file in files:
                    if uploaded_file and uploaded_file.filename:
                        file_id = generate_unique_id()
                        filename = f"{file_id}_{uploaded_file.filename}"
                        person_dir = os.path.join("projects", current_project["safe_name"], person_id)
                        os.makedirs(person_dir, exist_ok=True)
                        file_path = os.path.join(person_dir, filename)
                        uploaded_file.save(file_path)
                        
                        stored_files.append({
                            "id": file_id,
                            "name": uploaded_file.filename,
                            "path": filename
                        })
                
                if stored_files:
                    person["profile"][section_id][field_id] = stored_files if field.get("multiple") else stored_files[0]

            # Handle all other fields (including nested ones)
            else:
                field_data = process_field_data(section_id, field)
                if field_data:
                    person["profile"][section_id][field_id] = field_data
                elif field_id in person["profile"][section_id]:
                    # Remove the field if it's now empty
                    del person["profile"][section_id][field_id]

    save_project()
    return jsonify(success=True)


@app.route('/delete_person/<string:person_id>', methods=['POST'])
def delete_person(person_id):
    for idx, person in enumerate(current_project["people"]):
        if person.get("id") == person_id:
            del current_project["people"][idx]
            save_project()
            return jsonify(success=True) if request.content_type == 'application/json' else redirect(url_for('dashboard'))

    return jsonify(error="Person not found") if request.content_type == 'application/json' else redirect(url_for('dashboard'))

@app.route('/save_project', methods=['POST'])
def save_project_endpoint():
    save_project()
    return jsonify({"success": True})

def save_project():
    if not current_project.get("safe_name"):
        current_project["safe_name"] = slugify(current_project["name"])

    project_dir = f"projects/{current_project['safe_name']}"
    os.makedirs(project_dir, exist_ok=True)

    with open(os.path.join(project_dir, "project_data.json"), "w") as f:
        json.dump(current_project, f, indent=4)

@app.route('/download_project')
def download_project():
    if not current_project["name"]:
        return redirect(url_for('index'))

    filename = f"{current_project['name'].replace(' ', '_')}.json"
    temp_path = os.path.join('static', 'downloads', filename)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)

    with open(temp_path, 'w') as f:
        json.dump(current_project, f, indent=4)

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

    return jsonify({"success": True})

@app.route('/files/<person_id>/<filename>')
def serve_file(person_id, filename):
    project_path = os.path.join("projects", current_project["safe_name"], person_id)
    return send_from_directory(project_path, filename)

if __name__ == '__main__':
    os.makedirs('projects', exist_ok=True)
    app.run(debug=True)
