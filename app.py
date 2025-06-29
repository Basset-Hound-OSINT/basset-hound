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
from reports import reports_bp
from profiles import profiles_bp


app = Flask(__name__)
app.register_blueprint(reports_bp)
app.register_blueprint(profiles_bp)

# Initialize Neo4j handler
neo4j_handler = Neo4jHandler()
app.config['NEO4J_HANDLER'] = neo4j_handler

try:
    CONFIG = load_config()
    neo4j_handler.setup_schema_from_config(CONFIG)
except Exception as e:
    print(f"Error loading configuration: {e}")
    CONFIG = {"sections": []}

app.config['CONFIG'] = CONFIG  # <-- Make sure this is always set!

# Global current project (now stored in Neo4j)
current_project_safe_name = None

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

    try:
        # Create project in Neo4j
        project = neo4j_handler.create_project(project_name, project_safe_name)
        
        if not project:
            return jsonify({"success": False, "error": "Failed to create project"}), 400

        # Set current project
        global current_project_safe_name, current_project_id
        current_project_safe_name = project_safe_name
        current_project_id = project.get('id')  # Ensure `id` is returned by `create_project`
        app.config['CURRENT_PROJECT_ID'] = current_project_id
        app.config['CURRENT_PROJECT_SAFE_NAME'] = current_project_safe_name

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
    app.config['CURRENT_PROJECT_ID'] = current_project_id
    app.config['CURRENT_PROJECT_SAFE_NAME'] = current_project_safe_name
    
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


@app.route('/get_config')
def get_config():
    try:
        config = load_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

    # Update app config for blueprints!
    app.config['CONFIG'] = CONFIG

    # Update Neo4j schema
    neo4j_handler.setup_schema_from_config(CONFIG)

    return jsonify({"success": True})

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

@app.route('/tag_person/<string:person_id>', methods=['POST'])
def tag_person(person_id):
    try:
        if not current_project_safe_name:
            return jsonify({"success": False, "error": "No project selected"}), 400

        data = request.get_json()
        if not data or 'tagged_ids' not in data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400

        # Update person in Neo4j
        updated_person = neo4j_handler.update_person(
            current_project_safe_name,
            person_id,
            {
                "profile": {
                    "Tagged People": {
                        "tagged_people": data['tagged_ids'],
                        "transitive_relationships": data.get('transitive_relationships', [])
                    }
                }
            }
        )

        if not updated_person:
            return jsonify({"success": False, "error": "Person not found or update failed"}), 404

        return jsonify({"success": True})
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "An error occurred while saving tags"
        }), 500
    
if __name__ == '__main__':
    os.makedirs('projects', exist_ok=True)
    app.run(debug=True)