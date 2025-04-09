import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import threading
import scapy.all as scapy
import socket
import psutil
from queue import Queue
from ipaddress import IPv4Network

queue = Queue()
devices = {}
default_port_range = (1, 1024)

def get_network_interfaces():
    interfaces = {}
    list_interfaces = psutil.net_if_addrs()
    for interface, addrs in list_interfaces.items():
        for addr in addrs:
            if addr.family == socket.AF_INET:  # Check if the address is IPv4
                interfaces[interface] = {'ip': addr.address, 'netmask': addr.netmask}
                break  # Stop after the first IPv4 address is found
    return interfaces

def calculate_network_range(ip, netmask):
    network = IPv4Network(f"{ip}/{netmask}", strict=False)
    return str(network)

def scan_network(network, interface):
    global devices
    devices = {}
    arp_request = scapy.ARP(pdst=network)
    broadcast = scapy.Ether(dst="ff:ff:ff:ff:ff:ff")
    arp_request_broadcast = broadcast / arp_request
    answered = scapy.srp(arp_request_broadcast, timeout=2, iface=interface, verbose=False)[0]
    
    for sent, received in answered:
        devices[received.psrc] = {"mac": received.hwsrc, "ports": []}
    return devices

def port_scan(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect((ip, port))
        sock.close()
        return True
    except:
        return False

def fill_queue(ips, ports):
    for ip in ips:
        for port in ports:
            queue.put((ip, port))

def worker():
    global devices
    while not queue.empty():
        ip, port = queue.get()
        if port_scan(ip, port):
            devices[ip]["ports"].append(port)
        queue.task_done()

def start_scan(network, port_range, interface):
    scan_network(network, interface)
    ips = list(devices.keys())
    ports = range(port_range[0], port_range[1] + 1)
    fill_queue(ips, ports)
    
    threads = []
    for _ in range(100):
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()
    queue.join()

def create_dash_app(flask_app):
    dash_app = dash.Dash(
        __name__,
        server=flask_app,
        url_base_pathname='/dash/',
        external_stylesheets=["https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css"]
    )

    interfaces = get_network_interfaces()
    options = [{'label': f"{iface} - {info['ip']}", 'value': iface} for iface, info in interfaces.items()]

    dash_app.layout = html.Div(className="container mt-5", children=[
        html.H1("Network Scanner Dashboard", className="text-center mb-4"),
        html.Div(className="row mb-3", children=[
            html.Div(className="col-md-6", children=[
                dcc.Dropdown(id="interface-dropdown", options=options, placeholder="Select Network Interface")
            ]),
            html.Div(className="col-md-3", children=[
                dcc.Input(id="port-start", type="number", className="form-control", placeholder="Start Port", min=1, max=65535, value=default_port_range[0])
            ]),
            html.Div(className="col-md-3", children=[
                dcc.Input(id="port-end", type="number", className="form-control", placeholder="End Port", min=1, max=65535, value=default_port_range[1])
            ]),
            html.Div(className="col-md-2", children=[
                html.Button("Start Scan", id="scan-button", n_clicks=0, className="btn btn-primary w-100")
            ])
        ]),
        dcc.Interval(id='interval', interval=2000, n_intervals=0),
        html.Div(className="card shadow mt-4", children=[
            html.Div(className="card-body", children=[
                html.H4("Scan Results", className="card-title"),
                dash_table.DataTable(
                    id='result-table',
                    columns=[
                        {'name': 'IP', 'id': 'ip'},
                        {'name': 'MAC Address', 'id': 'mac'},
                        {'name': 'Open Ports', 'id': 'ports'}
                    ],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'center', 'padding': '10px'},
                    style_header={'backgroundColor': '#007bff', 'color': 'white', 'fontWeight': 'bold'}
                )
            ])
        ])
    ])

    @dash_app.callback(Output('interval', 'disabled'),
                    Input('scan-button', 'n_clicks'),
                    State('interface-dropdown', 'value'),
                    State('port-start', 'value'),
                    State('port-end', 'value'))
    def trigger_scan(n_clicks, interface, port_start, port_end):
        if n_clicks > 0 and interface and port_start and port_end:
            ip = interfaces[interface]['ip']
            netmask = interfaces[interface]['netmask']
            network = calculate_network_range(ip, netmask)
            threading.Thread(target=start_scan, args=(network, (port_start, port_end), interface)).start()
        return False

    @dash_app.callback(Output('result-table', 'data'), Input('interval', 'n_intervals'))
    def update_table(n_intervals):
        data = []
        for ip, info in devices.items():
            data.append({'ip': ip, 'mac': info['mac'], 'ports': ', '.join(map(str, info['ports']))})
        return data

    return dash_app