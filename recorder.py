import subprocess
import logging
import os
import time

# This module handles the screen recording using FFmpeg.

def start_recording(ffmpeg_path, output_path, width, height, offset_x, offset_y, audio_device_name):
    """
    Starts recording screen and audio to separate temporary files.

    Args:
        ffmpeg_path (str): Path to the ffmpeg executable.
        output_path (str): The final output file path.
        ...
        audio_device_name (str): The name of the audio capture device.

    Returns:
        dict: A dictionary containing the Popen objects for the video and audio processes,
              or None on failure.
    """
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Define paths for temporary files
    temp_video_path = output_path + ".temp.mkv"
    temp_audio_path = output_path + ".temp.wav"

    # --- Video Recording Command ---
    video_command = [
        ffmpeg_path,
        '-f', 'gdigrab',
        '-framerate', '60',
        '-offset_x', str(offset_x),
        '-offset_y', str(offset_y),
        '-video_size', f'{width}x{height}',
        '-i', 'desktop',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-pix_fmt', 'yuv420p',
        '-y',
        temp_video_path
    ]

    # --- Audio Recording Command ---
    audio_command = [
        ffmpeg_path,
        '-f', 'dshow',
        '-i', f'audio="{audio_device_name}"',
        '-y',
        temp_audio_path
    ]

    logging.info(f"Starting video recording: {' '.join(video_command)}")
    logging.info(f"Starting audio recording: {' '.join(audio_command)}")

    try:
        # Start both processes
        video_process = subprocess.Popen(video_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        audio_process = subprocess.Popen(audio_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        logging.info(f"Video process started with PID: {video_process.pid}")
        logging.info(f"Audio process started with PID: {audio_process.pid}")
        
        time.sleep(3) # Give processes time to initialize

        return {"video": video_process, "audio": audio_process, "temp_video": temp_video_path, "temp_audio": temp_audio_path}

    except Exception as e:
        logging.error(f"Failed to start recording processes: {e}")
        return None

def stop_recording(recorder_processes, ffmpeg_path, final_output_path):
    """
    Stops the recording processes and merges the temporary files.

    Args:
        recorder_processes (dict): The dictionary of processes from start_recording.
        ffmpeg_path (str): Path to the ffmpeg executable.
        final_output_path (str): The path for the final merged video file.
    """
    if not recorder_processes:
        logging.warning("No recorder processes to stop.")
        return

    video_proc = recorder_processes.get("video")
    audio_proc = recorder_processes.get("audio")
    temp_video = recorder_processes.get("temp_video")
    temp_audio = recorder_processes.get("temp_audio")

    # --- Stop Video and Audio Recording ---
    for name, proc in [("Video", video_proc), ("Audio", audio_proc)]:
        if proc and proc.poll() is None:
            logging.info(f"Stopping {name} recording...")
            try:
                proc.terminate()
                proc.wait(timeout=10)
                logging.info(f"{name} recording stopped.")
            except Exception as e:
                logging.error(f"Error stopping {name} process: {e}")
                proc.kill()
        else:
            logging.warning(f"{name} process was not running or already terminated.")

    # --- Merge Files ---
    if os.path.exists(temp_video) and os.path.exists(temp_audio):
        logging.info("Merging temporary video and audio files...")
        merge_command = [
            ffmpeg_path,
            '-i', temp_video,
            '-i', temp_audio,
            '-c:v', 'copy',      # Copy video stream without re-encoding
            '-c:a', 'aac',       # Re-encode audio to AAC
            '-b:a', '192k',
            '-y',
            final_output_path
        ]
        try:
            # Use subprocess.run for the merge since we need to wait for it to finish.
            result = subprocess.run(merge_command, capture_output=True, text=True, check=True)
            logging.info("Merge successful.")
        except subprocess.CalledProcessError as e:
            logging.error("Failed to merge video and audio files.")
            logging.error(f"FFmpeg stderr: {e.stderr}")
        except Exception as e:
            logging.error(f"An unexpected error occurred during merge: {e}")
    else:
        logging.error("One or both temporary files are missing. Cannot merge.")

    # --- Cleanup ---
    for temp_file in [temp_video, temp_audio]:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                logging.info(f"Deleted temporary file: {temp_file}")
            except Exception as e:
                logging.error(f"Failed to delete temporary file {temp_file}: {e}")
