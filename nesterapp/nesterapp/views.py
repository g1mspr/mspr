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

    return render_template('login.html')

@app.route('/login')

def login():

    return render_template('login.html')

@app.route('/accueil')

def accueil():
    conn = get_db_connection()
    # Get the most recent ping date per probe from the online table.
    # We assume the ping_date is stored as 'YYYY-MM-DD HH:MM:SS'
    probes_data = conn.execute(
        """
        SELECT probe_id, MAX(ping_date) as last_ping
        FROM online
        GROUP BY probe_id
        """
    ).fetchall()
    conn.close()

    probes = []
    now = datetime.now()
    # Process each probe to determine its status.
    for row in probes_data:
        # Parse the ping date
        last_ping = datetime.strptime(row["last_ping"], '%Y-%m-%d %H:%M:%S')
        # Determine if probe is online: within 10 seconds from now.
        status = "online" if (now - last_ping).total_seconds() <= 10 else "offline"
        probes.append({
            "probe_id": row["probe_id"],
            "last_ping": row["last_ping"],
            "status": status
        })

    # Pass the list of probes to the template
    return render_template('index.html', probes=probes)

@app.route('/probe')
def probe_detail():
    probe_id = request.args.get('id')
    if not probe_id:
        return "Probe ID is required", 400

    conn = get_db_connection()
    # Get all scans for the given probe. Use SQLite's date() to extract the date portion.
    query = """
        SELECT *, date(scan_date) as scan_day
        FROM scans
        WHERE probe_id = ?
        ORDER BY scan_date DESC
    """
    scans = conn.execute(query, (probe_id,)).fetchall()
    conn.close()

    # Group scans by date.
    grouped_scans = {}
    for scan in scans:
        day = scan['scan_day']
        if day not in grouped_scans:
            grouped_scans[day] = []
        grouped_scans[day].append(scan)

    # Sort the groups by date descending.
    sorted_groups = sorted(grouped_scans.items(), key=lambda x: x[0], reverse=True)
    
    return render_template('probe.html', probe_id=probe_id, grouped_scans=sorted_groups)


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
