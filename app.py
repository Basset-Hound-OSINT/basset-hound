from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
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
        return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Main dashboard for managing people"""
    return render_template('dashboard.html', project=current_project)

@app.route('/get_people')
def get_people():
    """API endpoint to get all people in the project"""
    return jsonify(current_project["people"])

@app.route('/get_person/<int:person_id>')
def get_person(person_id):
    """API endpoint to get a specific person's details"""
    if 0 <= person_id < len(current_project["people"]):
        return jsonify(current_project["people"][person_id])
    return jsonify({"error": "Person not found"}), 404

@app.route('/add_person', methods=['POST'])
def add_person():
    """Add a new person to the project"""
    person_data = {
        "first_name": request.form.get('first_name', ''),
        "middle_name": request.form.get('middle_name', ''),
        "last_name": request.form.get('last_name', ''),
        "date_of_birth": request.form.get('date_of_birth', '')
    }
    
    current_project["people"].append(person_data)
    save_project()
    
    return redirect(url_for('dashboard'))

@app.route('/update_person/<int:person_id>', methods=['POST'])
def update_person(person_id):
    """Update an existing person's information"""
    if 0 <= person_id < len(current_project["people"]):
        current_project["people"][person_id] = {
            "first_name": request.form.get('first_name', ''),
            "middle_name": request.form.get('middle_name', ''),
            "last_name": request.form.get('last_name', ''),
            "date_of_birth": request.form.get('date_of_birth', '')
        }
        save_project()
        return redirect(url_for('dashboard'))
    return jsonify({"error": "Person not found"}), 404

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