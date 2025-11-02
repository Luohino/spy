"""
Remote Webcam Streaming System - Desktop Application
Runs as Windows service with embedded signaling server and WebRTC streaming
"""

import asyncio
import json
import logging
import socket
import sys
import threading
import time
import hashlib
import os
from datetime import datetime
from typing import Dict, Set, Optional

import cv2
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import requests
import socketio as client_socketio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('webcam_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Fixed password for authentication
FIXED_PASSWORD = "luohino"
PASSWORD_HASH = hashlib.sha256(FIXED_PASSWORD.encode()).hexdigest()

# Signaling server URL
SIGNALING_SERVER_URL = os.environ.get('SIGNALING_SERVER', 'https://connection-iyj0.onrender.com')

# Local server port
HTTP_PORT = 5000

# Device info
DEVICE_NAME = socket.gethostname()
DEVICE_ID = hashlib.md5(DEVICE_NAME.encode()).hexdigest()[:12]

# Flask app for signaling server
app = Flask(__name__)
app.config['SECRET_KEY'] = 'luohino-secret-key-2024'
CORS(app, resources={r"/*": {"origins": "*"}})

# Let Flask-SocketIO auto-detect async_mode (works with PyInstaller)
socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False)

# Global state
connected_devices: Dict[str, dict] = {}  # device_id -> device_info
active_sessions: Dict[str, dict] = {}  # session_id -> session_info
camera_active = False
camera_thread = None
stop_camera_event = threading.Event()


class WebcamStreamer:
    """Handles webcam capture and streaming"""
    
    def __init__(self):
        self.camera = None
        self.is_streaming = False
        self.frame_queue = []
        self.max_queue_size = 30
        
    def start_camera(self):
        """Initialize and start camera"""
        try:
            self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            if not self.camera.isOpened():
                logger.error("Failed to open camera")
                return False
                
            self.is_streaming = True
            logger.info("Camera started successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            return False
    
    def stop_camera(self):
        """Stop and release camera"""
        self.is_streaming = False
        if self.camera:
            self.camera.release()
            self.camera = None
        logger.info("Camera stopped")
    
    def get_frame(self) -> Optional[bytes]:
        """Capture and encode a single frame"""
        if not self.camera or not self.is_streaming:
            return None
            
        try:
            ret, frame = self.camera.read()
            if not ret:
                logger.warning("Failed to read frame")
                return None
            
            # Encode frame as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            return buffer.tobytes()
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None


# Global webcam streamer instance
streamer = WebcamStreamer()


# ============================================================================
# SIGNALING SERVER ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'device_name': DEVICE_NAME,
        'device_id': DEVICE_ID,
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/authenticate', methods=['POST'])
def authenticate():
    """Authenticate client with password"""
    data = request.get_json()
    password = data.get('password', '')
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if password_hash == PASSWORD_HASH:
        return jsonify({
            'success': True,
            'message': 'Authentication successful'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Invalid password'
        }), 401


@app.route('/api/devices', methods=['POST'])
def list_devices():
    """List all registered devices (requires authentication)"""
    data = request.get_json()
    password = data.get('password', '')
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if password_hash != PASSWORD_HASH:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Return list of connected devices
    devices = []
    for device_id, info in connected_devices.items():
        devices.append({
            'device_id': device_id,
            'device_name': info['device_name'],
            'last_seen': info['last_seen'],
            'status': 'online'
        })
    
    return jsonify({
        'success': True,
        'devices': devices
    })


@app.route('/api/register', methods=['POST'])
def register_device():
    """Register a device with the signaling server"""
    data = request.get_json()
    
    device_id = data.get('device_id', DEVICE_ID)
    device_name = data.get('device_name', DEVICE_NAME)
    
    connected_devices[device_id] = {
        'device_id': device_id,
        'device_name': device_name,
        'last_seen': datetime.utcnow().isoformat(),
        'ip': request.remote_addr
    }
    
    logger.info(f"Device registered: {device_name} ({device_id})")
    
    return jsonify({
        'success': True,
        'device_id': device_id
    })


@app.route('/api/stream/start', methods=['POST'])
def start_stream():
    """Start streaming from a device"""
    data = request.get_json()
    password = data.get('password', '')
    device_id = data.get('device_id', '')
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if password_hash != PASSWORD_HASH:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if device_id == DEVICE_ID:
        # Start local camera
        if streamer.start_camera():
            return jsonify({
                'success': True,
                'message': 'Camera started',
                'stream_url': f'http://{get_local_ip()}:{HTTP_PORT}/api/stream/frame'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to start camera'
            }), 500
    else:
        return jsonify({
            'success': False,
            'message': 'Device not found'
        }), 404


@app.route('/api/stream/stop', methods=['POST'])
def stop_stream():
    """Stop streaming from a device"""
    data = request.get_json()
    password = data.get('password', '')
    device_id = data.get('device_id', '')
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if password_hash != PASSWORD_HASH:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if device_id == DEVICE_ID:
        streamer.stop_camera()
        return jsonify({
            'success': True,
            'message': 'Camera stopped'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Device not found'
        }), 404


@app.route('/api/stream/frame', methods=['GET'])
def get_frame():
    """Get a single frame from the camera"""
    frame = streamer.get_frame()
    if frame:
        from flask import Response
        return Response(frame, mimetype='image/jpeg')
    else:
        return jsonify({'error': 'No frame available'}), 404


@app.route('/api/stream/mjpeg', methods=['GET'])
def stream_mjpeg():
    """Stream MJPEG video"""
    def generate():
        while streamer.is_streaming:
            frame = streamer.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.033)  # ~30 FPS
    
    from flask import Response
    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


# ============================================================================
# SOCKETIO EVENTS (WebRTC Signaling)
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'sid': request.sid})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on('authenticate')
def handle_authenticate(data):
    """Authenticate WebSocket connection"""
    password = data.get('password', '')
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if password_hash == PASSWORD_HASH:
        emit('authenticated', {'success': True})
    else:
        emit('authenticated', {'success': False, 'message': 'Invalid password'})


@socketio.on('join_device')
def handle_join_device(data):
    """Join a device room for signaling"""
    device_id = data.get('device_id', '')
    join_room(device_id)
    logger.info(f"Client {request.sid} joined device room {device_id}")
    emit('joined_device', {'device_id': device_id})


@socketio.on('leave_device')
def handle_leave_device(data):
    """Leave a device room"""
    device_id = data.get('device_id', '')
    leave_room(device_id)
    logger.info(f"Client {request.sid} left device room {device_id}")


@socketio.on('offer')
def handle_offer(data):
    """Forward WebRTC offer to device"""
    device_id = data.get('device_id', '')
    offer = data.get('offer', {})
    emit('offer', {'offer': offer, 'from': request.sid}, room=device_id, skip_sid=request.sid)


@socketio.on('answer')
def handle_answer(data):
    """Forward WebRTC answer to client"""
    to_sid = data.get('to', '')
    answer = data.get('answer', {})
    emit('answer', {'answer': answer, 'from': request.sid}, room=to_sid)


@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    """Forward ICE candidate"""
    to = data.get('to', '')
    candidate = data.get('candidate', {})
    
    if to:
        emit('ice_candidate', {'candidate': candidate, 'from': request.sid}, room=to)
    else:
        # Broadcast to device room
        device_id = data.get('device_id', '')
        emit('ice_candidate', {'candidate': candidate, 'from': request.sid}, 
             room=device_id, skip_sid=request.sid)


def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def get_public_ip():
    """Get public IP address"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except:
        return None


def heartbeat_loop():
    """Send periodic heartbeat to maintain registration"""
    while True:
        try:
            # Update device registration
            connected_devices[DEVICE_ID] = {
                'device_id': DEVICE_ID,
                'device_name': DEVICE_NAME,
                'last_seen': datetime.utcnow().isoformat(),
                'ip': get_local_ip()
            }
            logger.debug(f"Heartbeat: {DEVICE_NAME} is online")
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
        
        time.sleep(30)  # Heartbeat every 30 seconds


def register_with_signaling_server():
    """Register this device with cloud signaling server"""
    try:
        # Try to get ngrok URL first, fallback to public IP
        from ngrok_helper import get_connection_url
        connection_url = get_connection_url()
        
        # Extract IP and port from URL for backwards compatibility
        public_ip = connection_url.replace('http://', '').replace('https://', '').split(':')[0]
        port = HTTP_PORT
        
        logger.info(f"Connection URL: {connection_url}")
        
        # Connect to signaling server
        sio = client_socketio.Client(reconnection=True, reconnection_attempts=0)
        
        @sio.on('connect')
        def on_connect():
            logger.info(f"Connected to signaling server: {SIGNALING_SERVER_URL}")
            # Register as device with full connection URL
            sio.emit('device_register', {
                'password': FIXED_PASSWORD,
                'device_id': DEVICE_ID,
                'device_name': DEVICE_NAME,
                'public_ip': public_ip,
                'port': port,
                'connection_url': connection_url  # Send full ngrok URL
            })
        
        @sio.on('device_registered')
        def on_registered(data):
            if data.get('success'):
                logger.info(f"✅ Registered with signaling server!")
                logger.info(f"   Device ID: {DEVICE_ID}")
                logger.info(f"   Device Name: {DEVICE_NAME}")
                logger.info(f"   Public IP: {public_ip}:{HTTP_PORT}")
        
        @sio.on('disconnect')
        def on_disconnect():
            logger.warning("Disconnected from signaling server, will reconnect...")
        
        @sio.on('error')
        def on_error(data):
            logger.error(f"Signaling server error: {data}")
        
        # Connect
        logger.info(f"Connecting to signaling server: {SIGNALING_SERVER_URL}")
        sio.connect(SIGNALING_SERVER_URL, transports=['websocket', 'polling'])
        
        # Keep connection alive in background
        def keep_alive():
            while True:
                time.sleep(30)
                if sio.connected:
                    logger.debug("Signaling server connection alive")
                else:
                    logger.warning("Lost connection to signaling server")
                    try:
                        sio.connect(SIGNALING_SERVER_URL)
                    except:
                        pass
        
        threading.Thread(target=keep_alive, daemon=True).start()
        
    except Exception as e:
        logger.error(f"Failed to connect to signaling server: {e}")
        logger.info("Continuing without signaling server (local mode only)")


def start_signaling_server():
    """Start the embedded signaling server"""
    logger.info(f"Starting local server on port {HTTP_PORT}")
    logger.info(f"Device: {DEVICE_NAME} (ID: {DEVICE_ID})")
    logger.info(f"Local IP: {get_local_ip()}")
    
    public_ip = get_public_ip()
    if public_ip:
        logger.info(f"Public IP: {public_ip}")
    
    # Register with cloud signaling server
    threading.Thread(target=register_with_signaling_server, daemon=True).start()
    
    # Start heartbeat thread
    heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    
    # Register self locally
    connected_devices[DEVICE_ID] = {
        'device_id': DEVICE_ID,
        'device_name': DEVICE_NAME,
        'last_seen': datetime.utcnow().isoformat(),
        'ip': get_local_ip()
    }
    
    # Run Flask-SocketIO server
    socketio.run(app, host='0.0.0.0', port=HTTP_PORT, debug=False, allow_unsafe_werkzeug=True)


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Remote Webcam Streaming System - Desktop Application")
    logger.info("=" * 60)
    
    try:
        start_signaling_server()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        streamer.stop_camera()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
