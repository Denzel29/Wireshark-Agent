# Wireshark Agent Suite

> AI-powered network traffic analysis. Captures live traffic via `tshark`, classifies each flow with an LLM, and streams results to a live web dashboard.

---

## What it does

Raw network traffic is mostly noise. This tool captures it, tags what's interesting, and tells you why.

- Attaches to a network interface and captures live traffic via `tshark` — no GUI, no manual captures
- A classifier agent tags each flow as **benign**, **suspicious**, or **unknown** using the Gemini API
- An alert agent watches for repeated suspicious/unknown flows from the same source and fires structured alerts
- Flows, alerts, and sessions are persisted to SQLite
- A live web dashboard streams flows in real time over WebSockets

---

## Stack

| Layer | Tool |
|---|---|
| Packet capture | tshark (Wireshark CLI) |
| Backend runtime | Python 3.11+ |
| AI / LLM | Gemini API (`gemini-2.5-flash-lite`) |
| Storage | SQLite |
| Backend | FastAPI |
| Real-time | FastAPI WebSockets |
| Frontend | Next.js + TypeScript |
| Styling | Tailwind CSS |

---

## Project structure

```
Wireshark-Agent/
├── main.py                     # Entry point: starts capture + web server
├── config.yaml                 # Agent thresholds
├── requirements.txt
│
├── capture/
│   ├── tshark_stream.py        # Live capture (tshark -T ek stream)
│   └── filter.py               # Pre-agent noise filter
│
├── agents/
│   ├── classifier.py           # Classifies each flow via Gemini
│   └── alert_agent.py          # Evaluates thresholds, fires alerts
│
├── storage/
│   ├── db.py                   # SQLite queries
│   └── schema.sql              # Table definitions
│
├── server/
│   ├── app.py                  # FastAPI app + WebSocket endpoint
│   └── websocket.py            # WebSocket connection manager
│
├── data/
│   └── wireshark_agent.db      # Auto-created on first run
│
└── frontend/
    └── src/app/                # Next.js live feed UI
```

---

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+
- tshark installed (`sudo apt install tshark` on Ubuntu, or install Wireshark on macOS/Windows)
- A Gemini API key

### 1. Clone and install

```bash
git clone https://github.com/Denzel29/Wireshark-Agent.git
cd Wireshark-Agent

# Backend
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### 2. Configure

Set your Gemini API key as an environment variable (or place it in a `.env` file at the project root):

```bash
export GEMINI_API_KEY=your_key_here
```

Agent thresholds live in `config.yaml`:

```yaml
agents:
  model: gemini-2.5-flash-lite
  alert_thresholds:
    suspicious_count: 3      # alert after N suspicious flows from same source
    unknown_count: 5         # alert after N unknown flows from same source
    time_window_seconds: 60  # rolling window for the counts above
```

### 3. Run

**Backend + live capture** — attach to a network interface:

```bash
python main.py --interface eth0
```

On Windows, use the interface name or index (e.g. `--interface "Ethernet"` or `--interface 1`).

**Frontend** (separate terminal):

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000` for the live feed. The FastAPI backend runs on `http://localhost:8000`.

---

## How the pipeline works

```
Network interface
        │
        ▼
   tshark (NDJSON / EK stream)
        │
        ▼
   Filter layer          ← drops non-IP packets and broadcasts
        │
        ▼
   Classifier Agent      ← Gemini tags each flow: benign / suspicious / unknown
        │
        ├──▶  Alert Agent      ← fires when suspicious/unknown counts cross thresholds
        │          │
        │          └──▶  WebSocket push to UI + terminal output
        │
        └──▶  SQLite           ← flows, alerts, and sessions stored
                  │
                  └──▶  FastAPI ──▶ Next.js live feed
```

### The agents

**Classifier** (`agents/classifier.py`) — called for every flow that survives the filter. Sends flow metadata to Gemini and returns a classification, a confidence score, and descriptive tags. Falls back to `unknown` with `0.0` confidence if the API call fails or returns invalid JSON.

**Alert Agent** (`agents/alert_agent.py`) — tracks suspicious and unknown flows per source IP within a rolling time window. When a count crosses its threshold, it asks Gemini to generate a structured alert (severity, category, description, reasoning) and falls back to a threshold-based alert if the model doesn't respond.

---

## Data model

Three SQLite tables defined in `storage/schema.sql`:

- **sessions** — one row per capture run, with flow counts and per-severity alert tallies
- **flows** — every flow that passed the filter, with its classification, confidence, and tags
- **alerts** — fired alerts, linked back to their session, with severity and reasoning

---

## Roadmap

Planned but not yet implemented:

- [ ] PCAP file import (analyze historical `.pcap` / `.pcapng` captures)
- [ ] Report agent + PDF report generation
- [ ] Email delivery of reports
- [ ] REST API routes for sessions, flows, and alerts
- [ ] Additional UI views (alerts, session history, reports)
- [ ] IP whitelist and configurable capture filters
- [ ] Basic auth for the web UI

---

## License

MIT
