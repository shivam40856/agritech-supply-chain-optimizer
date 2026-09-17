# Mandi-to-Market Supply Chain Optimizer

> Built for the **TransOrg AgentIQ Datathon — Track 3 (AgriTech)**

---

## What is this?

Indian agricultural mandis generate massive amounts of data every day — crop arrivals, wholesale prices, transport logs, weather readings — but most of it sits in messy spreadsheets and disconnected files. This project takes all of that raw, noisy data and turns it into something actually useful.

We built an end-to-end pipeline that cleans up the data, loads it into a structured database, and serves it through an interactive dashboard where you can explore trends, catch anomalies, and make sense of what's happening across the supply chain — from mandi gates to warehouse docks.

There's also a natural language assistant baked into the dashboard, so you can just type a question like *"What was the average wheat price in Amritsar last month?"* and get a chart + summary without writing a single SQL query.

---

## Why we built this

The problem statement was straightforward: the State Agriculture Board needs a single system to keep tabs on everything happening in the agri supply chain. Specifically:

- **Crop arrival monitoring** — How many quintals of which crop arrived at which mandi, on which day? Are there sudden spikes or drops?
- **Price tracking vs MSP** — Are farmers getting fair prices? Where is the modal price falling below the Minimum Support Price?
- **Weather correlation** — Is rainfall or temperature affecting arrivals? Can we spot patterns?
- **Transport & logistics** — How long are shipments taking? Which routes are delayed? Which vehicles are underperforming?
- **Data quality checks** — The raw data is intentionally messy (missing values, inconsistent units, typos in crop names). We needed to quantify how clean our processed output actually is.

---

## Tech Stack

| Layer | Tool / Library | Why |
|-------|---------------|-----|
| Data Cleaning | `pandas`, `numpy`, `openpyxl` | Handles CSV, JSON, and Excel ingestion with robust type coercion |
| Validation | `pydantic` | Schema-level validation for cleaned records |
| Database | `SQLite` + `SQLAlchemy` | Lightweight, zero-config, perfect for a self-contained demo |
| Dashboard | `Streamlit` | Rapid prototyping for interactive data apps |
| Charts | `Plotly` | Interactive, publication-quality visualizations |
| Stats | `scipy`, `scikit-learn` | Anomaly detection (Z-score, IQR) and statistical summaries |
| NL Agent | `Google Gemini API` | Powers the graph-based assistant for natural language queries |

---

## Folder Structure

```
agritech-supply-chain-optimizer/
├── app.py                          # Main Streamlit entry point
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
│
├── data/
│   ├── raw/                        # Original messy datasets (CSV, JSON, Excel)
│   │   ├── track3_mandi_arrivals.csv
│   │   ├── track3_price_and_msp.json
│   │   ├── track3_transport_logistics.csv
│   │   ├── track3_weather_sensors.xlsx
│   │   ├── track3_mandi_master.csv
│   │   └── track3_dataset_notes.txt
│   └── processed/                  # Cleaned outputs + SQLite DB
│       ├── agritech.db
│       ├── mandi_arrivals.csv
│       ├── price_and_msp.csv
│       ├── transport_logistics.csv
│       ├── weather_sensors.csv
│       ├── crop_mapping.csv
│       ├── mandi_master.csv
│       └── transport_exceptions.csv
│
├── src/
│   ├── cleaning/
│   │   ├── pipeline.py             # Full ETL pipeline (ingest → clean → export)
│   │   └── cleaners.py             # Column-level cleaning functions
│   ├── database/
│   │   └── load_data.py            # Loads CSVs into SQLite, runs schema + views
│   ├── visualization/
│   │   ├── pages.py                # All 6 dashboard pages + AI agent page
│   │   ├── charts.py               # Plotly chart builders
│   │   ├── kpis.py                 # KPI card rendering logic
│   │   ├── filters.py              # Sidebar filter widgets
│   │   └── queries.py              # SQL query functions for dashboard data
│   └── agent/
│       └── graph_agent.py          # Graph-first NL assistant (intent → SQL → chart)
│
├── sql/
│   ├── schema.sql                  # Table definitions
│   └── views.sql                   # Analytical views (pre-aggregated queries)
│
├── notebooks/                      # Jupyter notebooks for EDA (if any)
├── reports/                        # Generated reports or exports
├── tests/                          # Unit tests
└── docs/                           # Additional documentation
```

---

## Database Schema

The SQLite database (`agritech.db`) has 5 core tables:

| Table | Description | Primary Key |
|-------|-------------|-------------|
| `mandi_master` | Mandi metadata — name, district, state, type, area | `mandi_id` |
| `crop_master` | Maps raw (messy) crop names to canonical names | `raw_crop_name` |
| `mandi_arrivals` | Daily crop arrival records with cleaned quantities | `arrival_id` |
| `price_msp` | Wholesale prices (min/max/modal) and MSP per crop per day | `record_id` |
| `weather_daily` | Sensor readings — temperature, rainfall, humidity | `sensor_id` + `timestamp` |
| `transport_logistics` | Trip-level data — departure, arrival, transit time, distance | `trip_id` |

On top of these, we created SQL views (`sql/views.sql`) that pre-aggregate common queries so the dashboard doesn't need to do heavy joins on every page load.

---

## Getting Started

### Prerequisites
- Python 3.10 or higher
- pip (comes with Python)
- A Google Gemini API key (only needed for the NL assistant feature)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/your-username/agritech-supply-chain-optimizer.git
cd agritech-supply-chain-optimizer

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Open .env and paste your GEMINI_API_KEY
```

### Running the ETL Pipeline

If you want to re-process the raw data from scratch:

```bash
# Step 1: Clean raw data → generates processed CSVs
python src/cleaning/pipeline.py

# Step 2: Load processed CSVs into SQLite
python src/database/load_data.py
```

> **Note:** The `data/processed/` folder already ships with pre-processed files and `agritech.db`, so you can skip straight to running the dashboard if you just want to explore.

### Launching the Dashboard

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501` by default.

---

## Dashboard Pages

Here's what each page does:

### Executive Overview
Top-level KPIs — total arrivals, active mandis, average prices, weather summary. Quick snapshot of the entire supply chain health.

### Price & MSP Discovery
Compare modal prices against MSP across crops, mandis, and time periods. Highlights where farmers are getting shortchanged (price below MSP).

### Arrivals & Anomalies
Daily/weekly arrival trends with statistical anomaly detection. Uses Z-score and IQR methods to flag unusual spikes or drops in crop volumes.

### Weather Impact
Correlates temperature, rainfall, and humidity readings with crop arrival patterns. Useful for understanding seasonal effects and weather-driven disruptions.

### Logistics Performance
Transport efficiency metrics — average transit time, distance distributions, route-level delays, vehicle performance. Flags trips that exceeded expected durations.

### Data Quality
Shows how messy the raw data was and how much of it we managed to clean. Tracks null rates, format inconsistencies, and records that failed validation.

### AgentIQ Graph Assistant
Type a question in plain English and get back a SQL-generated chart + text summary. The agent detects your intent, writes a safe read-only query, picks the best chart type, and renders it inline.

**Example queries you can try:**
- *"Show me the top 5 mandis by wheat arrivals this quarter"*
- *"Plot daily rice prices in Ludhiana vs MSP"*
- *"Which routes had the most transport delays last month?"*
- *"What's the correlation between rainfall and potato arrivals?"*

---

## How the ETL Pipeline Works

The raw data is intentionally noisy to simulate real-world conditions. Here's what the cleaning pipeline handles:

1. **Crop name standardization** — Maps variations like `"WHEAT"`, `"wheat "`, `"Gehun"`, `"wheet"` to a single canonical name using a fuzzy matching + lookup table approach.
2. **Date parsing** — Handles multiple date formats (DD/MM/YYYY, YYYY-MM-DD, timestamps with mixed timezones) and normalizes everything to `YYYY-MM-DD`.
3. **Unit conversion** — Converts quantities to quintals, distances to kilometers, temperatures to Celsius.
4. **Missing value handling** — Applies sensible imputation where possible; logs exceptions for records that can't be salvaged.
5. **Outlier flagging** — Statistical checks on prices and quantities to catch data entry errors.

Exception records are exported to `transport_exceptions.csv` so nothing gets silently dropped.

---

## Configuration

The `.env` file supports these variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes (for AI agent) | Your Google Gemini API key |
| `DB_HOST` | No | PostgreSQL host (if migrating from SQLite) |
| `DB_PORT` | No | PostgreSQL port |
| `DB_USER` | No | PostgreSQL username |
| `DB_PASS` | No | PostgreSQL password |
| `DB_NAME` | No | PostgreSQL database name |

The PostgreSQL options are there for future use — right now everything runs on SQLite out of the box.

---

## Known Limitations

- The weather sensor data doesn't have direct mandi-level mapping, so weather correlations are approximate (district-level).
- The NL assistant works best with simple analytical questions. Complex multi-table joins or subjective questions might not produce great results.
- SQLite doesn't support concurrent writes, so this isn't suitable for multi-user production deployment without migrating to PostgreSQL.
- The raw dataset is synthetic — patterns and anomalies are simulated, not from real mandi records.

---

## What's Next

A few things we'd like to add if we had more time:

- **Forecasting module** — Time series models (ARIMA/Prophet) for predicting arrivals and price movements
- **Real-time ingestion** — Kafka-based pipeline for streaming IoT sensor data
- **Alert system** — Push notifications when prices crash below MSP or arrivals drop unexpectedly
- **Cloud deployment** — Containerized deployment on GCP/AWS with a proper data warehouse backend
- **Mobile-friendly UI** — Responsive layout tweaks for field officers accessing the dashboard on phones

---

## Contributing

Pull requests are welcome. For anything major, please open an issue first so we can discuss the approach.

1. Fork the repo
2. Create your branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m "Add some feature"`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

This project was built as part of the TransOrg AgentIQ Datathon. Feel free to use it for learning and reference purposes.
