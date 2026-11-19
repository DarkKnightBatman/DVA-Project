import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="MarketPulse | Stock Analytics",
    page_icon="📈",
    layout="wide"
)

# ---------------- CUSTOM STYLE ----------------
st.markdown("""
<style>
.stApp {background-color: #0b1220; color: #e5e7eb;}
[data-testid="stSidebar"] {background-color: #111c2f;}
[data-testid="stMetric"] {
    background: #142238;
    border: 1px solid #263b59;
    padding: 14px;
    border-radius: 12px;
}
h1, h2, h3 {color: #f8fafc;}
</style>
""", unsafe_allow_html=True)

# ---------------- STOCK LIST ----------------
STOCKS = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "Reliance": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "Infosys": "INFY.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "State Bank of India": "SBIN.NS",
    "ITC": "ITC.NS",
    "Tata Motors": "TATAMOTORS.NS"
}

COMPANIES = {
    "Reliance": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "Infosys": "INFY.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "SBI": "SBIN.NS",
    "ITC": "ITC.NS",
    "Tata Motors": "TATAMOTORS.NS"
}

# ---------------- DATA FUNCTIONS ----------------
@st.cache_data(ttl=1800, show_spinner=False)
def get_stock_data(ticker, period):
    data = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False
    )

    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.reset_index()

    if "Date" not in data.columns and "Datetime" in data.columns:
        data = data.rename(columns={"Datetime": "Date"})

    required = ["Date", "Open", "High", "Low", "Close"]
    if not all(col in data.columns for col in required):
        return pd.DataFrame()

    if "Volume" not in data.columns:
        data["Volume"] = 0

    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=["Date", "Close"])
    data = data.drop_duplicates(subset="Date")
    return data.sort_values("Date").reset_index(drop=True)


@st.cache_data(ttl=1800, show_spinner=False)
def get_company_prices(tickers, period):
    data = yf.download(
        list(tickers),
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False
    )

    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" not in data.columns.get_level_values(0):
            return pd.DataFrame()
        return data["Close"]

    if "Close" in data.columns:
        return data[["Close"]]

    return pd.DataFrame()


# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Dashboard Controls")

selected_stock = st.sidebar.selectbox("Select stock / index", list(STOCKS.keys()))
period = st.sidebar.selectbox(
    "Historical period", ["6mo", "1y", "2y", "5y", "10y"], index=3
)
chart_type = st.sidebar.radio("Main chart type", ["Line", "Candlestick"])
moving_averages = st.sidebar.multiselect(
    "Show moving averages",
    [7, 20, 50, 100, 200],
    default=[20, 50]
)
rolling_window = st.sidebar.select_slider(
    "Rolling window (trading days)",
    options=[7, 14, 20, 30, 50, 90],
    value=30
)

# ---------------- HEADER ----------------
st.title("📈 MarketPulse")
st.markdown("### Interactive Indian Stock Market Analytics")
st.caption("Explore historical prices, trends, rolling statistics and relationships between stocks.")

ticker = STOCKS[selected_stock]

with st.spinner("Downloading market data..."):
    df = get_stock_data(ticker, period)

if df.empty:
    st.error("Market data could not be loaded. Check your internet connection or try another stock/period.")
    st.info("Yahoo Finance may occasionally limit requests. Wait a little and try again.")
    st.stop()

# ---------------- DATE FILTER ----------------
min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

st.sidebar.subheader("Date filter")
selected_dates = st.sidebar.date_input(
    "Choose date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(selected_dates, (tuple, list)):
    if len(selected_dates) == 2:
        start_date, end_date = selected_dates
    elif len(selected_dates) == 1:
        start_date = end_date = selected_dates[0]
    else:
        start_date, end_date = min_date, max_date
else:
    start_date = end_date = selected_dates

filtered = df[
    (df["Date"].dt.date >= start_date) &
    (df["Date"].dt.date <= end_date)
].copy()

if filtered.empty:
    st.warning("No trading records found for this date selection. Choose a wider date range.")
    st.stop()

# ---------------- FEATURE ENGINEERING ----------------
for window in [7, 20, 50, 100, 200]:
    filtered[f"MA_{window}"] = filtered["Close"].rolling(window).mean()

filtered["Rolling_Mean"] = filtered["Close"].rolling(rolling_window).mean()
filtered["Rolling_STD"] = filtered["Close"].rolling(rolling_window).std()
filtered["Rolling_Min"] = filtered["Close"].rolling(rolling_window).min()
filtered["Rolling_Max"] = filtered["Close"].rolling(rolling_window).max()

unit = "points" if ticker.startswith("^") else "₹"
latest_price = filtered["Close"].iloc[-1]
highest_price = filtered["High"].max()
lowest_price = filtered["Low"].min()
average_price = filtered["Close"].mean()
average_volume = filtered["Volume"].mean()

# ---------------- KPI CARDS ----------------
st.subheader("Market overview")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Latest closing price", f"{latest_price:,.2f} {unit}")
k2.metric("Period high", f"{highest_price:,.2f} {unit}")
k3.metric("Period low", f"{lowest_price:,.2f} {unit}")
k4.metric("Average closing price", f"{average_price:,.2f} {unit}")

# ---------------- MAIN PRICE CHART ----------------
st.subheader("1. Price movement")

price_fig = go.Figure()

if chart_type == "Candlestick":
    price_fig.add_trace(go.Candlestick(
        x=filtered["Date"],
        open=filtered["Open"],
        high=filtered["High"],
        low=filtered["Low"],
        close=filtered["Close"],
        name="Price"
    ))
else:
    price_fig.add_trace(go.Scatter(
        x=filtered["Date"],
        y=filtered["Close"],
        mode="lines",
        name="Closing price",
        line=dict(width=2)
    ))

for window in moving_averages:
    price_fig.add_trace(go.Scatter(
        x=filtered["Date"],
        y=filtered[f"MA_{window}"],
        mode="lines",
        name=f"{window}-day MA"
    ))

price_fig.update_layout(
    template="plotly_dark",
    height=480,
    hovermode="x unified",
    xaxis_title="Date",
    yaxis_title=f"Price ({unit})",
    xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=35, b=10)
)
st.plotly_chart(price_fig, use_container_width=True)

# ---------------- ANALYSIS TABS ----------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📉 Rolling analysis",
    "📊 Price distribution",
    "📅 Monthly & yearly",
    "🔗 Correlation",
    "🗂️ Data & download"
])

with tab1:
    st.subheader("Rolling statistics")
    left, right = st.columns(2)

    with left:
        mean_fig = go.Figure()
        mean_fig.add_trace(go.Scatter(
            x=filtered["Date"], y=filtered["Close"],
            name="Closing price", mode="lines"
        ))
        mean_fig.add_trace(go.Scatter(
            x=filtered["Date"], y=filtered["Rolling_Mean"],
            name=f"{rolling_window}-day rolling mean", mode="lines"
        ))
        mean_fig.update_layout(
            title="Closing price vs rolling mean",
            template="plotly_dark", height=370
        )
        st.plotly_chart(mean_fig, use_container_width=True)

    with right:
        std_fig = px.line(
            filtered, x="Date", y="Rolling_STD",
            title=f"{rolling_window}-day rolling standard deviation"
        )
        std_fig.update_layout(template="plotly_dark", height=370)
        st.plotly_chart(std_fig, use_container_width=True)

    range_fig = go.Figure()
    range_fig.add_trace(go.Scatter(
        x=filtered["Date"], y=filtered["Rolling_Max"],
        name="Rolling maximum", mode="lines"
    ))
    range_fig.add_trace(go.Scatter(
        x=filtered["Date"], y=filtered["Rolling_Min"],
        name="Rolling minimum", mode="lines", fill="tonexty"
    ))
    range_fig.update_layout(
        title="Rolling minimum and maximum",
        template="plotly_dark", height=350
    )
    st.plotly_chart(range_fig, use_container_width=True)

    st.info(
        f"Rolling statistics use the previous {rolling_window} trading observations. "
        "The standard deviation here measures variation in closing-price levels, not returns."
    )

with tab2:
    st.subheader("Closing-price distribution")
    left, right = st.columns(2)

    with left:
        hist = px.histogram(
            filtered, x="Close", nbins=30,
            title="Histogram of closing prices"
        )
        hist.update_layout(template="plotly_dark", height=380)
        st.plotly_chart(hist, use_container_width=True)

    with right:
        box = px.box(
            filtered, y="Close",
            title="Box plot of closing prices"
        )
        box.update_layout(template="plotly_dark", height=380)
        st.plotly_chart(box, use_container_width=True)

    st.subheader("Price relationship scatter plots")
    scatter1, scatter2 = st.columns(2)

    with scatter1:
        open_close = px.scatter(
            filtered, x="Open", y="Close",
            title="Opening price vs closing price",
            hover_data=["Date"]
        )
        open_close.update_layout(template="plotly_dark", height=380)
        st.plotly_chart(open_close, use_container_width=True)

    with scatter2:
        high_low = px.scatter(
            filtered, x="Low", y="High",
            title="Lowest price vs highest price",
            hover_data=["Date"]
        )
        high_low.update_layout(template="plotly_dark", height=380)
        st.plotly_chart(high_low, use_container_width=True)

with tab3:
    st.subheader("Monthly and yearly price analysis")

    monthly = (
        filtered.set_index("Date")["Close"]
        .resample("ME").mean().dropna()
        .rename("Average Close").reset_index()
    )
    yearly = (
        filtered.set_index("Date")["Close"]
        .resample("YE").mean().dropna()
        .rename("Average Close").reset_index()
    )

    if not monthly.empty:
        monthly_fig = px.bar(
            monthly, x="Date", y="Average Close",
            title="Monthly average closing price"
        )
        monthly_fig.update_layout(template="plotly_dark", height=380)
        st.plotly_chart(monthly_fig, use_container_width=True)

    if not yearly.empty:
        yearly_fig = px.bar(
            yearly, x="Date", y="Average Close",
            title="Yearly average closing price"
        )
        yearly_fig.update_layout(template="plotly_dark", height=380)
        st.plotly_chart(yearly_fig, use_container_width=True)

with tab4:
    st.subheader("Correlation between selected companies")
    st.write("Select at least two companies to compare their daily price movements.")

    chosen_companies = st.multiselect(
        "Companies",
        list(COMPANIES.keys()),
        default=["Reliance", "TCS", "Infosys", "HDFC Bank"]
    )

    if len(chosen_companies) >= 2:
        chosen_tickers = tuple(COMPANIES[name] for name in chosen_companies)

        with st.spinner("Loading comparison data..."):
            prices = get_company_prices(chosen_tickers, period)

        if not prices.empty:
            price_changes = prices.diff()
            correlation = price_changes.corr()

            heatmap = px.imshow(
                correlation,
                text_auto=".2f",
                aspect="auto",
                color_continuous_scale="RdBu_r",
                zmin=-1,
                zmax=1,
                title="Correlation of daily price differences"
            )
            heatmap.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(heatmap, use_container_width=True)

            st.caption(
                "Interpretation: +1 means the two series moved together strongly; "
                "−1 means they moved in opposite directions; 0 means little linear relationship. "
                "This uses absolute daily price differences, not percentage returns. "
                "Different stock price scales can affect interpretation."
            )
        else:
            st.warning("Comparison data is unavailable. Try fewer companies or another period.")
    else:
        st.info("Please select at least two companies.")

with tab5:
    st.subheader("Historical data")
    st.dataframe(
        filtered.sort_values("Date", ascending=False),
        use_container_width=True,
        hide_index=True
    )

    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download filtered data (CSV)",
        data=csv,
        file_name=f"{selected_stock.lower().replace(' ', '_')}_data.csv",
        mime="text/csv"
    )

    st.subheader("Quick summary")
    summary = filtered[["Open", "High", "Low", "Close", "Volume"]].describe().round(2)
    st.dataframe(summary, use_container_width=True)

# ---------------- FOOTER ----------------
st.divider()
st.caption(
    "MarketPulse | Educational data analytics project. "
    "Data is sourced from Yahoo Finance and may be delayed or incomplete. "
    "This dashboard is not investment advice."
)
