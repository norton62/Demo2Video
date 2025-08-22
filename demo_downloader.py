import requests
import bz2
import shutil
import os
import logging
import re

# This module handles downloading and extracting CS2 demos from share codes.

API_URLS = [
    "https://csreplay.moon-moon.tech/decode",
    "https://csreplay2.moon-moon.tech/decode",
    "https://appeared-cite-reach-fy.trycloudflare.com"
]

def parse_share_code(share_link_or_code):
    """Extracts the match share code from a full steam link or just the code."""
    match = re.search(r'(CSGO(-[A-Za-z0-9]{5}){5})', share_link_or_code)
    if match:
        return match.group(1)
    return None

def is_demo_url(input_string):
    """
    Checks if the input string is a direct demo download URL.
    Demo URLs typically end with .dem.bz2 and contain replay servers.
    """
    input_string = input_string.strip()
    # Check if it's a URL and ends with .dem.bz2
    if (input_string.startswith(('http://', 'https://')) and 
        input_string.endswith('.dem.bz2')):
        return True
    return False

def download_demo(share_code_or_url, download_folder):
    """
    Downloads a demo using either a share code (via CSReplay API) or a direct demo URL.
    
    Args:
        share_code_or_url: Either a CS2 share code or a direct demo download URL
        download_folder: The folder where the demo should be saved
    
    Returns:
        str: The full path to the downloaded .dem file, or None on failure.
    """
    download_url = None
    
    # Check if input is a direct demo URL
    if is_demo_url(share_code_or_url):
        logging.info(f"Direct demo URL detected: {share_code_or_url}")
        download_url = share_code_or_url
        share_code = None  # No share code available for fallback filename
    else:
        # Treat as share code and get download URL from API
        share_code = share_code_or_url
        api_response_data = None
        headers = {'Content-Type': 'application/json'}
        payload = {'shareCode': share_code}

        for api_url in API_URLS:
            try:
                # UPDATED: Changed from GET to POST request
                logging.info(f"Attempting to get download link from: {api_url} with POST request.")
                
                response = requests.post(api_url, headers=headers, json=payload)
                response.raise_for_status()

                api_response_data = response.json()
                download_url = api_response_data.get("downloadLink")

                if download_url:
                    logging.info("Successfully retrieved download link.")
                    break
                else:
                    logging.warning(f"API at {api_url} did not return a download URL.")

            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to connect to API at {api_url}: {e}")
                continue
        
        if not download_url:
            logging.error("Failed to get a download URL from all available APIs.")
            return None

    # Extract original filename from download URL
    try:
        # Extract filename from URL (e.g., "003768214888862712028_0847912006.dem.bz2")
        original_filename = download_url.split('/')[-1]
        if original_filename.endswith('.dem.bz2'):
            # Remove .bz2 extension to get the .dem filename
            dem_filename_only = original_filename[:-4]  # Remove ".bz2"
        else:
            # Fallback filename generation
            if share_code:
                logging.warning(f"Could not parse original filename from URL: {download_url}")
                dem_filename_only = f"{share_code}.dem"
            else:
                # For direct URLs without share code, use a generic name with timestamp
                import time
                timestamp = int(time.time())
                logging.warning(f"Could not parse original filename from URL: {download_url}")
                dem_filename_only = f"demo_{timestamp}.dem"
        
        bz2_filename = os.path.join(download_folder, original_filename)
        dem_filename = os.path.join(download_folder, dem_filename_only)
        
        # Check if demo file already exists
        if os.path.exists(dem_filename):
            logging.info(f"Demo file already exists: {dem_filename}")
            return dem_filename
        
        logging.info(f"Downloading demo from: {download_url}")
        logging.info(f"Original filename: {dem_filename_only}")

        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(bz2_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        logging.info("Download complete. Extracting demo...")

        with bz2.open(bz2_filename, 'rb') as f_in:
            with open(dem_filename, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        logging.info(f"Extraction complete. Demo saved to: {dem_filename}")
        os.remove(bz2_filename)
        
        return dem_filename

    except Exception as e:
        logging.error(f"An error occurred during download/extraction: {e}")
        return None
