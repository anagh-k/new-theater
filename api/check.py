import json
import logging
import os
from datetime import datetime

import requests
from redis import Redis
from twilio.rest import Client

logging.basicConfig(level=logging.INFO)

redis = Redis.from_url(os.environ["REDIS_URL"])

twilio = Client(
    os.environ["TWILIO_ACCOUNT_SID"],
    os.environ["TWILIO_AUTH_TOKEN"]
)

URL = "https://api3.pvrcinemas.com/api/v1/booking/content/msessions"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "appversion": "1.0",
    "authorization": "Bearer",
    "chain": "PVR",
    "city": os.environ["CITY"],
    "content-type": "application/json",
    "country": "INDIA",
    "origin": "https://www.pvrcinemas.com",
    "platform": "WEBSITE",
    "user-agent": "Mozilla/5.0"
}


def send_sms(message):

    twilio.messages.create(
        body=message,
        from_=os.environ["TWILIO_PHONE"],
        to=os.environ["YOUR_PHONE"]
    )

    logging.info("SMS sent")


def fetch_theatres():

    payload = {
        "city": os.environ["CITY"],
        "mid": os.environ["MOVIE_ID"],
        "experience": "ALL",
        "specialTag": "ALL",
        "lat": os.environ["LAT"],
        "lng": os.environ["LNG"],
        "lang": "ALL",
        "format": "ALL",
        "dated": os.environ["DATE"],
        "time": "08:00-24:00",
        "cinetype": "ALL",
        "hc": "ALL",
        "adFree": False,
        "bbt": False
    }

    response = requests.post(
        URL,
        headers=HEADERS,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    theatres = {}

    sessions = data["output"]["movieCinemaSessions"]

    for cinema_session in sessions:

        cinema = cinema_session["cinema"]

        theatres[cinema["theatreId"]] = {
            "name": cinema["name"],
            "distance": cinema.get("distanceText", ""),
            "shows": cinema_session["showCount"]
        }

    return theatres


def load_known():

    value = redis.get("known_theatres")

    if value is None:
        return None

    return json.loads(value)


def save_known(data):

    redis.set("known_theatres", json.dumps(data))


def check():

    known = load_known()

    current = fetch_theatres()

    logging.info("--------------------------------------")
    logging.info(datetime.now())
    logging.info("Current theatres : %s", len(current))

    if known is None:

        logging.info("First run.")
        logging.info("Saving baseline.")

        save_known(current)

        return {
            "status": "baseline saved"
        }

    logging.info("Known theatres : %s", len(known))

    new_theatres = []

    for theatre_id, theatre in current.items():

        if theatre_id not in known:
            new_theatres.append(theatre)

    logging.info("New theatres : %s", len(new_theatres))

    if not new_theatres:

        logging.info("No new theatres.")

        return {
            "status": "no changes"
        }

    message = "🎬 New Odyssey theatre(s)\n\n"

    for theatre in new_theatres:

        logging.info(theatre["name"])

        message += (
            f'{theatre["name"]}\n'
            f'{theatre["distance"]}\n'
            f'Shows: {theatre["shows"]}\n\n'
        )

    send_sms(message)

    known.update(current)

    save_known(known)

    return {
        "status": "notification sent"
    }


def handler(request):

    result = check()

    return result