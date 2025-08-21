import os
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# This module handles the video upload to YouTube.

TOKEN_FILE = 'token.json'
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_youtube_service():
    """
    Builds and returns an authenticated YouTube service object.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save the refreshed credentials
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                logging.error(f"Failed to refresh YouTube API token: {e}")
                logging.error("Please run setup_youtube_auth.py again.")
                return None
        else:
            logging.error("YouTube API credentials not found or invalid. Please run setup_youtube_auth.py.")
            return None
    
    return build('youtube', 'v3', credentials=creds)

def upload_video(video_path, title, description="Suspected cheater highlights.", category="20", privacy_status="unlisted"):
    """
    Uploads a video file to YouTube.

    Args:
        video_path (str): The path to the video file.
        title (str): The title of the YouTube video.
        description (str): The description of the video.
        category (str): The YouTube category ID (20 = Gaming).
        privacy_status (str): 'public', 'private', or 'unlisted'.

    Returns:
        str: The URL of the uploaded video, or None on failure.
    """
    try:
        youtube = get_youtube_service()
        if not youtube:
            return None

        logging.info(f"Starting upload of '{video_path}' to YouTube.")
        
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': ['csgo', 'cheater', 'highlights'],
                'categoryId': category
            },
            'status': {
                'privacyStatus': privacy_status
            }
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logging.info(f"Uploaded {int(status.progress() * 100)}%.")
        
        video_id = response.get('id')
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        logging.info(f"Upload successful! Video URL: {video_url}")
        return video_url

    except HttpError as e:
        logging.error(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during YouTube upload: {e}")
        return None
