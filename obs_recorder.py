import logging
import obsws_python as obsws

# This module handles all recording interactions with OBS via the obs-websocket plugin.

class OBSRecorder:
    def __init__(self, host='localhost', port=4455):
        self.host = host
        self.port = port
        self.ws = None
        self.is_connected = False
        self.is_recording = False

    def connect(self):
        """Connects to the OBS WebSocket server."""
        try:
            self.ws = obsws.ReqClient(host=self.host, port=self.port)
            self.is_connected = True
            logging.info(f"Successfully connected to OBS at {self.host}:{self.port}")
        except Exception as e:
            logging.error(f"Failed to connect to OBS WebSocket: {e}")
            logging.error("Please ensure OBS is running and the obs-websocket plugin is enabled and configured correctly.")
            self.is_connected = False

    def start_recording(self):
        """Sends the command to OBS to start recording."""
        if not self.is_connected:
            logging.error("Cannot start recording, not connected to OBS.")
            return
        try:
            # Check if already recording
            status = self.ws.get_record_status()
            if not status.output_active:
                self.ws.start_record()
                self.is_recording = True
                logging.info("OBS recording started.")
            else:
                logging.warning("OBS is already recording.")
                self.is_recording = True # Assume we are controlling this recording
        except Exception as e:
            logging.error(f"Failed to start OBS recording: {e}")
            self.is_recording = False

    def stop_recording(self):
        """Sends the command to OBS to stop recording."""
        if not self.is_connected:
            logging.error("Cannot stop recording, not connected to OBS.")
            return
        try:
            # Check if we think we are recording
            status = self.ws.get_record_status()
            if status.output_active:
                self.ws.stop_record()
                self.is_recording = False
                logging.info("OBS recording stopped.")
            else:
                logging.warning("OBS was not recording.")
                self.is_recording = False
        except Exception as e:
            logging.error(f"Failed to stop OBS recording: {e}")

    def disconnect(self):
        """Disconnects from the OBS WebSocket server."""
        if self.is_connected and self.ws:
            self.ws.base_client.ws.close()
            self.is_connected = False
            logging.info("Disconnected from OBS.")
