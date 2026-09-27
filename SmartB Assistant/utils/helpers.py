def report(df, metrics, findings, actions):
    return f"# SmartB Business Report\n\n**Period:** {df.order_date.min():%d %b %Y} – {df.order_date.max():%d %b %Y}\n\n## KPIs\n"+"\n".join(f"- {k}: {v}" for k,v in metrics.items())+"\n\n## Insights\n"+"\n".join(f"- {x}" for x in findings)+"\n\n## Actions\n"+"\n".join(f"- {x}" for x in actions)
