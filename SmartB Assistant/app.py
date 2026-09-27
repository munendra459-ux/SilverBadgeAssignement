from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from src.data_loader import CSVFormatError, load_csv, quality_summary
from src.analytics import metrics
from src.charts import charts
from src.insights import insights
from src.sentiment import prepare, summary, chart
from src.recommendations import actions
from src.llm import RAG, ask
from src.database import init_db, upsert_inventory
from src.inventory import analyze_inventory, get_inventory_recommendations, get_slow_moving_items
from src.campaigns import (calculate_campaign_metrics, generate_campaign_recommendations, 
                           calculate_customer_ltv, calculate_churn_indicators)
from src.market import analyze_market_position, generate_competitive_recommendations
from src.statistics import (detect_sales_anomalies, calculate_trend, identify_seasonality, 
                            forecast_sales, analyze_product_velocity, calculate_growth_rate,
                            calculate_statistical_summary)
from src.scheduler import generate_weekly_report, generate_monthly_report, get_report_history
from utils.helpers import report

load_dotenv()
ROOT = Path(__file__).parent
st.set_page_config(page_title="SmartB Assistant", page_icon="📊", layout="wide")

# Initialize database
init_db()

@st.cache_data
def data(name, content=None):
    return load_csv(content if content is not None else ROOT / "data" / name)

sales = data("SuperStoreOrders.csv")
reviews = data("Womens Clothing E-Commerce Reviews.csv")

st.title("📊 SmartB Assistant - Complete Business Intelligence")
st.markdown("*Analyze sales, inventory, campaigns, market trends, and more.*")

with st.sidebar:
    st.subheader("📁 Data Upload")
    sales_file = st.file_uploader("Sales CSV", type="csv")
    review_file = st.file_uploader("Feedback CSV", type="csv")
    inventory_file = st.file_uploader("Inventory CSV", type="csv")
    allow_external_ai = st.checkbox(
        "Allow external AI processing",
        help="When enabled, the question and retrieved data excerpts are sent to OpenAI. Keep this off for sensitive data.",
    )

try:
    if sales_file:
        sales = load_csv(sales_file.getvalue())
    if review_file:
        reviews = load_csv(review_file.getvalue())
    if inventory_file and st.button("Save inventory data"):
        inventory_data = load_csv(inventory_file.getvalue())
        required_inventory = {"product_id", "stock_quantity", "reorder_level", "unit_cost"}
        missing_inventory = required_inventory - set(inventory_data.columns)
        if missing_inventory:
            st.error("Inventory CSV is missing: " + ", ".join(sorted(missing_inventory)))
        else:
            upsert_inventory(inventory_data)
            st.success(f"Saved {len(inventory_data):,} inventory records.")
except CSVFormatError as error:
    st.error(str(error))
    st.stop()

missing_sales = [column for column in ("order_date", "sales") if column not in sales.columns]
if missing_sales:
    st.error("Sales CSV is missing required column(s): " + ", ".join(missing_sales) + ".")
    st.stop()
if sales.empty:
    st.error("Upload a sales CSV.")
    st.stop()

with st.sidebar:
    st.subheader("🔍 Filters")
    date_range = st.date_input("Date range", value=(sales.order_date.min().date(), sales.order_date.max().date()))
    products = st.multiselect("Product", sorted(sales["product"].dropna().unique()))
    regions = st.multiselect("Region", sorted(sales["region"].dropna().unique()))
    categories = st.multiselect("Category", sorted(sales["category"].dropna().unique()))

with st.expander("Data quality"):
    profile = quality_summary(sales)
    quality_cols = st.columns(4)
    for col, (name, value) in zip(quality_cols, list(profile.items())[:4]):
        col.metric(name, value)
    st.caption(f"Date coverage: {profile['Date range']}. Repeated order IDs are expected for orders with multiple line items.")

filtered_sales = sales.copy()
if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_sales = filtered_sales[filtered_sales.order_date.dt.date.between(start_date, end_date)]
if products:
    filtered_sales = filtered_sales[filtered_sales.product.isin(products)]
if regions:
    filtered_sales = filtered_sales[filtered_sales.region.isin(regions)]
if categories:
    filtered_sales = filtered_sales[filtered_sales.category.isin(categories)]

if filtered_sales.empty:
    st.warning("No sales records match the selected filters.")
    st.stop()

sales = filtered_sales

# Calculate key metrics and insights
sales_metrics = metrics(sales)
findings = insights(sales)
todo = actions(sales, findings)

# Display KPIs
st.subheader("📊 Key Performance Indicators")
for col, (name, value) in zip(st.columns(5), sales_metrics.items()):
    col.metric(name, value)

# Main tabs
tabs = st.tabs(["📈 Dashboard", "💬 AI Assistant", "💝 Sentiment", "📦 Inventory", 
                "🎯 Campaigns", "🏢 Market Analysis", "📊 Statistics", "📋 Reports"])

with tabs[0]:  # Dashboard
    st.subheader("Sales Dashboard")
    for fig in charts(sales):
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("🎯 Business Insights & Recommendations")
    cols = st.columns(2)
    with cols[0]:
        st.write("**Key Findings:**")
        for item in findings:
            st.info(item)
    with cols[1]:
        st.write("**Recommended Actions:**")
        for item in todo:
            st.success(item)

with tabs[1]:  # AI Assistant
    st.subheader("💬 Ask Business Questions")
    st.markdown("*Ask about your sales, trends, products, customers, and more.*")
    
    question = st.chat_input("Example: Why did sales change last month? Which region is underperforming?")
    if question:
        with st.spinner("Analyzing..."):
            rag = RAG(sales, reviews)
            result = ask(question, rag, sales_metrics, findings, sales, allow_external_ai)
            
            st.write("**Answer:**")
            st.markdown(result.text)
            
            st.metric("Confidence", f"{result.confidence:.0%}")
            
            with st.expander("📚 Retrieved Evidence"):
                for i, source in enumerate(result.sources, 1):
                    st.caption(f"{i}. {source}")
            
            if result.mode == "local":
                st.info("Local answer mode is active. Enable external AI processing only if your data may be sent to OpenAI.")

with tabs[2]:  # Sentiment Analysis
    st.subheader("💝 Customer Sentiment Analysis")
    reviews_prep = prepare(reviews)
    
    if reviews_prep.empty or not {"rating", "review_text"}.issubset(reviews_prep.columns):
        st.info("Upload customer reviews with 'rating' and 'review_text' columns.")
    else:
        cols = st.columns(3)
        for col, (name, value) in zip(cols, summary(reviews_prep).items()):
            col.metric(name, value)
        
        st.plotly_chart(chart(reviews_prep), use_container_width=True)
        st.dataframe(reviews_prep[["rating", "sentiment", "review_text"]].head(25), use_container_width=True)

with tabs[3]:  # Inventory
    st.subheader("📦 Inventory Management")
    
    inventory_analysis = analyze_inventory()
    
    if inventory_analysis['total_items']:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Inventory Value", f"₹{inventory_analysis['total_value']:,.0f}")
        col2.metric("Total Items", inventory_analysis['total_items'])
        col3.metric("Low Stock Alerts", len(inventory_analysis['low_stock_items']))
        
        if inventory_analysis['alerts']:
            st.subheader("⚠️ Alerts")
            for alert in inventory_analysis['alerts']:
                st.warning(alert)
        
        # Slow-moving items
        slow_movers = get_slow_moving_items(sales)
        if not slow_movers.empty:
            st.subheader("🐢 Slow-Moving Products")
            st.dataframe(slow_movers.head(10), use_container_width=True)
    else:
        st.info("No inventory data available. Add inventory records to get started.")
    
    # Inventory recommendations
    inv_recs = get_inventory_recommendations()
    if inv_recs:
        st.subheader("💡 Inventory Recommendations")
        for rec in inv_recs:
            st.success(rec)

with tabs[4]:  # Campaigns
    st.subheader("🎯 Marketing Campaign Analysis")
    
    st.caption("These are sales-performance metrics, not campaign-attributed results. Upload campaign performance data before using ROI.")
    campaign_metrics_data = calculate_campaign_metrics(sales)
    
    cols = st.columns(4)
    cols[0].metric("Sales Revenue", f"₹{campaign_metrics_data['total_revenue']:,.0f}")
    cols[1].metric("Avg Order Value", f"₹{campaign_metrics_data['avg_order_value']:,.0f}")
    cols[2].metric("Customers", campaign_metrics_data['customer_count'])
    cols[3].metric("Total Orders", campaign_metrics_data['orders'])
    
    # Customer LTV
    ltv = calculate_customer_ltv(sales)
    st.metric("Customer Lifetime Value (LTV)", f"₹{ltv:,.0f}")
    
    # Churn analysis
    churn_data = calculate_churn_indicators(sales)
    if churn_data:
        col1, col2, col3 = st.columns(3)
        col1.metric("Active Customers", churn_data.get('active_customers', 0))
        col2.metric("Churned Customers", churn_data.get('churned_customers', 0))
        col3.metric("Churn Rate", f"{churn_data.get('churn_rate', 0):.1f}%")
    
    # Campaign recommendations
    camp_recs = generate_campaign_recommendations(sales)
    if camp_recs:
        st.subheader("💡 Campaign Recommendations")
        for rec in camp_recs:
            st.success(rec)

with tabs[5]:  # Market Analysis
    st.subheader("🏢 Market & Competitor Analysis")
    
    if not sales.empty and 'category' in sales.columns:
        selected_category = st.selectbox("Select Category for Analysis", sales['category'].dropna().unique())
        
        market_analysis = analyze_market_position(sales[sales['category'] == selected_category], selected_category)
        
        if market_analysis:
            st.subheader("📊 Your Market Position")
            your_metrics = market_analysis.get('your_metrics', {})
            
            cols = st.columns(3)
            cols[0].metric("Total Revenue", f"₹{your_metrics.get('total_revenue', 0):,.0f}")
            cols[1].metric("Avg Sales per Line", f"₹{your_metrics.get('avg_price', 0):,.0f}")
            cols[2].metric("Avg Rating", f"{your_metrics.get('avg_rating', 0):.1f}/5")
            
            if market_analysis.get('competitors') and 'your_market_share' in market_analysis:
                st.metric("Market Share", f"{market_analysis['your_market_share']:.1f}%")
            else:
                st.info("Add competitor data to calculate a market-share estimate and competitive recommendations.")
        
        # Competitive recommendations
        comp_recs = generate_competitive_recommendations(sales[sales['category'] == selected_category], selected_category)
        if comp_recs:
            st.subheader("💡 Competitive Recommendations")
            for rec in comp_recs:
                st.success(rec)

with tabs[6]:  # Statistics
    st.subheader("📊 Advanced Statistical Analysis")
    
    cols = st.columns(2)
    
    with cols[0]:
        st.write("**Sales Trend Analysis (Last 30 Days)**")
        trend = calculate_trend(sales, 30)
        if trend:
            st.write(f"**Trend:** {trend.get('trend', 'N/A').upper()}")
            st.write(f"**Daily Change:** ₹{trend.get('slope', 0):.0f}")
            st.write(f"**R² (Fit Quality):** {trend.get('r_squared', 0):.3f}")
    
    with cols[1]:
        st.write("**Seasonality Analysis (average monthly revenue)**")
        seasonality = identify_seasonality(sales)
        if seasonality and 'peak_month' in seasonality:
            st.write(f"**Peak Month:** {seasonality['peak_month']} (₹{seasonality['peak_sales']:,.0f})")
            st.write(f"**Trough Month:** {seasonality['trough_month']} (₹{seasonality['trough_sales']:,.0f})")
    
    # Sales anomalies
    st.subheader("🚨 Sales Anomalies")
    anomalies = detect_sales_anomalies(sales, window=7)
    if not anomalies.empty:
        st.dataframe(anomalies, use_container_width=True)
    else:
        st.info("No significant sales anomalies detected.")
    
    # Product velocity
    st.subheader("⚡ Product Velocity Analysis")
    velocity = analyze_product_velocity(sales)
    if not velocity.empty:
        st.dataframe(velocity.head(15), use_container_width=True)
    
    # Growth rates
    st.subheader("📈 Growth Rate Analysis")
    growth_rates = calculate_growth_rate(sales)
    if growth_rates:
        growth_df = pd.DataFrame(growth_rates)
        st.line_chart(data=growth_df.set_index('month')['growth_rate'])
    
    # Statistical summary
    st.subheader("📊 Statistical Summary")
    stats_summary = calculate_statistical_summary(sales)
    if stats_summary:
        stats_df = pd.DataFrame([stats_summary]).T
        st.dataframe(stats_df, use_container_width=True)

with tabs[7]:  # Reports
    st.subheader("📋 Business Reports")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📅 Generate Weekly Report"):
            with st.spinner("Generating weekly report..."):
                filepath = generate_weekly_report(sales, reviews)
                st.success(f"✅ Report saved to {filepath}")
    
    with col2:
        if st.button("📆 Generate Monthly Report"):
            with st.spinner("Generating monthly report..."):
                filepath = generate_monthly_report(sales, reviews)
                st.success(f"✅ Report saved to {filepath}")
    
    with col3:
        custom_days = st.number_input("Custom Period (days)", 1, 365, 30)
        if st.button("📊 Generate Custom Report"):
            with st.spinner(f"Generating {custom_days}-day report..."):
                from src.scheduler import generate_custom_period_report
                filepath = generate_custom_period_report(sales, reviews, custom_days)
                st.success(f"✅ Report saved to {filepath}")
    
    # Display recent reports
    st.subheader("📚 Recent Reports")
    recent = get_report_history()
    if recent:
        report_df = pd.DataFrame(recent)
        st.dataframe(report_df, use_container_width=True)
    else:
        st.info("No reports generated yet.")
    
    # Downloadable full report
    st.subheader("📥 Download Full Report")
    full_report_text = report(sales, sales_metrics, findings, todo)
    st.download_button(
        label="📥 Download Current Report as Markdown",
        data=full_report_text,
        file_name="smartb_report.md",
        mime="text/markdown"
    )
