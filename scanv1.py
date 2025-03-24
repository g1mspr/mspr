import threading
from queue import Queue
import scapy.all as scapy
import socket
import psutil
import ipaddress

def scan_network(network, interface):
    arp_request = scapy.ARP(pdst=str(network)) # Create an ARP request object with the network given
    broadcast = scapy.Ether(dst="ff:ff:ff:ff:ff:ff") # Create a broadcast object
    arp_request_broadcast = broadcast/arp_request
    answered_list = scapy.srp(arp_request_broadcast, timeout=1, iface=interface, verbose=False)[0] # Send the ARP broadcast request and receive the response
    devices = {}  #Create a dictionary to store the devices the ports will filled in the worker function

    for device in answered_list:    
        devices[device[1].psrc] = {"mac": device[1].hwsrc, "ports": []} # Store the IP (keys), MAC and open ports (values) in the dictionary
    return devices
    
def fill_queue(ips, ports):
    for ip in ips:  # Loop through the IPs and the ports
        for port in ports:
            queue.put((ip, port)) # Add them to the queue

def scan_port(ip, port):
    try:    # try the socket connection to get a True or false return on the connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    # Create a socket object
        sock.settimeout(1)  # Set the timeout to 1 second
        sock.connect((ip, port)) # Connect to the IP and port
        sock.close()    # Close the socket
        return True
    except:
        return False
        

def worker(devices):
    while not queue.empty(): # As long as the queue is not empty it will get the ip and port from the queue
        ip, port = queue.get() 
        result = scan_port(ip, port) # Scan the port for each ip and port in the queue and return the result (True or False)
        if result:
            print(f"Port {port} is open on {ip}") ## to remove
            devices[ip]["ports"].append(port) # Add the open port to the dictionary created before
        queue.task_done()
        

def main():  

    interfaces = psutil.net_if_addrs()  # Get all the interface on the computer
    for interface in interfaces.keys():        # loop on the interfaces and only print their name (the key in the dictionary)
        print(f"{interface} - {interfaces[interface][1][1]}" ) # affiche le nom de l'interface et l'IP associé

    chosen_interface = input("Entrer l'interface voulue : ") # Ask the user wich interface he wants to use
    ip_interface = interfaces[chosen_interface][1][1] # store the ip of the chosen interface
    mask_interface = interfaces[chosen_interface][1][2] # store the mask of the chosen interface

    network = ipaddress.IPv4Network(((ip_interface, mask_interface)), strict=False) # Transform the pair of ip/mask their network address

    ports = range(1, 1024)  ## to change to get the value from the user in a graphical way

    devices = scan_network(network, chosen_interface) # Get the devices from the network

    if devices:
        ips = devices.keys() # get the ips from the devices (ip is the key in the dictionary)
        fill_queue(ips, ports) # Fill the queue with the ips and ports
        for _ in range(500):   # Create 500 threads to work on the queue
            threads = threading.Thread(target=worker, args=(devices,)) # Create a thread for the worker function
            threads.start() # start the thread
    else:
        print("No devices found on the netwotk") ## to change or even remove 

    return devices


queue = Queue() # Create the queue object
resutl = main() # Call the main function
queue.join() # Wait for the queue to be done before going on with the code
print(resutl)