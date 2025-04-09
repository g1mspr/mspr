from flask import Flask, render_template
from dash_app import create_dash_app
import time
import requests
import os
from threading import Thread
from dotenv import load_dotenv

# Load environment variables from the .env file in the current directory
load_dotenv()

# Retrieve configuration values from environment variables
url = os.environ.get("URL", "https://seahawks.nfl-it.local")
url = url + "/api/online"
probe_id = int(os.environ.get("PROBE_ID", 0))

# Set headers and payload using the environment variable
headers = {
    "Content-Type": "application/json"
}
payload = {
    "probe_id": probe_id,
}

app = Flask(__name__)
dash_app = create_dash_app(app)

@app.route('/')
def index():
    return render_template('index.html')

def send_requests():
    """Background task to periodically send a POST request."""
    while True:
        try:
            response = requests.post(url, headers=headers, json=payload)
            print(f"Sent POST request. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error sending POST request: {e}")
        time.sleep(5)  # Wait for 5 seconds before sending the next request

if __name__ == '__main__':
    # Start the background task in daemon mode so that it terminates when the main thread does
    thread = Thread(target=send_requests, daemon=True)
    thread.start()
    
    # Start the Flask application
    app.run(host="0.0.0.0", port=8000, debug=True)
    
