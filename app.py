import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from groq import Groq
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="AI RevOps Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .alert-box {
        background: #fff3cd;
        border: 1px solid #ffc107;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #28a745;
        padding: 10px;
        border-radius: 5px;
    }
    .chat-message {
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Database connection
def get_db_connection():
    return sqlite3.connect('revops.db')

def run_query(sql):
    """Execute SQL query and return DataFrame"""
    try:
        conn = get_db_connection()
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df, None
    except Exception as e:
        return None, str(e)

def get_schema():
    """Get database schema for AI context"""
    schema = """
    DATABASE SCHEMA:
    
    1. accounts (account_id, company_name, industry, contract_value, contract_start, 
       contract_end, health_score, last_login_days, support_tickets, nps_score, 
       csm_owner, status)
       - status values: 'Active', 'At Risk', 'Churned', 'New'
       - health_score: 0-100 (higher is better)
    
    2. opportunities (opp_id, account_id, opp_name, stage, amount, close_date, 
       created_date, last_activity_date, owner, probability, lead_source, next_step)
       - stage values: 'Prospecting', 'Qualification', 'Proposal', 'Negotiation', 
         'Closed Won', 'Closed Lost'
    
    3. activities (activity_id, opp_id, activity_type, date, owner, outcome, notes)
       - activity_type: 'Call', 'Email', 'Meeting', 'Demo', 'Follow-up'
       - outcome: 'Positive', 'Neutral', 'No Response', 'Negative'
    
    4. revenue (month, mrr, new_mrr, churned_mrr, expansion_mrr, customers)
       - mrr: Monthly Recurring Revenue
    """
    return schema

def generate_sql_from_question(question):
    """Use Groq to convert natural language to SQL"""
    schema = get_schema()
    
    prompt = f"""You are a RevOps data analyst. Convert the user's question to a SQLite SQL query.

{schema}

RULES:
- Return ONLY the SQL query, nothing else
- No markdown, no backticks, no explanation
- Use proper SQLite syntax
- Keep queries simple and efficient
- For date comparisons use string comparison (dates stored as 'YYYY-MM-DD HH:MM:SS')

User question: {question}

SQL Query:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500
    )
    
    return response.choices[0].message.content.strip()

def generate_insight(question, data_summary):
    """Generate AI insight from query results"""
    prompt = f"""You are a Revenue Operations analyst at a SaaS company. 
    
A user asked: "{question}"

The data shows: {data_summary}

Provide a concise, actionable insight in 2-3 sentences. Focus on:
- What the data means for the business
- Any risks or opportunities
- A specific recommended action

Be direct and business-focused. No bullet points, just clear prose."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200
    )
    
    return response.choices[0].message.content.strip()

def run_pipeline_hygiene():
    """Automated pipeline hygiene checks"""
    alerts = []
    
    # Check 1: Stale deals (no activity in 30+ days)
    df, _ = run_query("""
        SELECT opp_name, owner, stage, amount, last_activity_date
        FROM opportunities 
        WHERE stage NOT IN ('Closed Won', 'Closed Lost')
        AND date(last_activity_date) < date('now', '-30 days')
        ORDER BY last_activity_date ASC
    """)
    if df is not None and len(df) > 0:
        alerts.append({
            'type': 'warning',
            'title': f'🕐 {len(df)} Stale Deals (No activity 30+ days)',
            'data': df
        })
    
    # Check 2: Missing next steps
    df2, _ = run_query("""
        SELECT opp_name, owner, stage, amount
        FROM opportunities 
        WHERE stage NOT IN ('Closed Won', 'Closed Lost')
        AND (next_step IS NULL OR next_step = '')
    """)
    if df2 is not None and len(df2) > 0:
        alerts.append({
            'type': 'warning',
            'title': f'📋 {len(df2)} Deals Missing Next Steps',
            'data': df2
        })
    
    # Check 3: At-risk accounts
    df3, _ = run_query("""
        SELECT company_name, health_score, last_login_days, 
               support_tickets, csm_owner, contract_value
        FROM accounts 
        WHERE health_score < 40 OR last_login_days > 60
        ORDER BY health_score ASC
    """)
    if df3 is not None and len(df3) > 0:
        alerts.append({
            'type': 'danger',
            'title': f'⚠️ {len(df3)} At-Risk Accounts (Low health score or inactive)',
            'data': df3
        })
    
    # Check 4: Overdue close dates
    df4, _ = run_query("""
        SELECT opp_name, owner, stage, amount, close_date
        FROM opportunities
        WHERE stage NOT IN ('Closed Won', 'Closed Lost')
        AND date(close_date) < date('now')
        ORDER BY close_date ASC
    """)
    if df4 is not None and len(df4) > 0:
        alerts.append({
            'type': 'danger',
            'title': f'📅 {len(df4)} Deals with Overdue Close Dates',
            'data': df4
        })
    
    return alerts

# ============================================================
# MAIN APP
# ============================================================

# Header
st.markdown("""
<div class="main-header">
    <h1>🤖 AI RevOps Copilot</h1>
    <p>Conversational Revenue Operations Analytics | Pipeline Intelligence | Real-time Insights</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=80)
    st.title("Navigation")
    
    page = st.radio("", [
        "💬 AI Copilot Chat",
        "📊 Pipeline Dashboard", 
        "🔍 Pipeline Hygiene",
        "👥 Account Health",
        "📈 Revenue Analytics"
    ])
    
    st.divider()
    st.caption("Built with LangChain + Groq/Llama 3.3")
    st.caption("Simulating Salesforce + Planhat Data")

# ============================================================
# PAGE 1: AI COPILOT CHAT
# ============================================================
if page == "💬 AI Copilot Chat":
    st.header("💬 AI Revenue Operations Copilot")
    st.caption("Ask me anything about your pipeline, accounts, revenue or activities")
    
    # Example questions
    with st.expander("💡 Example questions you can ask"):
        examples = [
            "Show me all deals in the negotiation stage",
            "Which accounts have a health score below 50?",
            "What is our total pipeline value by stage?",
            "Who are the top performing sales reps by deal value?",
            "Show me revenue trend for the last 6 months",
            "Which deals are closing this month?",
            "How many churned accounts do we have?",
            "Show me all at-risk accounts with their contract values",
            "What is our win rate?",
            "Which lead source generates the most revenue?"
        ]
        for ex in examples:
            if st.button(f"→ {ex}", key=ex):
                st.session_state['question'] = ex
    
    # Chat history
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    
    # Display chat history
    for chat in st.session_state['chat_history']:
        with st.chat_message("user"):
            st.write(chat['question'])
        with st.chat_message("assistant"):
            st.write(f"**SQL Generated:** `{chat['sql']}`")
            if chat['data'] is not None:
                st.dataframe(chat['data'], use_container_width=True)
            if chat['insight']:
                st.info(f"💡 **AI Insight:** {chat['insight']}")
    
    # Chat input
    question = st.chat_input("Ask about your pipeline, accounts, or revenue...")
    
    # Handle example button clicks
    if 'question' in st.session_state:
        question = st.session_state.pop('question')
    
    if question:
        with st.chat_message("user"):
            st.write(question)
        
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                # Generate SQL
                sql = generate_sql_from_question(question)
                st.write(f"**SQL Generated:** `{sql}`")
                
                # Execute SQL
                df, error = run_query(sql)
                
                if error:
                    st.error(f"Query error: {error}")
                    insight = None
                elif df is not None and len(df) > 0:
                    st.dataframe(df, use_container_width=True)
                    
                    # Generate insight
                    data_summary = df.head(5).to_string()
                    insight = generate_insight(question, data_summary)
                    st.info(f"💡 **AI Insight:** {insight}")
                    
                    # Auto-visualise if numeric data available
                    numeric_cols = df.select_dtypes(include='number').columns.tolist()
                    if len(numeric_cols) > 0 and len(df) > 1:
                        cat_cols = df.select_dtypes(include='object').columns.tolist()
                        if cat_cols and numeric_cols:
                            fig = px.bar(
                                df.head(15), 
                                x=cat_cols[0], 
                                y=numeric_cols[0],
                                title=f"{question}",
                                color_discrete_sequence=['#667eea']
                            )
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No data found for this query.")
                    insight = None
                
                # Save to history
                st.session_state['chat_history'].append({
                    'question': question,
                    'sql': sql,
                    'data': df,
                    'insight': insight
                })

# ============================================================
# PAGE 2: PIPELINE DASHBOARD
# ============================================================
elif page == "📊 Pipeline Dashboard":
    st.header("📊 Pipeline Dashboard")
    
    # KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_pipeline, _ = run_query("SELECT SUM(amount) as total FROM opportunities WHERE stage NOT IN ('Closed Won', 'Closed Lost')")
    closed_won, _ = run_query("SELECT SUM(amount) as total FROM opportunities WHERE stage = 'Closed Won'")
    open_deals, _ = run_query("SELECT COUNT(*) as count FROM opportunities WHERE stage NOT IN ('Closed Won', 'Closed Lost')")
    win_rate, _ = run_query("SELECT ROUND(COUNT(CASE WHEN stage='Closed Won' THEN 1 END) * 100.0 / COUNT(*), 1) as rate FROM opportunities WHERE stage IN ('Closed Won', 'Closed Lost')")
    
    with col1:
        val = total_pipeline['total'].iloc[0] if total_pipeline is not None else 0
        st.metric("Total Pipeline", f"£{val:,.0f}")
    with col2:
        val = closed_won['total'].iloc[0] if closed_won is not None else 0
        st.metric("Closed Won", f"£{val:,.0f}")
    with col3:
        val = open_deals['count'].iloc[0] if open_deals is not None else 0
        st.metric("Open Deals", f"{val}")
    with col4:
        val = win_rate['rate'].iloc[0] if win_rate is not None else 0
        st.metric("Win Rate", f"{val}%")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pipeline by stage
        stage_data, _ = run_query("""
            SELECT stage, COUNT(*) as deals, SUM(amount) as value
            FROM opportunities
            GROUP BY stage
            ORDER BY value DESC
        """)
        if stage_data is not None:
            fig = px.funnel(
                stage_data,
                x='value',
                y='stage',
                title='Pipeline by Stage (£)',
                color_discrete_sequence=['#667eea']
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Pipeline by owner
        owner_data, _ = run_query("""
            SELECT owner, SUM(amount) as total_value, COUNT(*) as deals
            FROM opportunities
            WHERE stage NOT IN ('Closed Won', 'Closed Lost')
            GROUP BY owner
            ORDER BY total_value DESC
        """)
        if owner_data is not None:
            fig = px.bar(
                owner_data,
                x='owner',
                y='total_value',
                title='Pipeline by Sales Rep (£)',
                color='deals',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        # Lead source analysis
        lead_data, _ = run_query("""
            SELECT lead_source, COUNT(*) as deals, SUM(amount) as value
            FROM opportunities
            GROUP BY lead_source
            ORDER BY value DESC
        """)
        if lead_data is not None:
            fig = px.pie(
                lead_data,
                values='value',
                names='lead_source',
                title='Pipeline by Lead Source',
                color_discrete_sequence=px.colors.sequential.Purples_r
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        # Deals closing this month
        closing_data, _ = run_query("""
            SELECT opp_name, owner, stage, amount, close_date
            FROM opportunities
            WHERE stage NOT IN ('Closed Won', 'Closed Lost')
            ORDER BY close_date ASC
            LIMIT 10
        """)
        if closing_data is not None:
            st.subheader("🎯 Upcoming Closes")
            st.dataframe(closing_data, use_container_width=True)

# ============================================================
# PAGE 3: PIPELINE HYGIENE
# ============================================================
elif page == "🔍 Pipeline Hygiene":
    st.header("🔍 Pipeline Hygiene Checker")
    st.caption("Automated data quality checks across your revenue pipeline")
    
    if st.button("🔄 Run Hygiene Check", type="primary"):
        with st.spinner("Running pipeline hygiene checks..."):
            alerts = run_pipeline_hygiene()
            
            if not alerts:
                st.success("✅ Pipeline is clean! No issues found.")
            else:
                st.error(f"⚠️ Found {len(alerts)} hygiene issues that need attention")
                
                for alert in alerts:
                    with st.expander(alert['title'], expanded=True):
                        st.dataframe(alert['data'], use_container_width=True)
                        
                        # AI recommendation for each issue
                        with st.spinner("Getting AI recommendation..."):
                            rec = generate_insight(
                                f"How should we address: {alert['title']}?",
                                alert['data'].head(3).to_string()
                            )
                            st.info(f"💡 **AI Recommendation:** {rec}")
    
    # Data quality score
    st.divider()
    st.subheader("📊 Data Quality Score")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        missing_next, _ = run_query("SELECT COUNT(*) as c FROM opportunities WHERE next_step IS NULL AND stage NOT IN ('Closed Won','Closed Lost')")
        total_open, _ = run_query("SELECT COUNT(*) as c FROM opportunities WHERE stage NOT IN ('Closed Won','Closed Lost')")
        if missing_next is not None and total_open is not None:
            score = 100 - (missing_next['c'].iloc[0] / max(total_open['c'].iloc[0], 1) * 100)
            st.metric("Next Step Completion", f"{score:.0f}%")
    
    with col2:
        stale, _ = run_query("SELECT COUNT(*) as c FROM opportunities WHERE stage NOT IN ('Closed Won','Closed Lost') AND date(last_activity_date) < date('now','-30 days')")
        if stale is not None and total_open is not None:
            score = 100 - (stale['c'].iloc[0] / max(total_open['c'].iloc[0], 1) * 100)
            st.metric("Activity Freshness", f"{score:.0f}%")
    
    with col3:
        healthy_accounts, _ = run_query("SELECT COUNT(*) as c FROM accounts WHERE health_score >= 60")
        total_accounts, _ = run_query("SELECT COUNT(*) as c FROM accounts")
        if healthy_accounts is not None and total_accounts is not None:
            score = healthy_accounts['c'].iloc[0] / max(total_accounts['c'].iloc[0], 1) * 100
            st.metric("Account Health Rate", f"{score:.0f}%")

# ============================================================
# PAGE 4: ACCOUNT HEALTH
# ============================================================
elif page == "👥 Account Health":
    st.header("👥 Account Health Monitor")
    st.caption("Planhat-style customer health tracking and churn risk analysis")
    
    # Health overview
    col1, col2, col3, col4 = st.columns(4)
    
    active, _ = run_query("SELECT COUNT(*) as c FROM accounts WHERE status='Active'")
    at_risk, _ = run_query("SELECT COUNT(*) as c FROM accounts WHERE status='At Risk'")
    churned, _ = run_query("SELECT COUNT(*) as c FROM accounts WHERE status='Churned'")
    avg_health, _ = run_query("SELECT ROUND(AVG(health_score),1) as avg FROM accounts")
    
    with col1:
        st.metric("Active Accounts", active['c'].iloc[0] if active is not None else 0, delta="↑ Healthy")
    with col2:
        st.metric("At Risk", at_risk['c'].iloc[0] if at_risk is not None else 0, delta="Needs attention", delta_color="inverse")
    with col3:
        st.metric("Churned", churned['c'].iloc[0] if churned is not None else 0, delta_color="inverse")
    with col4:
        st.metric("Avg Health Score", f"{avg_health['avg'].iloc[0] if avg_health is not None else 0}/100")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Health score distribution
        health_dist, _ = run_query("""
            SELECT 
                CASE 
                    WHEN health_score >= 80 THEN 'Healthy (80-100)'
                    WHEN health_score >= 60 THEN 'Good (60-79)'
                    WHEN health_score >= 40 THEN 'At Risk (40-59)'
                    ELSE 'Critical (0-39)'
                END as health_band,
                COUNT(*) as accounts,
                SUM(contract_value) as arr
            FROM accounts
            GROUP BY health_band
            ORDER BY arr DESC
        """)
        if health_dist is not None:
            fig = px.bar(
                health_dist,
                x='health_band',
                y='arr',
                title='ARR by Health Band (£)',
                color='health_band',
                color_discrete_map={
                    'Healthy (80-100)': '#28a745',
                    'Good (60-79)': '#17a2b8',
                    'At Risk (40-59)': '#ffc107',
                    'Critical (0-39)': '#dc3545'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Churn risk scatter
        accounts_data, _ = run_query("""
            SELECT company_name, health_score, last_login_days, 
                   contract_value, status, support_tickets
            FROM accounts
            ORDER BY health_score ASC
        """)
        if accounts_data is not None:
            fig = px.scatter(
                accounts_data,
                x='last_login_days',
                y='health_score',
                size='contract_value',
                color='status',
                hover_name='company_name',
                title='Churn Risk Matrix (Health vs Login Activity)',
                color_discrete_map={
                    'Active': '#28a745',
                    'At Risk': '#ffc107',
                    'Churned': '#dc3545',
                    'New': '#17a2b8'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # At-risk accounts table
    st.subheader("⚠️ Accounts Requiring Immediate Attention")
    at_risk_data, _ = run_query("""
        SELECT company_name, health_score, last_login_days, 
               support_tickets, nps_score, csm_owner, 
               contract_value, status
        FROM accounts
        WHERE health_score < 50 OR last_login_days > 45 OR status = 'At Risk'
        ORDER BY health_score ASC
    """)
    if at_risk_data is not None:
        st.dataframe(at_risk_data, use_container_width=True)
        
        if st.button("🤖 Get AI Action Plan"):
            with st.spinner("Generating action plan..."):
                insight = generate_insight(
                    "What actions should the CS team take for these at-risk accounts?",
                    at_risk_data.head(5).to_string()
                )
                st.info(f"💡 **AI Action Plan:** {insight}")

# ============================================================
# PAGE 5: REVENUE ANALYTICS
# ============================================================
elif page == "📈 Revenue Analytics":
    st.header("📈 Revenue Analytics")
    st.caption("MRR trends, growth analysis and forecasting")
    
    # Revenue KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    latest_mrr, _ = run_query("SELECT mrr FROM revenue ORDER BY month DESC LIMIT 1")
    total_new, _ = run_query("SELECT SUM(new_mrr) as total FROM revenue")
    total_churn, _ = run_query("SELECT SUM(churned_mrr) as total FROM revenue")
    avg_growth, _ = run_query("""
        SELECT ROUND(AVG((mrr - lag_mrr) * 100.0 / lag_mrr), 1) as growth
        FROM (
            SELECT mrr, LAG(mrr) OVER (ORDER BY month) as lag_mrr FROM revenue
        )
        WHERE lag_mrr IS NOT NULL
    """)
    
    with col1:
        val = latest_mrr['mrr'].iloc[0] if latest_mrr is not None else 0
        st.metric("Latest MRR", f"£{val:,.0f}")
    with col2:
        val = total_new['total'].iloc[0] if total_new is not None else 0
        st.metric("Total New MRR", f"£{val:,.0f}")
    with col3:
        val = total_churn['total'].iloc[0] if total_churn is not None else 0
        st.metric("Total Churned MRR", f"£{val:,.0f}", delta_color="inverse")
    with col4:
        val = avg_growth['growth'].iloc[0] if avg_growth is not None else 0
        st.metric("Avg Monthly Growth", f"{val}%")
    
    st.divider()
    
    # MRR Trend
    revenue_data, _ = run_query("SELECT * FROM revenue ORDER BY month")
    
    if revenue_data is not None:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.line(
                revenue_data,
                x='month',
                y='mrr',
                title='MRR Growth Trend (£)',
                markers=True,
                color_discrete_sequence=['#667eea']
            )
            fig.update_traces(fill='tozeroy', fillcolor='rgba(102,126,234,0.1)')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = go.Figure()
            fig.add_trace(go.Bar(name='New MRR', x=revenue_data['month'], y=revenue_data['new_mrr'], marker_color='#28a745'))
            fig.add_trace(go.Bar(name='Expansion MRR', x=revenue_data['month'], y=revenue_data['expansion_mrr'], marker_color='#17a2b8'))
            fig.add_trace(go.Bar(name='Churned MRR', x=revenue_data['month'], y=-revenue_data['churned_mrr'], marker_color='#dc3545'))
            fig.update_layout(title='MRR Waterfall by Month', barmode='relative')
            st.plotly_chart(fig, use_container_width=True)
        
        # Revenue by industry
        industry_rev, _ = run_query("""
            SELECT a.industry, SUM(a.contract_value) as total_arr, COUNT(*) as accounts
            FROM accounts a
            GROUP BY a.industry
            ORDER BY total_arr DESC
        """)
        
        if industry_rev is not None:
            fig = px.treemap(
                industry_rev,
                path=['industry'],
                values='total_arr',
                title='ARR by Industry',
                color='total_arr',
                color_continuous_scale='Purples'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # AI Revenue Insight
        if st.button("🤖 Get AI Revenue Analysis"):
            with st.spinner("Analysing revenue trends..."):
                insight = generate_insight(
                    "What are the key revenue trends and what should we focus on?",
                    revenue_data.tail(6).to_string()
                )
                st.info(f"💡 **AI Revenue Insight:** {insight}")

# Footer
st.divider()
st.caption("🤖 AI RevOps Copilot | Built with LangChain + Groq/Llama 3.3 + Streamlit | Vinit Bhalerao")