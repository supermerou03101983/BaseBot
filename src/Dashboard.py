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
    
    # Rafraîchissement auto avec intervalle configurable
    auto_refresh = st.checkbox("Rafraîchissement auto", value=False)

    if auto_refresh:
        refresh_interval = st.selectbox(
            "Intervalle de rafraîchissement",
            options=[30, 60, 120, 300],
            format_func=lambda x: f"{x} secondes",
            index=1  # 60 secondes par défaut
        )
        # Utiliser st.empty pour créer un placeholder
        placeholder = st.empty()
        with placeholder:
            st.info(f"🔄 Prochain rafraîchissement dans {refresh_interval} secondes...")
        time.sleep(refresh_interval)
        placeholder.empty()
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
    # Compter les positions actives depuis les fichiers JSON (source de vérité)
    position_files_count = len(list((PROJECT_DIR / 'data').glob('position_*.json')))
    st.metric("Positions Actives", position_files_count)

with col4:
    # Compter les trades complétés (positions fermées)
    total_trades = pd.read_sql_query("""
        SELECT COUNT(*) as count
        FROM trade_history
        WHERE exit_time IS NOT NULL
    """, conn).iloc[0]['count']
    st.metric("Trades Complétés", total_trades)

# Tabs principaux
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Positions Actives", "📈 Performance", "🎯 Tokens Approuvés", 
     "📜 Historique", "⚙️ Configuration"]
)

with tab1:
    st.header("Positions Actives")

    # Compter les fichiers JSON (source de vérité)
    position_files = list((PROJECT_DIR / 'data').glob('position_*.json'))
    num_json_positions = len(position_files)

    # Compter dans la DB
    db_positions_count = pd.read_sql_query("""
        SELECT COUNT(*) as count FROM trade_history WHERE exit_time IS NULL
    """, conn).iloc[0]['count']

    # Afficher les compteurs avec avertissement si désynchronisé
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Positions en mémoire (JSON)", num_json_positions)
    with col_b:
        st.metric("Positions en base (DB)", db_positions_count)

    if num_json_positions != db_positions_count:
        st.warning(f"⚠️ Désynchronisation: {num_json_positions} fichiers JSON mais {db_positions_count} dans la DB. Redémarrez le Trader pour synchroniser.")

    # Récupérer les positions actives depuis les fichiers JSON
    positions_data = []

    for pos_file in position_files:
        try:
            with open(pos_file, 'r') as f:
                pos_data = json.load(f)

                # Calculer le profit actuel
                entry_price = pos_data.get('entry_price', 0)
                current_price = pos_data.get('current_price', entry_price)
                profit = 0
                if entry_price > 0:
                    profit = ((current_price - entry_price) / entry_price) * 100

                positions_data.append({
                    'Symbol': pos_data.get('symbol', 'Unknown'),
                    'Prix Entrée': f"${entry_price:.8f}",
                    'Prix Actuel': f"${current_price:.8f}",
                    'Profit': f"{profit:+.2f}%",
                    'Prix Stop': f"${pos_data.get('stop_loss', 0):.8f}",
                    'Niveau': pos_data.get('current_level', 0),
                    'Trailing': '✅' if pos_data.get('trailing_active') else '❌',
                    'Entrée': pos_data.get('entry_time', 'Unknown')
                })
        except Exception as e:
            st.error(f"Erreur lecture position {pos_file.name}: {e}")

    if positions_data:
        positions_df = pd.DataFrame(positions_data)
        st.dataframe(positions_df, use_container_width=True)
    else:
        st.info("Aucune position active")

with tab2:
    st.header("Performance")
    
    # Graphique des profits par jour (positions fermées uniquement)
    profits_df = pd.read_sql_query("""
        SELECT
            DATE(exit_time) as date,
            AVG(profit_loss) as avg_profit,
            COUNT(*) as trades
        FROM trade_history
        WHERE exit_time IS NOT NULL AND profit_loss IS NOT NULL
        GROUP BY DATE(exit_time)
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
        WHERE exit_time IS NOT NULL
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
            at.token_address,
            at.symbol,
            at.name,
            at.score,
            at.created_at
        FROM approved_tokens at
        WHERE at.token_address NOT IN (
            SELECT DISTINCT token_address FROM trade_history
        )
        ORDER BY at.score DESC, at.created_at DESC
        LIMIT 20
    """, conn)
    
    if not approved_df.empty:
        # Formater l'affichage
        approved_df['score'] = approved_df['score'].apply(lambda x: f"{x:.1f}")
        approved_df.columns = ['Adresse', 'Symbol', 'Nom', 'Score', 'Approuvé le']
        st.dataframe(approved_df, use_container_width=True)
    else:
        st.info("Aucun token en attente")

with tab4:
    st.header("Historique des Trades")

    # Afficher les derniers trades (fermés uniquement)
    history_df = pd.read_sql_query("""
        SELECT
            symbol,
            price as entry_price,
            amount_in,
            amount_out,
            profit_loss,
            entry_time,
            exit_time,
            ROUND((JULIANDAY(exit_time) - JULIANDAY(entry_time)) * 24, 1) as duration_hours
        FROM trade_history
        WHERE exit_time IS NOT NULL
        ORDER BY exit_time DESC
        LIMIT 50
    """, conn)

    if not history_df.empty:
        # Formater l'affichage
        history_df['entry_price'] = history_df['entry_price'].apply(lambda x: f"${x:.8f}" if x else "N/A")
        history_df['profit_loss'] = history_df['profit_loss'].apply(lambda x: f"{x:.2f}%" if x else "N/A")
        history_df['amount_in'] = history_df['amount_in'].apply(lambda x: f"{x:.4f}" if x else "N/A")
        history_df['amount_out'] = history_df['amount_out'].apply(lambda x: f"{x:.4f}" if x else "N/A")
        history_df['duration_hours'] = history_df['duration_hours'].apply(lambda x: f"{x:.1f}h" if x else "N/A")
        history_df.columns = ['Symbol', 'Prix Entrée', 'In (ETH)', 'Out (ETH)', 'P&L', 'Entrée', 'Sortie', 'Durée']
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("Aucun historique disponible")

with tab5:
    st.header("Configuration du Bot")

    # Lire la configuration depuis le fichier .env
    import os
    from pathlib import Path

    env_path = PROJECT_DIR / 'config' / '.env'
    config_data = {}

    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config_data[key.strip()] = value.strip()

    # Afficher les paramètres par catégorie
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 Stratégie de Trading")
        st.metric("Mode", config_data.get('TRADING_MODE', 'N/A').upper())
        st.metric("Taille Position", f"{config_data.get('POSITION_SIZE_PERCENT', 'N/A')}%")
        st.metric("Max Positions", config_data.get('MAX_POSITIONS', 'N/A'))
        st.metric("Max Trades/Jour", config_data.get('MAX_TRADES_PER_DAY', 'N/A'))
        st.metric("Stop Loss", f"-{config_data.get('STOP_LOSS_PERCENT', 'N/A')}%")
        st.metric("Expiration Tokens", f"{config_data.get('TOKEN_APPROVAL_MAX_AGE_HOURS', 'N/A')}h")

        st.subheader("🔍 Scanner")
        st.text(f"Intervalle: {config_data.get('SCAN_INTERVAL_SECONDS', 'N/A')}s")
        st.text(f"Max Blocks/Scan: {config_data.get('MAX_BLOCKS_PER_SCAN', 'N/A')}")

    with col2:
        st.subheader("📈 Trailing Stop")
        st.text(f"Activation: +{config_data.get('TRAILING_ACTIVATION_THRESHOLD', 'N/A')}%")

        st.markdown("**Niveaux:**")
        st.text(f"Niveau 1: {config_data.get('TRAILING_L1_MIN', 'N/A')}-{config_data.get('TRAILING_L1_MAX', 'N/A')}% → -{config_data.get('TRAILING_L1_DISTANCE', 'N/A')}%")
        st.text(f"Niveau 2: {config_data.get('TRAILING_L2_MIN', 'N/A')}-{config_data.get('TRAILING_L2_MAX', 'N/A')}% → -{config_data.get('TRAILING_L2_DISTANCE', 'N/A')}%")
        st.text(f"Niveau 3: {config_data.get('TRAILING_L3_MIN', 'N/A')}-{config_data.get('TRAILING_L3_MAX', 'N/A')}% → -{config_data.get('TRAILING_L3_DISTANCE', 'N/A')}%")
        st.text(f"Niveau 4: {config_data.get('TRAILING_L4_MIN', 'N/A')}%+ → -{config_data.get('TRAILING_L4_DISTANCE', 'N/A')}%")

        st.subheader("⏱️ Time Exit")
        st.text(f"Stagnation: {config_data.get('TIME_EXIT_STAGNATION_HOURS', 'N/A')}h si < {config_data.get('TIME_EXIT_STAGNATION_MIN_PROFIT', 'N/A')}%")
        st.text(f"Low Momentum: {config_data.get('TIME_EXIT_LOW_MOMENTUM_HOURS', 'N/A')}h si < {config_data.get('TIME_EXIT_LOW_MOMENTUM_MIN_PROFIT', 'N/A')}%")
        st.text(f"Maximum: {config_data.get('TIME_EXIT_MAXIMUM_HOURS', 'N/A')}h force exit")

    # Section Filter
    st.subheader("🎯 Critères de Filtrage")
    col3, col4, col5 = st.columns(3)

    with col3:
        st.markdown("**Âge & Volume**")
        st.text(f"Min Âge: {config_data.get('MIN_AGE_HOURS', 'N/A')}h")
        st.text(f"Min Volume 24h: ${config_data.get('MIN_VOLUME_24H', 'N/A')}")
        st.text(f"Min Liquidité: ${config_data.get('MIN_LIQUIDITY_USD', 'N/A')}")

    with col4:
        st.markdown("**Market Cap**")
        st.text(f"Min: ${config_data.get('MIN_MARKET_CAP', 'N/A')}")
        st.text(f"Max: ${config_data.get('MAX_MARKET_CAP', 'N/A')}")
        st.markdown("**Holders**")
        st.text(f"Min: {config_data.get('MIN_HOLDERS', 'N/A')}")

    with col5:
        st.markdown("**Taxes & Scores**")
        st.text(f"Max Buy Tax: {config_data.get('MAX_BUY_TAX', 'N/A')}%")
        st.text(f"Max Sell Tax: {config_data.get('MAX_SELL_TAX', 'N/A')}%")
        st.text(f"Min Safety Score: {config_data.get('MIN_SAFETY_SCORE', 'N/A')}")

    # Historique des trailing stops qui ont été déclenchés
    st.subheader("📊 Historique Trailing Stops Déclenchés")

    trailing_history = pd.read_sql_query("""
        SELECT
            th.symbol,
            th.entry_time,
            th.exit_time,
            th.profit_loss,
            ROUND((JULIANDAY(th.exit_time) - JULIANDAY(th.entry_time)) * 24, 1) as duration_hours,
            tls.level as trailing_level,
            tls.activation_price,
            tls.stop_loss_price
        FROM trade_history th
        LEFT JOIN trailing_level_stats tls ON th.token_address = tls.token_address
        WHERE th.exit_time IS NOT NULL
        AND tls.level IS NOT NULL
        ORDER BY th.exit_time DESC
        LIMIT 10
    """, conn)

    if not trailing_history.empty:
        trailing_history['profit_loss'] = trailing_history['profit_loss'].apply(lambda x: f"{x:.2f}%" if x else "N/A")
        trailing_history['activation_price'] = trailing_history['activation_price'].apply(lambda x: f"${x:.8f}" if x else "N/A")
        trailing_history['stop_loss_price'] = trailing_history['stop_loss_price'].apply(lambda x: f"${x:.8f}" if x else "N/A")
        trailing_history['duration_hours'] = trailing_history['duration_hours'].apply(lambda x: f"{x:.1f}h" if x else "N/A")
        trailing_history.columns = ['Symbol', 'Entrée', 'Sortie', 'Profit', 'Durée', 'Niveau', 'Prix Max', 'Stop Loss']
        st.dataframe(trailing_history, use_container_width=True)
    else:
        st.info("Aucun trailing stop déclenché pour le moment")

conn.close()

# Footer
st.markdown("---")
st.markdown("Base Trading Bot - Stratégie Unique avec Trailing Stop Dynamique")
