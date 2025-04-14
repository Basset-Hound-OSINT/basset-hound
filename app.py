from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, send_from_directory
import json
import os
from datetime import datetime
import hashlib
from collections import defaultdict
import yaml
import re
import zipfile
from neo4j_handler import Neo4jHandler

# Import config loader functions
from config_loader import load_config, initialize_person_data

app = Flask(__name__)

# Initialize Neo4j handler
neo4j = Neo4jHandler()

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

@app.route('/map.html')
def map_page():
    return render_template('map.html')

@app.route('/osint.html')
def osint_page():
    return render_template('osint.html')

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
    people = neo4j.get_all_people()
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
    person = neo4j.get_person_by_id(person_id)
    if person:
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
    neo4j.create_person(person_data)
    return redirect(url_for('dashboard'))

def get_display_name(person):
    name_data = person.get("profile", {}).get("core", {}).get("name", [])
    if isinstance(name_data, list) and name_data:
        first = name_data[0].get("first", "")
        last = name_data[0].get("last", "")
        return f"{first} {last}".strip()
    return "Unnamed"

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

    # --- Process regular form fields ---
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

    # --- Process file components ---
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

        file_id = generate_unique_id()
        filename = f"{file_id}_{uploaded_file.filename}"
        person_id = request.form.get("person_id", "unknown")
        person_dir = os.path.join("projects", current_project["safe_name"], person_id)
        os.makedirs(person_dir, exist_ok=True)
        file_path = os.path.join(person_dir, filename)
        uploaded_file.save(file_path)

        file_data = {
            "id": file_id,
            "name": uploaded_file.filename,
            "path": filename
        }

        # Attach comments (if defined) to the file
        for comp in components:
            if comp["type"] == "comment":
                comment_key = f"{field_key}.{comp['id']}_{field_index}"
                comment_value = request.form.get(comment_key, "").strip()
                if comment_value:
                    file_data[comp["id"]] = comment_value

        # Only add file_data if we actually uploaded a file
        if uploaded_file and uploaded_file.filename:
            field_instances[field_index][component_id] = file_data


    # --- Final aggregation ---
    instances = [entry for entry in field_instances.values() if entry]
    return instances if field.get("multiple") else (instances[0] if instances else None)

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

def is_image_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@app.route('/update_person/<person_id>', methods=['POST'])
def update_person_route(person_id):
    updates = request.json
    if not updates:
        return jsonify({"error": "No updates provided"}), 400
    neo4j.update_person(person_id, updates)
    return jsonify(success=True)

@app.route('/delete_person/<string:person_id>', methods=['POST'])
def delete_person_route(person_id):
    neo4j.delete_person(person_id)
    return jsonify({"success": True})

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

    # Define project directory and JSON file path
    project_safe_name = current_project["safe_name"]
    project_dir = os.path.join('projects', project_safe_name)
    json_filename = f"{current_project['name'].replace(' ', '_')}.json"
    json_path = os.path.join(project_dir, json_filename)

    # Ensure the project directory exists
    os.makedirs(project_dir, exist_ok=True)

    # Save the JSON file
    with open(json_path, 'w') as f:
        json.dump(current_project, f, indent=4)

    # Check if there are additional files in the project directory
    additional_files = [
        f for f in os.listdir(project_dir)
        if os.path.isfile(os.path.join(project_dir, f)) and f != json_filename
    ]

    # Create a zip file if there are additional files or just the JSON file
    zip_filename = f"{project_safe_name}.zip"
    zip_path = os.path.join('static', 'downloads', zip_filename)
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, _, files in os.walk(project_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Include the project directory name in the archive structure
                arcname = os.path.join(project_safe_name, os.path.relpath(file_path, project_dir))
                zipf.write(file_path, arcname)

    # Send the zip file to the user
    return send_file(zip_path, as_attachment=True)

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

@app.route('/zip_user_files/<person_id>', methods=['POST'])
def zip_user_files(person_id):
    # Define the user's directory
    project_safe_name = current_project["safe_name"]
    user_dir = os.path.join("projects", project_safe_name, person_id)

    if not os.path.exists(user_dir):
        return jsonify({"error": "User directory not found"}), 404

    # Create a temporary directory for the zip file
    zip_filename = f"{person_id}.zip"
    zip_path = os.path.join("static", "downloads", zip_filename)
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)

    # Save the Markdown report sent from the frontend
    report_content = request.data.decode('utf-8')
    report_path = os.path.join(user_dir, f"{person_id}.md")
    with open(report_path, 'w') as report_file:
        report_file.write(report_content)

    # Create the zip file
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, _, files in os.walk(user_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.join(person_id, os.path.relpath(file_path, user_dir))  # Include user ID as folder
                zipf.write(file_path, arcname)

    # Send the zip file to the user
    return send_file(zip_path, as_attachment=True)

@app.route('/tag_person/<person_id>', methods=['POST'])
def tag_person(person_id):
    tag_data = request.get_json()
    tagged_ids = tag_data.get("tagged_ids", [])
    neo4j.tag_person(person_id, tagged_ids)
    return jsonify({"success": True})

@app.route('/projects/<project_name>/project_data.json')
def serve_project_data(project_name):
    return send_from_directory(f'projects/{project_name}', 'project_data.json')

@app.route('/get_connections/<person_id>')
def get_connections_route(person_id):
    max_hops = request.args.get('max_hops', 2, type=int)
    connections = neo4j.get_connections(person_id, max_hops)
    return jsonify(connections)

@app.route('/get_full_graph')
def get_full_graph_route():
    return jsonify(neo4j.get_full_graph())

@app.teardown_appcontext
def shutdown_neo4j(exception=None):
    """Close Neo4j driver on application shutdown."""
    neo4j.close()

if __name__ == '__main__':
    os.makedirs('projects', exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
