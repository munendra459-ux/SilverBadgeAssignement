"""Statistical analysis and anomaly detection."""
import pandas as pd
import numpy as np
from datetime import timedelta

def detect_sales_anomalies(sales_df, window=7):
    """Detect anomalies in daily sales using moving average + std dev."""
    if sales_df.empty or 'order_date' not in sales_df.columns or 'sales' not in sales_df.columns:
        return pd.DataFrame()
    
    # Group by date
    daily_sales = sales_df.groupby(pd.to_datetime(sales_df['order_date']).dt.date)['sales'].sum()
    daily_sales.index = pd.to_datetime(daily_sales.index)
    
    # Calculate moving average and std dev
    ma = daily_sales.rolling(window=window, center=True).mean()
    std = daily_sales.rolling(window=window, center=True).std()
    
    # Define anomalies as > 2 std dev from mean
    upper_bound = ma + (2 * std)
    lower_bound = ma - (2 * std)
    
    anomalies = pd.DataFrame({
        'date': daily_sales.index,
        'sales': daily_sales.values,
        'moving_avg': ma.values,
        'upper_bound': upper_bound.values,
        'lower_bound': lower_bound.values,
        'is_anomaly': (daily_sales.values > upper_bound.values) | (daily_sales.values < lower_bound.values)
    })
    
    return anomalies[anomalies['is_anomaly']].reset_index(drop=True)

def calculate_trend(sales_df, period_days=30):
    """Calculate sales trend using linear regression."""
    if sales_df.empty or 'order_date' not in sales_df.columns or 'sales' not in sales_df.columns:
        return {}
    
    # Filter recent data
    recent_date = pd.to_datetime(sales_df['order_date']).max() - timedelta(days=period_days)
    recent_sales = sales_df[pd.to_datetime(sales_df['order_date']) >= recent_date]
    
    if len(recent_sales) < 2:
        return {'trend': 'insufficient_data', 'slope': 0, 'r_squared': 0}
    
    # Group by date
    daily_sales = recent_sales.groupby(pd.to_datetime(recent_sales['order_date']).dt.normalize())['sales'].sum()
    # Include calendar days with no transactions so the slope is genuinely per day.
    daily_sales = daily_sales.asfreq('D', fill_value=0)
    
    # Simple linear regression
    x = np.arange(len(daily_sales))
    y = daily_sales.values
    
    # Calculate coefficients
    n = len(x)
    x_mean = x.mean()
    y_mean = y.mean()
    
    numerator = ((x - x_mean) * (y - y_mean)).sum()
    denominator = ((x - x_mean) ** 2).sum()
    
    if denominator == 0:
        return {'trend': 'flat', 'slope': 0, 'r_squared': 0, 'period_days': period_days}
    
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    
    # Calculate R-squared
    ss_tot = ((y - y_mean) ** 2).sum()
    ss_res = ((y - (slope * x + intercept)) ** 2).sum()
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    trend = 'uptrend' if slope > 0 else 'downtrend' if slope < 0 else 'flat'
    
    return {
        'trend': trend,
        'slope': round(float(slope), 2),
        'r_squared': round(float(r_squared), 3),
        'period_days': period_days,
        'interpretation': f"{trend.replace('_', ' ').title()}: ₹{slope:.0f} per day change"
    }

def identify_seasonality(sales_df):
    """Identify seasonal patterns in sales."""
    if sales_df.empty or 'order_date' not in sales_df.columns or 'sales' not in sales_df.columns:
        return {}
    
    # Compare total revenue for each calendar month across years, not individual order lines.
    dated_sales = sales_df[["order_date", "sales"]].copy()
    dated_sales["order_date"] = pd.to_datetime(dated_sales["order_date"])
    monthly_totals = dated_sales.set_index("order_date")["sales"].resample("MS").sum()
    monthly_avg = monthly_totals.groupby(monthly_totals.index.month).mean()
    
    if len(monthly_avg) < 3:
        return {'seasonality': 'insufficient_data'}
    
    # Find peak and trough months
    peak_month = monthly_avg.idxmax()
    trough_month = monthly_avg.idxmin()
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    seasonality_ratio = monthly_avg.max() / max(monthly_avg.min(), 1)
    
    return {
        'peak_month': months[peak_month - 1],
        'peak_sales': round(float(monthly_avg.max()), 2),
        'trough_month': months[trough_month - 1],
        'trough_sales': round(float(monthly_avg.min()), 2),
        'seasonality_ratio': round(float(seasonality_ratio), 2),
        'interpretation': f"Sales peak in {months[peak_month - 1]} (₹{monthly_avg.max():.0f}) and trough in {months[trough_month - 1]} (₹{monthly_avg.min():.0f})"
    }

def forecast_sales(sales_df, periods=30):
    """Simple sales forecast using exponential smoothing."""
    if sales_df.empty or 'order_date' not in sales_df.columns or 'sales' not in sales_df.columns:
        return []
    
    # Group by date
    daily_sales = sales_df.groupby(pd.to_datetime(sales_df['order_date']).dt.date)['sales'].sum()
    
    if len(daily_sales) < 3:
        return []
    
    # Simple exponential smoothing
    alpha = 0.3
    forecast = []
    last_value = daily_sales.iloc[-1]
    
    for _ in range(periods):
        forecast.append(last_value)
    
    return forecast

def analyze_product_velocity(sales_df):
    """Analyze product sales velocity and performance."""
    if sales_df.empty or 'product' not in sales_df.columns or 'sales' not in sales_df.columns:
        return pd.DataFrame()
    
    product_stats = sales_df.groupby('product').agg({
        'sales': ['sum', 'mean', 'count'],
        'quantity': 'sum'
    }).round(2)
    
    product_stats.columns = ['total_revenue', 'avg_order_value', 'order_count', 'units_sold']
    product_stats['velocity'] = product_stats['order_count'] / max(product_stats['order_count'].sum(), 1)
    product_stats = product_stats.sort_values('total_revenue', ascending=False)
    
    return product_stats.reset_index()

def calculate_growth_rate(sales_df, periods=12):
    """Calculate period-over-period growth rate."""
    if sales_df.empty or 'order_date' not in sales_df.columns or 'sales' not in sales_df.columns:
        return []
    
    monthly_sales = sales_df.set_index('order_date').resample('MS')['sales'].sum()
    
    if len(monthly_sales) < 2:
        return []
    
    growth_rates = monthly_sales.pct_change().dropna() * 100
    
    return [{
        'month': date.strftime('%Y-%m'),
        'growth_rate': round(rate, 2)
    } for date, rate in growth_rates.items()]

def calculate_statistical_summary(sales_df):
    """Generate comprehensive statistical summary."""
    if sales_df.empty or 'sales' not in sales_df.columns:
        return {}
    
    sales_values = sales_df['sales']
    
    return {
        'mean': round(float(sales_values.mean()), 2),
        'median': round(float(sales_values.median()), 2),
        'std_dev': round(float(sales_values.std()), 2),
        'min': round(float(sales_values.min()), 2),
        'max': round(float(sales_values.max()), 2),
        'q1': round(float(sales_values.quantile(0.25)), 2),
        'q3': round(float(sales_values.quantile(0.75)), 2),
        'coefficient_of_variation': round(float(sales_values.std() / sales_values.mean()), 2) if sales_values.mean() != 0 else 0
    }
