#!/usr/bin/env python3
"""
Test script for Telegram messaging functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sdrtrunk_monitor import SDRTrunkMonitor

def test_telegram():
    print("Testing Telegram messaging functionality...")
    print("=" * 50)
    
    monitor = SDRTrunkMonitor()
    
    # Check current Telegram config
    telegram_config = monitor.config.get("telegram", {})
    print(f"Telegram enabled: {telegram_config.get('enabled', False)}")
    print(f"Bot token: {telegram_config.get('bot_token', 'Not set')}")
    print(f"Channel ID: {telegram_config.get('channel_id', 'Not set')}")
    print(f"Computer name: {telegram_config.get('computer_name', 'Not set')}")
    
    # Test sending a message
    print("\nTesting Telegram message send...")
    test_message = "🧪 **Test Message**\n\nThis is a test message from the SDRTrunk Monitor."
    result = monitor.send_telegram_message(test_message)
    
    if result:
        print("✅ Telegram message test completed successfully")
    else:
        print("❌ Telegram message test failed")
        print("Note: This is expected if Telegram is not configured or enabled")

if __name__ == "__main__":
    test_telegram() 