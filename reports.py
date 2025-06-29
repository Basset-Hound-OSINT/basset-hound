from flask import Blueprint, request, jsonify, send_from_directory, current_app
import os
from datetime import datetime
from uuid import uuid4

reports_bp = Blueprint('reports', __name__)

def get_reports_dir(current_project_id, person_id):
    return os.path.join("projects", current_project_id, "people", person_id, "reports")

@reports_bp.route('/person/<person_id>/reports', methods=['GET'])
def list_reports(person_id):
    current_project_id = current_app.config.get('CURRENT_PROJECT_ID')
    reports_dir = get_reports_dir(current_project_id, person_id)
    if not os.path.exists(reports_dir):
        return jsonify([])
    files = [f for f in os.listdir(reports_dir) if f.endswith('.md')]
    return jsonify(files)

@reports_bp.route('/person/<person_id>/reports/<report_name>', methods=['GET'])
def get_report(person_id, report_name):
    current_project_id = current_app.config.get('CURRENT_PROJECT_ID')
    reports_dir = get_reports_dir(current_project_id, person_id)
    return send_from_directory(reports_dir, report_name)

@reports_bp.route('/person/<person_id>/reports', methods=['POST'])
def create_report(person_id):
    current_project_id = current_app.config.get('CURRENT_PROJECT_ID')
    neo4j_handler = current_app.config['NEO4J_HANDLER']
    data = request.json
    toolname = data.get('toolname')
    content = data.get('content', '')
    date_str = datetime.now().strftime('%Y%m%d')
    unique_id = str(uuid4())[:8]
    report_name = f"{toolname}_{date_str}_{person_id}_{unique_id}.md"
    reports_dir = get_reports_dir(current_project_id, person_id)
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, report_name)
    with open(report_path, 'w') as f:
        f.write(content)
    # Register in Neo4j
    neo4j_handler.add_report_to_person(
        current_app.config['CURRENT_PROJECT_SAFE_NAME'],
        person_id,
        {
            "name": report_name,
            "path": report_name,
            "tool": toolname,
            "created_at": datetime.now().isoformat(),
            "id": unique_id
        }
    )
    return jsonify({"success": True, "report": report_name})

@reports_bp.route('/person/<person_id>/reports/<report_name>', methods=['PUT'])
def update_report(person_id, report_name):
    current_project_id = current_app.config.get('CURRENT_PROJECT_ID')
    reports_dir = get_reports_dir(current_project_id, person_id)
    report_path = os.path.join(reports_dir, report_name)
    if not os.path.exists(report_path):
        return jsonify({"error": "Report not found"}), 404
    content = request.json.get('content', '')
    with open(report_path, 'w') as f:
        f.write(content)
    return jsonify({"success": True})

@reports_bp.route('/person/<person_id>/reports/<report_name>', methods=['DELETE'])
def delete_report(person_id, report_name):
    current_project_id = current_app.config.get('CURRENT_PROJECT_ID')
    neo4j_handler = current_app.config['NEO4J_HANDLER']
    reports_dir = get_reports_dir(current_project_id, person_id)
    report_path = os.path.join(reports_dir, report_name)
    if os.path.exists(report_path):
        os.remove(report_path)
        neo4j_handler.remove_report_from_person(
            current_app.config['CURRENT_PROJECT_SAFE_NAME'],
            person_id,
            report_name
        )
        return jsonify({"success": True})
    return jsonify({"error": "Report not found"}), 404