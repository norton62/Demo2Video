from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import queue
import logging
from collections import deque
import os
import json
import configparser
import secrets
from threading import Lock

app = Flask(__name__)

# Load configuration and set secret key
def load_config():
    config = configparser.ConfigParser()
    if os.path.exists('config.ini'):
        config.read('config.ini')
        video_generate_only_conf = config.get('Video','video_generate_only')
        # Use password from config as base for secret key, or generate one
        if config.has_option('Web', 'password'):
            password = config.get('Web', 'password')
            # Create a secret key based on the password
            app.secret_key = f"demo2video_{password}_{secrets.token_hex(16)}"
        else:
            # Generate a random secret key
            app.secret_key = secrets.token_hex(32)
    else:
        # Fallback secret key
        app.secret_key = secrets.token_hex(32)
        logging.error("No access to ini")
        video_generate_only_conf = True

load_config()

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

demo_queue = queue.Queue()

current_status = {
    "status": "Idle",
    "suspect": "",
    "step": "Waiting for a new demo to be submitted."
}

RESULTS_FILE = 'results.json'
completed_jobs = deque(maxlen=250) # results.json now saves 250 entries instead of 50
results_lock = Lock()

def save_results():
    with results_lock:
        try:
            with open(RESULTS_FILE, 'w') as f:
                json.dump(list(completed_jobs), f, indent=4)
            logging.info(f"Successfully saved {len(completed_jobs)} results to {RESULTS_FILE}")
        except Exception as e:
            logging.error(f"Failed to save results to {RESULTS_FILE}: {e}")

def load_results():
    with results_lock:
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, 'r') as f:
                try:
                    content = f.read()
                    if content:
                        results_list = json.loads(content)
                        completed_jobs.extend(results_list)
                        logging.info(f"Loaded {len(completed_jobs)} previous results from {RESULTS_FILE}")
                except json.JSONDecodeError:
                    logging.error(f"Could not decode JSON from {RESULTS_FILE}. Starting with empty results.")
        else:
            logging.info(f"{RESULTS_FILE} not found. Starting with empty results.")

# The /login and /logout routes are no longer needed.

@app.route('/')
def index():
    # No login check is needed.
    return render_template("index.html")

@app.route('/add_demo', methods=['POST'])
def add_demo():
    # No login check is needed.
    share_code = request.form.get('share_code')
    suspect_steam_id = request.form.get('suspect_steam_id')
    submitted_by = request.form.get('submitted_by')
    youtube_upload = request.form.get('youtube_upload').lower() in ['True','true']

    # Personal QoL code
    # if(submitted_by == "538676037559517205" or submitted_by == 538676037559517205):
    #    submitted_by = "OeschMe"

    if not all([share_code, suspect_steam_id, submitted_by]):
        return jsonify({"success": False, "message": "All fields are required."}), 400

    job = {"share_code": share_code, "suspect_steam_id": suspect_steam_id, "submitted_by": submitted_by, "youtube_upload": youtube_upload}
    demo_queue.put(job)
    logging.info(f"Added new job to queue: {job}")
    
    return jsonify({"success": True, "message": "Demo added to the queue."})

@app.route('/run')
def run_hyperlink():
    """
    Hyperlink runner that accepts URL parameters and automatically adds a job to the queue.
    
    Example URL: http://localhost:5001/run?demo=CSGO-87xm7-dtW7U-s9Ubx-sRc3X-BZAYN&steam64=76561198872751464&name=Soul
    Or with demo URL: http://localhost:5001/run?demo=http://replay129.valve.net/730/003767354559668683295_1542993054.dem.bz2&steam64=76561198872751464&name=Soul
    """
    config = configparser.ConfigParser()
    if os.path.exists('config.ini'):
        config.read('config.ini')
        video_generate_only_conf = config.get('Video','video_generate_only')
    demo = request.args.get('demo')
    steam64 = request.args.get('steam64')
    name = request.args.get('name')
    youtube_upload = request.args.get('youtube_upload', '')
    if(youtube_upload == ""):
        if(video_generate_only_conf != True):
            youtube_upload = True
        else:
            youtube_upload = False


    # Personal QoL code
    # if(submitted_by == "538676037559517205" or submitted_by == 538676037559517205):
    #    submitted_by = "OeschMe
    
    if not all([demo, steam64, name]):
        missing_params = []
        if not demo: missing_params.append('demo')
        if not steam64: missing_params.append('steam64')
        if not name: missing_params.append('name')
        
        error_msg = f"Missing required parameters: {', '.join(missing_params)}"
        flash(error_msg, 'error')
        return redirect(url_for('index'))
    
    if not steam64.isdigit() or len(steam64) != 17:
        flash('Invalid Steam64 ID format. Must be 17 digits.', 'error')
        return redirect(url_for('index'))
    
    job = {
        "share_code": demo,
        "suspect_steam_id": steam64,
        "submitted_by": name,
        "youtube_upload": youtube_upload
    }
    
    try:
        demo_queue.put(job)
        logging.info(f"Added new job to queue via hyperlink: {job}")
        flash(f'Demo successfully added to queue for suspect {steam64} (submitted by {name})', 'success')
    except Exception as e:
        logging.error(f"Failed to add job via hyperlink: {e}")
        flash('Failed to add demo to queue. Please try again.', 'error')
    
    return redirect(url_for('index'))

@app.route('/status')
def status():
    # No login check is needed.
    queued_jobs = list(demo_queue.queue)
    results = list(completed_jobs) 
    return jsonify({
        "current_job": current_status,
        "queue": queued_jobs,
        "results": results 
    })

def run_web_server(): # Password parameter is removed
    load_results()
    # No need to set the password in the app config.
    app.run(host='0.0.0.0', port=5001)
