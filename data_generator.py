import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import random

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

def generate_revops_data():
    """Generate realistic RevOps data simulating Salesforce + Planhat"""
    
    # --- ACCOUNTS (Planhat-style customer data) ---
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
        'contract_start': [datetime(2023, 1, 1) + timedelta(days=random.randint(0, 365)) for _ in range(30)],
        'contract_end': [datetime(2025, 1, 1) + timedelta(days=random.randint(0, 365)) for _ in range(30)],
        'health_score': np.random.randint(20, 100, 30),
        'last_login_days': np.random.randint(1, 120, 30),
        'support_tickets': np.random.randint(0, 15, 30),
        'nps_score': np.random.randint(1, 10, 30),
        'csm_owner': np.random.choice(['Alice Johnson', 'Bob Smith', 'Carol White', 'David Brown'], 30),
        'status': np.random.choice(['Active', 'At Risk', 'Churned', 'New'], 30, p=[0.6, 0.2, 0.1, 0.1])
    })
    
    # --- OPPORTUNITIES (Salesforce-style pipeline data) ---
    stages = ['Prospecting', 'Qualification', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost']
    stage_probabilities = [0.15, 0.20, 0.25, 0.20, 0.12, 0.08]
    
    opportunities = pd.DataFrame({
        'opp_id': [f'OPP{str(i).zfill(4)}' for i in range(1, 51)],
        'account_id': np.random.choice(accounts['account_id'], 50),
        'opp_name': [f'Deal - {random.choice(companies)} Q{random.randint(1,4)} 2025' for _ in range(50)],
        'stage': np.random.choice(stages, 50, p=stage_probabilities),
        'amount': np.random.randint(5000, 200000, 50),
        'close_date': [datetime(2025, 1, 1) + timedelta(days=random.randint(-60, 180)) for _ in range(50)],
        'created_date': [datetime(2024, 6, 1) + timedelta(days=random.randint(0, 300)) for _ in range(50)],
        'last_activity_date': [datetime(2025, 5, 1) + timedelta(days=random.randint(-90, 60)) for _ in range(50)],
        'owner': np.random.choice(['James Wilson', 'Sarah Connor', 'Mike Davis', 'Emma Thompson'], 50),
        'probability': np.random.randint(10, 95, 50),
        'lead_source': np.random.choice(['Inbound', 'Outbound', 'Referral', 'Partner', 'Event'], 50),
        'next_step': np.random.choice(['Follow up call', 'Send proposal', 'Demo scheduled', 'Contract review', None], 50)
    })
    
    # Introduce data quality issues for pipeline hygiene demo
    # Missing next steps for some open deals
    open_mask = ~opportunities['stage'].isin(['Closed Won', 'Closed Lost'])
    opportunities.loc[open_mask.sample(8).index, 'next_step'] = None
    
    # Stale deals - no activity in 30+ days
    stale_indices = opportunities.sample(7).index
    opportunities.loc[stale_indices, 'last_activity_date'] = datetime(2025, 3, 1)
    
    # --- ACTIVITIES (call logs, emails) ---
    activities = pd.DataFrame({
        'activity_id': [f'ACT{str(i).zfill(4)}' for i in range(1, 101)],
        'opp_id': np.random.choice(opportunities['opp_id'], 100),
        'activity_type': np.random.choice(['Call', 'Email', 'Meeting', 'Demo', 'Follow-up'], 100),
        'date': [datetime(2025, 1, 1) + timedelta(days=random.randint(0, 180)) for _ in range(100)],
        'owner': np.random.choice(['James Wilson', 'Sarah Connor', 'Mike Davis', 'Emma Thompson'], 100),
        'outcome': np.random.choice(['Positive', 'Neutral', 'No Response', 'Negative'], 100, p=[0.4, 0.3, 0.2, 0.1]),
        'notes': np.random.choice([
            'Client interested in Q3 renewal',
            'Demo went well, sending proposal',
            'No response to follow up',
            'Contract under legal review',
            'Escalation required',
            'Budget approved',
            'Decision maker changed',
            None
        ], 100)
    })
    
    # --- REVENUE (monthly MRR data) ---
    months = pd.date_range(start='2024-01-01', end='2025-06-01', freq='MS')
    revenue = pd.DataFrame({
        'month': months,
        'mrr': [45000, 47000, 49500, 51000, 53000, 55500,
                58000, 61000, 63500, 66000, 68000, 71000,
                73500, 76000, 78500, 80000, 82500, 85000],
        'new_mrr': np.random.randint(3000, 8000, len(months)),
        'churned_mrr': np.random.randint(500, 3000, len(months)),
        'expansion_mrr': np.random.randint(1000, 5000, len(months)),
        'customers': np.random.randint(25, 35, len(months))
    })
    
    return accounts, opportunities, activities, revenue


def setup_database():
    """Create SQLite database with all RevOps tables"""
    conn = sqlite3.connect('revops.db')
    
    accounts, opportunities, activities, revenue = generate_revops_data()
    
    # Convert dates to strings for SQLite
    opportunities['close_date'] = opportunities['close_date'].astype(str)
    opportunities['created_date'] = opportunities['created_date'].astype(str)
    opportunities['last_activity_date'] = opportunities['last_activity_date'].astype(str)
    accounts['contract_start'] = accounts['contract_start'].astype(str)
    accounts['contract_end'] = accounts['contract_end'].astype(str)
    activities['date'] = activities['date'].astype(str)
    revenue['month'] = revenue['month'].astype(str)
    
    # Write to SQLite
    accounts.to_sql('accounts', conn, if_exists='replace', index=False)
    opportunities.to_sql('opportunities', conn, if_exists='replace', index=False)
    activities.to_sql('activities', conn, if_exists='replace', index=False)
    revenue.to_sql('revenue', conn, if_exists='replace', index=False)
    
    conn.close()
    print("✅ Database created successfully!")
    print(f"   - {len(accounts)} accounts")
    print(f"   - {len(opportunities)} opportunities")
    print(f"   - {len(activities)} activities")
    print(f"   - {len(revenue)} months of revenue data")
    
    return accounts, opportunities, activities, revenue


if __name__ == "__main__":
    setup_database()