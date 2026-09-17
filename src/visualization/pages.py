import streamlit as st
import pandas as pd
import sqlite3

from src.visualization import kpis, charts, queries
from src.visualization.filters import previous_period_filters

DB_PATH = "data/processed/agritech.db"

TOTAL_ARRIVALS_ROWS = 19996
TOTAL_PRICE_ROWS = 11390
TOTAL_TRANSPORT_ROWS = 9419


def _empty_state(label="No data found for this filter combination."):
    st.markdown(
        f"<div class='empty-state'>🌾 {label}</div>",
        unsafe_allow_html=True,
    )


def _kpi_card(label, value, delta=None, delta_label="", help_text=""):
    delta_html = ""
    if delta is not None:
        if delta >= 0:
            delta_html = f"<div class='kpi-delta-pos'>▲ {delta:+.1f}% {delta_label}</div>"
        else:
            delta_html = f"<div class='kpi-delta-neg'>▼ {delta:.1f}% {delta_label}</div>"
    help_icon = f' <span title="{help_text}" style="cursor:help;color:#6B7280;">ⓘ</span>' if help_text else ""
    html = (
        f"<div class='kpi-card'>"
        f"<div class='kpi-label'>{label}{help_icon}</div>"
        f"<div class='kpi-value'>{value}</div>"
        f"{delta_html}"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _cached_distress(filters_tuple):
    filters = dict(filters_tuple)
    return queries.fetch_distress_base_data(filters)


@st.cache_data(show_spinner=False)
def _cached_view(view_name, filters_tuple):
    filters = dict(filters_tuple)
    return queries.fetch_data(view_name, filters)


def _filters_tuple(filters: dict):
    """Make filters hashable for cache keying."""
    def _val(v):
        if isinstance(v, list):
            return tuple(v)
        return v
    return tuple(sorted({k: _val(v) for k, v in filters.items()}.items()))


def _pct_delta(curr, prev):
    if prev == 0:
        return None
    return ((curr - prev) / abs(prev)) * 100


# ─────────────────────────────────────────────────────────────────
# PAGE 1 — Executive Overview
# ─────────────────────────────────────────────────────────────────
def page_executive_overview(filters: dict, compare: bool):
    st.subheader("Is the mandi system healthy this period?")

    df_arr = _cached_view("vw_daily_arrivals", _filters_tuple(filters))
    df_mandi_summary = _cached_view("vw_mandi_summary", _filters_tuple(filters))
    df_dist = _cached_distress(_filters_tuple(filters))
    df_trans = _cached_view("vw_transport_performance", _filters_tuple(filters))

    # Row count caption
    st.caption(f"Showing {len(df_arr):,} of {TOTAL_ARRIVALS_ROWS:,} arrival records")

    if df_arr.empty:
        _empty_state()
        return

    # Compute KPIs
    total_arr = kpis.compute_total_arrivals(df_arr)
    avg_price = kpis.compute_avg_modal_price(df_dist)
    avg_msp = kpis.compute_avg_msp(df_dist)
    msp_gap = kpis.compute_msp_gap_pct(df_dist)
    dsi = kpis.compute_distress_sale_index(df_dist)
    avg_transit, n_trips = kpis.compute_delay_rate(df_trans)  # returns rate, total
    delay_rate, n_trips = kpis.compute_delay_rate(df_trans)
    avg_transit = kpis.compute_avg_transit_time(df_trans)
    crashes = kpis.compute_price_crash_instances(df_dist)
    active_m = kpis.compute_active_mandis(df_arr)
    farmers = kpis.compute_farmers_served(
        _cached_view("vw_daily_arrivals", _filters_tuple(filters))
    )

    # Previous period deltas
    prev_total = prev_dsi = prev_transit = prev_gap = None
    if compare:
        pf = previous_period_filters(filters)
        pf_tuple = _filters_tuple(pf)
        prev_arr = _cached_view("vw_daily_arrivals", pf_tuple)
        prev_dist = _cached_distress(pf_tuple)
        prev_tran = _cached_view("vw_transport_performance", pf_tuple)
        prev_total = _pct_delta(total_arr, kpis.compute_total_arrivals(prev_arr))
        prev_dsi = kpis.compute_distress_sale_index(prev_dist)
        prev_gap = _pct_delta(msp_gap, kpis.compute_msp_gap_pct(prev_dist))
        prev_transit = _pct_delta(avg_transit, kpis.compute_avg_transit_time(prev_tran))

    # Insight sentence
    status = "⚠️ AT RISK" if dsi > 30 else "✅ HEALTHY"
    st.info(
        f"**System Status: {status}** — "
        f"{total_arr:,.0f} Qtl arrived across {active_m} mandis. "
        f"Distress Sale Index is **{dsi:.1f}%** (quantity-weighted share sold below MSP). "
        f"Average MSP gap: **{msp_gap:+.1f}%**. "
        f"Transit delay rate: **{delay_rate:.1f}%** of {n_trips:,} trips."
    )

    # 6 KPI cards
    c1, c2, c3 = st.columns(3)
    with c1:
        _kpi_card("Total Arrivals (Qtl)", f"{total_arr:,.0f}",
                  delta=prev_total,
                  help_text="SUM(quantity_quintals) over filtered rows.")
    with c2:
        _kpi_card("Avg Modal Price", f"₹{avg_price:,.0f}",
                  help_text="AVG(modal_price_clean) across selected mandi-crop-dates.")
        st.caption(f"Avg MSP: ₹{avg_msp:,.0f}")
    with c3:
        _kpi_card("MSP Gap %", f"{msp_gap:+.1f}%",
                  delta=prev_gap,
                  help_text="AVG((modal_price - msp) / msp × 100). Negative = below support price.")

    c4, c5, c6 = st.columns(3)
    with c4:
        dsi_delta = _pct_delta(dsi, prev_dsi) if compare and prev_dsi is not None else None
        _kpi_card("Distress Sale Index", f"{dsi:.1f}%",
                  delta=dsi_delta,
                  help_text="Quantity-weighted % of arrivals sold below MSP. Formula: SUM(qty WHERE modal<msp)/SUM(qty).")
    with c5:
        _kpi_card("Avg Transit Time", f"{avg_transit:.1f} hrs",
                  delta=prev_transit,
                  help_text="AVG(transit_hours) excluding quarantined exception trips (transit_hours < 0).")
    with c6:
        _kpi_card("Transit Delay Rate", f"{delay_rate:.1f}%",
                  help_text=f"Trips where transit_hours > distance_km/40 + 2. Base: {n_trips:,} trips.")

    # Supplementary metrics row
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Active Mandis", active_m)
    m2.metric("Farmers Served", f"{farmers:,.0f}")
    m3.metric("Price Crash Instances", f"{crashes:,}",
              help="Count of mandi-crop-days where modal price < MSP.")

    # Charts
    st.markdown("---")
    st.plotly_chart(charts.chart_daily_arrivals_trend(df_arr), width="stretch")
    st.caption("A stable trend with seasonal peaks is expected. Sharp spikes may indicate glut conditions.")

    st.plotly_chart(charts.chart_top_mandis(df_mandi_summary), width="stretch")
    st.caption("The top 10 mandis account for the bulk of the total volume — check if smaller mandis are being overlooked.")


# ─────────────────────────────────────────────────────────────────
# PAGE 2 — Price & MSP
# ─────────────────────────────────────────────────────────────────
def page_price_msp(filters: dict, compare: bool):
    st.subheader("Where are farmers selling below the support price?")

    df = _cached_distress(_filters_tuple(filters))
    st.caption(f"Showing {len(df):,} of {TOTAL_PRICE_ROWS:,} price records (with valid modal price and MSP)")

    if df.empty:
        _empty_state()
        return

    dsi = kpis.compute_distress_sale_index(df)
    crashes = kpis.compute_price_crash_instances(df)
    gap = kpis.compute_msp_gap_pct(df)

    worst_crop = df[df["modal_price_clean"] < df["msp_clean"]].groupby("crop")["quantity_quintals"].sum().idxmax() \
        if not df[df["modal_price_clean"] < df["msp_clean"]].empty else "N/A"

    st.warning(
        f"**{dsi:.1f}% of arrivals (by weight) were sold below MSP** across {crashes:,} mandi-crop-day instances. "
        f"Average MSP gap: {gap:+.1f}%. Worst crop: **{worst_crop}**. "
        f"Join rule: prices joined by Date + Mandi ID; fallback to District average where mandi_id is missing in price data."
    )

    # Price vs MSP timeline
    # Rename columns for the chart
    chart_df = df.rename(columns={"modal_price_clean": "modal_price", "msp_clean": "msp"})
    st.plotly_chart(charts.chart_price_vs_msp_timeline(chart_df), width="stretch")
    st.caption("Red shaded region = days/crops where the average modal price fell below MSP.")

    # MSP gap by district
    df["msp_gap"] = df["modal_price_clean"] - df["msp_clean"]
    df["district"] = df["district"].fillna("Unmapped")
    st.plotly_chart(charts.chart_msp_gap_by_district(df), width="stretch")
    st.caption("Districts with negative bars are experiencing systematic price crashes below the minimum support price.")

    # Worst mandi-crop pairs table
    st.subheader("Worst Mandi-Crop Pairs (by Distress Quantity)")
    worst = df[df["modal_price_clean"] < df["msp_clean"]].groupby(
        ["mandi_name", "crop"]
    ).agg(
        distress_qty=("quantity_quintals", "sum"),
        avg_gap=("msp_gap", "mean"),
        instances=("date", "count")
    ).reset_index().sort_values("distress_qty", ascending=False).head(20)
    worst["avg_gap"] = worst["avg_gap"].map("₹{:.0f}".format)
    st.dataframe(worst, width="stretch")

    # Download button
    csv = worst.to_csv(index=False)
    st.download_button("⬇️ Download Worst Pairs CSV", csv, "worst_pairs.csv", "text/csv")


# ─────────────────────────────────────────────────────────────────
# PAGE 3 — Arrivals & Anomalies
# ─────────────────────────────────────────────────────────────────
def page_arrivals_anomalies(filters: dict, compare: bool):
    st.subheader("Where is supply spiking or collapsing?")

    df = _cached_view("vw_daily_arrivals", _filters_tuple(filters))
    st.caption(f"Showing {len(df):,} of {TOTAL_ARRIVALS_ROWS:,} arrival records")

    if df.empty:
        _empty_state()
        return

    # Get price data for glut detection
    df_price = _cached_distress(_filters_tuple(filters))
    df_with_glut = kpis.compute_glut_flags(df, df_price.rename(columns={"modal_price_clean": "modal_price", "msp_clean": "msp"}) if not df_price.empty else None)

    glut_days = int(df_with_glut["is_glut"].sum()) if "is_glut" in df_with_glut.columns else 0
    anomaly_days = int((df_with_glut.groupby("date")["total_arrival_quintals"].sum() >
                        df_with_glut.groupby("date")["total_arrival_quintals"].sum().rolling(7, min_periods=1).mean() * 2).sum())

    top_crop = df.groupby("crop")["total_arrival_quintals"].sum().idxmax() if not df.empty else "N/A"
    st.info(
        f"Top crop by volume: **{top_crop}**. "
        f"**{glut_days}** mandi-crop-day glut signals detected (arrivals >1.5× 30-day mean AND price below MSP). "
        f"Anomalous days (>2σ above 7-day rolling mean): estimated ~{anomaly_days}."
    )

    # Crop-wise stacked area
    st.plotly_chart(charts.chart_crop_stacked_area(df), width="stretch")
    st.caption("The composition of crop arrivals over time. Sudden area expansion indicates a seasonal or weather-driven supply surge.")

    # Anomaly band
    st.plotly_chart(charts.chart_anomaly_band(df), width="stretch")
    st.caption("Days marked with ✕ exceed the 7-day rolling mean by more than 2 standard deviations — potential glut or reporting artefact.")

    # Glut flag table
    if glut_days > 0:
        st.subheader("🚨 Glut Alert Feed")
        glut_rows = df_with_glut[df_with_glut["is_glut"] == True][
            ["date", "mandi_name", "crop", "total_arrival_quintals"]
        ].sort_values("total_arrival_quintals", ascending=False).head(50)
        st.dataframe(glut_rows, width="stretch")
        st.caption("Glut = arrivals > 1.5× 30-day rolling mean AND modal price below MSP on same date.")
        csv = glut_rows.to_csv(index=False)
        st.download_button("⬇️ Download Glut Alerts CSV", csv, "glut_alerts.csv", "text/csv")


# ─────────────────────────────────────────────────────────────────
# PAGE 4 — Weather Impact
# ─────────────────────────────────────────────────────────────────
def page_weather_impact(filters: dict, compare: bool):
    st.subheader("Does rainfall move arrivals, and with what lag?")

    # Weather data — date-level aggregate (state-level, no district mapping available)
    conn = sqlite3.connect(DB_PATH)
    weather_q = """
        SELECT date_clean AS date,
               AVG(rain_mm) AS avg_rain_mm,
               AVG(temp_celsius) AS avg_temp_celsius,
               AVG(humidity_percent) AS avg_humidity
        FROM weather_daily
        WHERE date_clean BETWEEN ? AND ?
        GROUP BY date_clean
        ORDER BY date_clean
    """
    wf = pd.read_sql(weather_q, conn,
                     params=[filters.get("start_date", "2026-01-01"),
                              filters.get("end_date", "2026-12-08")])

    arr_q = """
        SELECT date_clean AS date, SUM(quantity_quintals) AS total_arrival_quintals
        FROM mandi_arrivals
        WHERE date_clean BETWEEN ? AND ?
        GROUP BY date_clean ORDER BY date_clean
    """
    af = pd.read_sql(arr_q, conn,
                     params=[filters.get("start_date", "2026-01-01"),
                              filters.get("end_date", "2026-12-08")])
    conn.close()

    st.caption(
        "⚠️ **Weather note**: No district-level sensor mapping exists in this dataset. "
        "Weather metrics shown are a **national daily aggregate** across all sensors. "
        "Correlation results should be interpreted as directional only — not causal."
    )

    if wf.empty or af.empty:
        _empty_state("No weather or arrival data for this date range.")
        return

    # Merge on date
    merged = pd.merge(wf, af, on="date", how="inner")

    # Lag correlation
    lag_df = kpis.compute_lag_correlations(merged)
    best_lag = int(lag_df.loc[lag_df["correlation"].abs().idxmax(), "lag"])
    best_corr = lag_df.loc[lag_df["lag"] == best_lag, "correlation"].values[0]

    st.info(
        f"Best lag between rainfall and arrivals: **{best_lag} days** "
        f"(Pearson r = {best_corr:.3f}). "
        f"Positive correlation means higher rainfall precedes higher arrivals; negative means the opposite. "
        f"Correlation does not establish causation."
    )

    st.plotly_chart(charts.chart_lag_correlation(lag_df, best_lag), width="stretch")
    st.caption(f"The lag-{best_lag} correlation (highlighted) is the strongest predictor. This may reflect harvest-to-market delay cycles.")

    st.plotly_chart(charts.chart_rainfall_arrivals_dual(merged.rename(columns={"total_arrival_quintals": "total_arrival_quintals"})), width="stretch")
    st.caption("Rainfall bars (right axis) and total arrivals line (left axis). Look for arrivals surges 1–2 weeks after heavy rain.")


# ─────────────────────────────────────────────────────────────────
# PAGE 5 — Logistics
# ─────────────────────────────────────────────────────────────────
def page_logistics(filters: dict, compare: bool):
    st.subheader("Which routes are bleeding time?")

    df = _cached_view("vw_transport_performance", _filters_tuple(filters))
    st.caption(f"Showing {len(df):,} of {TOTAL_TRANSPORT_ROWS:,} transport records (excluding quarantined exceptions)")

    # Show quarantined count
    import os
    exc_path = "data/processed/transport_exceptions.csv"
    exc_count = len(pd.read_csv(exc_path)) if os.path.exists(exc_path) else 0
    st.info(f"**{exc_count} trips quarantined** (negative/impossible transit times) — excluded from all KPIs above.")

    if df.empty:
        _empty_state()
        return

    delay_rate, n_trips = kpis.compute_delay_rate(df)
    avg_transit = kpis.compute_avg_transit_time(df)
    worst_wh = df.groupby("destination_warehouse").apply(
        lambda g: (g["is_delayed"].sum() / len(g) * 100) if len(g) > 0 else 0
    ).idxmax()

    st.warning(
        f"**{delay_rate:.1f}% of {n_trips:,} trips are delayed** (transit > distance/40 + 2 hrs buffer). "
        f"Avg transit time: **{avg_transit:.1f} hrs**. "
        f"Worst warehouse: **{worst_wh}**."
    )

    # Transit by warehouse chart
    st.plotly_chart(charts.chart_transit_by_warehouse(df), width="stretch")
    st.caption("Warehouses with high delay rates and long transit times are bottlenecks — investigate route or vehicle allocation.")

    st.plotly_chart(charts.chart_transit_distribution(df), width="stretch")
    st.caption("Most trips cluster in the 5-15 hour range. The right tail indicates routes with significant delays.")

    # Route performance table
    st.subheader("Route Performance Table")
    route_tbl = df.groupby(["mandi_name", "destination_warehouse"]).agg(
        trips=("trip_id", "count"),
        avg_distance=("distance_km", "mean"),
        avg_transit=("transit_hours", "mean"),
        delayed=("is_delayed", "sum")
    ).reset_index()
    route_tbl["delay_rate_pct"] = (route_tbl["delayed"] / route_tbl["trips"] * 100).round(1)
    route_tbl["avg_distance"] = route_tbl["avg_distance"].round(1)
    route_tbl["avg_transit"] = route_tbl["avg_transit"].round(1)
    route_tbl = route_tbl.sort_values("delay_rate_pct", ascending=False)
    st.dataframe(route_tbl.drop(columns=["delayed"]), width="stretch")
    csv = route_tbl.to_csv(index=False)
    st.download_button("⬇️ Download Route Table CSV", csv, "routes.csv", "text/csv")


# ─────────────────────────────────────────────────────────────────
# PAGE 6 — Data Quality
# ─────────────────────────────────────────────────────────────────
def page_data_quality(filters: dict, compare: bool):
    st.subheader("Can we trust this data?")

    import os
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    rows = {
        "mandi_arrivals": pd.read_sql("SELECT COUNT(*) as c FROM mandi_arrivals", conn).iloc[0]["c"],
        "price_msp": pd.read_sql("SELECT COUNT(*) as c FROM price_msp", conn).iloc[0]["c"],
        "weather_daily": pd.read_sql("SELECT COUNT(*) as c FROM weather_daily", conn).iloc[0]["c"],
        "transport_logistics": pd.read_sql("SELECT COUNT(*) as c FROM transport_logistics", conn).iloc[0]["c"],
    }
    conn.close()

    exc_path = "data/processed/transport_exceptions.csv"
    exc_count = len(pd.read_csv(exc_path)) if os.path.exists(exc_path) else 0

    dq_path = "reports/data_quality_report.csv"
    if os.path.exists(dq_path):
        dq = pd.read_csv(dq_path)
        st.subheader("Raw vs Cleaned Row Counts")
        st.dataframe(dq, width="stretch")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Arrivals Loaded", f"{rows['mandi_arrivals']:,}", help="After dedup and missing-key drop")
    c2.metric("Price Records Loaded", f"{rows['price_msp']:,}", help="After price string cleaning")
    c3.metric("Weather Logs Loaded", f"{rows['weather_daily']:,}", help="After UTC→IST conversion")
    c4.metric("Transport Quarantined", f"{exc_count:,}", delta=f"-{exc_count}", help="Trips with impossible transit times")

    st.markdown("---")
    st.subheader("Cleaning Methodology")
    st.markdown("""
    | Step | Rule |
    |---|---|
    | **Mandi IDs** | Regex normalized to `MANDIXXX`. Unmatchable IDs logged and dropped. |
    | **Crop Names** | Canonical map: Hindi (गेहूं), English (Wheat, WHEAT), phonetic (Gehun, Kanak) → `Wheat`. |
    | **Quantities** | All units converted to Quintals: 1 Tonne = 10 Qtl, 1 Qtl = 100 KG. Missing unit → NULL (excluded). |
    | **Prices** | Stripped ₹, Rs., INR, commas, /- suffixes → float. Empty strings → NULL. |
    | **Dates** | `pd.to_datetime(format='mixed', dayfirst=True)`. Invalid dates → NaT → dropped. |
    | **Temperature** | °F → °C formula: (F−32) × 5/9. |
    | **Rainfall** | inches → mm: × 25.4. |
    | **Timezone** | UTC timestamps shifted +5:30 → IST. |
    | **Transport** | Negative transit hours flagged → quarantined to `transport_exceptions.csv`. |
    | **Vehicle Numbers** | Stripped to alphanumeric: `UP-50-BC-6882` → `UP50BC6882`. |
    | **Missing Values** | Per-column strategy: NULL kept for prices without MSP, 'Unmapped' for geography. |
    | **Weather→Geography** | No sensor-district key in dataset. Weather is a **national daily aggregate only**. |
    """)


# ─────────────────────────────────────────────────────────────────
# PAGE 7 — AI Agent
# ─────────────────────────────────────────────────────────────────
def page_ai_agent(filters: dict, compare: bool):
    st.subheader("Ask AgentIQ — Natural Language Queries")
    st.markdown("The agent extracts intent, entities, and date ranges, generates read-only SQL, selects the best chart, and returns a data-driven summary.")

    from src.agent.graph_agent import run_agent_query

    presets = [
        "Plot the daily arrival trend of Wheat in Amritsar mandi vs MSP for the last 30 days.",
        "Show total arrivals by crop type.",
        "Which mandi has the highest average transit delay?",
        "Compare total rainfall by district over the last 3 months.",
        "Show the distribution of wholesale prices for Rice.",
        "Which warehouse receives the highest volume of crops?",
    ]
    selected_preset = st.selectbox("Try an example query:", ["(type your own)"] + presets)
    default_q = selected_preset if selected_preset != "(type your own)" else ""

    query = st.text_area("Your question:", value=default_q, height=80)

    if st.button("🔍 Ask Agent", type="primary"):
        if not query.strip():
            st.warning("Please enter a question.")
            return
        with st.spinner("Agent is thinking..."):
            result = run_agent_query(query)

        st.markdown("---")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"**Intent:** {result.get('intent', 'N/A')}")
            entities = result.get('entities', {})
            if entities:
                st.markdown("**Extracted Entities:**")
                for k, v in entities.items():
                    st.markdown(f"- `{k}`: {v}")
            sql = result.get('sql', '')
            if sql:
                st.markdown("**Generated SQL:**")
                st.code(sql, language="sql")

        with col2:
            if "chart" in result:
                st.plotly_chart(result["chart"], width="stretch")
            summary = result.get("summary", "")
            if summary:
                st.info(summary)
            if not result.get("chart") and not summary:
                _empty_state(result.get("summary", "No results returned for this query."))
