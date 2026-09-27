SYSTEM_PROMPT="You are SmartB, a precise business analyst. Answer only from supplied evidence, never invent figures, and end with one practical next action."
def prompt(question, summary, evidence, findings): return f"KPIs: {summary}\nInsights: {findings}\nEvidence:\n"+"\n".join(evidence)+f"\nQuestion: {question}"
