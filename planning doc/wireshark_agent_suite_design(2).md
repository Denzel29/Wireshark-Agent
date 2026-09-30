# Wireshark Agent Suite
## System Design Document

**Defensive Cyber Monitoring Project — Tool 1 of 2**
Version 1.0 | Classification: Internal

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [High Level Design](#3-high-level-design)
4. [Architecture](#4-architecture)
   - 4.1 [Architecture Diagram Description](#41-architecture-diagram-description)
   - 4.2 [Component Breakdown](#42-component-breakdown)
5. [Capture Modes](#5-capture-modes)
   - 5.1 [Live Capture](#51-live-capture)
   - 5.2 [PCAP File Import](#52-pcap-file-import)
6. [Agent Pipeline](#6-agent-pipeline)
   - 6.1 [Filter Layer](#61-filter-layer)
   - 6.2 [Classifier Agent](#62-classifier-agent)
   - 6.3 [Alert Agent](#63-alert-agent)
   - 6.4 [Report Agent](#64-report-agent)
7. [Web Interface](#7-web-interface)
   - 7.1 [Live Traffic Feed](#71-live-traffic-feed)
   - 7.2 [Alert Feed](#72-alert-feed)
   - 7.3 [Session History](#73-session-history)
   - 7.4 [Report Viewer](#74-report-viewer)
   - 7.5 [PCAP Import UI](#75-pcap-import-ui)
8. [Notifications and Delivery](#8-notifications-and-delivery)
9. [Tech Stack](#9-tech-stack)
10. [Proposed File Structure](#10-proposed-file-structure)
11. [Data Model](#11-data-model)
12. [Configuration](#12-configuration)
13. [Future Expansion](#13-future-expansion)

---

## 1. Executive Summary

The Wireshark Agent Suite is the first of two tools in the Defensive Cyber Monitoring Project. It captures and analyses network traffic using an AI-driven agent pipeline, classifying flows, generating actionable alerts, and producing structured reports. The tool operates independently of the second tool (ELK Agent Suite) and targets home lab environments, with a design that supports future expansion to small business and enterprise networks.

The core problem it solves is cognitive load. Raw network traffic is high-volume and largely uninteresting. This tool sits between the wire and the analyst, filtering noise, tagging suspicious behaviour, and surfacing only what matters — in real time and across historical captures.

---

## 2. System Overview

The suite consists of three layers working in sequence: a capture layer, an agent pipeline, and a presentation layer. All three run from a single startup command.

| Component | Description |
|---|---|
| Capture Layer | Attaches to a live network interface via tshark, or reads from an uploaded pcap file. Streams packets as structured JSON into the pipeline. |
| Agent Pipeline | Three AI agents — Filter, Classifier, and Alert — process each flow in sequence. A fourth agent, the Report Agent, generates PDF summaries on demand or on session end. |
| Storage | SQLite database stores all flows, alerts, sessions, and reports. Single file, no external infrastructure. |
| Backend | FastAPI server exposes REST endpoints and WebSocket connections. Handles all data access, report generation, and email dispatch. |
| Frontend | Next.js application with TypeScript and Tailwind CSS. Five primary views: Live Feed, Alert Feed, Session History, Report Viewer, PCAP Import. |

---

## 3. High Level Design

The system follows a unidirectional data pipeline. Traffic enters from one of two sources, passes through sequential processing stages, is persisted to storage, and is then served to the web interface. No stage writes back to an earlier stage.

The key design principle is separation of concerns. Each stage has a single job. The Classifier Agent does not alert. The Alert Agent does not store. The frontend does not touch the database. This keeps each component testable and replaceable independently.

| Stage | Input | Output | Technology |
|---|---|---|---|
| Ingestion | Network interface / pcap file | Raw packet JSON stream | tshark |
| Filtering | Raw packet stream | Cleaned flow stream | Python + rule config |
| Classification | Cleaned flows | Tagged flows (benign / suspicious / unknown) | Gemini API |
| Alerting | Suspicious/unknown flows | Structured alerts with severity | Gemini API |
| Persistence | Flows + alerts | Stored records | SQLite |
| Reporting | Session records | PDF report file | ReportLab |
| Serving | DB queries | JSON API + WebSocket events | FastAPI |
| Presentation | API + WebSocket | Web UI views | Next.js + TypeScript |

---

## 4. Architecture

### 4.1 Architecture Diagram Description

The architecture flows left to right across six logical zones: Input Sources, Capture Layer, Agent Pipeline, Storage, Backend, and Frontend.

```
Input Sources
      │
      ├── Network Interface
      └── PCAP File Upload
            │
            ▼
      Capture Layer
            │
            ├── tshark (live stream)
            ├── tshark (pcap reader)
            └── Filter Layer  ──── strips noise, broadcasts, whitelisted IPs
                  │
                  ▼
         Agent Pipeline
                  │
                  ├── Classifier Agent ──── tags each flow (benign / suspicious / unknown)
                  │         │
                  │         ▼
                  ├── Alert Agent ──────── evaluates thresholds, generates alerts
                  │
                  └── Report Agent ─────── aggregates session data, generates PDF
                        │
                        ▼
                    Storage (SQLite)
                    flows / alerts / sessions / reports
                        │
                        ▼
                   FastAPI Backend
                        │
                  ┌─────┴──────┐
                  │            │
              REST API    WebSocket
                  │            │
                  └─────┬──────┘
                        │
                  Next.js Frontend
                        │
          ┌─────────────┼─────────────┐
          │             │             │
    Live Feed     Alert Feed    Session History
                              Report Viewer / PCAP Import
```

| Zone | Components | Connections |
|---|---|---|
| Input Sources | Network Interface, PCAP File Upload | Both feed into the Capture Layer |
| Capture Layer | tshark (live), tshark (pcap reader), Filter Layer | tshark output feeds the Filter Layer, which strips noise before passing flows to the Agent Pipeline |
| Agent Pipeline | Classifier Agent, Alert Agent, Report Agent | Classifier tags each flow. Suspicious/unknown flows go to the Alert Agent. Report Agent aggregates session findings on demand. |
| Storage | SQLite — tables: flows, alerts, sessions, reports | All agents write to SQLite. FastAPI reads from it for every API response. |
| Backend | FastAPI REST API, WebSocket Server, SMTP Service, PDF Generator (ReportLab) | REST serves historical data. WebSocket pushes live events. SMTP handles on-request email. ReportLab renders PDF reports. |
| Frontend | Live Feed, Alert Feed, Session History, Report Viewer, PCAP Import UI | Consumes REST for historical data and WebSocket for live events. Report Viewer triggers download and email. |

---

### 4.2 Component Breakdown

| Component | Role | Notes |
|---|---|---|
| tshark | Packet capture and pcap file reading | Wireshark CLI engine. No GUI required. Outputs structured JSON per packet. |
| Filter Layer | Pre-agent noise reduction | Deterministic rule engine. Drops broadcasts, ARP, DHCP, whitelisted IPs, and undersized packets before any Gemini API calls. |
| Classifier Agent | Flow tagging | Calls Gemini API per flow. Returns classification (benign / suspicious / unknown), confidence score (0.0–1.0), and descriptive tags. |
| Alert Agent | Threat evaluation | Receives suspicious/unknown flows. Applies threshold logic then calls Gemini for a structured alert with severity, affected hosts, and reasoning. |
| Report Agent | Narrative generation | Aggregates session data, calls Gemini for a narrative summary, passes output to ReportLab for PDF rendering. |
| SQLite | Persistent storage | Single-file database. Four tables: sessions, flows, alerts, reports. No external database server required. |
| FastAPI | API server | Async Python framework. REST endpoints, WebSocket server, file serving for PDF downloads. Auto-generates /docs. |
| ReportLab | PDF rendering | Constructs structured PDF reports from Report Agent output. |
| smtplib | Email dispatch | Sends email with PDF attachment on manual request. Configured via config.yaml. |
| Next.js + TypeScript | Frontend application | Five views as React components. TypeScript enforces type safety across all API contracts. |
| Tailwind CSS | Styling | Utility-first. Clean minimal light theme throughout. |

---

## 5. Capture Modes

### 5.1 Live Capture

The tool attaches directly to a named network interface at startup. No manual packet capture is required. tshark streams packets as JSON in real time via a subprocess pipe. The pipeline runs continuously until stopped.

- Interface specified via CLI argument (`--interface`) or `config.yaml`
- Configurable tshark capture filter expression — defaults to IP traffic only
- Packets streamed line-by-line and parsed into normalised flow dicts
- Session record created in SQLite on start, closed and summarised on stop
- Live flows and alerts pushed to all connected frontend clients via WebSocket

---

### 5.2 PCAP File Import

Historical pcap files can be uploaded through the web UI. tshark reads the file using the same subprocess approach as live capture, streaming packets through the identical pipeline at full speed. No timestamp replay — analysis runs as fast as possible.

- File uploaded via PCAP Import UI — drag and drop or file picker, accepts `.pcap` and `.pcapng`
- Backend receives the file, writes to temporary storage, passes the path to tshark
- Same filter layer and agent pipeline as live capture — identical output contracts
- Session created in SQLite with `type: imported` and the original filename stored
- Progress indicator shown in the UI during analysis
- Report generated automatically on completion
- Imported sessions visually distinguished from live sessions in the Session History view

---

## 6. Agent Pipeline

All traffic passes through the same four-stage pipeline regardless of capture mode. Each stage has a defined input contract and output contract. Stages do not share state. Every stage can be updated or replaced without affecting the others.

---

### 6.1 Filter Layer

The first stage. Not an AI agent — a deterministic rule engine. Drops packets that are guaranteed noise before spending any Gemini API tokens on them. Rules are configurable via `config.yaml`.

| Rule Type | Default Behaviour |
|---|---|
| Protocol drop | Drops ARP, DHCP, SSDP, mDNS |
| Broadcast drop | Drops any packet with destination 255.255.255.255 |
| IP whitelist | Packets from whitelisted source IPs are passed through as benign without classification |
| Port whitelist | Configurable list of internal service ports to always pass through |
| Minimum size | Drops packets below a configurable byte threshold (default: 40 bytes) |

---

### 6.2 Classifier Agent

Calls the Gemini API with a structured prompt containing flow metadata. Returns a classification decision with supporting detail as structured JSON.

- **Input fields:** `src_ip`, `dst_ip`, `src_port`, `dst_port`, `protocol`, `length`, `ttl`, `tcp_flags`, `http_method`, `dns_query`, `tls_handshake_type`
- **Output:** classification (`benign` / `suspicious` / `unknown`), confidence score (0.0–1.0), tags (JSON array of descriptive strings)
- Prompt tuned to recognise: port scan patterns, beaconing behaviour, unusual protocols on standard ports, unexpected external destinations, abnormal packet sizes
- Output validated as structured JSON before writing to the `flows` table in SQLite

---

### 6.3 Alert Agent

Receives flows tagged suspicious or unknown from the Classifier. Applies threshold logic before calling the Gemini API to generate a structured alert object. Thresholds are configurable in `config.yaml`.

| Severity | Trigger Criteria | UI Behaviour |
|---|---|---|
| Low | Single suspicious flow with confidence below threshold, or first unknown flow from a new source | Listed in Alert Feed with low badge. No banner. |
| Medium | Repeated suspicious flows from the same source IP within a time window, or an unknown protocol on a standard port | Listed in Alert Feed with amber highlight. |
| High | Clear attack signature (port scan pattern, data exfiltration indicators, known malicious patterns), or high-confidence suspicious classification | Persistent top banner in the UI until manually acknowledged by the analyst. |

---

### 6.4 Report Agent

Runs on demand from the Report Viewer in the UI, or automatically when a session ends. Aggregates all session data from SQLite, calls Gemini to produce a narrative summary, and passes the result to ReportLab for PDF rendering.

- Report sections: Session Overview, Traffic Summary, Flagged Flows table, Alert Breakdown by Severity, Top Suspicious Actors, Timeline, Analyst Recommendations
- PDF written to the `reports/generated/` directory; file path stored in the `reports` table
- Available for inline viewing, download, and on-request email from the Report Viewer

---

## 7. Web Interface

Built with Next.js 14+, TypeScript, and Tailwind CSS. Clean minimal light theme. Five views accessible from a persistent top navigation bar. Unacknowledged alert count shown as a badge in the navigation.

---

### 7.1 Live Traffic Feed

- Real-time scrolling table of flows arriving from the WebSocket connection
- Columns: Timestamp, Source IP, Destination IP, Protocol, Port, Classification, Confidence Score
- Row colour coding: white (benign), amber background (unknown), red background (suspicious)
- Auto-scrolls by default — a Pause button freezes the feed for manual inspection
- Filter controls: filter by classification, protocol, source or destination IP
- Updates via WebSocket — no polling, no page refreshes

---

### 7.2 Alert Feed

- Dedicated view for all Alert Agent output — not mixed with the general flow feed
- Each alert card shows: severity badge, timestamp, affected source and destination IP, category label, agent reasoning text
- High severity alerts trigger a persistent banner at the top of every view until acknowledged
- Acknowledge button marks the alert as reviewed; analyst can add free-text notes
- Filter controls: by severity level or date range
- Unacknowledged alert count displayed as a badge in the navigation bar

---

### 7.3 Session History

- Lists all capture sessions in reverse chronological order
- Each row shows: session type badge (Live / Imported), interface name or filename, start and end time, total flow count, alert counts by severity
- Click any session to replay its flow feed and alerts as they were recorded
- Link to the session's report if one has been generated
- Generate Report button available per session to trigger the Report Agent on demand

---

### 7.4 Report Viewer

- Renders PDF reports inline within the browser — no need to download to read
- Download button pulls the PDF file directly from the FastAPI backend
- Email button sends the report as an attachment to configured recipients on manual request
- Reports listed per session, sorted by generation date

---

### 7.5 PCAP Import UI

- Drag-and-drop file picker accepting `.pcap` and `.pcapng` file formats
- Upload button submits the file to the FastAPI `/upload/pcap` endpoint
- Progress bar displayed during tshark analysis
- On completion: redirects automatically to the new session view
- Error state displayed if the file is invalid, corrupt, or unreadable by tshark

---

## 8. Notifications and Delivery

| Channel | Trigger | Content | Notes |
|---|---|---|---|
| Terminal output | Every suspicious or unknown flow | Flow summary line with classification tag | Live capture mode only |
| WebSocket push | Every new flow and every new alert | Structured JSON event object | Pushed to all currently connected browser clients |
| UI persistent banner | High severity alert fired | Alert summary and acknowledge button | Remains visible across all views until the analyst acknowledges it |
| Email | Manual — triggered from Report Viewer | PDF report as email attachment | Uses SMTP config in config.yaml. Sent on request only. |
| PDF download | Manual — download button in Report Viewer | Full PDF report file | Served directly from `reports/generated/` via FastAPI file endpoint |

---

## 9. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Packet Capture | tshark (Wireshark CLI) | Live interface capture and pcap file reading. Outputs structured JSON per packet. |
| Agent Runtime | Python 3.11+ | Pipeline orchestration, agent logic, filter rules. |
| AI / LLM | Gemini API (gemini-2.5-flash) | Flow classification, alert generation, report narrative synthesis. |
| Storage | SQLite | Single-file database for flows, alerts, sessions, and reports. No external DB server. |
| Backend Framework | FastAPI | Async Python web framework. REST API, WebSocket server, file serving. Auto-docs at /docs. |
| Real-time Transport | FastAPI WebSockets (built-in) | Pushes `new_flow` and `new_alert` events to connected frontend clients. |
| PDF Generation | ReportLab | Constructs structured PDF reports from Report Agent output. |
| Email | Python smtplib | SMTP email dispatch with PDF as attachment. On-request only. |
| Frontend Framework | Next.js 14+ | React-based web application with file-system routing. |
| Frontend Language | TypeScript | Type-safe API contracts, interfaces, and component props. |
| Styling | Tailwind CSS | Utility-first CSS. Clean minimal light theme. |

---

## 10. Proposed File Structure

```
wireshark-agent/
├── main.py                         # Entry point — starts pipeline and server
├── config.yaml                     # Interface, thresholds, SMTP, API keys
├── requirements.txt                # Python dependencies
│
├── capture/
│   ├── __init__.py
│   ├── tshark_stream.py            # Live tshark subprocess + JSON parsing
│   ├── pcap_reader.py              # PCAP file mode — same output contract as live
│   └── filter.py                   # Rule-based noise filter
│
├── agents/
│   ├── __init__.py
│   ├── classifier.py               # Classifier Agent — Gemini API calls
│   ├── alert_agent.py              # Alert Agent — threshold logic + Gemini
│   └── report_agent.py             # Report Agent — narrative generation
│
├── storage/
│   ├── __init__.py
│   ├── db.py                       # SQLite connection, queries, schema init
│   └── schema.sql                  # Table definitions (reference copy)
│
├── reports/
│   ├── __init__.py
│   ├── pdf_builder.py              # ReportLab PDF construction
│   └── generated/                  # Output directory for generated PDF files
│
├── notifications/
│   ├── __init__.py
│   └── email_service.py            # SMTP email with PDF attachment
│
├── server/
│   ├── __init__.py
│   ├── app.py                      # FastAPI app factory and startup
│   ├── websocket.py                # WebSocket connection manager
│   └── routes/
│       ├── sessions.py             # GET /sessions, GET /sessions/{id}
│       ├── flows.py                # GET /flows
│       ├── alerts.py               # GET /alerts, PATCH /alerts/{id}
│       ├── reports.py              # GET /reports, POST /reports/generate
│       ├── upload.py               # POST /upload/pcap
│       └── email.py                # POST /email/report/{id}
│
├── data/
│   └── wireshark_agent.db          # SQLite database (auto-created on first run)
│
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.ts
    ├── next.config.ts
    └── src/
        ├── app/
        │   ├── layout.tsx               # Root layout with navigation bar
        │   ├── page.tsx                 # Root redirect to /live
        │   ├── live/page.tsx            # Live Traffic Feed view
        │   ├── alerts/page.tsx          # Alert Feed view
        │   ├── sessions/
        │   │   ├── page.tsx             # Session History list
        │   │   └── [id]/page.tsx        # Individual session detail
        │   ├── reports/
        │   │   ├── page.tsx             # Reports list
        │   │   └── [id]/page.tsx        # Report Viewer (inline + download + email)
        │   └── import/page.tsx          # PCAP Import UI
        ├── components/
        │   ├── nav/Navbar.tsx
        │   ├── live/FlowTable.tsx
        │   ├── live/FlowRow.tsx
        │   ├── alerts/AlertCard.tsx
        │   ├── alerts/AlertBanner.tsx
        │   ├── sessions/SessionTable.tsx
        │   ├── reports/ReportViewer.tsx
        │   ├── reports/ReportCard.tsx
        │   └── import/UploadZone.tsx
        ├── hooks/
        │   ├── useWebSocket.ts          # WebSocket connection and event handling
        │   ├── useFlows.ts              # Flow data fetching and state
        │   └── useAlerts.ts             # Alert data fetching and state
        ├── lib/
        │   ├── api.ts                   # Typed fetch wrappers for all FastAPI endpoints
        │   └── types.ts                 # Shared TypeScript interfaces (Flow, Alert, Session, Report)
        └── styles/
            └── globals.css
```

---

## 11. Data Model

Four SQLite tables. All timestamps stored as ISO 8601 strings. Foreign keys enforced.

---

### Table: sessions

| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment primary key |
| interface | TEXT | Network interface name (live) or pcap filename (imported) |
| type | TEXT | `live` or `imported` |
| started_at | TEXT | ISO 8601 timestamp — session start |
| ended_at | TEXT | ISO 8601 timestamp — null if session still active |
| total_flows | INTEGER | Total flow count — populated when session ends |
| alert_low | INTEGER | Count of low severity alerts for this session |
| alert_medium | INTEGER | Count of medium severity alerts for this session |
| alert_high | INTEGER | Count of high severity alerts for this session |

---

### Table: flows

| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment primary key |
| session_id | INTEGER FK | References sessions.id |
| timestamp | TEXT | ISO 8601 timestamp of the packet |
| src_ip | TEXT | Source IP address |
| dst_ip | TEXT | Destination IP address |
| src_port | INTEGER | Source port number |
| dst_port | INTEGER | Destination port number |
| protocol | TEXT | Protocol label — TCP, UDP, ICMP, etc. |
| length | INTEGER | Packet size in bytes |
| classification | TEXT | `benign`, `suspicious`, or `unknown` |
| confidence | REAL | Classifier Agent confidence score — 0.0 to 1.0 |
| tags | TEXT | JSON array of descriptive tag strings from the Classifier Agent |
| raw_json | TEXT | Full tshark JSON output for the packet — kept for replay and audit |

---

### Table: alerts

| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment primary key |
| flow_id | INTEGER FK | References flows.id — the triggering flow |
| session_id | INTEGER FK | References sessions.id |
| timestamp | TEXT | ISO 8601 timestamp of alert generation |
| severity | TEXT | `low`, `medium`, or `high` |
| category | TEXT | Alert category label — e.g. Port Scan, Beaconing, Unknown Protocol |
| description | TEXT | Human-readable alert description |
| affected_src | TEXT | Source IP address involved in the alert |
| affected_dst | TEXT | Destination IP address involved in the alert |
| reasoning | TEXT | Full reasoning text returned by the Alert Agent |
| acknowledged | INTEGER | 0 (unacknowledged) or 1 (acknowledged by analyst) |
| notes | TEXT | Free-text analyst notes added at acknowledgement time |

---

### Table: reports

| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment primary key |
| session_id | INTEGER FK | References sessions.id |
| generated_at | TEXT | ISO 8601 timestamp of report generation |
| title | TEXT | Report title string |
| pdf_path | TEXT | Absolute path to the PDF file on disk |
| summary | TEXT | Short plain-text summary for display in the Report Viewer list |

---

## 12. Configuration

All runtime configuration lives in `config.yaml` at the project root. No credentials are hardcoded in source files. Sensitive values (SMTP password, API key) are read from environment variables.

```yaml
capture:
  interface: eth0              # Default network interface for live capture
  filter: ip                   # tshark capture filter expression
  drop_broadcasts: true        # Drop 255.255.255.255 destination packets
  whitelist_ips: []            # IPs to always classify as benign without agent calls
  min_packet_size: 40          # Minimum packet size in bytes — smaller packets dropped

agents:
  model: gemini-2.5-flash       # Gemini model used for all three agents
  classifier_confidence_threshold: 0.6
  alert_thresholds:
    suspicious_count: 3        # Fire alert after N suspicious flows from same source
    unknown_count: 5           # Fire alert after N unknown flows from same source
    time_window_seconds: 60    # Window for threshold counting

smtp:
  host: smtp.gmail.com
  port: 587
  username: your@email.com
  password_env: SMTP_PASSWORD  # Read from environment variable
  recipients:
    - analyst@yourdomain.com

storage:
  db_path: data/wireshark_agent.db
  reports_dir: reports/generated
  temp_uploads_dir: data/uploads

server:
  host: 0.0.0.0
  port: 8000

gemini:
  api_key_env: GEMINI_API_KEY  # Read from environment variable
```

---

## 13. Future Expansion

The following features are not in scope for the initial build but are accounted for in the architecture. None require breaking changes to the existing design.

| Feature | Description |
|---|---|
| ELK Integration | The Wireshark tool exports session logs as JSON. A Filebeat or Logstash pipeline picks them up and ships them to Elasticsearch, where the ELK Agent Suite takes over. No code changes required to either tool — a log shipper sits between them. |
| Automatic Email Alerts | Currently email is manual and on-request only. A severity threshold can be added to config.yaml to trigger automatic email on high-severity alerts without UI changes. |
| Multi-interface Capture | Extend `tshark_stream.py` to capture from multiple interfaces simultaneously, merging flows into a single pipeline. Each flow tagged with its source interface. |
| Authentication | Add basic auth or OAuth to the web UI and FastAPI backend for production use. FastAPI supports both natively. |
| Dashboard View | A sixth view: summary dashboard with total flows today, alert trend chart, top talkers, protocol breakdown, and active session status. |
| Alert Correlation | Upgrade the Alert Agent to reason across multiple flows and sessions — identifying campaign-level patterns rather than evaluating individual events in isolation. |
| Custom Rules via UI | Expose the filter whitelist, IP whitelist, and alert thresholds as editable settings in the web UI rather than requiring config file edits. |

---

*Wireshark Agent Suite — System Design Document | Version 1.0 | Defensive Cyber Monitoring Project*
