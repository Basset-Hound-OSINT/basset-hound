from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import json
import os
from datetime import datetime
import hashlib
from collections import defaultdict
import yaml
from config_loader import load_config, initialize_person_data
import pprint

app = Flask(__name__)

# Load the profile configuration
try:
    CONFIG = load_config()
except Exception as e:
    print(f"Error loading configuration: {e}")
    CONFIG = {"sections": []}

# Global variable to store current project data
current_project = {
    "name": "",
    "start_date": "",
    "people": []
}

@app.route('/')
def index():
    """Landing page to create new project or open existing one"""
    return render_template('index.html')

@app.route('/new_project', methods=['POST'])
def new_project():
    """Create a new project"""
    project_name = request.form.get('project_name')
    
    global current_project
    current_project = {
        "name": project_name,
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "people": []
    }
    
    # Save the new project
    save_project()
    
    return redirect(url_for('dashboard'))

@app.route('/open_project', methods=['POST'])
def open_project():
    """Open an existing project"""
    if 'project_file' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['project_file']
    
    if file.filename == '':
        return redirect(url_for('index'))
    
    if file:
        global current_project
        current_project = json.load(file)
        
        # Ensure all people have IDs and created_at timestamps (for backward compatibility)
        for person in current_project["people"]:
            if "id" not in person:
                person["id"] = generate_unique_id()
            if "created_at" not in person:
                person["created_at"] = datetime.now().isoformat()  # Current time as default
                
        return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Main dashboard for managing people"""
    return render_template('dashboard.html', project=current_project, config=CONFIG, person=None)

@app.route('/get_people')
def get_people():
    """API endpoint to get all people in the project"""
    return jsonify(current_project["people"])

@app.route('/get_config')
def get_config():
    """API endpoint to get the profile configuration"""
    return jsonify(CONFIG)

@app.route('/get_person/<string:person_id>')
def get_person(person_id):
    """API endpoint to get a specific person's details by ID"""
    for person in current_project["people"]:
        if person.get("id") == person_id:
            return jsonify(person)
    return jsonify({"error": "Person not found"}), 404

def generate_unique_id():
    """Generate a unique ID that doesn't exist in the current project"""
    length=12
    while True:
        random_bytes = os.urandom(32)  # cryptographically strong randomness
        digest = hashlib.sha256(random_bytes).hexdigest()
        new_id = digest[:length]
        # Check if ID already exists
        if not any(person.get("id") == new_id for person in current_project["people"]):
            return new_id

@app.route('/add_person', methods=['POST'])
def add_person():
    """Add a new person to the project based on form data"""
    person_data = {
        "id": generate_unique_id(),
        "created_at": datetime.now().isoformat(),
        "profile": {}
    }

    print("Received form keys:")
    print(list(request.form.keys()))

    # Initialize the profile structure
    for section in CONFIG["sections"]:
        section_id = section["id"]
        person_data["profile"][section_id] = {}
        
        for field in section["fields"]:
            field_id = field["id"]
            field_data = process_field_data(section_id, field)
            
            if field_data:
                person_data["profile"][section_id][field_id] = field_data

    current_project["people"].append(person_data)

    print("[DEBUG] Saved person:")
    pprint.pprint(person_data)
    
    save_project()
    return redirect(url_for('dashboard'))

def process_field_data(section_id, field):
    """Process form data for a specific field"""
    form_data = request.form
    field_id = field["id"]
    field_key = f"{section_id}.{field_id}"
    is_multiple = field.get("multiple", False)

    if "components" in field:
        return process_component_field(field, field_key)
    
    values = [v for k, v in form_data.items() 
              if k.startswith(field_key) and v.strip()]
    
    if not values:
        return None
    return values if is_multiple else values[0]

def process_component_field(field, field_key):
    """Process a field with components"""
    components = field.get("components", [])
    instances = defaultdict(dict)
    
    for key in request.form:
        if key.startswith(field_key):
            parts = key.split('.')
            if len(parts) < 3:
                continue
                
            # Extract the component ID and instance index
            # Format is section_id.field_id.component_id_index
            component_part = parts[2]
            if '_' in component_part:
                component_id, instance_idx = component_part.split('_', 1)
            else:
                component_id = component_part
                instance_idx = '0'
            
            value = request.form[key].strip()
            if value:  # Only add non-empty values
                instances[instance_idx][component_id] = value
    
    # Convert to list for multiple values or return single instance
    result = [v for v in instances.values() if v]
    if not result:
        return None
    
    return result if field.get("multiple", False) else result[0]

@app.route('/update_person/<person_id>', methods=['POST'])
def update_person(person_id):
    from pprint import pprint

    person = next((p for p in current_project["people"] if p["id"] == person_id), None)
    if not person:
        return "Person not found", 404

    if request.is_json:
        incoming_profile = request.get_json().get("profile", {})
        print("[DEBUG] Incoming JSON profile data:")
        pprint(incoming_profile)

        for section_id, fields in incoming_profile.items():
            if section_id not in person["profile"]:
                person["profile"][section_id] = {}
            for field_id, value in fields.items():
                person["profile"][section_id][field_id] = value

        save_project()
        print("[DEBUG] Updated person (via JSON):")
        pprint(person)

        return jsonify(success=True)

    # fallback: handle legacy form submissions
    print("=== UPDATE PERSON FORM KEYS ===")
    print(list(request.form.keys()))

    for section in CONFIG["sections"]:
        section_id = section["id"]
        if section_id not in person["profile"]:
            person["profile"][section_id] = {}

        for field in section["fields"]:
            field_id = field["id"]
            field_data = process_field_data(section_id, field)
            print(f"[DEBUG] Processed {section_id}.{field_id} = {field_data}")
            if field_data:
                person["profile"][section_id][field_id] = field_data
            elif field_id in person["profile"][section_id]:
                del person["profile"][section_id][field_id]

    save_project()
    print("[DEBUG] Updated person (via form):")
    pprint(person)

    return redirect(url_for('dashboard'))




@app.route('/delete_person/<string:person_id>', methods=['POST'])
def delete_person(person_id):
    """Delete a person from the project"""
    for idx, person in enumerate(current_project["people"]):
        if person.get("id") == person_id:
            del current_project["people"][idx]
            save_project()
            
            if request.content_type == 'application/json':
                return jsonify({"success": True})
            else:
                return redirect(url_for('dashboard'))
    
    if request.content_type == 'application/json':
        return jsonify({"error": "Person not found"}), 404
    else:
        return redirect(url_for('dashboard'))

@app.route('/save_project', methods=['POST'])
def save_project_endpoint():
    """API endpoint to save the current project"""
    save_project()
    return jsonify({"success": True})

def save_project():
    """Helper function to save the current project to a JSON file"""
    if not os.path.exists('projects'):
        os.makedirs('projects')
    
    filename = f"projects/{current_project['name'].replace(' ', '_')}.json"
    with open(filename, 'w') as f:
        json.dump(current_project, f, indent=4)

@app.route('/download_project')
def download_project():
    """Download the current project as a JSON file"""
    if not current_project["name"]:
        return redirect(url_for('index'))
    
    # Create a temporary file
    filename = f"{current_project['name'].replace(' ', '_')}.json"
    temp_path = os.path.join('static', 'downloads', filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    
    # Save project to temp file
    with open(temp_path, 'w') as f:
        json.dump(current_project, f, indent=4)
    
    # Send file for download
    return send_file(temp_path, as_attachment=True)

@app.route('/profile_editor')
def profile_editor():
    """Page for editing the profile structure"""
    return render_template('profile_editor.html', config=CONFIG)

@app.route('/save_config', methods=['POST'])
def save_config():
    """Save the updated profile configuration"""
    if not request.is_json:
        return jsonify({"error": "JSON data expected"}), 400
    
    config_data = request.json
    
    # Basic validation
    if "sections" not in config_data:
        return jsonify({"error": "Invalid configuration format"}), 400
    
    # Save to file
    with open('data_config.yaml', 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    # Update global config
    global CONFIG
    CONFIG = config_data
    
    return jsonify({"success": True})

if __name__ == '__main__':
    # Create projects directory if it doesn't exist
    if not os.path.exists('projects'):
        os.makedirs('projects')
    
    app.run(debug=True)