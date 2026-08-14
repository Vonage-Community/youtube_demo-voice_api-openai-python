import os
import json
from datetime import datetime

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from vonage import Vonage, Auth
from vonage_voice import Talk
from openai import OpenAI
from openpyxl import load_workbook
from threading import Thread
import requests

# Load environment variables
load_dotenv()
APP_ID = os.getenv("VONAGE_APPLICATION_ID")
PRIVATE_KEY_PATH = os.getenv("VONAGE_PRIVATE_KEY_PATH")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", 3000))
TICKETS_FILE = os.getenv("TICKETS_FILE")
PLAYBOOK_FILE = os.getenv("PLAYBOOK_FILE")

# Set up clients
vonage_client = Vonage(Auth(application_id=APP_ID, private_key=PRIVATE_KEY_PATH))
openai_client = OpenAI()

# Load the company playbook
with open(PLAYBOOK_FILE) as f:
    PLAYBOOK = f.read()

# Create Flask app
app = Flask(__name__)

# Keep track of who called, keyed by conversation ID
callers = {}


@app.route("/webhooks/answer", methods=["GET"])
def answer():
    callers[request.args.get("conversation_uuid")] = request.args.get("from")
    talk = Talk(
        text="You've reached customer support. Please leave a message "
             "after the beep, and our team will get back to you shortly.",
        language="en-US")
    record = {
        "action": "record",
        "beepStart": True,
        "endOnSilence": 3,
        "transcription": {
            "language": "en-US",
            "eventMethod": "POST",
            "eventUrl": [BASE_URL + "/webhooks/transcription"],
        },
    }

    return jsonify([
        talk.model_dump(exclude_none=True, mode="json"),
        record,
    ])


@app.route("/webhooks/transcription", methods=["POST"])
def transcription():
    Thread(target=process_transcription, args=(request.get_json(),)).start()
    return ("", 204)

def process_transcription(data):
    caller = callers.pop(data.get("conversation_uuid"), "Unknown")

    # Fetch the transcript from Vonage
    jwt = vonage_client.http_client.auth.create_jwt_auth_string()
    response = requests.get(data["transcription_url"],
                            headers={"Authorization": jwt})
    sentences = response.json()["channels"][0]["transcript"]
    transcript = " ".join(s["sentence"] for s in sentences)

    # Analyze it against the playbook
    completion = openai_client.chat.completions.create(
        model="gpt-5-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content":
                "You are a customer support analyst. Using the company "
                "playbook below, analyze the customer's voicemail and "
                "return JSON with the keys: summary, category, priority, "
                "and plan. The category must be one of: Refunds, "
                "Shipping, Account Access, Escalation, or Unknown. The "
                "priority must be one of: Low, Medium, or High. The "
                "plan should be the steps an employee should take to "
                "resolve the issue, based only on the playbook."
                "\n\nPLAYBOOK:\n" + PLAYBOOK},
            {"role": "user", "content": transcript},
        ])
    ticket = json.loads(completion.choices[0].message.content)

    create_ticket(caller, transcript, ticket)
    return ("", 204)


def create_ticket(caller, transcript, ticket):
    workbook = load_workbook(TICKETS_FILE)
    workbook.active.append([
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        caller,
        transcript,
        ticket["summary"],
        ticket["category"],
        ticket["priority"],
        str(ticket["plan"]),
    ])
    workbook.save(TICKETS_FILE)


@app.route("/webhooks/event", methods=["POST"])
def event():
    return ("", 204)


if __name__ == "__main__":
    app.run(port=PORT)
