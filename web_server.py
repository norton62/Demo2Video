from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import queue
import logging
from collections import deque
import os
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

demo_queue = queue.Queue()

current_status = {
    "status": "Idle",
    "suspect": "",
    "step": "Waiting for a new demo to be submitted."
}

RESULTS_FILE = 'results.json'
completed_jobs = deque(maxlen=50) 

def save_results():
    try:
        with open(RESULTS_FILE, 'w') as f:
            json.dump(list(completed_jobs), f, indent=4)
        logging.info(f"Successfully saved {len(completed_jobs)} results to {RESULTS_FILE}")
    except Exception as e:
        logging.error(f"Failed to save results to {RESULTS_FILE}: {e}")

def load_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'r') as f:
            try:
                results_list = json.load(f)
                completed_jobs.extend(results_list)
                logging.info(f"Loaded {len(completed_jobs)} previous results from {RESULTS_FILE}")
            except json.JSONDecodeError:
                logging.error(f"Could not decode JSON from {RESULTS_FILE}. Starting with empty results.")
    else:
        logging.info(f"{RESULTS_FILE} not found. Starting with empty results.")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password_attempt = request.form.get('password')
        if password_attempt == app.config['PASSWORD']:
            session['logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Incorrect password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/add_demo', methods=['POST'])
def add_demo():
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    share_code = request.form.get('share_code')
    # UPDATED: Get suspect_steam_id instead of suspect_name
    suspect_steam_id = request.form.get('suspect_steam_id')
    submitted_by = request.form.get('submitted_by')

    if not all([share_code, suspect_steam_id, submitted_by]):
        return jsonify({"success": False, "message": "All fields are required."}), 400

    job = {"share_code": share_code, "suspect_steam_id": suspect_steam_id, "submitted_by": submitted_by}
    demo_queue.put(job)
    logging.info(f"Added new job to queue: {job}")
    
    return jsonify({"success": True, "message": "Demo added to the queue."})

@app.route('/status')
def status():
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    queued_jobs = list(demo_queue.queue)
    results = list(completed_jobs) 
    return jsonify({
        "current_job": current_status,
        "queue": queued_jobs,
        "results": results 
    })

def run_web_server(password):
    load_results()
    app.config['PASSWORD'] = password
    app.run(host='0.0.0.0', port=5000)
