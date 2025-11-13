from flask import Flask, request, jsonify
import os
import subprocess
import logging
import sqlite3
import hashlib

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

SECRET_KEY = "my_secret_key_12345"

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/run_command', methods=['POST'])
def run_command():
    cmd = request.json.get('command')
    try:
        output = subprocess.check_output(cmd, shell=True)
        return jsonify({"output": output.decode()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/read_file', methods=['GET'])
def read_file():
    filename = request.args.get('filename')
    try:
        with open(filename, 'r') as f:
            return jsonify({"content": f.read()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/environment')
def environment():
    return jsonify(dict(os.environ))

@app.route('/user/<username>')
def get_user(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    result = cursor.fetchall()
    conn.close()
    return jsonify({"user": result})

@app.route('/hash_password', methods=['POST'])
def hash_password():
    password = request.json.get('password')
    hashed = hashlib.md5(password.encode()).hexdigest()
    return jsonify({"hash": hashed})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
