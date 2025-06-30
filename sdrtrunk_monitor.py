#!/usr/bin/env python3
"""
SDRTrunk Monitor Script
Monitors SDRTrunk application status, log files, and audio recordings
"""

import os
import sys
import json
import time
import psutil
import logging
import requests
import platform
from datetime import datetime, timedelta
from pathlib import Path
import wave
import threading
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sdrtrunk_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SDRTrunkMonitor:
    def __init__(self, config_file: str = "monitor_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.username = self.get_username()
        self.base_path = self.get_sdrtrunk_path()
        self.logs_path = self.base_path / "logs"
        self.recordings_path = self.base_path / "recordings"
        self.last_audio_check = datetime.now()
        self.audio_files_processed = 0
        self.start_time = datetime.now()  # Track when monitor started
        
    def get_username(self) -> str:
        """Get current Windows username"""
        return os.getenv('USERNAME') or os.getenv('USER')
    
    def get_sdrtrunk_path(self) -> Path:
        """Get SDRTrunk base path for current user"""
        return Path(f"C:/Users/{self.username}/SDRTrunk")
    
    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {self.config_file} not found, creating default")
            default_config = {
                "heartbeat_url": "https://your-heartbeat-endpoint.com/heartbeat",
                "error_keywords": [
                    "ERROR", "CRITICAL", "FAILED", "EXCEPTION", "TIMEOUT",
                    "Connection refused", "Network error", "Audio error"
                ],
                "check_interval_seconds": 60,
                "audio_quality_threshold_seconds": 5.0,
                "max_audio_age_hours": 4,
                "process_name": "sdrtrunk",
                "telegram": {
                    "enabled": False,
                    "bot_token": "your_telegram_bot_token_here",
                    "channel_id": "your_telegram_channel_id_here",
                    "computer_name": "SDRTrunk-Monitor"
                }
            }
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config: Dict):
        """Save configuration to JSON file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def is_sdrtrunk_running(self) -> bool:
        """Check if SDRTrunk process is running by looking for Java processes with SDRTrunk indicators"""
        try:
            sdrtrunk_found = False
            process_count = 0
            current_pid = os.getpid()  # Get our own PID to exclude it
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Skip our own process
                    if proc.info.get('pid') == current_pid:
                        continue
                        
                    name = proc.info.get('name', '').lower()
                    cmdline_raw = proc.info.get('cmdline', [])
                    
                    # Skip processes without command line info
                    if not cmdline_raw:
                        continue
                    
                    # Ensure cmdline is a list or tuple before joining
                    if isinstance(cmdline_raw, (list, tuple)):
                        cmdline = ' '.join(cmdline_raw).lower()
                    elif isinstance(cmdline_raw, str):
                        cmdline = cmdline_raw.lower()
                    else:
                        continue
                    
                    process_count += 1
                    
                    # Only look for Java processes that might be SDRTrunk
                    if name == 'java.exe' or name == 'javaw.exe':
                        # Check if command line contains SDRTrunk-related keywords
                        sdrtrunk_indicators = [
                            'sdrtrunk',
                            'sdr trunk',
                            'sdr-trunk',
                            'sdrtrunk.jar',
                            'sdrtrunk-',
                            'trunking'
                        ]
                        
                        for indicator in sdrtrunk_indicators:
                            if indicator in cmdline:
                                logger.info(f"Found SDRTrunk process: PID {proc.info.get('pid')}, CMD: {cmdline[:100]}...")
                                sdrtrunk_found = True
                                break
                        
                        if sdrtrunk_found:
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Skip processes we can't access
                    continue
            
            if not sdrtrunk_found:
                logger.info(f"SDRTrunk not found. Checked {process_count} processes.")
            
            return sdrtrunk_found
            
        except Exception as e:
            logger.error(f"Error checking process: {e}")
            return False
    
    def check_log_errors(self) -> List[str]:
        """Check log file for errors that occurred after the monitor started, ignoring lines with ignore_keywords"""
        errors = []
        log_file = self.logs_path / "sdrtrunk_app.log"
        
        logger.info(f"Checking log file: {log_file}")
        
        if not log_file.exists():
            logger.warning(f"Log file not found: {log_file}")
            return errors
        
        try:
            current_time = datetime.now()
            ignore_keywords = self.config.get("ignore_keywords", [])
            lines_checked = 0
            lines_after_start = 0
            
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    lines_checked += 1
                    # Check if line is from after monitor started
                    if self.is_line_after_start(line, current_time):
                        lines_after_start += 1
                        # Skip if any ignore keyword is present
                        if any(ignore_kw.lower() in line.lower() for ignore_kw in ignore_keywords):
                            continue
                        for keyword in self.config["error_keywords"]:
                            if keyword.lower() in line.lower():
                                logger.info(f"Found error keyword '{keyword}' in line: {line.strip()}")
                                errors.append(line.strip())
                                break
            
            logger.info(f"Log check complete: {lines_checked} total lines, {lines_after_start} after monitor start, {len(errors)} errors found")
            
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
        
        return errors
    
    def is_line_after_start(self, line: str, current_time: datetime) -> bool:
        """Check if log line is from after the monitor started"""
        try:
            # Try to parse timestamp from log line
            # SDRTrunk format: 20250629 224900.679
            parts = line.split()
            if len(parts) >= 2:
                date_str = parts[0]  # 20250629
                time_str = parts[1].split('.')[0]  # 224900 (remove milliseconds)
                
                # Parse date and time
                line_date = datetime.strptime(date_str, "%Y%m%d").date()
                line_time = datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M%S")
                
                # Check if line is from after monitor started
                return line_time >= self.start_time
        except:
            pass
        return False
    
    def check_audio_quality(self, audio_file: Path) -> bool:
        """Check audio file quality"""
        try:
            with wave.open(str(audio_file), 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration = frames / float(rate)
                
                # Check if audio is longer than threshold
                if duration >= self.config["audio_quality_threshold_seconds"]:
                    logger.info(f"Audio file {audio_file.name} quality OK: {duration:.2f}s")
                    return True
                else:
                    logger.warning(f"Audio file {audio_file.name} too short: {duration:.2f}s")
                    return False
        except Exception as e:
            logger.error(f"Error checking audio quality for {audio_file}: {e}")
            return False
    
    def process_audio_files(self) -> int:
        """Process audio files in recordings directory"""
        if not self.recordings_path.exists():
            logger.warning(f"Recordings directory not found: {self.recordings_path}")
            return 0
        
        processed_count = 0
        current_time = datetime.now()
        
        try:
            for audio_file in self.recordings_path.glob("*.wav"):
                # Check if file is older than max age
                file_age = current_time - datetime.fromtimestamp(audio_file.stat().st_mtime)
                if file_age > timedelta(hours=self.config["max_audio_age_hours"]):
                    logger.warning(f"Audio file too old, deleting: {audio_file.name}")
                    audio_file.unlink()
                    continue
                
                # Check audio quality
                if self.check_audio_quality(audio_file):
                    processed_count += 1
                
                # Delete file after processing
                audio_file.unlink()
                logger.info(f"Processed and deleted: {audio_file.name}")
                
        except Exception as e:
            logger.error(f"Error processing audio files: {e}")
        
        return processed_count
    
    def should_send_heartbeat(self) -> bool:
        """Determine if heartbeat should be sent"""
        # Check if SDRTrunk is running
        if not self.is_sdrtrunk_running():
            logger.warning("SDRTrunk is not running")
            self.send_telegram_message("❌ **SDRTrunk is not running!**\n\nPlease check the application status.")
            return False
        
        # Check for log errors
        errors = self.check_log_errors()
        if errors:
            logger.warning(f"Found {len(errors)} errors in log file")
            error_summary = f"Found {len(errors)} errors in SDRTrunk log file:\n\n"
            for i, error in enumerate(errors[:3], 1):  # Show first 3 errors
                error_summary += f"{i}. {error[:100]}...\n"
            if len(errors) > 3:
                error_summary += f"\n... and {len(errors) - 3} more errors"
            
            self.send_telegram_message(f"⚠️ **SDRTrunk Errors Detected**\n\n{error_summary}")
            return False
        
        # Check audio processing if enabled
        monitor_audio = self.config.get("monitor_audio", True)
        if monitor_audio:
            current_time = datetime.now()
            time_since_audio = current_time - self.last_audio_check
            if time_since_audio > timedelta(hours=self.config["max_audio_age_hours"]):
                logger.warning(f"No audio processing for more than {self.config['max_audio_age_hours']} hours")
                self.send_telegram_message(f"⚠️ **No Audio Processing**\n\nNo audio processing detected for more than {self.config['max_audio_age_hours']} hours.")
                return False
        
        return True
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to configured URL"""
        try:
            payload = {
                "timestamp": datetime.now().isoformat(),
                "status": "healthy",
                "sdrtrunk_running": self.is_sdrtrunk_running(),
                "audio_files_processed": self.audio_files_processed,
                "username": self.username
            }
            
            response = requests.post(
                self.config["heartbeat_url"],
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Heartbeat sent successfully")
                return True
            else:
                logger.error(f"Heartbeat failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            return False
    
    def send_telegram_message(self, message: str) -> bool:
        """Send message to Telegram channel"""
        telegram_config = self.config.get("telegram", {})
        
        if not telegram_config.get("enabled", False):
            return True  # Not enabled, consider it successful
        
        bot_token = telegram_config.get("bot_token")
        channel_id = telegram_config.get("channel_id")
        computer_name = telegram_config.get("computer_name", "SDRTrunk-Monitor")
        
        if not bot_token or not channel_id:
            logger.warning("Telegram bot token or channel ID not configured")
            return False
        
        try:
            # Format message with computer name
            formatted_message = f"🚨 **{computer_name}**\n\n{message}"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": channel_id,
                "text": formatted_message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram message failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        logger.info("Starting monitoring cycle")

        monitor_audio = self.config.get("monitor_audio", True)
        audio_processed = 0
        if monitor_audio:
            # Process audio files
            audio_processed = self.process_audio_files()
            if audio_processed > 0:
                self.audio_files_processed += audio_processed
                self.last_audio_check = datetime.now()
        else:
            logger.info("Audio monitoring is disabled by config.")

        # Check if we should send heartbeat
        if self.should_send_heartbeat():
            self.send_heartbeat()
        else:
            logger.warning("Conditions not met for heartbeat - skipping")

        logger.info("Monitoring cycle completed")
    
    def run(self):
        """Main monitoring loop"""
        logger.info(f"Starting SDRTrunk Monitor for user: {self.username}")
        logger.info(f"Monitor started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"SDRTrunk path: {self.base_path}")
        logger.info(f"Logs path: {self.logs_path}")
        logger.info(f"Recordings path: {self.recordings_path}")
        
        while True:
            try:
                self.run_monitoring_cycle()
                time.sleep(self.config["check_interval_seconds"])
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in monitoring cycle: {e}")
                time.sleep(self.config["check_interval_seconds"])

def main():
    """Main entry point"""
    monitor = SDRTrunkMonitor()
    monitor.run()

if __name__ == "__main__":
    main() 