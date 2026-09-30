# Wireshark Agent Suite — User Stories
## Iteration 1: Foundation

Each story builds on the previous one. By the end of this iteration you have a working capture pipeline storing data locally, with a live web feed and basic alerting in place — nothing polished, but everything end-to-end and testable.

---

### Story 1 — Live packet capture to terminal

**As a** developer setting up the tool,
**I want** tshark to capture live traffic from a network interface and print each flow to the terminal as structured JSON,
**so that** I can confirm the capture pipeline is working before anything else is built.

**Acceptance criteria**
- Running `python main.py --interface <name>` starts a capture session
- Each captured packet is parsed and printed to the terminal as a normalised JSON object containing: `timestamp`, `src_ip`, `dst_ip`, `src_port`, `dst_port`, `protocol`, `length`
- Broadcast and ARP packets are not printed — the filter layer drops them
- If tshark is not installed, the tool exits with a clear error message rather than a stack trace
- Stopping the process with `Ctrl+C` exits cleanly with no errors

**How to test**
1. Run `python main.py --interface eth0` (or your interface name)
2. Generate some traffic — open a browser, run a ping
3. Confirm JSON flow objects appear in the terminal
4. Confirm no ARP or broadcast entries appear
5. Press `Ctrl+C` and confirm clean exit

---

### Story 2 — Persist flows to SQLite

**As a** developer,
**I want** every captured flow to be written to a SQLite database,
**so that** all session data is stored and available for querying without relying on terminal output.

**Acceptance criteria**
- On first run, the database file is created automatically at `data/wireshark_agent.db`
- The `sessions` and `flows` tables exist with the correct schema after first run
- A new session record is created when capture starts, with `started_at` populated
- Every captured flow is inserted into the `flows` table linked to the current session
- When the process is stopped, the session record is updated with `ended_at` and `total_flows`
- The database can be queried directly with `sqlite3` to verify records

**How to test**
1. Run `python main.py --interface eth0` for 30 seconds, then stop
2. Open the database: `sqlite3 data/wireshark_agent.db`
3. Run `SELECT * FROM sessions;` — confirm one row with start and end times
4. Run `SELECT COUNT(*) FROM flows;` — confirm flow count matches what was captured
5. Run a second capture and confirm a second session is created, not overwriting the first

---

### Story 3 — Classify flows with the Gemini agent

**As a** developer,
**I want** each captured flow to be sent to the Gemini API for classification,
**so that** every flow in the database is tagged as benign, suspicious, or unknown before anything else acts on it.

**Acceptance criteria**
- The Classifier Agent sends each flow's metadata to `gemini-2.5-flash` and receives a structured response
- The response is validated as JSON containing: `classification` (benign / suspicious / unknown), `confidence` (0.0–1.0), `tags` (list of strings)
- If the API call fails or returns invalid JSON, the flow is stored with `classification: unknown` and `confidence: 0.0` — the pipeline does not crash
- The `flows` table `classification`, `confidence`, and `tags` columns are populated for every stored flow
- The `GEMINI_API_KEY` environment variable is read at startup — if missing, the tool exits with a clear message

**How to test**
1. Set `export GEMINI_API_KEY=your_key`
2. Run `python main.py --interface eth0` for 60 seconds
3. Query: `SELECT src_ip, dst_ip, protocol, classification, confidence FROM flows LIMIT 20;`
4. Confirm all rows have a non-null classification value
5. Confirm at least some rows show `benign` with confidence above 0.5 for normal traffic
6. Temporarily unset the key and confirm the tool exits with a readable error

---

### Story 4 — Fire alerts on suspicious flows

**As a** developer,
**I want** the Alert Agent to evaluate classified flows and write alerts to the database when thresholds are crossed,
**so that** suspicious activity is recorded as structured alerts separate from the raw flow data.

**Acceptance criteria**
- The Alert Agent only processes flows classified as `suspicious` or `unknown`
- An alert is created in the `alerts` table when a source IP produces 3 or more suspicious/unknown flows within a 60-second window (configurable in `config.yaml`)
- Each alert record contains: `severity` (low / medium / high), `category`, `description`, `affected_src`, `affected_dst`, `reasoning`, `timestamp`
- A single suspicious flow below the threshold is stored but does not generate an alert
- Alerts are also printed to the terminal when fired
- The `alerts` table exists with the correct schema after first run

**How to test**
1. Run a port scan against your own machine from another device: `nmap -p 1-1000 <your-ip>`
2. Run `python main.py --interface eth0` during the scan
3. Query: `SELECT severity, category, description, affected_src FROM alerts;`
4. Confirm at least one alert row exists
5. Query: `SELECT COUNT(*) FROM flows WHERE classification = 'suspicious';`
6. Confirm alert count is lower than suspicious flow count (threshold logic working)

---

### Story 5 — Live traffic feed in the web UI

**As a** developer,
**I want** a web UI that shows captured flows in real time as they arrive,
**so that** I can monitor live traffic visually rather than reading terminal output.

**Acceptance criteria**
- Running `python main.py --interface eth0` starts both the capture pipeline and the FastAPI backend
- Running `npm run dev` in the `frontend/` directory starts the Next.js app
- Opening `http://localhost:3000` shows the Live Traffic Feed view
- New flows appear in the table within 2 seconds of being captured, without a page refresh
- Each row shows: timestamp, source IP, destination IP, protocol, port, classification, confidence
- Rows are colour coded: white (benign), amber background (unknown), red background (suspicious)
- The table auto-scrolls as new rows arrive
- If no capture is running, the page loads without errors and shows an empty state message

**How to test**
1. Start the backend: `python main.py --interface eth0`
2. Start the frontend: `cd frontend && npm run dev`
3. Open `http://localhost:3000`
4. Generate traffic — open a browser tab, run a ping
5. Confirm rows appear in the table in real time without refreshing
6. Confirm row colours match classifications
7. Stop the backend and confirm the UI shows a connection lost or empty state rather than crashing

---

## Definition of done (all stories)

A story is done when:
- The described functionality works end-to-end on a local machine
- It can be verified using the steps in the **How to test** section without any extra setup
- No story breaks the functionality delivered by the previous stories
- The terminal produces no unhandled exceptions during normal operation
