"""
Simple Signage Player - Clean and Simple
Checks API for schedules, downloads videos, plays them at scheduled time
"""
import time
import os
import sys
import json
import subprocess
import requests
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
import platform

# Setup logging - when running as EXE, log file should be in same folder as EXE
if getattr(sys, 'frozen', False):
    # Running as compiled EXE
    exe_dir = Path(sys.executable).parent
    log_file = exe_dir / 'player.log'
else:
    # Running as script
    log_file = Path('player.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global state
vlc_process = None
config = None
current_playing_version = None
downloaded_videos = {}  # {version: file_path}
vlc_started_for_version = None  # Track if VLC was successfully started for current version
vlc_start_time = 0  # Track when VLC was last started
last_screenshot = 0  # Track last screenshot time


def load_config():
    """Load configuration"""
    global config
    
    # When running as EXE, config.json should be in same folder as EXE
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        exe_dir = Path(sys.executable).parent
        config_path = exe_dir / "config.json"
    else:
        # Running as script
        config_path = Path("config.json")
    
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        logger.info("Please create config.json in the same folder as the EXE")
        raise FileNotFoundError("Config file not found")
    
    with open(config_path, "r") as f:
        config = json.load(f)
    
    # Create video directory
    video_dir = Path(config["video_dir"])
    video_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Config loaded. Screen ID: {config['screen_id']}")
    return config


def get_schedules():
    """Get all schedules from API"""
    try:
        url = f"{config['server_url']}/api/screens/{config['screen_id']}/schedule-data"
        logger.info(f"Fetching schedules from: {url}")
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {config['api_key']}"},
            timeout=30  # Increased timeout for large responses
        )
        response.raise_for_status()
        data = response.json()
        schedules = data.get("schedules", [])
        logger.info(f"Successfully fetched {len(schedules)} schedule(s) from API")
        if schedules:
            for schedule in schedules:
                logger.info(f"  - Schedule {schedule.get('schedule_id')}: {schedule.get('schedule_time')} (version {schedule.get('version')})")
        else:
            logger.warning("API returned empty schedules list - check if schedules are configured and videos are READY")
            # Log the full response for debugging
            logger.debug(f"Full API response: {data}")
        return schedules
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching schedules from API (URL: {url})")
        logger.error("The API server may be slow or the endpoint is taking too long to respond")
        return []
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching schedules: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                logger.error(f"Error details: {error_detail}")
            except:
                logger.error(f"Response status: {e.response.status_code}, Response text: {e.response.text[:200]}")
        return []
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error fetching schedules: {e}")
        logger.error("Cannot connect to API server - check network connection and server URL")
        return []
    except Exception as e:
        logger.error(f"Failed to get schedules: {e}", exc_info=True)
        return []


def download_video(video_url: str, version: int) -> Optional[Path]:
    """Download video file"""
    video_dir = Path(config["video_dir"])
    video_file = video_dir / f"final_v{version}.mp4"
    
    # If file already exists, check if it's valid
    if video_file.exists():
        file_size = video_file.stat().st_size
        if file_size > 1024 * 1024:  # At least 1MB
            logger.info(f"Video v{version} already exists locally ({file_size / (1024*1024):.2f} MB)")
            return video_file
    
    # Download video
    try:
        logger.info(f"Downloading video v{version} from {video_url}")
        response = requests.get(video_url, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(video_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        if downloaded % (10 * 1024 * 1024) == 0:  # Log every 10MB
                            logger.info(f"Download progress: {percent:.1f}%")
        
        logger.info(f"Downloaded video v{version} ({video_file.stat().st_size / (1024*1024):.2f} MB)")
        return video_file
    except Exception as e:
        logger.error(f"Failed to download video v{version}: {e}")
        if video_file.exists():
            video_file.unlink()
        return None


def stop_vlc():
    """Stop VLC"""
    global vlc_process
    
    if vlc_process and vlc_process.poll() is None:
        try:
            vlc_process.terminate()
            vlc_process.wait(timeout=3)
        except:
            try:
                vlc_process.kill()
            except:
                pass
    
    vlc_process = None
    
    # Kill any VLC processes on Windows
    if platform.system() == "Windows":
        try:
            subprocess.run(["taskkill", "/F", "/IM", "vlc.exe", "/T"], 
                         capture_output=True, timeout=3)
        except:
            pass
    
    time.sleep(1)


def start_vlc(video_file: Path):
    """Start VLC playing video"""
    global vlc_process, vlc_start_time
    
    stop_vlc()
    
    # Verify video file exists and is valid
    if not video_file.exists():
        logger.error(f"Video file does not exist: {video_file}")
        return False
    
    try:
        file_size = video_file.stat().st_size
        if file_size < 1024 * 1024:  # Less than 1MB is suspicious
            logger.error(f"Video file is too small ({file_size / 1024:.2f} KB): {video_file}")
            return False
        logger.info(f"Video file size: {file_size / (1024*1024):.2f} MB")
    except Exception as e:
        logger.error(f"Cannot access video file: {e}")
        return False
    
    vlc_path = Path(config["vlc_path"])
    if not vlc_path.exists():
        logger.error(f"VLC not found at: {vlc_path}")
        return False
    
    video_path = str(video_file.resolve())
    
    try:
        # Use VLC command with flags to keep it running 24/7
        # --loop: Loop the video continuously
        # --fullscreen: Fullscreen mode
        # --no-video-title-show: Hide video title
        # --aspect-ratio=16:9: Force 16:9 aspect ratio
        # --quiet: Suppress console output
        vlc_cmd = [
            str(vlc_path),
            video_path,
            "--fullscreen",
            "--loop",
            "--no-video-title-show",
            "--aspect-ratio=16:9",
            "--quiet"
        ]
        
        logger.info(f"Starting VLC with: {video_file.name}")
        
        # On Windows, use CREATE_NEW_PROCESS_GROUP and DETACHED_PROCESS
        # to make VLC completely independent and keep it running
        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        
        vlc_process = subprocess.Popen(
            vlc_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags
        )
        
        logger.info(f"VLC process started (PID: {vlc_process.pid})")
        
        # Wait for VLC to initialize - check multiple times
        # VLC might spawn child processes, so check for any vlc.exe
        for i in range(10):  # Check 10 times over 5 seconds
            time.sleep(0.5)
            
            # Check if any VLC process is running (not just our tracked one)
            if platform.system() == "Windows":
                try:
                    result = subprocess.run(
                        ["tasklist", "/FI", "IMAGENAME eq vlc.exe", "/NH"],
                        capture_output=True,
                        timeout=2,
                        text=True
                    )
                    if "vlc.exe" in result.stdout:
                        logger.info(f"VLC is running (checked {i+1}/10)")
                        # Track when VLC started
                        vlc_start_time = time.time()
                        return True
                except:
                    pass
            
            # Also check our tracked process
            if vlc_process.poll() is None:
                logger.info(f"VLC process is running (checked {i+1}/10)")
                # Track when VLC started
                vlc_start_time = time.time()
                return True
        
        # If we get here, VLC didn't start properly
        exit_code = vlc_process.poll()
        if exit_code is not None:
            logger.error(f"VLC exited with code: {exit_code}")
            vlc_process = None
            vlc_start_time = 0
            return False
        else:
            logger.warning("VLC process check timeout, but process may still be running")
            # Assume it's running if we can't determine
            vlc_start_time = time.time()
            return True
        
    except Exception as e:
        logger.error(f"Failed to start VLC: {e}", exc_info=True)
        if vlc_process:
            try:
                vlc_process.kill()
            except:
                pass
            vlc_process = None
        return False


def check_vlc_running():
    """Check if VLC is running - robust check for any vlc.exe process"""
    global vlc_process
    
    # On Windows, check if any VLC process is running
    # VLC often spawns child processes, so we check for any vlc.exe
    if platform.system() == "Windows":
        try:
            # Use a more reliable method - check for vlc.exe processes
            # Use /NH to skip header, and /FO CSV for easier parsing
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq vlc.exe", "/NH", "/FO", "CSV"],
                capture_output=True,
                timeout=3,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Check the output
            output = result.stdout.strip()
            
            # CSV format: "vlc.exe","1234","Console","1","45,123 K"
            # Check if we have any lines with vlc.exe
            if output and 'vlc.exe' in output.lower():
                # Parse CSV to verify it's a real process
                lines = output.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    # CSV format - check if it starts with "vlc.exe"
                    if line.lower().startswith('"vlc.exe"'):
                        # Try to extract PID (second field)
                        try:
                            import csv
                            reader = csv.reader([line])
                            fields = next(reader)
                            if len(fields) >= 2:
                                pid = fields[1].strip('"')
                                int(pid)  # Verify it's a number
                                return True
                        except (ValueError, IndexError, csv.Error):
                            # If CSV parsing fails, just check if vlc.exe is in the line
                            if 'vlc.exe' in line.lower():
                                return True
            
            # VLC not found - log and return False
            logger.warning("[VLC CHECK] VLC is NOT running (not found in tasklist)")
            # Reset tracked process since VLC is not running
            vlc_process = None
            return False
            
        except Exception as e:
            logger.error(f"[VLC CHECK] Error checking VLC processes: {e}", exc_info=True)
            # On error, check tracked process as fallback
            if vlc_process:
                is_running = vlc_process.poll() is None
                if not is_running:
                    vlc_process = None
                return is_running
            return False
    
    # Fallback: check tracked process
    if vlc_process:
        is_running = vlc_process.poll() is None
        if not is_running:
            logger.warning("[VLC CHECK] VLC is NOT running (tracked process ended)")
            # Reset since process ended
            vlc_process = None
        return is_running
    
    # No tracked process and no VLC found - VLC is not running
    logger.warning("[VLC CHECK] VLC is NOT running (no tracked process)")
    return False


def get_current_schedule(schedules):
    """Get the schedule that should be playing now"""
    if not schedules:
        return None
    
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    current_hour, current_minute = map(int, current_time.split(":"))
    current_minutes = current_hour * 60 + current_minute
    
    # Sort schedules by time
    sorted_schedules = sorted(schedules, key=lambda s: s.get("schedule_time", "00:00"))
    
    # Find the most recent schedule that has passed
    current_schedule = None
    for schedule in sorted_schedules:
        schedule_time = schedule.get("schedule_time", "")
        if ":" in schedule_time:
            try:
                sched_hour, sched_minute = map(int, schedule_time.split(":"))
                sched_minutes = sched_hour * 60 + sched_minute
                
                if sched_minutes <= current_minutes:
                    current_schedule = schedule
                else:
                    # Future schedule - stop here
                    break
            except ValueError:
                logger.warning(f"Invalid schedule time format: {schedule_time}")
                continue
    
    # If no schedule passed today, use the last one from yesterday
    if not current_schedule and sorted_schedules:
        current_schedule = sorted_schedules[-1]
        logger.info(f"No schedule passed today, using last schedule: {current_schedule.get('schedule_time')}")
    
    return current_schedule


def send_heartbeat(version: int, status: str = "playing"):
    """Send heartbeat to API"""
    try:
        url = f"{config['server_url']}/api/screens/{config['screen_id']}/heartbeat"
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {config['api_key']}"},
            json={
                "version": version,
                "status": status,
                "player_info": {
                    "os": platform.system(),
                    "app_version": "2.0.0"
                }
            },
            timeout=5
        )
        response.raise_for_status()
    except Exception as e:
        logger.debug(f"Heartbeat failed: {e}")


def capture_and_send_screenshot(version: int):
    """Capture screenshot and send to server - safe version that won't interfere with VLC"""
    global last_screenshot
    
    if not config.get("screenshot_enabled", True):
        return
    
    # CRITICAL: Don't take screenshot if VLC is not running - it might interfere
    if not check_vlc_running():
        logger.debug("[SCREENSHOT] VLC not running, skipping screenshot")
        return
    
    try:
        import mss
        import mss.tools
        
        # Add a small delay before capture to ensure VLC is stable
        time.sleep(0.5)
        
        # Verify VLC is still running before capture
        if not check_vlc_running():
            logger.debug("[SCREENSHOT] VLC stopped before screenshot capture")
            return
        
        # Use a quick capture method that won't interfere with VLC's fullscreen
        with mss.mss() as sct:
            # Get primary monitor (monitor 1)
            monitor = sct.monitors[1]
            logger.debug(f"[SCREENSHOT] Capturing from monitor: {monitor}")
            
            # Use fast capture mode - grab in one shot
            img = sct.grab(monitor)
            
            # Verify image was captured
            if not img:
                logger.error("[SCREENSHOT] Failed to capture image - img is None")
                return
            
            logger.debug(f"[SCREENSHOT] Image captured: size={img.size}, width={img.width}, height={img.height}")
            
            # Convert to PNG - try multiple methods for reliability
            png_bytes = None
            
            # Method 1: Try using PIL (most reliable)
            try:
                from PIL import Image
                import numpy as np
                # Convert mss screenshot to PIL Image
                # mss returns BGRA format
                pixels = np.array(img)
                # Convert BGRA to RGB
                rgb_pixels = pixels[:, :, [2, 1, 0]]  # BGR to RGB
                pil_image = Image.fromarray(rgb_pixels)
                import io
                png_buffer = io.BytesIO()
                pil_image.save(png_buffer, format='PNG', optimize=False)
                png_bytes = png_buffer.getvalue()
                logger.debug("[SCREENSHOT] PNG created using PIL")
            except ImportError:
                logger.debug("[SCREENSHOT] PIL/numpy not available, trying mss.tools")
            except Exception as e:
                logger.warning(f"[SCREENSHOT] PIL conversion failed: {e}, trying fallback")
            
            # Method 2: Fallback to mss.tools
            if not png_bytes:
                try:
                    # Try saving to temp file first (more reliable)
                    import tempfile
                    temp_file = None
                    try:
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                            temp_file = tmp.name
                        mss.tools.to_png(img, output=temp_file)
                        with open(temp_file, 'rb') as f:
                            png_bytes = f.read()
                        logger.debug("[SCREENSHOT] PNG created using mss.tools (temp file method)")
                    finally:
                        if temp_file and os.path.exists(temp_file):
                            try:
                                os.unlink(temp_file)
                            except:
                                pass
                except Exception as e:
                    logger.error(f"[SCREENSHOT] mss.tools conversion failed: {e}")
                    return
            
            # Verify PNG bytes are valid
            if not png_bytes:
                logger.error("[SCREENSHOT] Failed to create PNG - no data")
                return
            
            if len(png_bytes) < 100:  # PNG should be at least 100 bytes
                logger.error(f"[SCREENSHOT] Invalid PNG data: only {len(png_bytes)} bytes (too small)")
                return
            
            # Verify it's a valid PNG (starts with PNG signature)
            if not png_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                logger.error("[SCREENSHOT] Invalid PNG - missing PNG signature")
                return
            
            logger.info(f"[SCREENSHOT] PNG created successfully: {len(png_bytes) / 1024:.2f} KB")
        
        # Immediately verify VLC is still running after screenshot
        if not check_vlc_running():
            logger.warning("[SCREENSHOT] VLC stopped during screenshot capture - aborting upload")
            return
        
        # Small delay before network operation
        time.sleep(0.2)
        
        # Verify VLC is still running before network call
        if not check_vlc_running():
            logger.warning("[SCREENSHOT] VLC stopped before upload - aborting")
            return
        
        # Send to server with shorter timeout to avoid blocking
        files = {"file": ("screen.png", png_bytes, "image/png")}
        data = {"version": str(version)}
        
        response = requests.post(
            f'{config["server_url"]}/api/screens/{config["screen_id"]}/screenshot',
            headers={"Authorization": f'Bearer {config["api_key"]}'},
            files=files,
            data=data,
            timeout=10  # Shorter timeout
        )
        response.raise_for_status()
        
        # Final check - verify VLC is still running after upload
        if not check_vlc_running():
            logger.warning("[SCREENSHOT] VLC stopped after screenshot upload")
            return
        
        # Log response details
        try:
            response_data = response.json()
            screenshot_id = response_data.get("screenshot_id")
            image_url = response_data.get("image_url", "N/A")
            logger.info(f"[SCREENSHOT] Screenshot sent successfully (version: {version}, ID: {screenshot_id}, URL: {image_url})")
        except:
            logger.info(f"[SCREENSHOT] Screenshot sent successfully (version: {version})")
    except requests.exceptions.HTTPError as e:
        error_detail = "Unknown error"
        try:
            error_detail = e.response.json().get("detail", str(e))
        except:
            error_detail = str(e)
        logger.error(f"[SCREENSHOT] HTTP error: {error_detail} (Status: {e.response.status_code if hasattr(e, 'response') else 'N/A'})")
    except ImportError:
        logger.error("[SCREENSHOT] mss library not installed. Install with: pip install mss")
    except Exception as e:
        logger.warning(f"[SCREENSHOT] Screenshot failed: {e}")


def main():
    """Main loop"""
    global current_playing_version
    
    logger.info("=" * 60)
    logger.info("Simple Signage Player Starting")
    logger.info("=" * 60)
    
    # Load config
    try:
        load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return
    
    video_dir = Path(config["video_dir"])
    
    logger.info("=" * 60)
    logger.info("Entering main loop...")
    logger.info("=" * 60)
    
    last_schedule_check = 0
    last_heartbeat = 0
    last_screenshot = 0
    schedules = []
    
    loop_count = 0
    while True:
        try:
            now = time.time()
            loop_count += 1
            
            # CRITICAL: Keep VLC alive - check FIRST before doing anything else
            # This runs every loop iteration to ensure VLC stays running 24/7
            vlc_is_running = check_vlc_running()
            
            # Log VLC status every 12 loops (every ~60 seconds) for monitoring
            if loop_count % 12 == 0:
                logger.info(f"[STATUS] VLC status: {'RUNNING' if vlc_is_running else 'NOT RUNNING'} (loop {loop_count})")
            
            # Always log when VLC is not running (so we can see it immediately)
            if not vlc_is_running:
                logger.error("=" * 60)
                logger.error(f"[KEEP-ALIVE] VLC is NOT running! (checked at {datetime.now().strftime('%H:%M:%S')})")
                logger.error("=" * 60)
                # VLC is not running - restart it immediately
                logger.error("=" * 60)
                logger.error("VLC IS NOT RUNNING - ATTEMPTING IMMEDIATE RESTART")
                logger.error("=" * 60)
                
                video_to_play = None
                target_version = None
                
                # Determine which video to play
                # Priority: 1) Current schedule, 2) Last played version, 3) Any available video
                current_schedule = get_current_schedule(schedules)
                logger.info(f"[KEEP-ALIVE] Current schedule: {current_schedule}")
                logger.info(f"[KEEP-ALIVE] Current playing version: {current_playing_version}")
                logger.info(f"[KEEP-ALIVE] Downloaded videos: {list(downloaded_videos.keys())}")
                
                # Try to get video from schedule first
                if current_schedule:
                    target_version = current_schedule.get("version")
                    logger.info(f"[KEEP-ALIVE] Trying schedule version: {target_version}")
                    if target_version:
                        video_to_play = downloaded_videos.get(target_version)
                        if video_to_play and video_to_play.exists():
                            current_playing_version = target_version
                            logger.info(f"[KEEP-ALIVE] Found video file from schedule: {video_to_play}")
                        else:
                            logger.warning(f"[KEEP-ALIVE] Video file not found for schedule version {target_version}")
                
                # If no video from schedule, try last played version
                if (not video_to_play or not video_to_play.exists()) and current_playing_version:
                    target_version = current_playing_version
                    logger.info(f"[KEEP-ALIVE] Trying last played version: {target_version}")
                    video_to_play = downloaded_videos.get(target_version)
                    if video_to_play and video_to_play.exists():
                        logger.info(f"[KEEP-ALIVE] Found video file from last played: {video_to_play}")
                    else:
                        logger.warning(f"[KEEP-ALIVE] Video file not found for last played version {target_version}")
                
                # If still no video, try any available video
                if (not video_to_play or not video_to_play.exists()) and downloaded_videos:
                    # Use the most recent version available
                    available_versions = sorted(downloaded_videos.keys(), reverse=True)
                    if available_versions:
                        target_version = available_versions[0]
                        video_to_play = downloaded_videos.get(target_version)
                        if video_to_play and video_to_play.exists():
                            current_playing_version = target_version
                            logger.info(f"[KEEP-ALIVE] Using any available video: version {target_version}")
                            logger.info(f"[KEEP-ALIVE] Video file: {video_to_play}")
                
                # If we have a video file, restart VLC immediately
                if video_to_play and video_to_play.exists():
                    logger.warning(f"[KEEP-ALIVE] VLC stopped! Restarting immediately with version {target_version}...")
                    logger.warning(f"[KEEP-ALIVE] Video file: {video_to_play}")
                    logger.warning(f"[KEEP-ALIVE] File exists: {video_to_play.exists()}")
                    logger.warning(f"[KEEP-ALIVE] File size: {video_to_play.stat().st_size / (1024*1024):.2f} MB")
                    
                    if start_vlc(video_to_play):
                        vlc_started_for_version = target_version
                        logger.info(f"[KEEP-ALIVE] VLC restarted successfully with version {target_version}")
                    else:
                        logger.error(f"[KEEP-ALIVE] Failed to restart VLC with version {target_version}")
                        vlc_started_for_version = None
                else:
                    logger.error("=" * 60)
                    logger.error("VLC stopped but no video file available to restart!")
                    logger.error(f"Target version: {target_version}")
                    logger.error(f"Video to play: {video_to_play}")
                    if video_to_play:
                        logger.error(f"File exists: {video_to_play.exists()}")
                    logger.error("=" * 60)
            
            # Check schedules every minute
            if now - last_schedule_check >= 60:
                logger.info("Checking schedules from API...")
                schedules = get_schedules()
                logger.info(f"Found {len(schedules)} schedule(s)")
                
                # Download all scheduled videos
                for schedule in schedules:
                    version = schedule.get("version")
                    video_url = schedule.get("video_url")
                    
                    if version and video_url:
                        video_file = download_video(video_url, version)
                        if video_file:
                            downloaded_videos[version] = video_file
                
                last_schedule_check = now
            
            # Get current schedule from cached schedules
            current_schedule = get_current_schedule(schedules)
            
            if current_schedule:
                version = current_schedule.get("version")
                schedule_time = current_schedule.get("schedule_time")
                
                # ONLY restart VLC if schedule version changed (and VLC is already running)
                # If VLC is not running, the keep-alive check above will restart it
                if version and version != current_playing_version:
                    # Schedule changed - switch to new video
                    video_file = downloaded_videos.get(version)
                    
                    if video_file and video_file.exists():
                        logger.info(f"Schedule changed: Switching to {schedule_time} (version {version})")
                        if start_vlc(video_file):
                            current_playing_version = version
                            vlc_started_for_version = version
                            logger.info(f"Now playing version {version} (scheduled for {schedule_time})")
                        else:
                            logger.error(f"Failed to start VLC with version {version}")
                            vlc_started_for_version = None
                    else:
                        logger.warning(f"Video file for version {version} not found locally, downloading...")
                        # Try to download it
                        video_url = current_schedule.get("video_url")
                        if video_url:
                            video_file = download_video(video_url, version)
                            if video_file:
                                downloaded_videos[version] = video_file
                                if start_vlc(video_file):
                                    current_playing_version = version
                                    vlc_started_for_version = version
                                    logger.info(f"Downloaded and started version {version}")
                                else:
                                    vlc_started_for_version = None
                elif version == current_playing_version:
                    # Already playing correct video - VLC should stay running 24/7
                    # Only start VLC if it was never started for this version
                    if vlc_started_for_version != version:
                        # VLC was never started for this version - start it now (first time)
                        video_file = downloaded_videos.get(version)
                        if video_file and video_file.exists():
                            logger.info(f"Starting VLC for version {version} (first time)")
                            if start_vlc(video_file):
                                vlc_started_for_version = version
                                logger.info("VLC started and will run 24/7")
                    # VLC keep-alive is handled above - no need to check here
            else:
                # No schedule - keep playing current video
                # VLC keep-alive is handled above - it will restart if needed
                pass
            
            # Send heartbeat every minute
            if now - last_heartbeat >= config.get("heartbeat_interval_seconds", 60):
                if current_playing_version:
                    send_heartbeat(current_playing_version, "playing" if check_vlc_running() else "stopped")
                last_heartbeat = now
            
            # Screenshot - only if VLC has been running for at least 60 seconds
            # This prevents screenshots from interfering with VLC startup
            screenshot_interval = config.get("screenshot_interval_seconds", 300)
            vlc_uptime = now - vlc_start_time if vlc_start_time > 0 else 0
            
            if (config.get("screenshot_enabled", True) and 
                now - last_screenshot >= screenshot_interval and
                check_vlc_running() and
                vlc_uptime >= 60 and  # Only take screenshot if VLC has been running for 60+ seconds
                current_playing_version):
                logger.debug(f"[SCREENSHOT] Capturing and sending screenshot (version: {current_playing_version}, VLC uptime: {vlc_uptime:.1f}s)")
                capture_and_send_screenshot(current_playing_version)
                last_screenshot = now
            elif config.get("screenshot_enabled", True) and now - last_screenshot >= screenshot_interval:
                if vlc_uptime < 60:
                    logger.debug(f"[SCREENSHOT] Skipping screenshot - VLC not stable enough (uptime: {vlc_uptime:.1f}s, need 60s)")
                last_screenshot = now  # Reset to avoid constant checking
            
            # Sleep - shorter interval for faster VLC keep-alive checks
            # This ensures VLC restarts quickly if it crashes
            # Note: We check VLC status every loop iteration (every 5 seconds)
            time.sleep(5)  # Check every 5 seconds for VLC keep-alive
            
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            stop_vlc()
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            time.sleep(10)


if __name__ == "__main__":
    main()

