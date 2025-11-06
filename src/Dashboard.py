#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Streamlit pour monitoring du bot
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from pathlib import Path
import json
import time

# Configuration
st.set_page_config(
    page_title="Base Trading Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Utiliser le chemin relatif au projet
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / 'data' / 'trading.db'
CONFIG_PATH = PROJECT_DIR / 'config' / 'trading_mode.json'

def get_connection():
    """Crée une connexion DB"""
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def get_trading_mode():
    """Récupère le mode de trading actuel"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f).get('mode', 'paper')
    return 'paper'

def set_trading_mode(mode):
    """Change le mode de trading"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump({'mode': mode, 'updated_at': datetime.now().isoformat()}, f)

# Titre principal
st.title("🤖 Base Trading Bot")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Mode de trading
    current_mode = get_trading_mode()
    new_mode = st.selectbox(
        "Mode de Trading",
        ["paper", "real"],
        index=0 if current_mode == "paper" else 1
    )
    
    if new_mode != current_mode:
        if st.button("Changer le mode"):
            set_trading_mode(new_mode)
            st.success(f"Mode changé en {new_mode}")
            st.rerun()
    
    # Affichage du mode actuel
    if current_mode == "paper":
        st.info("📝 Mode PAPER (Simulation)")
    else:
        st.warning("⚠️ Mode RÉEL (Production)")
    
    # Rafraîchissement auto
    auto_refresh = st.checkbox("Rafraîchissement auto (5s)", value=True)
    
    if auto_refresh:
        time.sleep(5)
        st.rerun()

# Métriques principales
col1, col2, col3, col4 = st.columns(4)

with col1:
    conn = get_connection()
    tokens_discovered = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM discovered_tokens", conn
    ).iloc[0]['count']
    st.metric("Tokens Découverts", tokens_discovered)

with col2:
    tokens_approved = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM approved_tokens", conn
    ).iloc[0]['count']
    st.metric("Tokens Approuvés", tokens_approved)

with col3:
    # Compter les positions actives en cherchant les BUY sans SELL correspondant
    active_positions = pd.read_sql_query("""
        SELECT COUNT(DISTINCT token_address) as count 
        FROM trade_history 
        WHERE side = 'BUY' 
        AND token_address NOT IN (
            SELECT token_address FROM trade_history WHERE side = 'SELL'
        )
    """, conn).iloc[0]['count']
    st.metric("Positions Actives", active_positions)

with col4:
    total_trades = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM trade_history WHERE side = 'SELL'", conn
    ).iloc[0]['count']
    st.metric("Trades Complétés", total_trades)

# Tabs principaux
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Positions Actives", "📈 Performance", "🎯 Tokens Approuvés", 
     "📜 Historique", "⚙️ Configuration"]
)

with tab1:
    st.header("Positions Actives")
    
    # Récupérer les positions actives depuis les fichiers JSON
    positions_data = []
    position_files = list((PROJECT_DIR / 'data').glob('position_*.json'))
    
    for pos_file in position_files:
        try:
            with open(pos_file, 'r') as f:
                pos_data = json.load(f)
                positions_data.append({
                    'Symbol': pos_data.get('symbol', 'Unknown'),
                    'Prix Entrée': f"${pos_data.get('entry_price', 0):.8f}",
                    'Prix Stop': f"${pos_data.get('stop_loss', 0):.8f}",
                    'Niveau': pos_data.get('current_level', 0),
                    'Trailing Actif': '✅' if pos_data.get('trailing_active') else '❌',
                    'Entrée': pos_data.get('entry_time', 'Unknown')
                })
        except Exception as e:
            st.error(f"Erreur lecture position: {e}")
    
    if positions_data:
        positions_df = pd.DataFrame(positions_data)
        st.dataframe(positions_df, use_container_width=True)
    else:
        st.info("Aucune position active")

with tab2:
    st.header("Performance")
    
    # Graphique des profits par jour
    profits_df = pd.read_sql_query("""
        SELECT 
            DATE(timestamp) as date,
            AVG(profit_loss) as avg_profit,
            COUNT(*) as trades
        FROM trade_history
        WHERE side = 'SELL' AND profit_loss IS NOT NULL
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        LIMIT 30
    """, conn)
    
    if not profits_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=profits_df['date'],
            y=profits_df['avg_profit'],
            name='Profit moyen %',
            marker_color=['green' if x > 0 else 'red' for x in profits_df['avg_profit']]
        ))
        fig.update_layout(title="Performance Quotidienne", height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Statistiques globales
    col1, col2, col3 = st.columns(3)
    
    stats = pd.read_sql_query("""
        SELECT 
            COUNT(*) as total_trades,
            COUNT(CASE WHEN profit_loss > 0 THEN 1 END) as winning_trades,
            AVG(profit_loss) as avg_profit,
            MAX(profit_loss) as best_trade,
            MIN(profit_loss) as worst_trade
        FROM trade_history
        WHERE side = 'SELL'
    """, conn)
    
    if not stats.empty and stats.iloc[0]['total_trades'] > 0:
        row = stats.iloc[0]
        with col1:
            win_rate = (row['winning_trades'] / row['total_trades'] * 100)
            st.metric("Win Rate", f"{win_rate:.1f}%")
        with col2:
            st.metric("Profit Moyen", f"{row['avg_profit']:.2f}%")
        with col3:
            st.metric("Meilleur Trade", f"+{row['best_trade']:.1f}%")

with tab3:
    st.header("Tokens Approuvés en Attente")
    
    approved_df = pd.read_sql_query("""
        SELECT 
            at.symbol,
            at.liquidity_usd,
            at.volume_24h,
            at.holders,
            at.risk_score,
            at.approved_at
        FROM approved_tokens at
        WHERE at.address NOT IN (
            SELECT DISTINCT token_address FROM trade_history WHERE side = 'BUY'
        )
        ORDER BY at.risk_score ASC, at.approved_at DESC
        LIMIT 20
    """, conn)
    
    if not approved_df.empty:
        # Formater l'affichage
        approved_df['liquidity_usd'] = approved_df['liquidity_usd'].apply(lambda x: f"${x:,.0f}")
        approved_df['volume_24h'] = approved_df['volume_24h'].apply(lambda x: f"${x:,.0f}")
        approved_df.columns = ['Symbol', 'Liquidité', 'Volume 24h', 'Holders', 'Score Risque', 'Approuvé']
        st.dataframe(approved_df, use_container_width=True)
    else:
        st.info("Aucun token en attente")

with tab4:
    st.header("Historique des Trades")
    
    # Afficher les derniers trades
    history_df = pd.read_sql_query("""
        SELECT 
            th.symbol,
            th.side,
            th.price,
            th.amount_in,
            th.amount_out,
            th.profit_loss,
            th.timestamp
        FROM trade_history th
        ORDER BY th.timestamp DESC
        LIMIT 50
    """, conn)
    
    if not history_df.empty:
        # Formater l'affichage
        history_df['price'] = history_df['price'].apply(lambda x: f"${x:.8f}" if x else "N/A")
        history_df['profit_loss'] = history_df['profit_loss'].apply(lambda x: f"{x:.2f}%" if x else "N/A")
        history_df.columns = ['Symbol', 'Side', 'Prix', 'In', 'Out', 'P&L', 'Date']
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("Aucun historique disponible")

with tab5:
    st.header("Configuration Avancée")
    
    # Afficher la configuration actuelle depuis trading_config
    st.subheader("Paramètres de Trading")
    
    config_df = pd.read_sql_query("""
        SELECT key, value FROM trading_config
        ORDER BY key
    """, conn)
    
    if not config_df.empty:
        # Organiser par catégorie
        scanner_config = config_df[config_df['key'].str.startswith('MAX_BLOCKS') | 
                                  config_df['key'].str.startswith('SCAN')]
        filter_config = config_df[config_df['key'].str.startswith('MIN_') | 
                                config_df['key'].str.startswith('MAX_')]
        trader_config = config_df[config_df['key'].str.startswith('POSITION') | 
                                config_df['key'].str.startswith('STOP') |
                                config_df['key'].str.startswith('TRAILING') |
                                config_df['key'].str.startswith('TIME')]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**Scanner**")
            for _, row in scanner_config.iterrows():
                st.text(f"{row['key']}: {row['value']}")
        
        with col2:
            st.write("**Filter**")
            for _, row in filter_config[:5].iterrows():
                st.text(f"{row['key']}: {row['value']}")
        
        with col3:
            st.write("**Trader**")
            for _, row in trader_config[:5].iterrows():
                st.text(f"{row['key']}: {row['value']}")
    
    # Statistiques des niveaux de trailing
    st.subheader("Statistiques Trailing Stop")
    
    trailing_stats = pd.read_sql_query("""
        SELECT 
            token_address,
            level,
            activation_price,
            stop_loss_price,
            timestamp
        FROM trailing_level_stats
        ORDER BY timestamp DESC
        LIMIT 20
    """, conn)
    
    if not trailing_stats.empty:
        st.dataframe(trailing_stats, use_container_width=True)
    else:
        st.info("Aucune statistique de trailing disponible")

conn.close()

# Footer
st.markdown("---")
st.markdown("Base Trading Bot - Stratégie Unique avec Trailing Stop Dynamique")
