import subprocess
import logging
import os

# This module is responsible for all interactions with the CS Demo Manager executable.

def run_csdm_command(csdm_path, command_args):
    """
    Executes a command using the CS Demo Manager executable and waits for it to complete.

    Args:
        csdm_path (str): The full path to the CSDemoManager.exe.
        command_args (list): A list of arguments to pass to the executable.

    Returns:
        bool: True if the command was successful, False otherwise.
    """
    command = [csdm_path] + command_args
    logging.info(f"Executing CSDM command and waiting for completion: {' '.join(command)}")
    try:
        # Using subprocess.run() to make the call blocking.
        # This will wait until the CSDM process is finished.
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        logging.info(f"CSDM command successful.")
        if result.stdout:
            logging.debug(f"CSDM stdout: {result.stdout}")
        return True

    except FileNotFoundError:
        logging.error(f"Error: The CSDM executable was not found at '{csdm_path}'")
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"CSDM command failed with return code {e.returncode}")
        if e.stderr:
            logging.error(f"CSDM stderr: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred while running CSDM command: {e}")
        return False

def import_demo(csdm_path, demo_path):
    """
    Imports a demo file into CS Demo Manager.

    Args:
        csdm_path (str): Path to CSDemoManager.exe.
        demo_path (str): Path to the .dem file.

    Returns:
        bool: True if import was successful, False otherwise.
    """
    logging.info(f"Importing demo: {demo_path}")
    return run_csdm_command(csdm_path, ['import', demo_path])

def analyze_demo(csdm_path, demo_path):
    """
    Runs analysis on an already imported demo.

    Args:
        csdm_path (str): Path to CSDemoManager.exe.
        demo_path (str): The FULL path of the demo file.

    Returns:
        bool: True if analysis was successful, False otherwise.
    """
    logging.info(f"Analyzing demo: {demo_path}")
    # UPDATED: Changed spelling from 'analyse' to 'analyze'
    return run_csdm_command(csdm_path, ['analyze', demo_path])


def start_highlights(csdm_path, demo_path, player_name):
    """
    Starts the highlight playback for a specific player. This is a non-blocking call.

    Args:
        csdm_path (str): Path to CSDemoManager.exe.
        demo_path (str): The FULL path to the demo file.
        player_name (str): The in-game name of the suspected cheater.

    Returns:
        subprocess.Popen: The process object for the running CSDM instance, or None on failure.
    """
    command = [csdm_path, 'highlights', demo_path, '--player', player_name]
    logging.info(f"Starting highlights for player '{player_name}' in demo '{os.path.basename(demo_path)}'")
    try:
        # Start the process and return the Popen object so the main script can monitor it.
        process = subprocess.Popen(command)
        logging.info(f"CSDM highlights process started with PID: {process.pid}")
        return process
    except FileNotFoundError:
        logging.error(f"Error: The CSDM executable was not found at '{csdm_path}'")
        return None
    except Exception as e:
        logging.error(f"Failed to start CSDM highlights: {e}")
        return None
