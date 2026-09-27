"""Scheduled report generation."""
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from src.database import save_report
from utils.helpers import report as generate_report_text
from src.analytics import metrics
from src.insights import insights
from src.recommendations import actions

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def _period_sales(sales, period_days):
    """Select the final calendar period present in a dataset.

    Using the latest dataset date, rather than today's date, makes historical
    uploads and reproducible reports work as users expect.
    """
    if sales.empty or "order_date" not in sales.columns:
        return sales.copy()
    dates = pd.to_datetime(sales["order_date"])
    end = dates.max().normalize()
    start = end - timedelta(days=period_days - 1)
    return sales.loc[dates.between(start, end)].copy()

def ensure_reports_dir():
    """Ensure reports directory exists."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def generate_weekly_report(sales, reviews, findings=None, actions_list=None):
    """Generate a weekly business report."""
    ensure_reports_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = REPORTS_DIR / f"weekly_report_{timestamp}.md"
    
    sales = _period_sales(sales, 7)
    sales_metrics = metrics(sales)
    insights_list = insights(sales)
    recommendations = actions(sales, insights_list)
    
    report_text = generate_report_text(sales, sales_metrics, insights_list, recommendations)
    report_text = f"# Weekly Report - {datetime.now().strftime('%Y-%m-%d')}\n\n" + report_text
    
    with open(filename, 'w') as f:
        f.write(report_text)
    
    save_report('weekly', 'weekly', str(filename))
    return str(filename)

def generate_monthly_report(sales, reviews, findings=None, actions_list=None):
    """Generate a monthly business report."""
    ensure_reports_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = REPORTS_DIR / f"monthly_report_{timestamp}.md"
    
    sales = _period_sales(sales, 30)
    sales_metrics = metrics(sales)
    insights_list = insights(sales)
    recommendations = actions(sales, insights_list)
    
    report_text = generate_report_text(sales, sales_metrics, insights_list, recommendations)
    report_text = f"# Monthly Report - {datetime.now().strftime('%Y-%m-%d')}\n\n" + report_text
    
    with open(filename, 'w') as f:
        f.write(report_text)
    
    save_report('monthly', 'monthly', str(filename))
    return str(filename)

def generate_custom_period_report(sales, reviews, period_days=30, findings=None, actions_list=None):
    """Generate a report for a custom period."""
    ensure_reports_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = REPORTS_DIR / f"custom_report_{period_days}d_{timestamp}.md"
    
    sales = _period_sales(sales, period_days)
    sales_metrics = metrics(sales)
    insights_list = insights(sales)
    recommendations = actions(sales, insights_list)
    
    report_text = generate_report_text(sales, sales_metrics, insights_list, recommendations)
    report_text = f"# Custom Report ({period_days} days) - {datetime.now().strftime('%Y-%m-%d')}\n\n" + report_text
    
    with open(filename, 'w') as f:
        f.write(report_text)
    
    save_report('custom', f'custom_{period_days}d', str(filename))
    return str(filename)

def get_report_history(limit=20):
    """Get list of recently generated reports."""
    ensure_reports_dir()
    reports = []
    for report_file in sorted(REPORTS_DIR.glob('*.md'), reverse=True)[:limit]:
        reports.append({
            'filename': report_file.name,
            'path': str(report_file),
            'created': datetime.fromtimestamp(report_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),
            'size_kb': report_file.stat().st_size / 1024
        })
    return reports
