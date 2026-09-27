"""Inventory management and analysis."""
import pandas as pd
from src.database import get_inventory, insert_inventory

def analyze_inventory():
    """Analyze current inventory status."""
    inventory = get_inventory()
    if inventory.empty:
        return {
            'low_stock_items': pd.DataFrame(),
            'overstock_items': pd.DataFrame(),
            'total_value': 0,
            'total_items': 0,
            'avg_turnover': 0,
            'alerts': []
        }
    
    alerts = []
    
    # Identify low stock items
    low_stock = inventory[inventory['stock_quantity'] <= inventory['reorder_level']]
    if not low_stock.empty:
        for _, item in low_stock.iterrows():
            alerts.append(f"⚠️ Low stock: {item['product_name']} - {item['stock_quantity']} units (reorder at {item['reorder_level']})")
    
    # Identify overstock items
    overstock = inventory[inventory['stock_quantity'] > inventory['reorder_level'] * 3]
    if not overstock.empty:
        for _, item in overstock.iterrows():
            alerts.append(f"📦 Overstock: {item['product_name']} - {item['stock_quantity']} units")
    
    # Calculate inventory value
    inventory['item_value'] = inventory['stock_quantity'] * inventory['unit_cost']
    total_value = inventory['item_value'].sum()
    
    return {
        'low_stock_items': low_stock,
        'overstock_items': overstock,
        'total_value': total_value,
        'total_items': len(inventory),
        'alerts': alerts,
        'inventory_df': inventory
    }

def get_inventory_recommendations():
    """Generate inventory management recommendations."""
    analysis = analyze_inventory()
    recommendations = []
    
    low_stock = analysis['low_stock_items']
    overstock = analysis['overstock_items']
    
    if not low_stock.empty:
        recommendations.append(f"Reorder {len(low_stock)} product(s) with low stock to avoid stockouts.")
    
    if not overstock.empty:
        recommendations.append(f"Consider promotions or discounts for {len(overstock)} overstocked product(s).")
    
    total_value = analysis['total_value']
    if total_value > 100000:
        recommendations.append(f"Total inventory value is ₹{total_value:,.0f}. Monitor holding costs.")
    
    return recommendations

def get_inventory_by_category(sales_df):
    """Get inventory analysis by category."""
    inventory = get_inventory()
    if inventory.empty:
        return pd.DataFrame()
    
    return inventory.groupby('category').agg({
        'stock_quantity': 'sum',
        'item_value': 'sum',
        'product_id': 'count'
    }).rename(columns={'product_id': 'product_count'}).reset_index()

def get_slow_moving_items(sales_df, days=90):
    """Identify slow-moving inventory based on sales data."""
    if sales_df.empty or 'product_id' not in sales_df.columns:
        return pd.DataFrame()
    
    # Calculate sales velocity by product
    sales_by_product = sales_df.groupby('product_id').size().reset_index(name='sold_count')
    sales_by_product = sales_by_product.sort_values('sold_count')
    
    # Get products with low sales
    slow_movers = sales_by_product[sales_by_product['sold_count'] < sales_by_product['sold_count'].quantile(0.25)]
    
    inventory = get_inventory()
    if inventory.empty:
        return slow_movers
    
    result = slow_movers.merge(inventory[['product_id', 'product_name', 'category', 'stock_quantity']], 
                               on='product_id', how='left')
    return result.sort_values('sold_count')

def calculate_reorder_points(sales_df, lead_time_days=7):
    """Calculate optimal reorder points based on sales velocity."""
    if sales_df.empty or 'product_id' not in sales_df.columns:
        return pd.DataFrame()
    
    # Calculate daily sales velocity
    daily_sales = sales_df.groupby('product_id').size() / max((sales_df['order_date'].max() - sales_df['order_date'].min()).days, 1)
    
    # Reorder point = daily sales * lead time + safety stock
    safety_stock = daily_sales * 7  # 1 week safety stock
    reorder_points = (daily_sales * lead_time_days) + safety_stock
    
    return pd.DataFrame({
        'product_id': daily_sales.index,
        'daily_velocity': daily_sales.values,
        'reorder_point': reorder_points.values,
        'safety_stock': safety_stock.values
    })
