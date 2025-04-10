import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import threading
import scapy.all as scapy
import socket
import psutil
from queue import Queue
from ipaddress import IPv4Network
import sqlite3
import os
from datetime import datetime  # Pour gérer la date/heure

queue = Queue()
devices = {}              # Garde éventuellement les résultats en mémoire
default_port_range = (1, 1024)

############################
# PARTIE BASE DE DONNÉES
############################

DB_FILE = "scan_results.db"

def init_db():
    """Initialise la base SQLite et crée la table devices si elle n'existe pas."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Ajout d'une colonne scan_date pour mémoriser la date du scan
    cur.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        ip         TEXT,
        mac        TEXT,
        port       TEXT,
        scan_date  TEXT
    )
    """)
    conn.commit()
    conn.close()

def clear_db():
    """Efface les anciennes données de la table devices."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM devices")
    conn.commit()
    conn.close()

def insert_open_port(ip, mac, port):
    """
    Insère un enregistrement (ip, mac, port, scan_date) dans la table devices.
    Le port est stocké au format texte.
    La date du scan est insérée en utilisant la date/heure actuelle.
    """
    scan_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # On convertit le port en texte (str) pour coller à la colonne port TEXT
    cur.execute(
        "INSERT INTO devices (ip, mac, port, scan_date) VALUES (?, ?, ?, ?)",
        (ip, mac, str(port), scan_date)
    )
    conn.commit()
    conn.close()

def get_scan_results():
    """
    Récupère les données depuis la base SQLite et les regroupe par IP, MAC et scan_date,
    concaténant les ports ouverts en une seule chaîne.
    """
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # On ajoute scan_date dans le GROUP BY pour distinguer les éventuels scans effectués à des moments différents
    cur.execute("""
        SELECT ip, mac, scan_date, GROUP_CONCAT(port, ', ') AS ports
        FROM devices
        GROUP BY ip, mac, scan_date
        ORDER BY ip, scan_date
    """)
    rows = cur.fetchall()
    conn.close()

    # rows est une liste de tuples (ip, mac, scan_date, 'port1, port2, ...')
    results = []
    for row in rows:
        ip_val, mac_val, scan_date_val, ports_val = row
        results.append({
            'ip': ip_val,
            'mac': mac_val,
            'ports': ports_val if ports_val else "",
            'scan_date': scan_date_val
        })
    return results

###########################
# FONCTIONS DE SCAN
###########################

def get_network_interfaces():
    interfaces = {}
    list_interfaces = psutil.net_if_addrs()
    for interface in list_interfaces.keys():
        # Vérifie qu’il y ait une adresse IPv4
        if len(list_interfaces[interface]) > 1:
            addr = list_interfaces[interface][1]
            if addr.family == socket.AF_INET:
                interfaces[interface] = {
                    'ip': addr.address, 
                    'netmask': addr.netmask
                }
    return interfaces

def calculate_network_range(ip, netmask):
    network = IPv4Network(f"{ip}/{netmask}", strict=False)
    return str(network)

def scan_network(network):
    """
    Scan ARP pour récupérer l'IP et MAC de chaque hôte actif.
    Met à jour le dictionnaire devices en mémoire.
    """
    global devices
    devices = {}
    arp_request = scapy.ARP(pdst=network)
    broadcast = scapy.Ether(dst="ff:ff:ff:ff:ff:ff")
    arp_request_broadcast = broadcast / arp_request
    answered = scapy.srp(arp_request_broadcast, timeout=2, verbose=False)[0]
    
    for sent, received in answered:
        devices[received.psrc] = {"mac": received.hwsrc, "ports": []}
    return devices

def port_scan(ip, port):
    """Teste si un port est ouvert en se connectant (TCP)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect((ip, port))
        sock.close()
        return True
    except:
        return False

def fill_queue(ips, ports):
    """Remplit la file d'attente (queue) avec le couple (ip, port) pour test."""
    for ip in ips:
        for port in ports:
            queue.put((ip, port))

def worker():
    """
    Fonction exécutée par chaque thread.
    Récupère (ip, port) dans la queue, teste l'ouverture de port, puis enregistre si ouvert.
    """
    global devices
    while not queue.empty():
        ip, port = queue.get()
        if port_scan(ip, port):
            # Mémorisation en mémoire
            devices[ip]["ports"].append(port)
            # Insertion dans la BDD (port en texte + date)
            insert_open_port(ip, devices[ip]["mac"], port)
        queue.task_done()

def start_scan(network, port_range):
    """
    Lance le scan ARP pour détecter les hôtes, puis lance le scan des ports.
    """
    # On vide la table devices pour repartir sur des données vierges
    clear_db()
    # Scan ARP pour remplir devices
    scan_network(network)

    ips = list(devices.keys())
    ports = range(port_range[0], port_range[1] + 1)
    fill_queue(ips, ports)
    
    threads = []
    for _ in range(50):  # 50 threads, ajustez selon votre machine
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()
    queue.join()

##########################
# APPLICATION DASH
##########################

def create_dash_app(flask_app):
    # Initialiser la base de données (crée la table si elle n’existe pas déjà)
    init_db()

    dash_app = dash.Dash(
        __name__,
        server=flask_app,
        url_base_pathname='/dash/',
        external_stylesheets=[
            "https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css"
        ]
    )

    interfaces = get_network_interfaces()
    options = [
        {'label': f"{iface} - {info['ip']}", 'value': iface} 
        for iface, info in interfaces.items()
    ]

    dash_app.layout = html.Div(className="container mt-5", children=[
        html.H1("Dashboard Scanner du Harverster", className="text-center mb-4"),

        html.Div(className="row mb-3", children=[
            html.Div(className="col-md-6", children=[
                dcc.Dropdown(
                    id="interface-dropdown",
                    options=options,
                    placeholder="Select Network Interface"
                )
            ]),
            html.Div(className="col-md-3", children=[
                dcc.Input(
                    id="port-start",
                    type="number",
                    className="form-control",
                    placeholder="Start Port",
                    min=1, max=65535,
                    value=default_port_range[0]
                )
            ]),
            html.Div(className="col-md-3", children=[
                dcc.Input(
                    id="port-end",
                    type="number",
                    className="form-control",
                    placeholder="End Port",
                    min=1, max=65535,
                    value=default_port_range[1]
                )
            ]),
            html.Div(className="col-md-2 mt-3", children=[
                html.Button(
                    "Start Scan",
                    id="scan-button",
                    n_clicks=0,
                    className="btn btn-primary w-100"
                )
            ])
        ]),

        # Interval pour rafraîchir la table
        dcc.Interval(id='interval', interval=2000, n_intervals=0),

        html.Div(className="card shadow mt-4", children=[
            html.Div(className="card-body", children=[
                html.H4("Scan Results", className="card-title"),
                dash_table.DataTable(
                    id='result-table',
                    columns=[
                        {'name': 'IP', 'id': 'ip'},
                        {'name': 'MAC Address', 'id': 'mac'},
                        {'name': 'Open Ports', 'id': 'ports'},
                        {'name': 'Scan Date', 'id': 'scan_date'}
                    ],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'center', 'padding': '10px'},
                    style_header={'backgroundColor': '#007bff', 'color': 'white', 'fontWeight': 'bold'}
                )
            ])
        ])
    ])

    # Callback pour déclencher le scan
    @dash_app.callback(
        Output('interval', 'disabled'),
        Input('scan-button', 'n_clicks'),
        State('interface-dropdown', 'value'),
        State('port-start', 'value'),
        State('port-end', 'value')
    )
    def trigger_scan(n_clicks, interface, port_start, port_end):
        if n_clicks > 0 and interface and port_start and port_end:
            ip = interfaces[interface]['ip']
            netmask = interfaces[interface]['netmask']
            network = calculate_network_range(ip, netmask)
            # On lance le scan dans un thread pour ne pas bloquer l’UI
            threading.Thread(
                target=start_scan,
                args=(network, (port_start, port_end))
            ).start()
        # Retourne False pour ne pas désactiver l'interval
        return False

    # Callback pour mettre à jour les résultats
    @dash_app.callback(
        Output('result-table', 'data'),
        Input('interval', 'n_intervals')
    )
    def update_table(n_intervals):
        # On récupère les données depuis la base SQLite
        data = get_scan_results()
        return data

    return dash_app
