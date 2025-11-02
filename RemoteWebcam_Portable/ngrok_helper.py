"""
Ngrok Helper - Gets the current ngrok tunnel URL
"""

import requests
import time
import logging
import os

logger = logging.getLogger(__name__)


def get_ngrok_url(max_retries=10, retry_delay=2):
    """
    Get the current ngrok tunnel URL
    
    Args:
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
    
    Returns:
        str: Ngrok public URL or None if not available
    """
    for attempt in range(max_retries):
        try:
            # Try to get URL from ngrok API
            response = requests.get('http://localhost:4040/api/tunnels', timeout=2)
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get('tunnels', [])
                
                if tunnels:
                    # Get the https URL (preferred) or http
                    for tunnel in tunnels:
                        url = tunnel.get('public_url', '')
                        if url.startswith('https'):
                            logger.info(f"Got ngrok URL: {url}")
                            return url
                    
                    # Fallback to first URL
                    url = tunnels[0].get('public_url', '')
                    if url:
                        logger.info(f"Got ngrok URL: {url}")
                        return url
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Attempt {attempt + 1}/{max_retries}: Ngrok API not ready - {e}")
        
        except Exception as e:
            logger.warning(f"Error getting ngrok URL: {e}")
        
        # Try reading from file as fallback
        try:
            url_file = os.path.join(os.path.dirname(__file__), 'ngrok_url.txt')
            if os.path.exists(url_file):
                with open(url_file, 'r') as f:
                    url = f.read().strip()
                    if url:
                        logger.info(f"Got ngrok URL from file: {url}")
                        return url
        except Exception as e:
            logger.debug(f"Could not read ngrok URL from file: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    
    logger.warning("Could not get ngrok URL after all retries")
    return None


def start_ngrok_tunnel():
    """
    Start ngrok tunnel by running the batch script
    """
    import subprocess
    import sys
    
    try:
        script_dir = os.path.dirname(__file__)
        script_path = os.path.join(script_dir, 'start_ngrok.bat')
        
        if os.path.exists(script_path):
            logger.info("Starting ngrok tunnel...")
            subprocess.Popen([script_path], shell=True, 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            return True
        else:
            logger.warning(f"Ngrok script not found: {script_path}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to start ngrok: {e}")
        return False


def get_connection_url():
    """
    Get the connection URL for this device.
    Tries ngrok first, falls back to public IP with port.
    
    Returns:
        str: Connection URL (ngrok or http://public_ip:5000)
    """
    # Try ngrok first
    ngrok_url = get_ngrok_url(max_retries=3, retry_delay=1)
    if ngrok_url:
        return ngrok_url
    
    # Fallback to public IP
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        public_ip = response.json()['ip']
        return f"http://{public_ip}:5000"
    except:
        return "http://localhost:5000"
