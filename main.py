import sys
import os
import configparser
import logging
import time
import threading
import pyautogui
import shutil
import re
import datetime
import requests
import calendar

import csdm_cli_handler
import youtube_uploader
import demo_downloader
from obs_recorder import OBSRecorder
from web_server import demo_queue, current_status, completed_jobs, run_web_server, save_results
from demo_downloader import DemoExpiredException



def setup_logging():
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f"csdm_processor_{time.strftime('%Y-%m-%d_%H-%M-%S')}.log"
    log_filepath = os.path.join(log_dir, log_filename)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filepath, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def update_status(status, step, suspect=""):
    """Helper function to update the global status dictionary."""
    logging.info(f"STATUS UPDATE: {status} - {step} (Suspect: {suspect})")
    current_status["status"] = status
    current_status["step"] = step
    current_status["suspect"] = suspect

def extract_demo_name_from_url(demo_url_or_code):
    """Extract demo filename from URL or return share code."""
    if demo_downloader.is_demo_url(demo_url_or_code):
        # Extract filename from URL (e.g., "003767976009224159760_0501691362.dem.bz2")
        filename = demo_url_or_code.split('/')[-1]
        if filename.endswith('.dem.bz2'):
            return filename[:-8]  # Remove ".dem.bz2"
        elif filename.endswith('.dem'):
            return filename[:-4]  # Remove ".dem"
        else:
            return filename
    else:
        # Return share code as-is
        return demo_url_or_code

def getSteamname(suspect_steam_id):
    # Get name for S64ID from cswatch API
    cswresp = requests.get(f'https://cswatch.in/api/players/{suspect_steam_id}')
    cswdata = cswresp.json()

    if cswdata and 'player' in cswdata:
        if 'name' in cswdata['player']:
            steamname_unesc = cswdata['player']['name']
            if steamname_unesc == "Unknown Player":
                if 'leetifyPublicStats' in cswdata['player'] and 'name' in cswdata['player']['leetifyPublicStats']:
                    steamname_unesc = cswdata['player']['leetifyPublicStats']['name']
                else:
                    steamname_unesc = "No username available"
        else:
            steamname_unesc = "No username available"
    else:
        steamname_unesc = "No username available"

    # YouTube doesn't like some characters
    ret_steamname = steamname_unesc.translate(str.maketrans({
        "<": "-",
        ">": "-",
        "¯": "-",
        "\\": "-",
        "/": "-",
        "(": "-",
        ")": "-",
        "ツ": "-"
    }))

    return ret_steamname


def rename_video_with_suspect_info(source_file, steam64_id, demo_name):
    """Rename video file in place with suspect and demo information."""
    try:
        # Added timestamp
        gmt = time.gmtime()
        ts_for_name = calendar.timegm(gmt)
        steamname = getSteamname(steam64_id)

        source_dir = os.path.dirname(source_file)
        base_name = f"{steamname} - {steam64_id} - Highlights - {ts_for_name}" # Changed Youtube upload title 

        new_filename = f"{base_name}.mp4"
        new_path = os.path.join(source_dir, new_filename)
        
        # If file with target name doesn't exist, rename directly
        if not os.path.exists(new_path):
            os.rename(source_file, new_path)
            logging.info(f"Video renamed to: {new_path}")
            return new_path
        
        # Find next available number if file exists
        counter = 2
        while True:
            numbered_name = f"{base_name} - {counter:03d}.mp4"
            numbered_path = os.path.join(source_dir, numbered_name)
            if not os.path.exists(numbered_path):
                os.rename(source_file, numbered_path)
                logging.info(f"Video renamed to: {numbered_path}")
                return numbered_path
            counter += 1
        
    except Exception as e:
        logging.error(f"Failed to rename video file: {e}")
        return source_file  # Return original path if rename fails

def processing_worker():
    """The main worker thread that processes demos from the queue."""
    logging.info("Processing worker started.")
    
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        csdm_project_path = config['Paths']['csdm_project_path']
        demos_folder = config['Paths']['demos_folder']
        output_folder = config['Paths']['output_folder']
        obs_host = config['OBS']['host']
        obs_port = int(config['OBS']['port'])
        video_generate_only = config['Video'].getboolean('video_generate_only', True)
    except KeyError as e:
        logging.error(f"Configuration error: Missing key {e} in config.ini.")
        return

    while True:
        try:
            task_status_override = False
            job = demo_queue.get()
            suspect_steam_id = job['suspect_steam_id']
            user_input = job['share_code']
            youtube_upload = job['youtube_upload']
            
            # Check if YouTube upload is requested (overrides default setting)
            #youtube_upload = job.get('savemethod', not video_generate_only)
            
            update_status("Processing", "Starting new job...", suspect_steam_id)

            workflow_successful = False
            youtube_link = None
            task_status = None
            final_video_path = None
            obs = OBSRecorder(host=obs_host, port=obs_port)

            try:
                # Step 1: Download Demo
                # Check if input is a direct demo URL or a share code
                if demo_downloader.is_demo_url(user_input):
                    update_status("Processing", "Direct demo URL detected, downloading...", suspect_steam_id)
                    demo_path = demo_downloader.download_demo(user_input, demos_folder)
                else:
                    update_status("Processing", "Parsing share code...", suspect_steam_id)
                    share_code = demo_downloader.parse_share_code(user_input)
                    if not share_code:
                        raise ValueError("Invalid share code provided.")
                    
                    update_status("Processing", f"Downloading demo for {share_code}...", suspect_steam_id)
                    demo_path = demo_downloader.download_demo(share_code, demos_folder)
                if not demo_path:
                    raise RuntimeError("Failed to download demo.")

                # Step 2: Analyze Demo
                update_status("Processing", "Analyzing demo...", suspect_steam_id)
                if not csdm_cli_handler.analyze_demo(csdm_project_path, demo_path):
                    raise RuntimeError("Demo analysis failed.")

                # Step 3: Connect to OBS
                update_status("Processing", "Connecting to OBS...", suspect_steam_id)
                obs.connect()
                if not obs.is_connected:
                    raise RuntimeError("Could not connect to OBS.")

                # Step 4: Start Highlights and Recording
                update_status("Recording", "Launching CS2 for highlights...", suspect_steam_id)
                if not csdm_cli_handler.start_highlights(csdm_project_path, demo_path, suspect_steam_id):
                    raise RuntimeError("Failed to launch highlights.")

                logging.info("Waiting 15 seconds for CS2 to load...")
                time.sleep(15)
                
                update_status("Recording", "Starting OBS recording...", suspect_steam_id)
                obs.start_recording()

                update_status("Recording", "Waiting for highlights to finish...", suspect_steam_id)
                
                if not csdm_cli_handler.wait_for_cs2_to_close():
                    raise RuntimeError("Timed out waiting for CS2 process to close.")

                workflow_successful = True

            except DemoExpiredException as e:
                logging.warning(f"Prep stage failed for {suspect_steam_id}: {e}")
                update_status("Error", "Demo Expired", suspect_steam_id, "prep_status")
                ts = time.time()
                completed_jobs.append({
                    "timestamp": datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),
                    "suspect_steam_id": suspect_steam_id,
                    "share_code": job['share_code'],
                    "youtube_link": "Demo expired",
                    "task_status": "Demo expired",
                    "final_video_path": final_video_path,
                    "youtube_upload": youtube_upload or "N/A",
                    "submitted_by": job.get('submitted_by', 'N/A'),
                    "suspect_steam_name": steamname
                })
                save_results()

            except Exception as e:
                logging.error(f"A critical error occurred for {suspect_steam_id}: {e}")
                update_status("Error", f"Workflow failed: {e}", suspect_steam_id)



            finally:
                steamname = getSteamname(suspect_steam_id)
                # --- Cleanup ---
                if obs.is_recording:
                    obs.stop_recording()
                    logging.info("Waiting 10 seconds for OBS to save the video file...")
                    time.sleep(10)
                if obs.is_connected:
                    obs.disconnect()
                
                # This is now just a backup in case the process hangs.
                csdm_cli_handler.force_close_cs2()

                # --- Upload/Save Step ---
                if workflow_successful:
                    update_status("Processing", "Finding latest recording...", suspect_steam_id)
                    try:
                        files = [os.path.join(output_folder, f) for f in os.listdir(output_folder) if f.endswith('.mp4')]
                        if not files:
                            raise FileNotFoundError("No .mp4 files found in the OBS output folder.")
                        
                        latest_file = max(files, key=os.path.getctime)
                        logging.info(f"Latest recording found: {latest_file}")
                        

                        # youtube_upload =  True;
                        if youtube_upload:
                            # Upload to YouTube
                            update_status("Uploading", f"Uploading {os.path.basename(latest_file)}...", suspect_steam_id)
                            video_title = f"{steamname} - {suspect_steam_id} - Highlights"
                            youtube_link = youtube_uploader.upload_video(latest_file, video_title)
                            
                            if youtube_link:
                                task_status = "Uploaded"
                                update_status("Finished", "Upload complete!", suspect_steam_id)
                            else:
                                task_status = "Upload Failed"
                                raise RuntimeError("Upload failed to return a URL.")
                        else:
                            # Save locally with proper naming
                            update_status("Processing", "Renaming video file...", suspect_steam_id)
                            demo_name = extract_demo_name_from_url(user_input)
                            final_video_path = rename_video_with_suspect_info(latest_file, suspect_steam_id, demo_name)
                            
                            task_status = "Saved Locally"
                            youtube_link = f"file://{final_video_path}"  # Local file reference
                            update_status("Finished", "Video saved locally!", suspect_steam_id)

                       


                    except Exception as e:
                        if youtube_upload:
                            logging.error(f"Failed to upload the recording: {e}")
                            task_status = "Upload Failed"
                            update_status("Error", f"Upload failed: {e}", suspect_steam_id)
                        else:
                            logging.error(f"Failed to save the recording: {e}")
                            task_status = "Failed to Save"
                            update_status("Error", f"Save failed: {e}", suspect_steam_id)
                        

                else:
                    logging.warning("Workflow did not complete successfully. Skipping upload/save.")
                    task_status = "Processing Failed"


                ts = time.time()
                completed_jobs.append({
                    "timestamp": datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),
                    "suspect_steam_id": suspect_steam_id,
                    "share_code": job['share_code'],
                    "youtube_link": youtube_link or "Processing Failed",
                    "task_status": task_status or "Processing Failed",
                    "final_video_path": final_video_path,
                    "youtube_upload": youtube_upload or "N/A",
                    "submitted_by": job.get('submitted_by', 'N/A'),
                    "suspect_steam_name": steamname
                })
                save_results()

            demo_queue.task_done()
            time.sleep(5)
            update_status("Idle", "Waiting for a new demo to be submitted.")

        except queue.Empty:
            time.sleep(1)


if __name__ == '__main__':
    setup_logging()
    
    # Start the processing worker in a separate thread
    worker_thread = threading.Thread(target=processing_worker, name="ProcessingWorker")
    worker_thread.daemon = True
    worker_thread.start()

    # Start the Flask web server in the main thread
    logging.info("Starting web server on http://localhost:5001")
    run_web_server()
