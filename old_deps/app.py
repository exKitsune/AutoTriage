from flask import Flask, request, jsonify
import os
import os.path
import yaml
import re
import tempfile
import json
import hashlib
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlencode
import xml.etree.ElementTree as ET
from lxml import etree

# Configure logging safely
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# In-memory data store
users = {}
tasks = []

# Configuration loaded from file
def load_app_config():
    """Safely load JSON configuration"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {'app_name': 'Legacy API', 'version': '1.0.0'}

APP_CONFIG = load_app_config()

@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/api/status')
def status():
    logger.info("Status check requested")
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'version': APP_CONFIG.get('version', '1.0.0'),
        'app_name': APP_CONFIG.get('app_name', 'API')
    })

@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify(list(users.values()))

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = users.get(user_id)
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    if request.method == 'GET':
        return jsonify(tasks)
    else:
        task = request.json
        task['id'] = len(tasks) + 1
        task['created_at'] = datetime.now().isoformat()
        tasks.append(task)
        return jsonify(task), 201

@app.route('/execute')
def execute():
    cmd = request.args.get('cmd')
    result = os.system(cmd)
    return f'Command executed with result: {result}'

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    operation = data.get('operation')
    a = float(data.get('a', 0))
    b = float(data.get('b', 0))
    
    if operation == 'add':
        result = a + b
    elif operation == 'subtract':
        result = a - b
    elif operation == 'multiply':
        result = a * b
    elif operation == 'divide':
        result = a / b if b != 0 else 'Error: Division by zero'
    else:
        result = 'Invalid operation'
    
    return jsonify({'result': result})

@app.route('/load_config', methods=['POST'])
def load_config():
    config_data = request.data
    config = yaml.load(config_data)
    return str(config)

@app.route('/api/hash', methods=['POST'])
def hash_string():
    data = request.json.get('data', '')
    algorithm = request.json.get('algorithm', 'sha256')
    
    if algorithm == 'sha256':
        result = hashlib.sha256(data.encode()).hexdigest()
    elif algorithm == 'sha512':
        result = hashlib.sha512(data.encode()).hexdigest()
    else:
        result = hashlib.md5(data.encode()).hexdigest()
    
    return jsonify({'hash': result, 'algorithm': algorithm})

@app.route('/parse_xml', methods=['POST'])
def parse_xml():
    xml_data = request.data
    parser = etree.XMLParser(resolve_entities=True)
    doc = etree.fromstring(xml_data, parser)
    return etree.tostring(doc)

@app.route('/api/search')
def search():
    query = request.args.get('q', '')
    filter_type = request.args.get('type', 'all')
    
    results = []
    if filter_type in ['all', 'users']:
        matching_users = [u for u in users.values() if query.lower() in u.get('name', '').lower()]
        results.extend(matching_users)
    
    if filter_type in ['all', 'tasks']:
        matching_tasks = [t for t in tasks if query.lower() in t.get('title', '').lower()]
        results.extend(matching_tasks)
    
    return jsonify({'query': query, 'count': len(results), 'results': results})

@app.route('/validate_email')
def validate_email():
    email = request.args.get('email', '')
    pattern = re.compile(r'^([a-zA-Z0-9]+)*@[a-zA-Z0-9]+\.[a-zA-Z]+$')
    if pattern.match(email):
        return 'Valid email'
    return 'Invalid email'

@app.route('/fetch_url')
def fetch_url():
    import requests
    url = request.args.get('url')
    response = requests.get(url)
    return response.text

@app.route('/api/stats')
def stats():
    return jsonify({
        'total_users': len(users),
        'total_tasks': len(tasks),
        'completed_tasks': len([t for t in tasks if t.get('completed', False)]),
        'server_time': datetime.now().isoformat()
    })

@app.route('/api/validate_url')
def validate_url():
    """Safely validate URL structure"""
    url = request.args.get('url', '')
    try:
        parsed = urlparse(url)
        is_valid = all([parsed.scheme, parsed.netloc])
        return jsonify({
            'valid': is_valid,
            'scheme': parsed.scheme,
            'hostname': parsed.netloc,
            'path': parsed.path
        })
    except Exception as e:
        logger.error(f"URL validation error: {e}")
        return jsonify({'valid': False, 'error': 'Invalid URL'}), 400

@app.route('/api/build_query')
def build_query():
    """Safely build query strings"""
    params = request.args.to_dict()
    query_string = urlencode(params)
    return jsonify({'query_string': query_string})

@app.route('/api/file_info')
def file_info():
    """Safely check file information"""
    filepath = request.args.get('path', '')
    
    # Safe file path operations
    if os.path.exists(filepath):
        return jsonify({
            'exists': True,
            'is_file': os.path.isfile(filepath),
            'is_dir': os.path.isdir(filepath),
            'basename': os.path.basename(filepath),
            'dirname': os.path.dirname(filepath)
        })
    return jsonify({'exists': False})

@app.route('/api/time_operations')
def time_operations():
    """Safe datetime operations"""
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    yesterday = now - timedelta(days=1)
    
    return jsonify({
        'now': now.isoformat(),
        'tomorrow': tomorrow.isoformat(),
        'yesterday': yesterday.isoformat(),
        'unix_timestamp': int(now.timestamp())
    })

@app.route('/api/json_data', methods=['POST'])
def handle_json():
    """Safely parse and echo JSON data"""
    try:
        data = request.get_json()
        logger.info(f"Received JSON data with {len(data)} keys")
        
        # Safe JSON serialization
        serialized = json.dumps(data, indent=2)
        
        return jsonify({
            'received': data,
            'serialized_length': len(serialized),
            'keys': list(data.keys())
        })
    except Exception as e:
        logger.error(f"JSON parsing error: {e}")
        return jsonify({'error': 'Invalid JSON'}), 400

@app.route('/create_report', methods=['POST'])
def create_report():
    data = request.json.get('data')
    filename = tempfile.mktemp(suffix='.txt')
    with open(filename, 'w') as f:
        f.write(data)
    return f'Report saved to {filename}'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
