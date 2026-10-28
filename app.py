from datetime import datetime
import os
import threading
import time
from dotenv import load_dotenv
from flask import Flask
import pytz
import requests
import schedule

# Load .env file locally (Render will provide them automatically in production)
load_dotenv()

# ================= CONFIGURATION =================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CITY = os.getenv("CITY", "Casablanca")
COUNTRY = os.getenv("COUNTRY", "Morocco")
TIMEZONE = os.getenv("TIMEZONE", "Africa/Casablanca")
METHOD = int(os.getenv("METHOD", 3))

# Validate that secrets are provided
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError(
        "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment variables!"
    )
# =================================================

app = Flask(__name__)


def send_telegram_notification(prayer_name):
    message = (
        f"🕌 Time for {prayer_name}!\n\n"
        f"It is now time for the {prayer_name} prayer in {CITY}."
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")


def get_prayer_times():
    url = f"http://api.aladhan.com/v1/timingsByCity?city={CITY}&country={COUNTRY}&method={METHOD}"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("code") == 200:
            timings = res["data"]["timings"]
            return {
                "Fajr": timings["Fajr"],
                "Dhuhr": timings["Dhuhr"],
                "Asr": timings["Asr"],
                "Maghrib": timings["Maghrib"],
                "Isha": timings["Isha"],
            }
    except Exception as e:
        print(f"Error fetching API: {e}")
    return None


def schedule_today_prayers():
    print(f"Updating prayer schedule for {CITY}...")
    schedule.clear("prayer_job")
    timings = get_prayer_times()
    if not timings:
        return

    for prayer, time_str in timings.items():
        print(f"Scheduled {prayer} at {time_str}")
        schedule.every().day.at(time_str).do(
            send_telegram_notification, prayer_name=prayer
        ).tag("prayer_job")


def run_scheduler():
    schedule_today_prayers()
    schedule.every().day.at("00:01").do(schedule_today_prayers)

    while True:
        schedule.run_pending()
        time.sleep(30)


@app.route("/")
def home():
    now = datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    return f"Prayer Notifier is ACTIVE for {CITY}. Local time: {now}"


# Background worker thread
t = threading.Thread(target=run_scheduler, daemon=True)
t.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)