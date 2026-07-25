import json
import os
import sys
from datetime import datetime

import requests
from twilio.rest import Client

# ==========================
# Configuration
# ==========================

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_PHONE = os.environ["TWILIO_PHONE"]
YOUR_PHONE = os.environ["YOUR_PHONE"]

URL = "https://api3.pvrcinemas.com/api/v1/booking/content/msessions"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "appversion": "1.0",
    "authorization": "Bearer",
    "chain": "PVR",
    "city": "Bengaluru",
    "content-type": "application/json",
    "country": "INDIA",
    "origin": "https://www.pvrcinemas.com",
    "platform": "WEBSITE",
    "user-agent": "Mozilla/5.0",
}

PAYLOAD = {
    "city": "Bengaluru",
    "mid": "35098",
    "experience": "ALL",
    "specialTag": "ALL",
    "lat": "12.9839857",
    "lng": "77.6559497",
    "lang": "ALL",
    "format": "ALL",
    "dated": "2026-07-30",
    "time": "08:00-24:00",
    "cinetype": "ALL",
    "hc": "ALL",
    "adFree": False,
    "bbt": False,
}

STATE_FILE = os.path.join(os.path.dirname(__file__), "known_theatres.json")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_sms(message):
    client.messages.create(body=message, from_=TWILIO_PHONE, to=YOUR_PHONE)
    print("SMS sent")


def load_known():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_known(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=4)


def fetch_theatres():
    r = requests.post(URL, headers=HEADERS, json=PAYLOAD, timeout=30)
    r.raise_for_status()
    data = r.json()

    theatres = {}
    sessions = data["output"]["movieCinemaSessions"]

    for cinema_session in sessions:
        cinema = cinema_session["cinema"]
        theatres[cinema["theatreId"]] = {
            "name": cinema["name"],
            "distance": cinema.get("distanceText", ""),
            "shows": cinema_session.get("showCount", 0),
        }

    return theatres


def main():
    known = load_known()
    first_run = not known

    if first_run:
        print("First run. Fetching current theatres as baseline...")
        current = fetch_theatres()
        save_known(current)
        print(f"Saved {len(current)} theatres. Baseline established, no SMS sent.")
        return

    try:
        current = fetch_theatres()
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}")
        sys.exit(1)  # non-zero exit so the Action run is visibly marked failed

    new_theatres = [t for tid, t in current.items() if tid not in known]

    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"Checked | Current: {len(current)} | Known: {len(known)} | New: {len(new_theatres)}"
    )

    if new_theatres:
        print("New theatres found:")
        msg = "🎬 New Odyssey theatre(s) available:\n\n"

        for t in new_theatres:
            print(f"  • {t['name']} ({t['distance']}) - {t['shows']} shows")
            msg += f"{t['name']}\nDistance: {t['distance']}\nShows: {t['shows']}\n\n"

        send_sms(msg)
        known.update(current)
        save_known(known)
    else:
        print("No new theatres.")


if __name__ == "__main__":
    main()
