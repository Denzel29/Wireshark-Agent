# Wireshark Agent Suite

> AI-powered network traffic analysis. Captures live traffic or reads pcap files, classifies flows, fires alerts, and generates PDF reports — all from a single command.

---

## What it does

Raw network traffic is mostly noise. This tool filters it, tags what's interesting, and tells you why. You get a live web dashboard, real-time alerts, and downloadable PDF reports — without having to babysit Wireshark yourself.

- Attaches to a network interface and captures live traffic via `tshark` — no GUI, no manual captures
- Upload historical `.pcap` / `.pcapng` files and run them through the same pipeline
- AI agents classify each flow as **benign**, **suspicious**, or **unknown**
- Suspicious flows trigger structured alerts with severity levels and reasoning
- Session reports generated as PDFs, viewable in-browser or downloadable
- Email reports on demand to configured recipients

---

## Stack

| Layer | Tool |
|---|---|
| Packet capture | tshark (Wireshark CLI) |
| Agent runtime | Python 3.11+ |
| AI / LLM | Claude API (`claude-sonnet-4`) |
| Storage | SQLite |
| Backend | FastAPI |
| Real-time | FastAPI WebSockets |
| PDF reports | ReportLab |
| Email | smtplib |
| Frontend | Next.js 14 + TypeScript |
| Styling | Tailwind CSS |
| Infrastructure | Docker Compose (optional) |

---

## Project structure

```
wireshark-agent/
├── main.py                         # Entry point
├── config.yaml                     # All runtime config
├── requirements.txt
├── docker-compose.yml
│
├── capture/
│   ├── tshark_stream.py            # Live capture
│   ├── pcap_reader.py              # pcap file import
│   └── filter.py                   # Pre-agent noise filter
│
├── agents/
│   ├── classifier.py               # Classifies each flow via Claude
│   ├── alert_agent.py              # Evaluates thresholds, fires alerts
│   └── report_agent.py             # Generates report narrative
│
├── storage/
│   ├── db.py                       # SQLite queries and schema
│   └── schema.sql
│
├── reports/
│   ├── pdf_builder.py              # ReportLab PDF construction
│   └── generated/                  # PDF output directory
│
├── notifications/
│   └── email_service.py            # SMTP with PDF attachment
│
├── server/
│   ├── app.py                      # FastAPI app
│   ├── websocket.py                # WebSocket manager
│   └── routes/                     # sessions, flows, alerts, reports, upload, email
│
├── data/
│   └── wireshark_agent.db          # Auto-created on first run
│
└── frontend/
    └── src/
        ├── app/                    # Next.js routes (live, alerts, sessions, reports, import)
        ├── components/             # FlowTable, AlertCard, ReportViewer, UploadZone, etc.
        ├── hooks/                  # useWebSocket, useFlows, useAlerts
        └── lib/
            ├── api.ts              # Typed fetch wrappers
            └── types.ts            # Shared TypeScript interfaces
```

---

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+
- tshark installed (`sudo apt install tshark` on Ubuntu / download Wireshark on macOS or Windows)
- An Anthropic API key

### 1. Clone and install

```bash
git clone https://github.com/your-username/wireshark-agent.git
cd wireshark-agent

# Backend
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### 2. Configure

Copy the example config and fill in your values:

```bash
cp config.example.yaml config.yaml
```

Set your secrets as environment variables — never put them directly in `config.yaml`:

```bash
export ANTHROPIC_API_KEY=your_key_here
export SMTP_PASSWORD=your_smtp_password  # only needed if using email
```

Key settings in `config.yaml`:

```yaml
capture:
  interface: eth0        # your network interface
  whitelist_ips: []      # IPs to always treat as benign

agents:
  model: claude-sonnet-4
  alert_thresholds:
    suspicious_count: 3  # alert after 3 suspicious flows from same source
    time_window_seconds: 60

smtp:
  host: smtp.gmail.com
  port: 587
  username: you@example.com
  recipients:
    - analyst@example.com
```

### 3. Run

**Live capture** — attach to a network interface:

```bash
python main.py --interface eth0
```

**Web server only** — no capture, just the UI and stored data:

```bash
python main.py --no-capture
```

**Frontend** (separate terminal):

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000`.

The FastAPI backend runs on `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

### 4. Docker (optional)

```bash
docker-compose up
```

---

## How the pipeline works

```
Network interface / pcap file
        │
        ▼
   tshark (JSON stream)
        │
        ▼
   Filter layer          ← drops ARP, broadcasts, whitelisted IPs
        │
        ▼
   Classifier Agent      ← Claude tags each flow: benign / suspicious / unknown
        │
        ├──▶  Alert Agent      ← fires on suspicious flows above threshold
        │          │
        │          └──▶  WebSocket push to UI + terminal output
        │
        └──▶  SQLite           ← all flows, alerts, sessions stored
                  │
                  └──▶  FastAPI ──▶ Next.js web UI
```

### The agents

**Classifier** — gets called for every flow that survives the filter. Sends flow metadata to Claude and gets back a classification, a confidence score, and descriptive tags. Output is validated JSON before anything hits the database.

**Alert Agent** — only sees suspicious and unknown flows. Counts hits per source IP within a rolling time window. Once a threshold is crossed, calls Claude to generate a structured alert with severity, category, and reasoning. High-severity alerts push a persistent banner in the UI.

**Report Agent** — runs on demand or at session end. Pulls all session data from SQLite, asks Claude to write a narrative summary, and hands it to ReportLab for PDF rendering.

---

## Web UI

Five views, one navigation bar:

| View | What it shows |
|---|---|
| **Live Feed** | Real-time scrolling table of flows. Green = benign, amber = unknown, red = suspicious. Pause to inspect. |
| **Alert Feed** | Every alert the agent has fired. Severity badges, reasoning, acknowledge + notes. High alerts banner until dismissed. |
| **Session History** | All past sessions — live and imported. Flow counts, alert breakdown, link to report. |
| **Report Viewer** | PDF rendered inline. Download button. Email button (sends to configured recipients on request). |
| **PCAP Import** | Drag-and-drop pcap upload. Progress bar during analysis. Drops into the session view when done. |

---

## Alert severity

| Severity | When it fires |
|---|---|
| Low | Single suspicious flow, low confidence, or first unknown from a new source |
| Medium | Repeated suspicious flows from same source, or unknown protocol on a standard port |
| High | Clear attack signature — port scan, beaconing, exfiltration indicators, high-confidence hit |

High severity alerts stay visible in the UI until you acknowledge them. You can add notes at acknowledgement time.

---

## Reports

Reports are generated as PDFs and cover:

- Session overview (interface, duration, total flows)
- Traffic breakdown by protocol and classification
- Flagged flows table
- Alert breakdown by severity
- Top suspicious actors
- Timeline of events
- Analyst recommendations from the agent

Reports are stored in `reports/generated/` and can be viewed inline, downloaded, or emailed from the Report Viewer.

---

## Data model

Four SQLite tables: `sessions`, `flows`, `alerts`, `reports`. Everything links back to a session. The `raw_json` field on each flow stores the original tshark output, so you can replay or audit any capture later.

See the [system design document](docs/system_design.md) for the full schema.

---

## Configuration reference

| Key | Default | Description |
|---|---|---|
| `capture.interface` | `eth0` | Network interface for live capture |
| `capture.filter` | `ip` | tshark BPF filter expression |
| `capture.min_packet_size` | `40` | Drop packets below this size (bytes) |
| `capture.whitelist_ips` | `[]` | IPs always classified as benign |
| `agents.model` | `claude-sonnet-4` | Claude model for all agents |
| `agents.classifier_confidence_threshold` | `0.6` | Minimum confidence to act on |
| `agents.alert_thresholds.suspicious_count` | `3` | Hits before firing alert |
| `agents.alert_thresholds.time_window_seconds` | `60` | Rolling window for threshold counts |
| `smtp.host` | — | SMTP server hostname |
| `smtp.port` | `587` | SMTP port |
| `smtp.password_env` | `SMTP_PASSWORD` | Env var name for SMTP password |
| `server.port` | `8000` | FastAPI backend port |

---

## Roadmap

- [ ] Dashboard view — flow trends, protocol breakdown, top talkers
- [ ] Automatic email on high-severity alert (configurable threshold)
- [ ] Multi-interface capture
- [ ] Alert correlation across sessions
- [ ] Custom filter rules and thresholds via web UI
- [ ] Basic auth for web UI
- [ ] Full Docker Compose setup

---

## Requirements

- Python 3.11+
- Node.js 18+
- tshark (Wireshark CLI)
- Anthropic API key
- SMTP credentials (optional, for email)

---

## License

MIT
