"""UI Styler for Streamlit: Premium Aesthetic UI overrides."""

from __future__ import annotations

def apply_premium_styling() -> None:
    """Inject premium CSS to override default Streamlit styling."""
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global Typography & Font */
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif !important;
    }

    /* Overall Background and Text Colors */
    .stApp {
        background-color: #0d0e15; /* Deep cyber dark */
        color: #e2e8f0;
    }

    /* Primary Action Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.3s ease-in-out !important;
        box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.39) !important;
    }

    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px 0 rgba(99, 102, 241, 0.6) !important;
        filter: brightness(1.1);
    }

    /* Secondary Action Buttons */
    .stButton > button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.05) !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
        backdrop-filter: blur(10px);
    }

    .stButton > button[kind="secondary"]:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }

    /* Glassmorphism Containers (Inputs, Expanders, sidebars) */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
        background-color: rgba(30, 41, 59, 0.7) !important;
        border: 1px solid rgba(148, 163, 184, 0.2) !important;
        border-radius: 8px !important;
        color: #f8fafc !important;
        backdrop-filter: blur(8px);
        transition: border 0.2s ease;
    }

    .stTextInput>div>div>input:focus, .stSelectbox>div>div>div:focus {
        border: 1px solid #6366f1 !important;
        box-shadow: 0 0 0 1px #6366f1 !important;
    }

    [data-testid="stSidebar"] {
        background-color: #111827 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: rgba(30, 41, 59, 0.5);
        border-radius: 8px 8px 0px 0px;
        color: #94a3b8;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(99, 102, 241, 0.15) !important;
        color: #818cf8 !important;
        border-bottom: 2px solid #818cf8 !important;
    }

    /* Metric Cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #c084fc !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 1rem !important;
        color: #94a3b8 !important;
    }

    /* Custom scrollbars */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #0f172a; 
    }
    ::-webkit-scrollbar-thumb {
        background: #334155; 
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #475569; 
    }
    
    /* Progress Bars */
    .stProgress .st-bo {
        background-color: #312e81 !important;
    }
    .stProgress .st-bp {
        background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%) !important;
    }
    </style>
    """
    import streamlit as st
    st.markdown(css, unsafe_allow_html=True)
