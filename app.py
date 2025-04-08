from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__)

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
        
        # Ensure all people have IDs (for backward compatibility)
        for person in current_project["people"]:
            if "id" not in person:
                person["id"] = generate_unique_id()
                
        return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Main dashboard for managing people"""
    return render_template('dashboard.html', project=current_project)

@app.route('/get_people')
def get_people():
    """API endpoint to get all people in the project"""
    return jsonify(current_project["people"])

@app.route('/get_person/<int:person_index>')
def get_person(person_index):
    """API endpoint to get a specific person's details"""
    if 0 <= person_index < len(current_project["people"]):
        return jsonify(current_project["people"][person_index])
    return jsonify({"error": "Person not found"}), 404

@app.route('/get_person_by_id/<string:person_id>')
def get_person_by_id(person_id):
    """API endpoint to get a specific person's details by ID"""
    for person in current_project["people"]:
        if person.get("id") == person_id:
            return jsonify(person)
    return jsonify({"error": "Person not found"}), 404

def generate_unique_id():
    """Generate a unique ID that doesn't exist in the current project"""
    while True:
        new_id = str(uuid.uuid4())[:8]  # Using first 8 characters of UUID for brevity
        # Check if ID already exists
        if not any(person.get("id") == new_id for person in current_project["people"]):
            return new_id

@app.route('/add_person', methods=['POST'])
def add_person():
    """Add a new person to the project"""
    person_data = {
        "id": generate_unique_id(),
        "names": [{
            "first_name": request.form.get('first_name', ''),
            "middle_name": request.form.get('middle_name', ''),
            "last_name": request.form.get('last_name', '')
        }],
        "dates_of_birth": request.form.getlist('date_of_birth'),
        "emails": request.form.getlist('email'),
        "linkedin": request.form.getlist('linkedin'),
        "twitter": request.form.getlist('twitter'),
        "facebook": request.form.getlist('facebook'),
        "instagram": request.form.getlist('instagram')
    }
    
    # Filter out empty values
    for key in ['dates_of_birth', 'emails', 'linkedin', 'twitter', 'facebook', 'instagram']:
        person_data[key] = [item for item in person_data[key] if item.strip()]
    
    current_project["people"].append(person_data)
    save_project()
    
    return redirect(url_for('dashboard'))

@app.route('/update_person/<int:person_id>', methods=['POST'])
def update_person(person_id):
    """Update an existing person's information"""
    if 0 <= person_id < len(current_project["people"]):
        # Process names - more complex as they are objects
        names = []
        first_names = request.form.getlist('first_name')
        middle_names = request.form.getlist('middle_name')
        last_names = request.form.getlist('last_name')
        
        # Make sure all lists have the same length by padding with empty strings
        max_length = max(len(first_names), len(middle_names), len(last_names))
        first_names = pad_list(first_names, max_length)
        middle_names = pad_list(middle_names, max_length)
        last_names = pad_list(last_names, max_length)
        
        for i in range(max_length):
            if first_names[i].strip() or last_names[i].strip():  # At least first or last name should be present
                names.append({
                    "first_name": first_names[i],
                    "middle_name": middle_names[i],
                    "last_name": last_names[i]
                })
        
        person_data = {
            "id": current_project["people"][person_id].get("id", generate_unique_id()),
            "names": names,
            "dates_of_birth": request.form.getlist('date_of_birth'),
            "emails": request.form.getlist('email'),
            "linkedin": request.form.getlist('linkedin'),
            "twitter": request.form.getlist('twitter'),
            "facebook": request.form.getlist('facebook'),
            "instagram": request.form.getlist('instagram')
        }
        
        # Filter out empty values
        for key in ['dates_of_birth', 'emails', 'linkedin', 'twitter', 'facebook', 'instagram']:
            person_data[key] = [item for item in person_data[key] if item.strip()]
        
        current_project["people"][person_id] = person_data
        save_project()
        return redirect(url_for('dashboard'))
    return jsonify({"error": "Person not found"}), 404

def pad_list(lst, length):
    """Helper function to pad a list to a specified length with empty strings"""
    return lst + [''] * (length - len(lst))

@app.route('/delete_person/<int:person_id>', methods=['POST'])
def delete_person(person_id):
    """Delete a person from the project"""
    if 0 <= person_id < len(current_project["people"]):
        del current_project["people"][person_id]
        save_project()
        return redirect(url_for('dashboard'))
    return jsonify({"error": "Person not found"}), 404

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

if __name__ == '__main__':
    # Create projects directory if it doesn't exist
    if not os.path.exists('projects'):
        os.makedirs('projects')
    
    app.run(debug=True)