"""Marketing campaign tracking and ROI analysis."""
import pandas as pd
from src.database import get_campaign_roi, insert_campaign, insert_campaign_performance

def analyze_campaign(campaign_id):
    """Analyze single campaign performance."""
    roi = get_campaign_roi(campaign_id)
    return {
        'campaign_id': campaign_id,
        'roi_percentage': round(roi, 2)
    }

def calculate_campaign_metrics(sales_df, campaign_sales_subset=None):
    """Calculate campaign performance metrics."""
    if sales_df.empty:
        return {
            'total_revenue': 0,
            'avg_order_value': 0,
            'customer_count': 0,
            'conversion_rate': 0,
            'roi': 0
        }
    
    sales_data = campaign_sales_subset if campaign_sales_subset is not None else sales_df
    
    total_revenue = sales_data['sales'].sum() if 'sales' in sales_data.columns else 0
    order_count = sales_data['order_id'].nunique() if 'order_id' in sales_data.columns else len(sales_data)
    avg_order_value = total_revenue / max(order_count, 1)
    customer_count = sales_data['customer_id'].nunique() if 'customer_id' in sales_data.columns else 0
    
    return {
        'total_revenue': total_revenue,
        'avg_order_value': round(avg_order_value, 2),
        'customer_count': customer_count,
        'orders': order_count,
        'roi': 0  # Will be calculated from campaign_performance table
    }

def generate_campaign_recommendations(sales_df):
    """Generate campaign optimization recommendations."""
    recommendations = []
    
    if sales_df.empty:
        return recommendations
    
    # Analyze by customer segment
    if 'segment' in sales_df.columns:
        segment_sales = sales_df.groupby('segment')['sales'].sum()
        top_segment = segment_sales.idxmax()
        recommendations.append(f"Focus campaigns on {top_segment} segment (highest revenue: ₹{segment_sales[top_segment]:,.0f}).")
    
    # Analyze by region
    if 'region' in sales_df.columns:
        region_sales = sales_df.groupby('region')['sales'].sum()
        top_region = region_sales.idxmax()
        bottom_region = region_sales.idxmin()
        recommendations.append(f"Increase marketing spend in {top_region}; strengthen presence in {bottom_region}.")
    
    # Analyze by category
    if 'category' in sales_df.columns:
        category_sales = sales_df.groupby('category')['sales'].sum()
        top_category = category_sales.idxmax()
        recommendations.append(f"High-performing category: {top_category}. Create targeted promotions.")
    
    # Product performance
    if 'product' in sales_df.columns:
        product_count = sales_df['product'].nunique()
        if product_count > 10:
            top_products = sales_df.groupby('product')['sales'].sum().nlargest(3)
            recommendations.append(f"Bundle top 3 products ({', '.join(top_products.index)}) for cross-sell campaigns.")
    
    # Customer acquisition
    new_customers_ratio = sales_df['customer_id'].nunique() / max(len(sales_df), 1)
    if new_customers_ratio < 0.2:
        recommendations.append("Low customer diversity - increase acquisition campaigns to reach new customers.")
    
    return recommendations

def calculate_customer_ltv(sales_df):
    """Calculate customer lifetime value."""
    if sales_df.empty or 'customer_id' not in sales_df.columns or 'sales' not in sales_df.columns:
        return 0
    
    customer_revenue = sales_df.groupby('customer_id')['sales'].sum()
    return round(customer_revenue.mean(), 2)

def calculate_churn_indicators(sales_df):
    """Calculate indicators of customer churn."""
    if sales_df.empty or 'order_date' not in sales_df.columns or 'customer_id' not in sales_df.columns:
        return {}
    
    # Group by customer and get last purchase date
    customer_last_purchase = sales_df.groupby('customer_id')['order_date'].max()
    
    # Assume 90-day period for churn detection
    from datetime import datetime, timedelta
    cutoff_date = pd.to_datetime(sales_df['order_date'].max()) - timedelta(days=90)
    
    churned = (customer_last_purchase < cutoff_date).sum()
    active = (customer_last_purchase >= cutoff_date).sum()
    
    total_customers = len(customer_last_purchase)
    churn_rate = (churned / total_customers * 100) if total_customers > 0 else 0
    
    return {
        'active_customers': active,
        'churned_customers': churned,
        'total_customers': total_customers,
        'churn_rate': round(churn_rate, 2)
    }

def analyze_channel_performance(campaign_data):
    """Analyze performance by marketing channel."""
    if campaign_data.empty or 'channel' not in campaign_data.columns:
        return pd.DataFrame()
    
    channel_metrics = campaign_data.groupby('channel').agg({
        'impressions': 'sum',
        'clicks': 'sum',
        'conversions': 'sum',
        'revenue': 'sum',
        'cost': 'sum'
    }).reset_index()
    
    # Calculate channel-specific KPIs
    channel_metrics['ctr'] = (channel_metrics['clicks'] / channel_metrics['impressions'] * 100).round(2)
    channel_metrics['conversion_rate'] = (channel_metrics['conversions'] / channel_metrics['clicks'] * 100).round(2)
    channel_metrics['cpc'] = (channel_metrics['cost'] / channel_metrics['clicks']).round(2)
    channel_metrics['roi'] = ((channel_metrics['revenue'] - channel_metrics['cost']) / channel_metrics['cost'] * 100).round(2)
    
    return channel_metrics.sort_values('roi', ascending=False)
