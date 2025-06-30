# SDRTrunk Monitor

A Python script to monitor SDRTrunk application status, log files, and audio recordings with automatic heartbeat reporting and Telegram notifications.

## Features

- **Universal Path Detection**: Automatically detects the current Windows username and SDRTrunk paths
- **Process Monitoring**: Checks if SDRTrunk is running
- **Log File Monitoring**: Scans `sdrtrunk_app.log` for errors after monitor start (ignores old errors)
- **Audio Quality Monitoring (Optional)**: Checks audio files in recordings folder and deletes after processing (can be disabled)
- **Heartbeat Reporting**: Sends status updates to configured endpoint
- **Telegram Notifications**: Sends instant alerts to Telegram channel when issues are detected
- **Configurable**: All settings stored in JSON configuration file
- **Ignore List**: Can ignore specific log lines to prevent false alerts

## Requirements

- Python 3.7 or higher
- Windows OS
- SDRTrunk installed in `C:\Users\{username}\SDRTrunk`

## One-Click Install: Auto Python and Dependencies

Run `install_everything.bat` as an **ADMINISTRATOR**. This will:
- Check for Python and install it if missing
- Install all required Python packages
- **Does NOT start the monitor automatically** (run it manually after install)

## Manual Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure the monitor:**
   - Edit `monitor_config.json` and update the `heartbeat_url` to your endpoint
   - Adjust error keywords, ignore keywords, check intervals, and other settings as needed

## Configuration

The `monitor_config.json` file contains all configurable settings:

```json
{
  "heartbeat_url": "https://your-heartbeat-endpoint.com/heartbeat",
  "error_keywords": [
    "ERROR", "Exception", "No Tuner Available", "Error getting source", "failed", "failed to load", "Pipe error", "USB error", "LibUsbException", "NullPointerException", "IndexOutOfBoundsException", "Couldn't design final output low pass filter", "AMBE CODEC failed", "JMBE audio conversion library failed", "No audio", "Audio error", "Buffer overflow", "Disk full"
  ],
  "ignore_keywords": [
    "FrequencyErrorCorrectionManager - Auto-Correcting Tuner PPM"
  ],
  "monitor_audio": true,
  "check_interval_seconds": 60,
  "audio_quality_threshold_seconds": 5.0,
  "max_audio_age_hours": 4,
  "process_name": "sdrtrunk",
  "telegram": {
    "enabled": false,
    "bot_token": "your_telegram_bot_token_here",
    "channel_id": "your_telegram_channel_id_here",
    "computer_name": "SDRTrunk-Monitor"
  }
}
```

### Configuration Options

- **heartbeat_url**: URL to send heartbeat status updates
- **error_keywords**: List of keywords that indicate errors in log files
- **ignore_keywords**: List of keywords/phrases to ignore in log lines (prevents false alerts)
- **monitor_audio**: Set to `true` to enable audio file monitoring and quality checks, or `false` to disable all audio monitoring
- **check_interval_seconds**: How often to run monitoring checks (default: 60 seconds)
- **audio_quality_threshold_seconds**: Minimum audio duration to consider "good quality"
- **max_audio_age_hours**: Maximum age of audio files before deletion or before heartbeat is blocked (if audio monitoring is enabled)
- **process_name**: Name of the SDRTrunk process to monitor (substring match)
- **telegram**: Telegram notification settings
  - **enabled**: Enable/disable Telegram notifications
  - **bot_token**: Your Telegram bot token (get from @BotFather)
  - **channel_id**: Your Telegram channel ID
  - **computer_name**: Custom name for your computer (appears in messages)

## Telegram Setup

### 1. Create a Telegram Bot
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Save the bot token (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Channel ID
1. Add your bot to your channel as an admin
2. Send a message in the channel
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find the `chat_id` for your channel (usually starts with `-100`)

### 3. Configure Monitor
Update your `monitor_config.json`:
```json
"telegram": {
  "enabled": true,
  "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
  "channel_id": "-1001234567890",
  "computer_name": "My-SDRTrunk-Server"
}
```

### 4. Test Configuration
Run the test script to verify your setup:
```bash
python test_telegram.py
```

## Usage

### Quick Start
```bash
python sdrtrunk_monitor.py
```

### Using the Batch File (Windows)
Double-click `start_monitor.bat` or run it from command prompt.

### Using the One-Click Installer
1. Run `install_everything.bat` as administrator
2. After install, start the monitor with:
   ```bash
   python sdrtrunk_monitor.py
   ```

### Running as a Service
You can set up the script to run as a Windows service using tools like:
- NSSM (Non-Sucking Service Manager)
- Windows Task Scheduler

## How It Works

### 1. Path Detection
The script automatically detects:
- Current Windows username
- SDRTrunk base path: `C:\Users\{username}\SDRTrunk`
- Logs path: `C:\Users\{username}\SDRTrunk\logs`
- Recordings path: `C:\Users\{username}\SDRTrunk\recordings`

### 2. Monitoring Cycle (Runs every minute)
1. **Process Check**: Verifies SDRTrunk is running
2. **Log Analysis**: Scans `sdrtrunk_app.log` for errors after monitor start (ignores old errors)
3. **Audio Processing (if enabled)**: 
   - Checks audio quality (duration ≥ threshold)
   - Deletes processed files
   - Tracks processing activity
4. **Heartbeat Decision**: Determines if conditions are met for heartbeat
5. **Status Report**: Sends heartbeat if all checks pass
6. **Telegram Notifications**: Sends alerts when issues are detected

### 3. Heartbeat Conditions
Heartbeat is sent ONLY when:
- ✅ SDRTrunk process is running
- ✅ No errors found in log file after monitor start (excluding ignored lines)
- ✅ Audio has been processed within last N hours (if audio monitoring is enabled)

### 4. Error Detection & Notifications
The script monitors for these types of issues and sends Telegram alerts:
- ❌ SDRTrunk process not running
- ⚠️ Error keywords in log files (excluding ignored lines)
- ⚠️ No audio processing for >N hours (if audio monitoring is enabled)
- ⚠️ Audio quality issues (files too short, if enabled)

## Logging

The script creates `sdrtrunk_monitor.log` with detailed monitoring information:
- Process status
- Log file errors
- Audio processing results
- Heartbeat success/failure
- Configuration warnings

## Troubleshooting

### Common Issues

1. **"Log file not found"**
   - Ensure SDRTrunk is configured to log to `sdrtrunk_app.log`
   - Check that the logs directory exists

2. **"Recordings directory not found"**
   - Verify SDRTrunk recordings path is correct
   - Create the directory if it doesn't exist

3. **"Heartbeat failed"**
   - Check your heartbeat URL is correct and accessible
   - Verify network connectivity
   - Check server endpoint is responding

4. **"SDRTrunk is not running"**
   - Verify the process name in config matches actual SDRTrunk process
   - Check if SDRTrunk is actually running

### Debug Mode
To see more detailed output, modify the logging level in the script:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## Customization

### Adding Error Keywords
Edit `monitor_config.json` and add keywords to the `error_keywords` array:
```json
"error_keywords": [
  "ERROR", "Exception", "No Tuner Available", ...
]
```

### Adding Ignore Keywords
Edit `monitor_config.json` and add keywords/phrases to the `ignore_keywords` array:
```json
"ignore_keywords": [
  "FrequencyErrorCorrectionManager - Auto-Correcting Tuner PPM",
  "YOUR_OTHER_IGNORE_PHRASE"
]
```

### Disabling Audio Monitoring
Set `monitor_audio` to `false` in the config to skip all audio file checks and related heartbeat conditions:
```json
"monitor_audio": false
```

### Changing Check Frequency
Modify `check_interval_seconds` in the config:
```json
"check_interval_seconds": 30  // Check every 30 seconds
```

### Adjusting Audio Quality Threshold
Change the minimum audio duration:
```json
"audio_quality_threshold_seconds": 3.0  // Minimum 3 seconds
```

## Security Notes

- The script reads log files and audio files but doesn't modify them (except deletion)
- Heartbeat payload includes username and status information
- Consider using HTTPS for heartbeat URLs in production
- Review error keywords and ignore keywords to avoid false positives

## Support

For issues or questions:
1. Check the log file for detailed error messages
2. Verify all paths and configurations
3. Test heartbeat URL manually before running
4. Ensure Python dependencies are installed correctly 