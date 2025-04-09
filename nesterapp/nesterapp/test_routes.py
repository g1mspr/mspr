from flask import Blueprint, render_template, request

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('login.html')

@main.route('/login')
def login():
    return render_template('login.html')

@main.route('/accueil')
def accueil():
    return render_template('index.html')

@main.route('/sonde1')
def sonde1_page():
    return render_template('sonde1.html')
    # selected_value = request.args.get('sonde1.html')
    
    # return f"Vous avez sélectionné : {selected_value}"

@main.route('/sonde2')
def sonde2_page():
    selected_value = request.args.get('sonde2.html')
    
    return f"Vous avez sélectionné : {selected_value}"

@main.route('/sonde3')
def sonde3_page():
    selected_value = request.args.get('sonde3.html')
    
    return f"Vous avez sélectionné : {selected_value}"