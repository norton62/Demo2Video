import os
import google.oauth2.credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# One-time OAuth 2.0 authorization for YouTube uploads.

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
CLIENT_SECRETS_FILE = 'client_secrets.json'
TOKEN_FILE = 'token.json'


def get_credentials():
    """
    Authenticates with the Google API, handling the OAuth 2.0 flow.
    If a valid token.json file exists, it's loaded.
    Otherwise, it initiates the browser-based authorization flow.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = google.oauth2.credentials.Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid credentials, start the flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                run_flow()
                return
        else:
            run_flow()


def run_flow():
    """
    Runs the installed application flow to get user credentials.
    Opens a web browser for authorization.
    """
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"Error: {CLIENT_SECRETS_FILE} not found. Please download it from the Google Cloud Console.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the credentials for the next run
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())
    print(f"✅ Credentials saved to {TOKEN_FILE}")


if __name__ == '__main__':
    print("Starting YouTube API authorization process...")
    get_credentials()
    print("✅ Authorization complete. You can now run main.py")
