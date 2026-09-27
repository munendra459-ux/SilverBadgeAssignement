import os, re, math
from dataclasses import dataclass
from openai import OpenAI
from prompts.business_prompts import SYSTEM_PROMPT, prompt
import pandas as pd

def words(x):
    return set(re.findall(r"[a-zA-Z0-9]+", str(x).lower()))

@dataclass
class Answer:
    text: str
    sources: list
    mode: str
    confidence: float = 0.0

class RAG:
    def __init__(self, sales, reviews, stats=None):
        self.sales = sales
        self.reviews = reviews
        self.stats = stats or {}
        self.docs = []
        self._build_docs()
    
    def _build_docs(self):
        """Build document corpus from data."""
        # Monthly sales trend
        if 'order_date' in self.sales.columns and 'sales' in self.sales.columns:
            m = self.sales.set_index('order_date').resample('MS').sales.sum()
            self.docs += [f"Sales month {d:%Y-%m}: revenue ₹{v:,.0f}." for d, v in m.items()]
            
            # Monthly change detection
            if len(m) > 1:
                for i in range(1, len(m)):
                    change = (m.iloc[i] / m.iloc[i-1] - 1) * 100 if m.iloc[i-1] > 0 else 0
                    direction = "increased" if change > 0 else "decreased"
                    self.docs.append(f"Sales {direction} by {abs(change):.1f}% from {m.index[i-1]:%Y-%m} to {m.index[i]:%Y-%m}.")
        
        # Product performance
        if 'product' in self.sales.columns and 'sales' in self.sales.columns:
            prod_sales = self.sales.groupby('product')['sales'].sum().sort_values(ascending=False)
            self.docs += [f"Product {k}: total revenue ₹{v:,.0f}." for k, v in prod_sales.head(20).items()]
            
            # Top and bottom products
            if len(prod_sales) > 0:
                self.docs.append(f"Top product: {prod_sales.index[0]} (₹{prod_sales.iloc[0]:,.0f})")
                self.docs.append(f"Lowest product: {prod_sales.index[-1]} (₹{prod_sales.iloc[-1]:,.0f})")
        
        # Regional performance
        if 'region' in self.sales.columns and 'sales' in self.sales.columns:
            region_sales = self.sales.groupby('region')['sales'].sum().sort_values(ascending=False)
            self.docs += [f"Region {k}: revenue ₹{v:,.0f}." for k, v in region_sales.items()]
        
        # Category performance
        if 'category' in self.sales.columns and 'sales' in self.sales.columns:
            cat_sales = self.sales.groupby('category')['sales'].sum().sort_values(ascending=False)
            self.docs += [f"Category {k}: revenue ₹{v:,.0f}." for k, v in cat_sales.items()]
        
        # Profit analysis
        if 'profit' in self.sales.columns:
            total_profit = self.sales['profit'].sum()
            profit_margin = (total_profit / max(self.sales['sales'].sum(), 1)) * 100
            self.docs.append(f"Total profit: ₹{total_profit:,.0f} (margin: {profit_margin:.1f}%)")
        
        # Customer feedback
        if not self.reviews.empty and 'review_text' in self.reviews.columns:
            avg_rating = self.reviews['rating'].mean() if 'rating' in self.reviews.columns else 0
            self.docs.append(f"Average customer rating: {avg_rating:.1f}/5")
            self.docs += [f"Customer feedback (rating {r.rating}): {r.review_text[:200]}" 
                         for r in self.reviews.head(100).itertuples() 
                         if hasattr(r, 'review_text') and r.review_text]
    
    def retrieve(self, q):
        """Retrieve relevant documents using semantic similarity."""
        if not self.docs:
            return []
        
        if os.getenv("OPENAI_API_KEY"):
            try:
                client = OpenAI()
                response = client.embeddings.create(
                    model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
                    input=[q] + self.docs
                )
                query_vector = response.data[0].embedding
                ranked = sorted(
                    ((self._cosine(query_vector, item.embedding), doc) 
                     for item, doc in zip(response.data[1:], self.docs)),
                    reverse=True
                )
                return [d for score, d in ranked[:6]]
            except Exception:
                pass
        
        # Fallback to keyword matching
        w = words(q)
        ranked = sorted(
            ((len(w & words(d)) / math.sqrt(max(len(words(d)), 1)), d) 
             for d in self.docs),
            reverse=True
        )
        return [d for s, d in ranked[:6] if s] or self.docs[:6]
    
    @staticmethod
    def _cosine(left, right):
        """Calculate cosine similarity."""
        denominator = math.sqrt(sum(value * value for value in left) * sum(value * value for value in right))
        return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0

def validate_answer(question, answer_text, metrics, findings):
    """Validate answer consistency with known metrics and findings."""
    confidence = 0.5  # Base confidence
    
    # Check if answer references key metrics
    q_lower = question.lower()
    
    if any(term in q_lower for term in ['revenue', 'sales', 'income']):
        confidence += 0.2 if 'revenue' in answer_text.lower() or '₹' in answer_text else 0
    
    if any(term in q_lower for term in ['profit', 'margin', 'roi']):
        confidence += 0.2 if 'profit' in answer_text.lower() else 0
    
    if any(term in q_lower for term in ['customer', 'rating', 'review']):
        confidence += 0.2 if 'customer' in answer_text.lower() or 'rating' in answer_text.lower() else 0
    
    if any(term in q_lower for term in ['product', 'category']):
        confidence += 0.2 if 'product' in answer_text.lower() else 0
    
    # Cap confidence at 1.0
    return min(confidence, 1.0)

def ask(q, rag, summary, findings, sales=None, external_ai_enabled=False):
    """Answer business questions with validation."""
    sources = rag.retrieve(q)
    
    if not os.getenv("OPENAI_API_KEY") or not external_ai_enabled:
        # Local mode with improved logic
        answer_text = f"Based on your data: {' '.join(sources[:3])} "
        
        # Add metrics-based insights
        if summary:
            for key, value in summary.items():
                if any(term in q.lower() for term in key.lower().split()):
                    answer_text += f"\n{key}: {value}"
        
        # Add findings
        if findings:
            relevant_findings = [f for f in findings if any(term in q.lower() for term in f.lower().split())]
            if relevant_findings:
                answer_text += "\n" + "\n".join(relevant_findings[:2])
        
        answer_text += "\n\nNote: This answer is generated locally from the retrieved data summary."
        confidence = validate_answer(q, answer_text, summary or {}, findings or [])
        return Answer(answer_text, sources, "local", confidence)
    
    try:
        response = OpenAI().responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            instructions=SYSTEM_PROMPT,
            input=prompt(q, summary, sources, findings),
            store=False
        )
        answer_text = response.output_text if hasattr(response, 'output_text') else str(response)
        confidence = validate_answer(q, answer_text, summary or {}, findings or [])
        return Answer(answer_text, sources, "openai", confidence)
    except Exception as e:
        error_msg = f"LLM request failed: {str(e)}. Retrieved evidence: {' '.join(sources[:3])}"
        return Answer(error_msg, sources, "error", 0.3)
