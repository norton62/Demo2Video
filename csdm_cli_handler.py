import subprocess
import logging
import os
import time
import psutil

# This module handles all interactions with the CS Demo Manager CLI tools.

def analyze_demo(csdm_project_path, demo_path):
    """
    Runs the 'analyze' command on a demo file using the node CLI.
    """
    command = ['node', 'out/cli.js', 'analyze', demo_path]
    logging.info(f"Executing analysis command in '{csdm_project_path}': {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            cwd=csdm_project_path,
            capture_output=True,
            text=True,
            check=True,
            shell=True
        )
        logging.info("Analysis command completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Analysis command failed. Stderr: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during analysis: {e}")
        return False

def start_highlights(csdm_project_path, demo_path, steam_id_64):
    """
    Launches CS2 to play highlights for a specific player.
    """
    command = ['node', 'out/cli.js', 'highlights', demo_path, steam_id_64]
    logging.info(f"Executing highlights command in '{csdm_project_path}': {' '.join(command)}")
    
    try:
        # We just need to launch the process and don't need to wait for it.
        subprocess.Popen(
            command,
            cwd=csdm_project_path,
            shell=True
        )
        logging.info("Highlights command sent. CS2 should be launching.")
        return True
    except Exception as e:
        logging.error(f"An unexpected error occurred while starting highlights: {e}")
        return False

def wait_for_cs2_to_close(timeout=1800):
    """
    Waits for the cs2.exe process to start and then for it to close.

    Args:
        timeout (int): The maximum time in seconds to wait for the process to close.

    Returns:
        bool: True if the process started and closed, False on timeout or if it never started.
    """
    logging.info("Waiting for cs2.exe process to appear...")
    start_time = time.time()
    cs2_started = False
    # Wait up to 60 seconds for the game to launch
    while time.time() - start_time < 60:
        if "cs2.exe" in (p.name() for p in psutil.process_iter()):
            logging.info("cs2.exe process found. Now waiting for it to close.")
            cs2_started = True
            break
        time.sleep(1)

    if not cs2_started:
        logging.error("cs2.exe process did not appear within 60 seconds.")
        return False

    # Now that the game is running, wait for it to close
    start_time = time.time()
    while time.time() - start_time < timeout:
        if "cs2.exe" not in (p.name() for p in psutil.process_iter()):
            logging.info("cs2.exe process has closed. Highlights finished.")
            return True
        time.sleep(2) # Check every 2 seconds

    logging.error(f"Timed out after {timeout} seconds waiting for cs2.exe to close.")
    return False

def force_close_cs2():
    """
    Forcefully terminates the Counter-Strike 2 process.
    """
    logging.info("Attempting to force-close Counter-Strike 2 (cs2.exe)...")
    try:
        result = subprocess.run(['taskkill', '/F', '/IM', 'cs2.exe', '/T'],
                                capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logging.info("CS2 terminated successfully.")
        elif result.returncode == 128:
            logging.warning("CS2 process not found.")
        else:
            logging.error(f"Taskkill failed: {result.stderr.strip()}")
    except Exception as e:
        logging.error(f"Error closing CS2: {e}")
