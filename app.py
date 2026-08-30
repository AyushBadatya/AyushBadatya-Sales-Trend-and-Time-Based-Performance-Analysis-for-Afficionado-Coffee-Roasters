"""
Afficionado Coffee Roasters — Sales Intelligence Dashboard
A Streamlit web app for exploring 2025 transaction data across three
NYC store locations (Lower Manhattan, Hell's Kitchen, Astoria).
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Afficionado Coffee Roasters | Sales Dashboard",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DATA_PATH = "Afficionado_Coffee_Roasters.csv"

CUSTOM_CSS = """
<style>
.block-container {padding-top: 1.5rem;}
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e6e6e6;
    border-radius: 12px;
    padding: 14px 16px 6px 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
[data-testid="stMetricLabel"] {font-weight: 600; color: #6b4f3b;}
h1, h2, h3 {color: #3b2418;}
.stTabs [data-baseweb="tab"] {font-size: 15px; font-weight: 600;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Data loading & feature engineering (cached)
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading and preparing transaction data...")
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # --- Clean text columns ---
    text_cols = ["store_location", "product_category", "product_type", "product_detail"]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip().str.title()

    # --- Correct dtypes ---
    df["transaction_id"] = df["transaction_id"].astype(int)
    df["store_id"] = df["store_id"].astype(int)
    df["product_id"] = df["product_id"].astype(int)
    df["transaction_qty"] = df["transaction_qty"].astype(int)
    df["unit_price"] = df["unit_price"].astype(float)
    df["year"] = df["year"].astype(int)

    # --- Time parsing ---
    df["transaction_time"] = pd.to_timedelta(df["transaction_time"])
    df["transaction_hour"] = df["transaction_time"].dt.components["hours"].astype(int)

    # --- Revenue ---
    df["revenue"] = df["transaction_qty"] * df["unit_price"]

    # --- Reconstruct calendar dates ---
    # The source file only retains a bare "year" field (no month/day), but each
    # store's rows are recorded in chronological order and the clock time
    # resets (goes down) every time a new business day begins. We use those
    # resets to rebuild a sequential day index per store, then map that index
    # onto a real calendar starting at Jan 1 of the given year. This recovers
    # true day-of-week / seasonal patterns instead of collapsing every row
    # onto a single date.
    df["day_index"] = 0
    for _, group in df.groupby("store_id", sort=False):
        idx = group.index
        diffs = group["transaction_time"].diff()
        resets = diffs.dt.total_seconds() < 0
        df.loc[idx, "day_index"] = resets.cumsum().values

    base_date = pd.Timestamp(f"{int(df['year'].iloc[0])}-01-01")
    df["full_date"] = base_date + pd.to_timedelta(df["day_index"], unit="D")
    df["day_of_week"] = pd.Categorical(
        df["full_date"].dt.day_name(), categories=DAY_ORDER, ordered=True
    )
    df["day_num"] = df["full_date"].dt.weekday
    df["day_type"] = np.where(df["day_num"] < 5, "Weekday", "Weekend")
    df["month"] = df["full_date"].dt.strftime("%b %Y")
    df["month_start"] = df["full_date"].values.astype("datetime64[M]")

    def classify_period(h):
        if 6 <= h <= 10:
            return "Morning Rush (6-10)"
        elif 11 <= h <= 14:
            return "Midday (11-14)"
        elif 15 <= h <= 17:
            return "Afternoon Peak (15-17)"
        else:
            return "Off-Peak (18-5)"

    df["operational_period"] = df["transaction_hour"].apply(classify_period)

    return df


df = load_data(DATA_PATH)

# --------------------------------------------------------------------------
# Sidebar — filters
# --------------------------------------------------------------------------
st.sidebar.markdown("## ☕ Filters")

locations = sorted(df["store_location"].unique().tolist())
sel_locations = st.sidebar.multiselect(
    "Store location", options=locations, default=locations
)

sel_days = st.sidebar.multiselect(
    "Day of week", options=DAY_ORDER, default=DAY_ORDER
)

hour_min, hour_max = st.sidebar.slider(
    "Hour range (24h)", min_value=0, max_value=23, value=(0, 23)
)

metric_choice = st.sidebar.radio(
    "Metric focus", options=["Revenue", "Quantity"], horizontal=True
)
metric_col = "revenue" if metric_choice == "Revenue" else "transaction_qty"
metric_label = "Revenue ($)" if metric_choice == "Revenue" else "Items Sold"
agg_func = "sum"

categories = sorted(df["product_category"].unique().tolist())
sel_categories = st.sidebar.multiselect(
    "Product category (optional)", options=categories, default=categories
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data: Afficionado Coffee Roasters transactions, "
    f"{df['full_date'].min().date()} to {df['full_date'].max().date()}, "
    f"{len(df):,} line items across {df['store_location'].nunique()} stores."
)

# --------------------------------------------------------------------------
# Apply filters
# --------------------------------------------------------------------------
mask = (
    df["store_location"].isin(sel_locations)
    & df["day_of_week"].isin(sel_days)
    & df["product_category"].isin(sel_categories)
    & df["transaction_hour"].between(hour_min, hour_max)
)
fdf = df.loc[mask].copy()

# --------------------------------------------------------------------------
# Header + KPIs
# --------------------------------------------------------------------------
st.markdown("# ☕ Afficionado Coffee Roasters")
st.markdown("#### Sales Intelligence Dashboard — 2025 Transactions")

if fdf.empty:
    st.warning("No transactions match the current filters. Try widening your selection.")
    st.stop()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Revenue", f"${fdf['revenue'].sum():,.0f}")
k2.metric("Items Sold", f"{fdf['transaction_qty'].sum():,.0f}")
k3.metric("Transactions", f"{fdf['transaction_id'].nunique():,.0f}")
k4.metric("Avg Order Value", f"${fdf.groupby('transaction_id')['revenue'].sum().mean():,.2f}")
active_days = fdf["full_date"].nunique()
k5.metric("Days in View", f"{active_days:,}")

st.markdown("")

# --------------------------------------------------------------------------
# Tabs — Core Modules
# --------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 Overall Sales Trend", "📅 Day-of-Week Performance", "🔥 Hourly Demand Heatmap", "📍 Location Comparison"]
)

# ---- TAB 1: Overall sales trend ----
with tab1:
    st.subheader(f"Daily {metric_choice} Trend")

    daily = (
        fdf.groupby("full_date")
        .agg(revenue=("revenue", "sum"), transaction_qty=("transaction_qty", "sum"))
        .reset_index()
        .sort_values("full_date")
    )
    daily["rolling_7d"] = daily[metric_col].rolling(7, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["full_date"], y=daily[metric_col], name=f"Daily {metric_choice}",
        mode="lines", line=dict(color="#c9a27a", width=1.5), opacity=0.6,
    ))
    fig.add_trace(go.Scatter(
        x=daily["full_date"], y=daily["rolling_7d"], name="7-Day Moving Avg",
        mode="lines", line=dict(color="#6b3f1d", width=3),
    ))
    fig.update_layout(
        height=420, hovermode="x unified", yaxis_title=metric_label, xaxis_title="Date",
        legend=dict(orientation="h", y=1.08),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Monthly Totals")
        monthly = fdf.groupby("month_start").agg(
            revenue=("revenue", "sum"), transaction_qty=("transaction_qty", "sum")
        ).reset_index().sort_values("month_start")
        monthly["month_label"] = monthly["month_start"].dt.strftime("%b %Y")
        fig_m = px.bar(
            monthly, x="month_label", y=metric_col, color_discrete_sequence=["#8a5a34"],
            labels={metric_col: metric_label, "month_label": "Month"},
        )
        fig_m.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_m, use_container_width=True)

    with c2:
        st.subheader("Revenue by Product Category")
        cat = fdf.groupby("product_category").agg(
            revenue=("revenue", "sum"), transaction_qty=("transaction_qty", "sum")
        ).reset_index().sort_values(metric_col, ascending=False)
        fig_c = px.bar(
            cat, x=metric_col, y="product_category", orientation="h",
            color=metric_col, color_continuous_scale="Oranges",
            labels={metric_col: metric_label, "product_category": ""},
        )
        fig_c.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10), coloraxis_showscale=False)
        fig_c.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig_c, use_container_width=True)

# ---- TAB 2: Day-of-week performance ----
with tab2:
    st.subheader(f"Average Daily {metric_choice} by Day of Week")

    daily_totals = (
        fdf.groupby(["full_date", "day_of_week"], observed=True)
        .agg(revenue=("revenue", "sum"), transaction_qty=("transaction_qty", "sum"))
        .reset_index()
    )
    weekday_perf = (
        daily_totals.groupby("day_of_week", observed=True)
        .agg(avg_revenue=("revenue", "mean"), avg_qty=("transaction_qty", "mean"))
        .reindex(DAY_ORDER)
        .dropna(how="all")
        .reset_index()
    )
    avg_col = "avg_revenue" if metric_choice == "Revenue" else "avg_qty"
    avg_label = "Avg Daily Revenue ($)" if metric_choice == "Revenue" else "Avg Daily Items Sold"

    fig_w = px.bar(
        weekday_perf, x="day_of_week", y=avg_col, color=avg_col,
        color_continuous_scale="Brwnyl", labels={avg_col: avg_label, "day_of_week": ""},
    )
    fig_w.update_layout(height=400, margin=dict(l=10, r=10, t=20, b=10), coloraxis_showscale=False)
    st.plotly_chart(fig_w, use_container_width=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Weekday vs Weekend")
        daily_totals["day_type"] = np.where(
            daily_totals["day_of_week"].isin(["Saturday", "Sunday"]), "Weekend", "Weekday"
        )
        dt_comp = daily_totals.groupby("day_type").agg(
            avg_revenue=("revenue", "mean"), avg_qty=("transaction_qty", "mean")
        ).reset_index()
        dt_col = "avg_revenue" if metric_choice == "Revenue" else "avg_qty"
        fig_dt = px.bar(
            dt_comp, x="day_type", y=dt_col, color="day_type",
            color_discrete_map={"Weekday": "#8a5a34", "Weekend": "#d9a066"},
            labels={dt_col: avg_label, "day_type": ""},
        )
        fig_dt.update_layout(height=340, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_dt, use_container_width=True)

    with c2:
        st.subheader("Basket Size by Day Type")
        fdf["day_type"] = np.where(fdf["day_of_week"].isin(["Saturday", "Sunday"]), "Weekend", "Weekday")
        basket = fdf.groupby(["transaction_id", "day_type"]).agg(
            items=("transaction_qty", "sum"), spend=("revenue", "sum")
        ).reset_index()
        basket_summary = basket.groupby("day_type").agg(
            avg_items=("items", "mean"), avg_spend=("spend", "mean")
        ).reset_index()
        b_col = "avg_spend" if metric_choice == "Revenue" else "avg_items"
        b_label = "Avg Spend per Order ($)" if metric_choice == "Revenue" else "Avg Items per Order"
        fig_b = px.bar(
            basket_summary, x="day_type", y=b_col, color="day_type",
            color_discrete_map={"Weekday": "#5c7a5c", "Weekend": "#9dbf9d"},
            labels={b_col: b_label, "day_type": ""},
        )
        fig_b.update_layout(height=340, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_b, use_container_width=True)

# ---- TAB 3: Hourly demand heatmap ----
with tab3:
    st.subheader(f"{metric_choice} Heatmap — Day of Week × Hour")

    heat = (
        fdf.groupby(["day_of_week", "transaction_hour"], observed=True)[metric_col]
        .agg(agg_func)
        .reset_index()
    )
    pivot = heat.pivot(index="day_of_week", columns="transaction_hour", values=metric_col)
    pivot = pivot.reindex(DAY_ORDER).dropna(how="all")
    pivot = pivot.reindex(columns=range(hour_min, hour_max + 1), fill_value=0)

    fig_h = px.imshow(
        pivot, color_continuous_scale="YlOrBr", aspect="auto",
        labels=dict(x="Hour of Day", y="", color=metric_label),
    )
    fig_h.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_h, use_container_width=True)

    st.subheader(f"{metric_choice} Heatmap — Product Category × Hour")
    heat2 = (
        fdf.groupby(["product_category", "transaction_hour"])[metric_col]
        .agg(agg_func)
        .reset_index()
    )
    pivot2 = heat2.pivot(index="product_category", columns="transaction_hour", values=metric_col)
    pivot2 = pivot2.reindex(columns=range(hour_min, hour_max + 1), fill_value=0)
    fig_h2 = px.imshow(
        pivot2, color_continuous_scale="YlGnBu", aspect="auto",
        labels=dict(x="Hour of Day", y="", color=metric_label),
    )
    fig_h2.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_h2, use_container_width=True)

    hourly_traffic = fdf.groupby("transaction_hour")["transaction_id"].nunique()
    if not hourly_traffic.empty:
        peak_hour = hourly_traffic.idxmax()
        st.info(f"🔥 Peak transaction hour in current view: **{peak_hour}:00–{peak_hour+1}:00** "
                f"({hourly_traffic.max():,} transactions).")

# ---- TAB 4: Location comparison ----
with tab4:
    st.subheader(f"{metric_choice} by Store Location")
    loc = fdf.groupby("store_location").agg(
        revenue=("revenue", "sum"), transaction_qty=("transaction_qty", "sum"),
        transactions=("transaction_id", "nunique"),
    ).reset_index().sort_values(metric_col, ascending=False)
    fig_l = px.bar(
        loc, x="store_location", y=metric_col, color="store_location",
        labels={metric_col: metric_label, "store_location": ""},
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig_l.update_layout(height=380, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_l, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Smoothed Daily Trend per Store")
        store_daily = fdf.groupby(["store_location", "full_date"]).agg(
            revenue=("revenue", "sum"), transaction_qty=("transaction_qty", "sum")
        ).reset_index().sort_values("full_date")
        store_daily["rolling_7d"] = store_daily.groupby("store_location")[metric_col].transform(
            lambda s: s.rolling(7, min_periods=1).mean()
        )
        fig_sd = px.line(
            store_daily, x="full_date", y="rolling_7d", color="store_location",
            labels={"rolling_7d": f"{metric_label} (7d avg)", "full_date": "Date", "store_location": "Store"},
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig_sd.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_sd, use_container_width=True)

    with c2:
        st.subheader("Peak Hour by Store")
        store_hour = fdf.groupby(["store_location", "transaction_hour"])["transaction_id"].nunique().reset_index()
        peak_by_store = store_hour.loc[store_hour.groupby("store_location")["transaction_id"].idxmax()]
        fig_p = px.bar(
            peak_by_store.sort_values("transaction_id", ascending=False),
            x="store_location", y="transaction_hour", color="store_location",
            text="transaction_id",
            labels={"transaction_hour": "Peak Hour (24h)", "store_location": ""},
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig_p.update_traces(texttemplate="%{text} orders", textposition="outside")
        fig_p.update_layout(height=380, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_p, use_container_width=True)

    st.subheader("Store × Hour Traffic Heatmap")
    sh = fdf.groupby(["store_location", "transaction_hour"])["transaction_id"].nunique().reset_index()
    pivot3 = sh.pivot(index="store_location", columns="transaction_hour", values="transaction_id")
    pivot3 = pivot3.reindex(columns=range(hour_min, hour_max + 1), fill_value=0)
    fig_sh = px.imshow(
        pivot3, color_continuous_scale="YlOrRd", aspect="auto",
        labels=dict(x="Hour of Day", y="", color="Transactions"),
    )
    fig_sh.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_sh, use_container_width=True)

st.markdown("---")
st.caption(
    "Built with Streamlit · Data reflects reconstructed calendar dates derived from "
    "per-store chronological ordering and time resets in the source transaction log."
)
