import os
import csv
import time
import asyncio
import random
import requests
import sqlite3
from telethon.sync import TelegramClient
from telethon.errors import (
    FloodWaitError, PhoneNumberBannedError, SessionPasswordNeededError
)
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import (
    InputReportReasonSpam,
    InputReportReasonViolence,
    InputReportReasonChildAbuse,
    InputReportReasonPornography,
    InputReportReasonCopyright,
    InputReportReasonFake,
    InputReportReasonOther
)

# TELEGRAM API CREDENTIALS
API_ID = 27157163  
API_HASH = "e0145db12519b08e1d2f5628e2db18c4"

# BOT API
BOT_API = "7588614459:AAHPU7D7LrwuOS51qscgNsiGamzLT9wVpRw"

# REQUIRED FILES
ACCOUNTS_FILE = "accounts.txt"
SELECT_MSG_FILE = "select_msg.csv"
SAVE_REPORT_FILE = "save_report.csv"

# REPORT REASONS
REPORT_REASONS = {
    "1": ("Child Abuse", InputReportReasonChildAbuse()),
    "2": ("Violence", InputReportReasonViolence()),
    "3": ("Illegal Goods", InputReportReasonOther()),
    "4": ("Illegal Adult Content", InputReportReasonPornography()),
    "5": ("Personal Data", InputReportReasonOther()),
    "6": ("Terrorism", InputReportReasonOther()),
    "7": ("Scam or Spam", InputReportReasonSpam()),
    "8": ("Copyright Violation", InputReportReasonCopyright()),
    "9": ("Fake Account", InputReportReasonFake()),
    "10": ("Other", InputReportReasonOther()),
}

# BANNER
BANNER = """
----------------------------------
♛ TELEGRAM MASS REPORT TOOL ♛
----------------------------------
☑ Use responsibly. Misuse may result in bans.
----------------------------------
"""

async def send_bot_notification(client, target, message_count):
    """Sends a confirmation message to the logged-in account."""
    me = await client.get_me()
    chat_id = me.id  # Get the logged-in account's chat ID

    text = (
        f"✔ **Report Successful!**\n"
        f"♔ **Target:** `{target}`\n"
        f"★ **Reported Messages:** `{message_count}`\n"
        f"☑ **Status:** ✅ Submitted\n"
        f"✗ **It may get banned soon!**"
    )

    url = f"https://api.telegram.org/bot{BOT_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✓ Notification sent to account!")
        else:
            print("✗ Failed to send notification!")
    except Exception as e:
        print(f"✗ Error sending notification: {e}")

async def report_messages(client, target_username, reason_key, message_urls, report_count):
    """Reports selected messages from a Telegram channel/group."""
    reason_text, reason_type = REPORT_REASONS[reason_key]

    print(f"\n♕ Target: {target_username}")
    print(f"☑ Reporting {len(message_urls)} messages for: {reason_text}")

    try:
        entity = await client.get_entity(target_username)
    except Exception as e:
        print(f"✗ Error: Could not find user/group ({e})")
        return

    for msg_url in message_urls:
        try:
            msg_id = int(msg_url.split("/")[-1])  # Extract message ID
            for i in range(report_count):
                await client(ReportPeerRequest(entity, reason_type, f"Violation report {i+1}"))
                print(f"✓ Report {i+1}/{report_count} sent for message: {msg_id}")
                time.sleep(random.uniform(2, 5))  

            with open(SAVE_REPORT_FILE, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([target_username, msg_url, reason_text, "Success"])

        except FloodWaitError as e:
            print(f"✗ Flood Wait! Switching accounts in {e.seconds} seconds...")
            time.sleep(e.seconds)
            break
        except Exception as e:
            print(f"✗ Error reporting message {msg_url}: {e}")
            break

    # Send bot notification
    await send_bot_notification(client, target_username, len(message_urls))

async def login_and_report(phone, target_username, reason_key, message_urls, report_count):
    """Handles login and reporting for a single account."""
    session_file = f"sessions/{phone.replace('+', '')}.session"

    if os.path.exists(session_file):
        try:
            with open(session_file, "rb") as f:
                if not f.read():
                    print(f"✗ Corrupted session for {phone}, deleting...")
                    os.remove(session_file)
        except Exception as e:
            print(f"✗ Error reading session for {phone}: {e}")
            os.remove(session_file)

    try:
        async with TelegramClient(session_file, API_ID, API_HASH) as client:
            await client.start(phone)
            print(f"✓ Logged in with {phone}")
            await report_messages(client, target_username, reason_key, message_urls, report_count)
    except sqlite3.OperationalError:
        print(f"✗ Session database error for {phone}. Deleting and retrying...")
        os.remove(session_file)
        return await login_and_report(phone, target_username, reason_key, message_urls, report_count)
    except PhoneNumberBannedError:
        print(f"✗ Account {phone} is banned! Skipping...")
    except SessionPasswordNeededError:
        print(f"✗ Account {phone} requires a password! Enter it manually.")

async def main():
    """Main function to initiate mass reporting."""
    print(BANNER)

    if not os.path.exists(ACCOUNTS_FILE):
        print(f"✗ Error: {ACCOUNTS_FILE} not found!")
        return

    with open(ACCOUNTS_FILE, "r") as f:
        phone_numbers = [line.strip() for line in f if line.strip()]

    if not phone_numbers:
        print("✗ No accounts found in accounts.txt!")
        return

    target_username = input("Enter Username or Group (@username): ").strip()

    print("\nChoose Report Reason:")
    for key, (reason_text, _) in REPORT_REASONS.items():
        print(f"   {key}. {reason_text}")

    reason_key = input("\nEnter Report Reason (1-10): ").strip()
    while reason_key not in REPORT_REASONS:
        print("✗ Invalid selection! Enter a number between 1-10.")
        reason_key = input("Enter Report Reason (1-10): ").strip()

    report_count = int(input("How many messages to report?: "))

    if not os.path.exists(SELECT_MSG_FILE):
        print(f"✗ Error: {SELECT_MSG_FILE} not found!")
        return

    with open(SELECT_MSG_FILE, "r") as f:
        message_urls = [line.strip() for line in f if line.strip()]

    if not message_urls:
        print("✗ No messages found in select_msg.csv!")
        return

    os.makedirs("sessions", exist_ok=True)

    for phone in phone_numbers:
        print(f"\n♛ Logging in with account: {phone}")
        await login_and_report(phone, target_username, reason_key, message_urls, report_count)

asyncio.run(main())