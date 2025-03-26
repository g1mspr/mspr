from flask import render_template, Flask, request, jsonify

app = Flask(__name__)

@app.route('/')

def index():

    return render_template('index.html')

@app.route('/sonde1', methods=['POST'])

def sonde1():
    data = request.get_json()
    if data:
        return render_template('sonde1.html')
    else:
        return render_template('sonde1.html')

@app.route('/sonde2')

def sonde2():

    return render_template('sonde2.html')

@app.route('/sonde3')

def sonde3():

    return render_template('sonde3.html')