"""Competitor and market analysis."""
import pandas as pd
from src.database import get_competitors, get_market_trends, insert_competitor, insert_market_trend

def analyze_market_position(sales_df, category):
    """Analyze your market position relative to competitors."""
    competitors = get_competitors(category)
    market_trends = get_market_trends(category)
    
    if sales_df.empty or 'sales' not in sales_df.columns:
        return {}
    
    your_revenue = sales_df['sales'].sum()
    your_avg_rating = 0
    if 'rating' in sales_df.columns:
        your_avg_rating = sales_df['rating'].mean()
    
    your_avg_price = sales_df['sales'].mean() if 'sales' in sales_df.columns else 0
    
    analysis = {
        'your_metrics': {
            'total_revenue': your_revenue,
            'avg_price': round(your_avg_price, 2),
            'avg_rating': round(your_avg_rating, 2),
            'category': category
        },
        'competitors': competitors.to_dict('records') if not competitors.empty else [],
        'market_trends': market_trends.to_dict('records') if not market_trends.empty else []
    }
    
    if not competitors.empty:
        total_market_revenue = competitors['market_share'].sum() * your_revenue / 100 if competitors['market_share'].sum() > 0 else 0
        analysis['your_market_share'] = (your_revenue / max(total_market_revenue + your_revenue, 1)) * 100
    
    return analysis

def generate_competitive_recommendations(sales_df, category):
    """Generate recommendations based on competitive analysis."""
    analysis = analyze_market_position(sales_df, category)
    recommendations = []
    
    your_metrics = analysis.get('your_metrics', {})
    competitors = analysis.get('competitors', [])
    
    if not competitors:
        return recommendations
    
    competitors_df = pd.DataFrame(competitors)
    
    # Price competitiveness
    if 'avg_price' in competitors_df.columns:
        comp_avg_price = competitors_df['avg_price'].mean()
        your_price = your_metrics.get('avg_price', 0)
        if your_price > comp_avg_price * 1.2:
            recommendations.append(f"Your price is {((your_price/comp_avg_price - 1)*100):.0f}% higher than competitors. Consider adjusting pricing.")
        elif your_price < comp_avg_price * 0.8:
            recommendations.append(f"Your pricing is competitive. Maintain quality to sustain margin advantage.")
    
    # Rating comparison
    if 'avg_rating' in competitors_df.columns:
        comp_avg_rating = competitors_df['avg_rating'].mean()
        your_rating = your_metrics.get('avg_rating', 0)
        if your_rating < comp_avg_rating:
            recommendations.append(f"Improve customer satisfaction (your rating {your_rating:.1f} vs competitor avg {comp_avg_rating:.1f}).")
    
    # Market share
    if 'your_market_share' in analysis:
        market_share = analysis['your_market_share']
        if market_share < 15:
            recommendations.append("Low market share. Focus on differentiation and customer retention.")
        elif market_share > 30:
            recommendations.append("Strong market position. Invest in brand building and expansion.")
    
    return recommendations

def identify_market_opportunities(sales_df, market_trends_df):
    """Identify growth opportunities in the market."""
    opportunities = []
    
    if market_trends_df.empty:
        return opportunities
    
    # Identify high-growth segments
    growth = market_trends_df.groupby('category')['growth_rate'].mean().sort_values(ascending=False)
    
    if not growth.empty:
        top_growth = growth.index[0]
        if sales_df.empty or top_growth not in sales_df.get('category', pd.Series()).values:
            opportunities.append(f"Opportunity: Enter high-growth category '{top_growth}' (growth: {growth[top_growth]:.1f}%)")
    
    # Identify underserved segments
    if not sales_df.empty and 'category' in sales_df.columns:
        your_categories = sales_df['category'].unique()
        market_categories = market_trends_df['category'].unique()
        
        underserved = set(market_categories) - set(your_categories)
        for category in list(underserved)[:3]:
            cat_growth = market_trends_df[market_trends_df['category'] == category]['growth_rate'].mean()
            if cat_growth > 5:
                opportunities.append(f"Expansion opportunity: '{category}' (market growth: {cat_growth:.1f}%)")
    
    return opportunities

def analyze_pricing_elasticity(sales_df):
    """Analyze price elasticity of demand."""
    if sales_df.empty or 'sales' not in sales_df.columns:
        return {}
    
    # Simple price elasticity proxy: correlation between price and quantity
    if 'quantity' not in sales_df.columns or 'sales' not in sales_df.columns:
        return {'elasticity_estimate': 0, 'recommendation': 'Insufficient data'}
    
    price_per_unit = sales_df['sales'] / (sales_df['quantity'] + 0.001)
    correlation = price_per_unit.corr(sales_df['quantity'])
    
    return {
        'price_elasticity_proxy': round(correlation, 2),
        'recommendation': 'Inelastic (hold prices)' if correlation > -0.3 else 'Elastic (reduce prices for volume)',
        'analysis': f"Correlation between price and quantity: {correlation:.2f}"
    }

def generate_market_summary(sales_df, category):
    """Generate a comprehensive market summary."""
    analysis = analyze_market_position(sales_df, category)
    opportunities = identify_market_opportunities(sales_df, pd.DataFrame(analysis.get('market_trends', [])))
    elasticity = analyze_pricing_elasticity(sales_df)
    
    summary = {
        'market_position': analysis,
        'opportunities': opportunities,
        'pricing_elasticity': elasticity,
        'recommendation': generate_competitive_recommendations(sales_df, category)
    }
    
    return summary
