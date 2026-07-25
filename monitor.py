import json
import os
import time
from datetime import datetime

import requests
from twilio.rest import Client

# ==========================
# Configuration
# ==========================

POLL_INTERVAL = 60  # seconds

TWILIO_ACCOUNT_SID = "AC5ea2174126f8b8f304bb09928ec8f81f"
TWILIO_AUTH_TOKEN = "6f0e49406d7cfd5f794fc1b87e1d2195"
TWILIO_PHONE = "+19379152576"
YOUR_PHONE = "+916282432948"

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
    "bbt": False
}

STATE_FILE = "known_theatres.json"

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_sms(message):
    client.messages.create(
        body=message,
        from_=TWILIO_PHONE,
        to=YOUR_PHONE
    )
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
    r = requests.post(
        URL,
        headers=HEADERS,
        json=PAYLOAD,
        timeout=30,
    )

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

    # First run - establish baseline only
    if not known:
        print("First run. Fetching current theatres as baseline...")
        known = fetch_theatres()
        save_known(known)
        print(f"Saved {len(known)} theatres. Monitoring for new ones...")
    else:
        print(f"Loaded {len(known)} known theatres.")

    while True:
        try:
            known = load_known()
            current = fetch_theatres()

            new_theatres = []

            for theatre_id, theatre in current.items():
                if theatre_id not in known:
                    new_theatres.append(theatre)

            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Checked | Current: {len(current)} | "
                f"Known: {len(known)} | "
                f"New: {len(new_theatres)}"
            )

            if new_theatres:
                print("New theatres found:")

                msg = "🎬 New Odyssey theatre(s) available:\n\n"

                for t in new_theatres:
                    print(f"  • {t['name']} ({t['distance']}) - {t['shows']} shows")

                    msg += (
                        f"{t['name']}\n"
                        f"Distance: {t['distance']}\n"
                        f"Shows: {t['shows']}\n\n"
                    )

                send_sms(msg)

                known.update(current)
                save_known(known)

            else:
                print("No new theatres.")

        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}")

        print("-" * 80)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
