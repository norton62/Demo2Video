# CS Demo Processor

This program automates the process of downloading a Counter-Strike 2 demo, analyzing it, recording highlights of a specified player, and uploading the resulting video to YouTube. It runs as a continuous service with a web interface for queuing jobs, making it a complete, hands-free pipeline.

This project uses the command-line tools provided by **CS Demo Manager** to handle the demo analysis and launch the game for recording.

## Features

* **Web Interface**: A simple web UI to queue up demos using a share code and Steam64 ID.
* **Automated Queue**: The program runs continuously, processing demos from the queue one by one.
* **Demo Downloading**: Automatically fetches and unzips demos from Valve's servers using the CSReplay.xyz API.
* **CLI-Powered Analysis**: Uses the official CSDM command-line tools for reliable demo analysis.
* **Headless Recording**: Launches CS2 via the CSDM CLI to play highlights, which can be recorded by an external program like OBS.
* **YouTube Upload**: Automatically uploads the final video to a specified YouTube channel.
* **Persistent Results**: Saves a history of completed jobs in a local `results.json` file.
* **Password Protection**: The web interface is protected by a simple password.


## Setup Instructions

### 1. Prerequisites

* **Python 3.7+**: Ensure Python is installed and added to your system's PATH.
* **Node.js**: The CSDM CLI tools require Node.js. Download and install it from [nodejs.org](https://nodejs.org/).
* **Modified CS Demo Manager (Project)**: **IMPORTANT:** This script requires a modified version of the CS Demo Manager project with a working highlights CLI feature. You cannot use the official repository directly. You must clone the specific version provided for this project. *https://github.com/norton62/cs-demo-manager*
* **OBS Studio**: For recording. Download from [obsproject.com](https://obsproject.com/).

### 2. Initial Setup

1.  **Clone This Repository**: Download or clone this project to your local machine.
2.  **Install Python Dependencies**: Open a terminal in the project folder and run:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Install CSDM Project Dependencies**:
    * Navigate to your cloned **modified** CSDM project folder.
    * Run `npm install` to install all the necessary Node.js packages.

### 3. Configuration

1.  **Create `config.ini`**: Rename the `config.ini.template` file to `config.ini`.
2.  **Edit `config.ini`**: Open the new `config.ini` file and fill in all the required paths and settings. Comments in the file will guide you. **This is the most important step.**

### 4. OBS Setup

You must configure OBS to work with the script.

* Install the **`obs-websocket`** plugin from its [GitHub releases page](https://github.com/obsproject/obs-websocket/releases).
* In OBS, go to **Tools -> obs-websocket Settings**.
* **Enable** the WebSocket server.
* **Uncheck** "Enable Authentication".
* Note the **port** (usually `4455`) and ensure it matches your `config.ini`.
* Create a scene in OBS with a **"Game Capture"** source set to "Capture any fullscreen application".
* Go to **File -> Settings -> Output -> Recording** and set the "Recording Path" to the **exact same folder** you specified for `output_folder` in your `config.ini`.

### 5. YouTube API Setup

To upload videos, you need Google API credentials.

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2.  Enable the **"YouTube Data API v3"**.
3.  Create an **OAuth 2.0 Client ID** for a **Desktop app**.
4.  Download the credentials JSON file, rename it to `client_secrets.json`, and place it in the root of this project folder.
5.  Run the authorization script from your terminal:
    ```bash
    python setup_youtube_auth.py
    ```
    This will open a browser window for you to authorize the application. A `token.json` file will be created.

## How to Run

1.  **Start the CSDM Dev Server**:
    * Open a terminal and navigate to your **modified** CSDM project folder.
    * Run the command: `node scripts/develop-cli.mjs`
    * **Leave this terminal running in the background.**
2.  **Start OBS Studio**:
    * Open OBS and leave it running in the background.
3.  **Start the Main Program**:
    * Open a **second terminal** and navigate to this project's folder.
    * Run the main script:
        ```bash
        python main.py
        ```
4.  **Access the Web Interface**:
    * Open your web browser and go to `http://localhost:5001`.
    * Log in with the password you set in `config.ini`.
    * You can now start adding demos to the queue.