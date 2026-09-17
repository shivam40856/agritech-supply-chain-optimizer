import streamlit as st
import pandas as pd
from datetime import date, timedelta
from src.visualization.queries import get_max_date, fetch_filter_options


def _parse_date(d) -> date:
    if isinstance(d, date):
        return d
    return pd.to_datetime(d).date()


def init_filters():
    """Initialize session state with defaults computed from data max date."""
    if "filters_initialized" not in st.session_state:
        max_date_str = get_max_date()
        max_date = _parse_date(max_date_str)
        min_date = date(2026, 1, 1)

        st.session_state["filter_start"] = min_date
        st.session_state["filter_end"] = max_date
        st.session_state["filter_states"] = []
        st.session_state["filter_districts"] = []
        st.session_state["filter_mandis"] = []
        st.session_state["filter_crops"] = []
        st.session_state["compare_previous"] = False
        st.session_state["_max_date"] = max_date
        st.session_state["_min_date"] = min_date
        st.session_state["filters_initialized"] = True


def build_sidebar(show_title: bool = True) -> dict:
    """Render global filter sidebar and return the current filter dict."""
    init_filters()

    opts = fetch_filter_options()
    master_df = opts["master"]
    all_crops = opts["crops"]

    max_date: date = st.session_state["_max_date"]
    min_date: date = st.session_state["_min_date"]

    with st.sidebar:
        if show_title:
            st.markdown("### 🎛️ Data Filters")
        else:
            st.markdown("---")
            st.markdown("### 🎛️ Data Filters")

        # --- Date Range ---
        st.subheader("📅 Date Range")
        preset = st.radio("Quick preset", ["Custom", "Last 30 days", "Last 90 days", "Full year"],
                          horizontal=True, key="date_preset")
        if preset == "Last 30 days":
            st.session_state["filter_start"] = max_date - timedelta(days=30)
            st.session_state["filter_end"] = max_date
        elif preset == "Last 90 days":
            st.session_state["filter_start"] = max_date - timedelta(days=90)
            st.session_state["filter_end"] = max_date
        elif preset == "Full year":
            st.session_state["filter_start"] = min_date
            st.session_state["filter_end"] = max_date

        col1, col2 = st.columns(2)
        start = col1.date_input("From", value=st.session_state["filter_start"],
                                min_value=min_date, max_value=max_date, key="date_start_input")
        end = col2.date_input("To", value=st.session_state["filter_end"],
                              min_value=min_date, max_value=max_date, key="date_end_input")
        if start <= end:
            st.session_state["filter_start"] = start
            st.session_state["filter_end"] = end
        else:
            st.warning("End date must be after start date.")

        st.markdown("---")

        # --- Cascading State → District → Mandi ---
        st.subheader("🗺️ Geography")

        all_states = sorted(master_df["state"].fillna("Unmapped").unique().tolist())
        sel_states = st.multiselect(
            "State", all_states,
            default=st.session_state["filter_states"],
            key="ms_states",
            placeholder=f"Select from {len(all_states)} states..."
        )
        st.session_state["filter_states"] = sel_states
        if not sel_states:
            st.caption(f"Available: {', '.join(all_states)}")

        # Filter districts by selected states
        if sel_states:
            real_states = [s for s in sel_states if s != "Unmapped"]
            if "Unmapped" in sel_states:
                dist_df = master_df[master_df["state"].isin(real_states) | master_df["state"].isna()]
            else:
                dist_df = master_df[master_df["state"].isin(real_states)]
        else:
            dist_df = master_df

        all_districts = sorted(dist_df["district"].fillna("Unmapped").unique().tolist())
        sel_districts = st.multiselect(
            "District", all_districts,
            default=[d for d in st.session_state["filter_districts"] if d in all_districts],
            key="ms_districts",
            placeholder=f"Select from {len(all_districts)} districts..."
        )
        st.session_state["filter_districts"] = sel_districts

        # Filter mandis by selected districts
        if sel_districts:
            real_dists = [d for d in sel_districts if d != "Unmapped"]
            if "Unmapped" in sel_districts:
                mandi_df = dist_df[dist_df["district"].isin(real_dists) | dist_df["district"].isna()]
            else:
                mandi_df = dist_df[dist_df["district"].isin(real_dists)]
        else:
            mandi_df = dist_df

        all_mandis = sorted(mandi_df["mandi_name"].dropna().unique().tolist())
        sel_mandis = st.multiselect(
            "Mandi", all_mandis,
            default=[m for m in st.session_state["filter_mandis"] if m in all_mandis],
            key="ms_mandis",
            placeholder=f"Select from {len(all_mandis)} mandis..."
        )
        st.session_state["filter_mandis"] = sel_mandis

        st.markdown("---")

        # --- Crops ---
        st.subheader("🌱 Crop")
        sel_crops = st.multiselect(
            "Crop", all_crops,
            default=st.session_state["filter_crops"],
            key="ms_crops",
            placeholder=f"Select from {len(all_crops)} crops..."
        )
        st.session_state["filter_crops"] = sel_crops
        if not sel_crops:
            st.caption(f"Available: {', '.join(all_crops)}")

        st.markdown("---")

        # --- Compare previous period ---
        compare = st.toggle("Compare to previous period", value=st.session_state["compare_previous"])
        st.session_state["compare_previous"] = compare

        # --- Active filter summary ---
        active_count = sum([
            bool(sel_states), bool(sel_districts),
            bool(sel_mandis), bool(sel_crops)
        ])
        if active_count > 0:
            summary_parts = []
            if sel_states:
                summary_parts.append(f"**States:** {', '.join(sel_states)}")
            if sel_districts:
                summary_parts.append(f"**Districts:** {', '.join(sel_districts)}")
            if sel_mandis:
                summary_parts.append(f"**Mandis:** {', '.join(sel_mandis)}")
            if sel_crops:
                summary_parts.append(f"**Crops:** {', '.join(sel_crops)}")
            st.success(f"🎯 **{active_count} filter(s) active**")
            for part in summary_parts:
                st.markdown(f"  {part}", unsafe_allow_html=True)
        else:
            st.caption("ℹ️ No filters applied — showing all data.")

        st.markdown("---")

        # --- Reset button ---
        if st.button("🔄 Reset all filters", use_container_width=True):
            st.session_state["filter_start"] = min_date
            st.session_state["filter_end"] = max_date
            st.session_state["filter_states"] = []
            st.session_state["filter_districts"] = []
            st.session_state["filter_mandis"] = []
            st.session_state["filter_crops"] = []
            st.session_state["compare_previous"] = False
            st.rerun()

    # Return current filter dict
    filters = {
        "start_date": str(st.session_state["filter_start"]),
        "end_date": str(st.session_state["filter_end"]),
        "state": st.session_state["filter_states"] or None,
        "district": st.session_state["filter_districts"] or None,
        "mandi": st.session_state["filter_mandis"] or None,
        "crop": st.session_state["filter_crops"] or None,
    }
    # Remove None values for cleaner downstream logic
    return {k: v for k, v in filters.items() if v is not None and v != []}


def previous_period_filters(filters: dict) -> dict:
    """Return filter dict shifted to the previous equal-length period."""
    start = _parse_date(filters["start_date"])
    end = _parse_date(filters["end_date"])
    delta = end - start
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - delta
    prev = filters.copy()
    prev["start_date"] = str(prev_start)
    prev["end_date"] = str(prev_end)
    return prev
