import yaml
import os
import re

def load_config(config_path='data_config.yaml'):
    """Load the configuration from the YAML file"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config

def get_section_by_id(config, section_id):
    """Get a section by its ID"""
    for section in config['sections']:
        if section['id'] == section_id:
            return section
    return None

def get_field_by_id(section, field_id):
    """Get a field by its ID within a section"""
    for field in section['fields']:
        if field['id'] == field_id:
            return field
    return None

def get_field_path(section_id, field_id):
    """Generate a consistent path string for a field"""
    return f"{section_id}.{field_id}"

def get_component_path(section_id, field_id, component_id):
    """Generate a consistent path string for a component"""
    return f"{section_id}.{field_id}.{component_id}"

def format_url(field, data):
    """Format URL according to the field's url_format if available"""
    if 'url_format' not in field:
        return data
    
    url_format = field['url_format']
    # Replace placeholders in the format string
    for placeholder in re.findall(r'\{(\w+)\}', url_format):
        if placeholder in data:
            url_format = url_format.replace(f"{{{placeholder}}}", data[placeholder])
    
    return url_format

def get_all_field_paths(config):
    """Get all possible field paths from the configuration"""
    paths = []
    for section in config['sections']:
        section_id = section['id']
        for field in section['fields']:
            field_id = field['id']
            path = get_field_path(section_id, field_id)
            paths.append(path)
            
            # Add component paths if any
            if 'components' in field:
                for component in field['components']:
                    component_id = component['id']
                    component_path = get_component_path(section_id, field_id, component_id)
                    paths.append(component_path)
    
    return paths

def get_field_input_type(field):
    """Get the HTML input type for a field based on its type"""
    field_type = field.get('type', 'string')
    
    type_mapping = {
        'string': 'text',
        'email': 'email',
        'url': 'url',
        'date': 'date',
        'number': 'number',
        'comment': 'textarea',
        'password': 'password'
    }
    
    return type_mapping.get(field_type, 'text')

def initialize_person_data():
    """Create an empty person data structure based on the configuration"""
    config = load_config()
    person_data = {}
    
    for section in config['sections']:
        section_id = section['id']
        person_data[section_id] = {}
        
        for field in section['fields']:
            field_id = field['id']
            if field.get('multiple', False):
                person_data[section_id][field_id] = []
            else:
                person_data[section_id][field_id] = None
    
    return person_data