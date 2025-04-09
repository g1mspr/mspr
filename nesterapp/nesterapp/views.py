from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)
DATABASE = 'data.db'

def get_db_connection():
    """Establish a SQLite database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This allows us to fetch rows as dictionaries.
    return conn

# -------------------------------
# Rendered View Endpoints
# -------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sonde1', methods=['GET', 'POST'])
def sonde1():
    # Optionally process JSON data if a POST is made.
    data = request.get_json()
    # Here you can add further processing logic based on data.
    return render_template('sonde1.html')

@app.route('/sonde2')
def sonde2():
    return render_template('sonde2.html')

@app.route('/sonde3')
def sonde3():
    return render_template('sonde3.html')

# -------------------------------
# API Endpoints for Scans Table
# -------------------------------

@app.route('/api/scans', methods=['GET'])
def get_scans():
    """Retrieve all scan records."""
    conn = get_db_connection()
    scans = conn.execute("SELECT * FROM scans").fetchall()
    conn.close()
    scans_list = [dict(scan) for scan in scans]
    return jsonify(scans_list)

@app.route('/api/scans/<int:scan_id>', methods=['GET'])
def get_scan(scan_id):
    """Retrieve a single scan record by ID."""
    conn = get_db_connection()
    scan = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()
    if scan is None:
        return jsonify({'error': 'Scan not found'}), 404
    return jsonify(dict(scan))

@app.route('/api/scans', methods=['POST'])
def create_scan():
    """Create a new scan record."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    # Required fields for a new scan.
    required = ['probe_id', 'ip_address', 'mac_address', 'ports', 'scan_date']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scans (probe_id, ip_address, mac_address, ports, scan_date)
        VALUES (?, ?, ?, ?, ?)
    """, (data['probe_id'], data['ip_address'], data['mac_address'], data['ports'], data['scan_date']))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({'message': 'Scan created', 'id': new_id}), 201

# -------------------------------
# API Endpoints for Online Table
# -------------------------------

@app.route('/api/online', methods=['GET'])
def get_online_records():
    """Retrieve all online records."""
    conn = get_db_connection()
    records = conn.execute("SELECT * FROM online").fetchall()
    conn.close()
    online_list = [dict(record) for record in records]
    return jsonify(online_list)

@app.route('/api/online', methods=['POST'])
def create_online_record():
    """Insert a new online record. 'ping_date' is optional as it defaults to the current time."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    required = ['probe_id']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required field: probe_id'}), 400

    # Use provided ping_date or default to the current time.
    ping_date = data.get('ping_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO online (probe_id, ping_date)
        VALUES (?, ?)
    """, (data['probe_id'], ping_date))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({'message': 'Online record created', 'id': new_id}), 201

# -------------------------------
# Main Entry Point
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)
