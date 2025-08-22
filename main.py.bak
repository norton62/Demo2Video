import sys
import os
import configparser
import logging
import time
import threading
import pyautogui

import csdm_cli_handler
import youtube_uploader
import demo_downloader
from obs_recorder import OBSRecorder
from web_server import demo_queue, current_status, completed_jobs, run_web_server, save_results

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

def processing_worker():
    """The main worker thread that processes demos from the queue."""
    logging.info("Processing worker started.")
    
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        csdm_project_path = config['Paths']['csdm_project_path']
        output_folder = config['Paths']['output_folder']
        obs_host = config['OBS']['host']
        obs_port = int(config['OBS']['port'])
    except KeyError as e:
        logging.error(f"Configuration error: Missing key {e} in config.ini.")
        return

    while True:
        try:
            job = demo_queue.get()
            suspect_steam_id = job['suspect_steam_id']
            update_status("Processing", "Starting new job...", suspect_steam_id)

            workflow_successful = False
            youtube_link = None
            obs = OBSRecorder(host=obs_host, port=obs_port)

            try:
                # Step 1: Download Demo
                user_input = job['share_code']
                
                # Check if input is a direct demo URL or a share code
                if demo_downloader.is_demo_url(user_input):
                    update_status("Processing", "Direct demo URL detected, downloading...", suspect_steam_id)
                    demo_path = demo_downloader.download_demo(user_input, output_folder)
                else:
                    update_status("Processing", "Parsing share code...", suspect_steam_id)
                    share_code = demo_downloader.parse_share_code(user_input)
                    if not share_code:
                        raise ValueError("Invalid share code provided.")
                    
                    update_status("Processing", f"Downloading demo for {share_code}...", suspect_steam_id)
                    demo_path = demo_downloader.download_demo(share_code, output_folder)
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

                logging.info("Waiting 20 seconds for CS2 to load...")
                time.sleep(20)
                
                update_status("Recording", "Starting OBS recording...", suspect_steam_id)
                obs.start_recording()

                update_status("Recording", "Waiting for highlights to finish...", suspect_steam_id)
                
                # UPDATED: Called the correct function name from the CLI handler.
                if not csdm_cli_handler.wait_for_cs2_to_close():
                    raise RuntimeError("Timed out waiting for CS2 process to close.")

                workflow_successful = True

            except Exception as e:
                logging.error(f"A critical error occurred for {suspect_steam_id}: {e}")
                update_status("Error", f"Workflow failed: {e}", suspect_steam_id)

            finally:
                # --- Cleanup ---
                if obs.is_recording:
                    obs.stop_recording()
                    logging.info("Waiting 10 seconds for OBS to save the video file...")
                    time.sleep(10)
                if obs.is_connected:
                    obs.disconnect()
                
                # This is now just a backup in case the process hangs.
                csdm_cli_handler.force_close_cs2()

                # --- Upload Step ---
                if workflow_successful:
                    update_status("Processing", "Finding latest recording for upload...", suspect_steam_id)
                    try:
                        files = [os.path.join(output_folder, f) for f in os.listdir(output_folder) if f.endswith('.mp4')]
                        if not files:
                            raise FileNotFoundError("No .mp4 files found in the OBS output folder.")
                        
                        latest_file = max(files, key=os.path.getctime)
                        logging.info(f"Latest recording found: {latest_file}")
                        
                        update_status("Uploading", f"Uploading {os.path.basename(latest_file)}...", suspect_steam_id)
                        video_title = f"Suspected Cheater: {suspect_steam_id} - Highlights"
                        youtube_link = youtube_uploader.upload_video(latest_file, video_title)
                        
                        if youtube_link:
                            update_status("Finished", "Upload complete!", suspect_steam_id)
                        else:
                            raise RuntimeError("Upload failed to return a URL.")

                    except Exception as e:
                        logging.error(f"Failed to find or upload the recording: {e}")
                        update_status("Error", f"Upload failed: {e}", suspect_steam_id)
                else:
                    logging.warning("Workflow did not complete successfully. Skipping upload.")

            # Add the completed job to the results list
            completed_jobs.append({
                "suspect_steam_id": suspect_steam_id,
                "share_code": job['share_code'],
                "youtube_link": youtube_link or "Upload Failed",
                "submitted_by": job.get('submitted_by', 'N/A')
            })
            save_results()

            demo_queue.task_done()
            time.sleep(5)
            update_status("Idle", "Waiting for a new demo to be submitted.")

        except queue.Empty:
            time.sleep(1)


if __name__ == '__main__':
    setup_logging()
    
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        password = config['Web']['password']
    except KeyError:
        logging.error("Password not found in config.ini.")
        sys.exit(1)

    worker_thread = threading.Thread(target=processing_worker, name="ProcessingWorker")
    worker_thread.daemon = True
    worker_thread.start()

    logging.info("Starting web server on http://localhost:5001")
    run_web_server(password=password)
