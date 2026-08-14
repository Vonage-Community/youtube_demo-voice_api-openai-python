# Automate Customer Support Calls with OpenAI and Vonage's Voice API

A small Flask app that turns customer voicemails into actionable support tickets.

A customer calls your support number and leaves a message. Vonage records and transcribes it, then OpenAI analyzes the transcript against your company support playbook and returns a summary, category, priority, and resolution plan. The app writes it all to an Excel file as a ready-to-work ticket.

## How it works

```
Customer call
      │
      ▼
/webhooks/answer ──► NCCO: Talk (greeting) + Record (with transcription)
      │
      ▼
Vonage records + transcribes the voicemail
      │
      ▼
/webhooks/transcription ──► fetch transcript (JWT-authed GET)
      │                     └─► OpenAI (gpt-5-mini) analyzes vs. playbook.txt
      ▼
create_ticket() ──► appends a row to tickets.xlsx
```

`/webhooks/event` receives call status updates (ringing, completed) and simply returns a 200.

## Prerequisites

- A [Vonage API account](https://developer.vonage.com/)
- An [OpenAI API key](https://platform.openai.com)
- Python 3
- [ngrok](https://ngrok.com) (or any tunneling tool) so Vonage can reach your local webhooks

## Vonage setup

1. In the Vonage dashboard, go to **Build → Applications** and click **Create a new application**. Give it a name.
2. Click **Generate public and private key**. The private key downloads to your machine — note where it lands.
3. Under **Capabilities**, toggle on **Voice**. Fill the webhook fields with a placeholder like `example.com` for now; you'll come back to these.
4. Click **Generate new application** and copy the **Application ID**.
5. Under **Build → Phone Numbers**, get a virtual number and link it to your application. This is the number customers will call. If you're in the US, follow the additional steps to make your number [10DLC compliant](https://developer.vonage.com/).

## Install

```bash
mkdir support-line
cd support-line
python3 -m venv venv && source venv/bin/activate
pip3 install vonage flask openai openpyxl requests python-dotenv
```

| Package | Why |
| --- | --- |
| `vonage` | Vonage Python SDK — builds the NCCO and generates the JWT for fetching transcripts |
| `flask` | Lightweight web framework for the webhook routes |
| `openai` | Analyzes the transcript against the playbook |
| `openpyxl` | Writes tickets to the Excel file |
| `requests` | Fetches the hosted transcript from Vonage |
| `python-dotenv` | Loads environment variables |

## Configuration

Create a `.env` file in the project root:

```
VONAGE_APPLICATION_ID=application_id
VONAGE_PRIVATE_KEY_PATH=./private.key
OPENAI_API_KEY=your_openai_api_key
TICKETS_FILE=tickets.xlsx
PLAYBOOK_FILE=playbook.txt
PORT=3000
BASE_URL=
```

Start ngrok and paste the forwarding URL into `BASE_URL`:

```bash
ngrok http 3000
```

### `playbook.txt`

The document OpenAI uses to decide how each issue should be resolved. Swap in your own — this is the demo version:

```
REFUNDS: Orders under $100 can be refunded right away. Orders over
$100 need manager approval before refunding.

SHIPPING: If a package is more than 5 days late, offer a replacement
or a full refund, and email the customer a tracking update.

ACCOUNT ACCESS: Send the customer a password reset link. Never change
account details over the phone.

ESCALATION: If the customer is upset or mentions legal action, set
the priority to High and assign a manager.

UNKNOWN: If an issue doesn't fit any of the categories above, set
the priority to High and leave the plan for an employee to decide.
```

### `tickets.xlsx`

Create the workbook with these column headers in row 1:

| Date | Caller | Transcript | Summary | Category | Priority | Plan |
| --- | --- | --- | --- | --- | --- | --- |

## Point Vonage at your webhooks

Back in your application's **Voice** capability settings, paste your ngrok forwarding URL into:

- **Answer URL** — `https://your-ngrok-url/webhooks/answer`
- **Event URL** — `https://your-ngrok-url/webhooks/event`

Click **Save changes**.

## Run it

```bash
python3 app.py
```

The app starts on `localhost:3000` (or whatever `PORT` you set). Make sure ngrok is still running, then call your support number and leave a message. A few moments after you hang up, a new row appears in `tickets.xlsx` with the transcript, summary, category, priority, and resolution plan.


## Resources

- [Voice API overview](https://developer.vonage.com/en/voice/voice-api/overview)
- [NCCO reference](https://developer.vonage.com/en/voice/voice-api/ncco-reference)
- [Recording guide](https://developer.vonage.com/en/voice/voice-api/guides/recording)
- [Transcription](https://developer.vonage.com/en/voice/voice-api/concepts/recording#transcription)
- [OpenAI Platform](https://platform.openai.com)
