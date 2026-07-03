import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from groq import Groq
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import numpy as np
import random

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
</style>
""", unsafe_allow_html=True)

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ============================================================
# DATABASE SETUP — THREADING SAFE
# ============================================================

def get_fresh_connection():
    """Always create a fresh connection and reload data from session state"""
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    if 'db_data' in st.session_state:
        for table_name, df in st.session_state['db_data'].items():
            df.to_sql(table_name, conn, if_exists='replace', index=False)
    return conn

def run_query(sql):
    """Execute SQL query and return DataFrame"""
    try:
        if 'db_data' not in st.session_state:
            setup_sample_database()
        conn = get_fresh_connection()
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df, None
    except Exception as e:
        return None, str(e)

def setup_sample_database():
    """Create sample RevOps data and store as DataFrames in session state"""
    np.random.seed(42)
    random.seed(42)

    companies = [
        "TechCorp Ltd", "BuildRight UK", "FinanceHub", "RetailPro",
        "HealthNet", "EduSmart", "LogiTrack", "MediaFlow",
        "CloudBase", "GreenEnergy", "SafeGuard", "DataBridge",
        "PropManage", "InsureTech", "LegalEdge", "HRConnect",
        "SupplyChain Co", "MarketBoost", "DevOps Pro", "SalesForce UK",
        "Nexus Systems", "Apex Solutions", "Vertex Group", "Orbit Tech",
        "Pinnacle Corp", "Summit Digital", "Horizon Labs", "Catalyst UK",
        "Fusion Works", "Elevate Tech"
    ]

    accounts = pd.DataFrame({
        'account_id': [f'ACC{str(i).zfill(3)}' for i in range(1, 31)],
        'company_name': companies,
        'industry': np.random.choice(['Technology', 'Finance', 'Healthcare', 'Retail', 'Construction', 'Education'], 30),
        'contract_value': np.random.randint(5000, 150000, 30),
        'contract_start': [(datetime(2023, 1, 1) + timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d') for _ in range(30)],
        'contract_end': [(datetime(2025, 1, 1) + timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d') for _ in range(30)],
        'health_score': np.random.randint(20, 100, 30),
        'last_login_days': np.random.randint(1, 120, 30),
        'support_tickets': np.random.randint(0, 15, 30),
        'nps_score': np.random.randint(1, 10, 30),
        'csm_owner': np.random.choice(['Alice Johnson', 'Bob Smith', 'Carol White', 'David Brown'], 30),
        'status': np.random.choice(['Active', 'At Risk', 'Churned', 'New'], 30, p=[0.6, 0.2, 0.1, 0.1])
    })

    stages = ['Prospecting', 'Qualification', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost']
    stage_probabilities = [0.15, 0.20, 0.25, 0.20, 0.12, 0.08]

    opportunities = pd.DataFrame({
        'opp_id': [f'OPP{str(i).zfill(4)}' for i in range(1, 51)],
        'account_id': np.random.choice(accounts['account_id'], 50),
        'opp_name': [f'Deal - {random.choice(companies)} Q{random.randint(1,4)} 2025' for _ in range(50)],
        'stage': np.random.choice(stages, 50, p=stage_probabilities),
        'amount': np.random.randint(5000, 200000, 50),
        'close_date': [(datetime(2025, 1, 1) + timedelta(days=random.randint(-60, 180))).strftime('%Y-%m-%d') for _ in range(50)],
        'created_date': [(datetime(2024, 6, 1) + timedelta(days=random.randint(0, 300))).strftime('%Y-%m-%d') for _ in range(50)],
        'last_activity_date': [(datetime(2025, 5, 1) + timedelta(days=random.randint(-90, 60))).strftime('%Y-%m-%d') for _ in range(50)],
        'owner': np.random.choice(['James Wilson', 'Sarah Connor', 'Mike Davis', 'Emma Thompson'], 50),
        'probability': np.random.randint(10, 95, 50),
        'lead_source': np.random.choice(['Inbound', 'Outbound', 'Referral', 'Partner', 'Event'], 50),
        'next_step': np.random.choice(['Follow up call', 'Send proposal', 'Demo scheduled', 'Contract review', None], 50)
    })

    open_mask = ~opportunities['stage'].isin(['Closed Won', 'Closed Lost'])
    stale_indices = opportunities[open_mask].sample(min(8, open_mask.sum())).index
    opportunities.loc[stale_indices, 'next_step'] = None
    opportunities.loc[opportunities.sample(7).index, 'last_activity_date'] = '2025-03-01'

    activities = pd.DataFrame({
        'activity_id': [f'ACT{str(i).zfill(4)}' for i in range(1, 101)],
        'opp_id': np.random.choice(opportunities['opp_id'], 100),
        'activity_type': np.random.choice(['Call', 'Email', 'Meeting', 'Demo', 'Follow-up'], 100),
        'date': [(datetime(2025, 1, 1) + timedelta(days=random.randint(0, 180))).strftime('%Y-%m-%d') for _ in range(100)],
        'owner': np.random.choice(['James Wilson', 'Sarah Connor', 'Mike Davis', 'Emma Thompson'], 100),
        'outcome': np.random.choice(['Positive', 'Neutral', 'No Response', 'Negative'], 100, p=[0.4, 0.3, 0.2, 0.1]),
        'notes': np.random.choice(['Client interested in Q3 renewal', 'Demo went well', 'No response', 'Contract under review', None], 100)
    })

    months = pd.date_range(start='2024-01-01', end='2025-06-01', freq='MS')
    revenue = pd.DataFrame({
        'month': [m.strftime('%Y-%m-%d') for m in months],
        'mrr': [45000, 47000, 49500, 51000, 53000, 55500, 58000, 61000, 63500, 66000, 68000, 71000, 73500, 76000, 78500, 80000, 82500, 85000],
        'new_mrr': np.random.randint(3000, 8000, len(months)),
        'churned_mrr': np.random.randint(500, 3000, len(months)),
        'expansion_mrr': np.random.randint(1000, 5000, len(months)),
        'customers': np.random.randint(25, 35, len(months))
    })

    st.session_state['db_data'] = {
        'accounts': accounts,
        'opportunities': opportunities,
        'activities': activities,
        'revenue': revenue
    }
    st.session_state['data_mode'] = 'sample'
    st.session_state['tables'] = ['accounts', 'opportunities', 'activities', 'revenue']

def load_csv_to_db(uploaded_file):
    """Load uploaded CSV into session state as DataFrame"""
    try:
        df = pd.read_csv(uploaded_file)
        table_name = uploaded_file.name.replace('.csv', '').replace('-', '_').replace(' ', '_').lower()

        if 'db_data' not in st.session_state or st.session_state.get('data_mode') == 'sample':
            st.session_state['db_data'] = {}
            st.session_state['tables'] = []
            st.session_state['data_mode'] = 'csv'

        st.session_state['db_data'][table_name] = df

        if table_name not in st.session_state.get('tables', []):
            st.session_state['tables'] = st.session_state.get('tables', []) + [table_name]

        return df, table_name, None
    except Exception as e:
        return None, None, str(e)

def get_schema():
    """Get schema from current data"""
    if 'db_data' not in st.session_state:
        setup_sample_database()

    tables = st.session_state.get('tables', [])
    schema = "DATABASE SCHEMA:\n\n"

    for table in tables:
        try:
            df = st.session_state['db_data'][table]
            cols = ", ".join([f"{col} ({str(df[col].dtype)})" for col in df.columns])
            sample = df.head(1).to_dict('records')
            schema += f"Table: {table}\nColumns: {cols}\nSample: {sample}\n\n"
        except:
            pass

    return schema

def generate_sql_from_question(question):
    """Use Groq to convert natural language to SQL"""
    schema = get_schema()

    prompt = f"""You are a data analyst. Convert the user's question to a SQLite SQL query.

{schema}

RULES:
- Return ONLY the SQL query, nothing else
- No markdown, no backticks, no explanation
- Use proper SQLite syntax
- Use exact table and column names from the schema above

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

    df, _ = run_query("""
        SELECT opp_name, owner, stage, amount, last_activity_date
        FROM opportunities
        WHERE stage NOT IN ('Closed Won', 'Closed Lost')
        AND date(last_activity_date) < date('now', '-30 days')
        ORDER BY last_activity_date ASC
    """)
    if df is not None and len(df) > 0:
        alerts.append({'type': 'warning', 'title': f'🕐 {len(df)} Stale Deals (No activity 30+ days)', 'data': df})

    df2, _ = run_query("""
        SELECT opp_name, owner, stage, amount
        FROM opportunities
        WHERE stage NOT IN ('Closed Won', 'Closed Lost')
        AND (next_step IS NULL OR next_step = '')
    """)
    if df2 is not None and len(df2) > 0:
        alerts.append({'type': 'warning', 'title': f'📋 {len(df2)} Deals Missing Next Steps', 'data': df2})

    df3, _ = run_query("""
        SELECT company_name, health_score, last_login_days,
               support_tickets, csm_owner, contract_value
        FROM accounts
        WHERE health_score < 40 OR last_login_days > 60
        ORDER BY health_score ASC
    """)
    if df3 is not None and len(df3) > 0:
        alerts.append({'type': 'danger', 'title': f'⚠️ {len(df3)} At-Risk Accounts', 'data': df3})

    df4, _ = run_query("""
        SELECT opp_name, owner, stage, amount, close_date
        FROM opportunities
        WHERE stage NOT IN ('Closed Won', 'Closed Lost')
        AND date(close_date) < date('now')
        ORDER BY close_date ASC
    """)
    if df4 is not None and len(df4) > 0:
        alerts.append({'type': 'danger', 'title': f'📅 {len(df4)} Deals with Overdue Close Dates', 'data': df4})

    return alerts

# ============================================================
# AUTO LOAD SAMPLE DATA ON FIRST RUN
# ============================================================
if 'db_data' not in st.session_state:
    setup_sample_database()

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

    # Data Source Selection
    st.subheader("📂 Data Source")

    data_option = st.radio("Choose data source:", [
        "🎯 Use Sample RevOps Data",
        "📤 Upload Your Own CSV"
    ])

    if data_option == "🎯 Use Sample RevOps Data":
        if st.button("Load Sample Data", type="primary"):
            with st.spinner("Loading sample RevOps data..."):
                setup_sample_database()
                st.session_state['chat_history'] = []
                st.success("✅ Sample data loaded!")
                st.caption("30 accounts | 50 opportunities | 100 activities | 18 months MRR")

        if st.session_state.get('data_mode') == 'sample':
            st.success("✅ Sample data active")
            st.caption("Tables: accounts, opportunities, activities, revenue")

    else:
        st.caption("Upload one or multiple CSV files")
        uploaded_files = st.file_uploader(
            "Upload CSV file(s)",
            type=['csv'],
            accept_multiple_files=True,
            help="Each CSV becomes a queryable table"
        )

        if uploaded_files:
            for uploaded_file in uploaded_files:
                df, table_name, error = load_csv_to_db(uploaded_file)
                if error:
                    st.error(f"Error loading {uploaded_file.name}: {error}")
                else:
                    st.success(f"✅ {uploaded_file.name} → table: **{table_name}**")
                    st.caption(f"{len(df)} rows × {len(df.columns)} columns")

            if st.session_state.get('tables'):
                st.info(f"Active tables: {', '.join(st.session_state['tables'])}")

    st.divider()
    st.caption("Built with LangChain + Groq/Llama 3.3")
    st.caption("Simulating Salesforce + Planhat Data")

# ============================================================
# PAGE 1: AI COPILOT CHAT
# ============================================================
if page == "💬 AI Copilot Chat":
    st.header("💬 AI Revenue Operations Copilot")

    if st.session_state.get('data_mode') == 'csv':
        tables = st.session_state.get('tables', [])
        st.info(f"🗂️ Querying your uploaded data — Tables: {', '.join(tables)}")
    else:
        st.caption("Ask me anything about your pipeline, accounts, revenue or activities")

    with st.expander("💡 Example questions you can ask"):
        if st.session_state.get('data_mode') == 'csv':
            tables = st.session_state.get('tables', [])
            st.write(f"Your tables: **{', '.join(tables)}**")
            st.write("Try asking:")
            if tables:
                st.write(f"→ Show me all records from {tables[0]}")
                st.write(f"→ How many rows are in {tables[0]}?")
            st.write("→ Show me the top 10 rows")
            st.write("→ Show me summary statistics")
        else:
            examples = [
                "Show me all deals in the negotiation stage",
                "Which accounts have a health score below 50?",
                "What is our total pipeline value by stage?",
                "Who are the top performing sales reps by deal value?",
                "Show me revenue trend for the last 6 months",
                "Which deals are closing this month?",
                "How many churned accounts do we have?",
                "What is our win rate?",
                "Which lead source generates the most revenue?",
                "Show me at-risk accounts with their contract values"
            ]
            for ex in examples:
                if st.button(f"→ {ex}", key=ex):
                    st.session_state['question'] = ex

    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    for chat in st.session_state['chat_history']:
        with st.chat_message("user"):
            st.write(chat['question'])
        with st.chat_message("assistant"):
            st.write(f"**SQL Generated:** `{chat['sql']}`")
            if chat['data'] is not None:
                st.dataframe(chat['data'], use_container_width=True)
            if chat['insight']:
                st.info(f"💡 **AI Insight:** {chat['insight']}")

    question = st.chat_input("Ask about your data...")

    if 'question' in st.session_state:
        question = st.session_state.pop('question')

    if question:
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                sql = generate_sql_from_question(question)
                st.write(f"**SQL Generated:** `{sql}`")

                df, error = run_query(sql)

                if error:
                    st.error(f"Query error: {error}")
                    insight = None
                elif df is not None and len(df) > 0:
                    st.dataframe(df, use_container_width=True)

                    data_summary = df.head(5).to_string()
                    insight = generate_insight(question, data_summary)
                    st.info(f"💡 **AI Insight:** {insight}")

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

    if st.session_state.get('data_mode') == 'csv':
        st.warning("⚠️ Pipeline Dashboard works with sample RevOps data. Switch to sample data in the sidebar.")
    else:
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
            stage_data, _ = run_query("SELECT stage, COUNT(*) as deals, SUM(amount) as value FROM opportunities GROUP BY stage ORDER BY value DESC")
            if stage_data is not None:
                fig = px.funnel(stage_data, x='value', y='stage', title='Pipeline by Stage (£)', color_discrete_sequence=['#667eea'])
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            owner_data, _ = run_query("SELECT owner, SUM(amount) as total_value, COUNT(*) as deals FROM opportunities WHERE stage NOT IN ('Closed Won', 'Closed Lost') GROUP BY owner ORDER BY total_value DESC")
            if owner_data is not None:
                fig = px.bar(owner_data, x='owner', y='total_value', title='Pipeline by Sales Rep (£)', color='deals', color_continuous_scale='Viridis')
                st.plotly_chart(fig, use_container_width=True)

        col3, col4 = st.columns(2)

        with col3:
            lead_data, _ = run_query("SELECT lead_source, COUNT(*) as deals, SUM(amount) as value FROM opportunities GROUP BY lead_source ORDER BY value DESC")
            if lead_data is not None:
                fig = px.pie(lead_data, values='value', names='lead_source', title='Pipeline by Lead Source', color_discrete_sequence=px.colors.sequential.Purples_r)
                st.plotly_chart(fig, use_container_width=True)

        with col4:
            closing_data, _ = run_query("SELECT opp_name, owner, stage, amount, close_date FROM opportunities WHERE stage NOT IN ('Closed Won', 'Closed Lost') ORDER BY close_date ASC LIMIT 10")
            if closing_data is not None:
                st.subheader("🎯 Upcoming Closes")
                st.dataframe(closing_data, use_container_width=True)

# ============================================================
# PAGE 3: PIPELINE HYGIENE
# ============================================================
elif page == "🔍 Pipeline Hygiene":
    st.header("🔍 Pipeline Hygiene Checker")
    st.caption("Automated data quality checks across your revenue pipeline")

    if st.session_state.get('data_mode') == 'csv':
        st.warning("⚠️ Pipeline Hygiene works with sample RevOps data. Switch to sample data in the sidebar.")
    else:
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
                            with st.spinner("Getting AI recommendation..."):
                                rec = generate_insight(f"How should we address: {alert['title']}?", alert['data'].head(3).to_string())
                                st.info(f"💡 **AI Recommendation:** {rec}")

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

    if st.session_state.get('data_mode') == 'csv':
        st.warning("⚠️ Account Health works with sample RevOps data. Switch to sample data in the sidebar.")
    else:
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
            health_dist, _ = run_query("""
                SELECT CASE
                    WHEN health_score >= 80 THEN 'Healthy (80-100)'
                    WHEN health_score >= 60 THEN 'Good (60-79)'
                    WHEN health_score >= 40 THEN 'At Risk (40-59)'
                    ELSE 'Critical (0-39)'
                END as health_band, COUNT(*) as accounts, SUM(contract_value) as arr
                FROM accounts GROUP BY health_band ORDER BY arr DESC
            """)
            if health_dist is not None:
                fig = px.bar(health_dist, x='health_band', y='arr', title='ARR by Health Band (£)',
                    color='health_band', color_discrete_map={
                        'Healthy (80-100)': '#28a745', 'Good (60-79)': '#17a2b8',
                        'At Risk (40-59)': '#ffc107', 'Critical (0-39)': '#dc3545'})
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            accounts_data, _ = run_query("SELECT company_name, health_score, last_login_days, contract_value, status, support_tickets FROM accounts ORDER BY health_score ASC")
            if accounts_data is not None:
                fig = px.scatter(accounts_data, x='last_login_days', y='health_score', size='contract_value',
                    color='status', hover_name='company_name', title='Churn Risk Matrix',
                    color_discrete_map={'Active': '#28a745', 'At Risk': '#ffc107', 'Churned': '#dc3545', 'New': '#17a2b8'})
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("⚠️ Accounts Requiring Immediate Attention")
        at_risk_data, _ = run_query("SELECT company_name, health_score, last_login_days, support_tickets, nps_score, csm_owner, contract_value, status FROM accounts WHERE health_score < 50 OR last_login_days > 45 OR status = 'At Risk' ORDER BY health_score ASC")
        if at_risk_data is not None:
            st.dataframe(at_risk_data, use_container_width=True)
            if st.button("🤖 Get AI Action Plan"):
                with st.spinner("Generating action plan..."):
                    insight = generate_insight("What actions should the CS team take for these at-risk accounts?", at_risk_data.head(5).to_string())
                    st.info(f"💡 **AI Action Plan:** {insight}")

# ============================================================
# PAGE 5: REVENUE ANALYTICS
# ============================================================
elif page == "📈 Revenue Analytics":
    st.header("📈 Revenue Analytics")
    st.caption("MRR trends, growth analysis and forecasting")

    if st.session_state.get('data_mode') == 'csv':
        st.warning("⚠️ Revenue Analytics works with sample RevOps data. Switch to sample data in the sidebar.")
    else:
        col1, col2, col3, col4 = st.columns(4)

        latest_mrr, _ = run_query("SELECT mrr FROM revenue ORDER BY month DESC LIMIT 1")
        total_new, _ = run_query("SELECT SUM(new_mrr) as total FROM revenue")
        total_churn, _ = run_query("SELECT SUM(churned_mrr) as total FROM revenue")
        avg_growth, _ = run_query("SELECT ROUND(AVG((mrr - lag_mrr) * 100.0 / lag_mrr), 1) as growth FROM (SELECT mrr, LAG(mrr) OVER (ORDER BY month) as lag_mrr FROM revenue) WHERE lag_mrr IS NOT NULL")

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

        revenue_data, _ = run_query("SELECT * FROM revenue ORDER BY month")

        if revenue_data is not None:
            col1, col2 = st.columns(2)

            with col1:
                fig = px.line(revenue_data, x='month', y='mrr', title='MRR Growth Trend (£)', markers=True, color_discrete_sequence=['#667eea'])
                fig.update_traces(fill='tozeroy', fillcolor='rgba(102,126,234,0.1)')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = go.Figure()
                fig.add_trace(go.Bar(name='New MRR', x=revenue_data['month'], y=revenue_data['new_mrr'], marker_color='#28a745'))
                fig.add_trace(go.Bar(name='Expansion MRR', x=revenue_data['month'], y=revenue_data['expansion_mrr'], marker_color='#17a2b8'))
                fig.add_trace(go.Bar(name='Churned MRR', x=revenue_data['month'], y=-revenue_data['churned_mrr'], marker_color='#dc3545'))
                fig.update_layout(title='MRR Waterfall by Month', barmode='relative')
                st.plotly_chart(fig, use_container_width=True)

            industry_rev, _ = run_query("SELECT a.industry, SUM(a.contract_value) as total_arr, COUNT(*) as accounts FROM accounts a GROUP BY a.industry ORDER BY total_arr DESC")
            if industry_rev is not None:
                fig = px.treemap(industry_rev, path=['industry'], values='total_arr', title='ARR by Industry', color='total_arr', color_continuous_scale='Purples')
                st.plotly_chart(fig, use_container_width=True)

            if st.button("🤖 Get AI Revenue Analysis"):
                with st.spinner("Analysing revenue trends..."):
                    insight = generate_insight("What are the key revenue trends and what should we focus on?", revenue_data.tail(6).to_string())
                    st.info(f"💡 **AI Revenue Insight:** {insight}")

# Footer
st.divider()
st.caption("🤖 AI RevOps Copilot | Built with LangChain + Groq/Llama 3.3 + Streamlit | Vinit Bhalerao")