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
import os
from dotenv import load_dotenv

# Charger .env pour récupérer les frais configurés
load_dotenv(Path(__file__).parent.parent / 'config' / '.env')

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

def calculate_trading_fees(amount_eth, slippage_percent=3):
    """
    Calcule les frais totaux de trading

    Frais sur Base Network:
    - Uniswap V3 swap fee: 0.3% par swap (0.6% total pour buy+sell)
    - Gas fees: ~0.0001-0.0003 ETH par transaction sur Base
    - Slippage: Variable (3% max configuré)

    Returns: dict avec détails des frais
    """
    # Frais Uniswap V3 (0.3% par swap, buy + sell = 0.6%)
    uniswap_fee_buy = amount_eth * 0.003
    uniswap_fee_sell = amount_eth * 0.003
    total_uniswap_fees = uniswap_fee_buy + uniswap_fee_sell

    # Gas fees sur Base (très bas, estimé à 0.0002 ETH par tx)
    gas_fee_per_tx = 0.0002
    total_gas_fees = gas_fee_per_tx * 2  # Buy + Sell

    # Slippage moyen estimé (on utilise la moitié du max pour être réaliste)
    avg_slippage_percent = slippage_percent / 2
    slippage_cost = amount_eth * (avg_slippage_percent / 100) * 2  # Buy + Sell

    # Total des frais
    total_fees_eth = total_uniswap_fees + total_gas_fees + slippage_cost
    total_fees_percent = (total_fees_eth / amount_eth) * 100

    return {
        'uniswap_fees_eth': total_uniswap_fees,
        'gas_fees_eth': total_gas_fees,
        'slippage_eth': slippage_cost,
        'total_fees_eth': total_fees_eth,
        'total_fees_percent': total_fees_percent,
        'uniswap_percent': 0.6,
        'slippage_percent': avg_slippage_percent * 2
    }

def calculate_net_profit(gross_profit_percent, amount_eth, slippage_percent=3):
    """
    Calcule le profit net après déduction de tous les frais

    Args:
        gross_profit_percent: Profit brut en %
        amount_eth: Montant de la position en ETH
        slippage_percent: Slippage max configuré (défaut 3%)

    Returns:
        dict avec profit brut, frais, et profit net
    """
    fees = calculate_trading_fees(amount_eth, slippage_percent)

    # Profit net = Profit brut - Frais totaux (en %)
    net_profit_percent = gross_profit_percent - fees['total_fees_percent']

    return {
        'gross_profit_percent': gross_profit_percent,
        'fees_percent': fees['total_fees_percent'],
        'net_profit_percent': net_profit_percent,
        'fees_breakdown': fees
    }

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

    # Récupérer slippage depuis config
    slippage_percent = float(os.getenv('MAX_SLIPPAGE_PERCENT', 3))
    position_size_eth = float(os.getenv('POSITION_SIZE_PERCENT', 15)) / 100  # Convertir en fraction

    # Afficher info sur les frais
    st.info(f"""
    💡 **Frais de trading intégrés dans les calculs:**
    - Uniswap V3: 0.6% (0.3% par swap)
    - Gas Base: ~0.0004 ETH par round-trip
    - Slippage moyen estimé: {slippage_percent}% ({slippage_percent/2}% par swap)
    - **Total frais estimés: ~{slippage_percent + 0.6:.1f}% par trade**
    """)

    # Graphique des profits par jour avec BRUT et NET
    profits_df = pd.read_sql_query("""
        SELECT
            DATE(exit_time) as date,
            AVG(profit_loss) as avg_profit_gross,
            COUNT(*) as trades,
            AVG(amount_in) as avg_amount_eth
        FROM trade_history
        WHERE exit_time IS NOT NULL AND profit_loss IS NOT NULL
        GROUP BY DATE(exit_time)
        ORDER BY date DESC
        LIMIT 30
    """, conn)
    
    if not profits_df.empty:
        # Calculer profit NET pour chaque jour
        profits_df['avg_profit_net'] = profits_df.apply(
            lambda row: calculate_net_profit(
                row['avg_profit_gross'],
                row['avg_amount_eth'] if pd.notna(row['avg_amount_eth']) else 0.15,
                slippage_percent
            )['net_profit_percent'],
            axis=1
        )

        fig = go.Figure()
        # Profit BRUT
        fig.add_trace(go.Bar(
            x=profits_df['date'],
            y=profits_df['avg_profit_gross'],
            name='Profit Brut %',
            marker_color='lightblue',
            opacity=0.6
        ))
        # Profit NET
        fig.add_trace(go.Bar(
            x=profits_df['date'],
            y=profits_df['avg_profit_net'],
            name='Profit Net % (après frais)',
            marker_color=['green' if x > 0 else 'red' for x in profits_df['avg_profit_net']]
        ))
        fig.update_layout(
            title="Performance Quotidienne (Brut vs Net)",
            height=400,
            barmode='group',
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Statistiques globales avec BRUT et NET
    st.subheader("📊 Statistiques Globales")

    col1, col2, col3, col4 = st.columns(4)

    stats = pd.read_sql_query("""
        SELECT
            COUNT(*) as total_trades,
            COUNT(CASE WHEN profit_loss > 0 THEN 1 END) as winning_trades,
            AVG(profit_loss) as avg_profit_gross,
            MAX(profit_loss) as best_trade,
            MIN(profit_loss) as worst_trade,
            AVG(amount_in) as avg_amount_eth
        FROM trade_history
        WHERE exit_time IS NOT NULL
    """, conn)

    if not stats.empty and stats.iloc[0]['total_trades'] > 0:
        row = stats.iloc[0]

        # Calculer profit NET moyen
        avg_amount = row['avg_amount_eth'] if pd.notna(row['avg_amount_eth']) else 0.15
        net_profit_data = calculate_net_profit(row['avg_profit_gross'], avg_amount, slippage_percent)

        # Calculer win rate NET (en tenant compte des frais)
        net_winning_trades_query = f"""
            SELECT COUNT(*) as net_winners
            FROM trade_history
            WHERE exit_time IS NOT NULL
            AND profit_loss > {net_profit_data['fees_percent']}
        """
        net_winners = pd.read_sql_query(net_winning_trades_query, conn).iloc[0]['net_winners']
        net_win_rate = (net_winners / row['total_trades'] * 100)

        with col1:
            win_rate_gross = (row['winning_trades'] / row['total_trades'] * 100)
            st.metric(
                "Win Rate Brut",
                f"{win_rate_gross:.1f}%",
                help="Trades gagnants avant frais"
            )

        with col2:
            st.metric(
                "Win Rate Net",
                f"{net_win_rate:.1f}%",
                delta=f"{net_win_rate - win_rate_gross:.1f}%",
                help="Trades gagnants après frais de trading"
            )

        with col3:
            st.metric(
                "Profit Moyen Brut",
                f"{row['avg_profit_gross']:.2f}%",
                help="Avant frais de trading"
            )

        with col4:
            st.metric(
                "Profit Moyen Net",
                f"{net_profit_data['net_profit_percent']:.2f}%",
                delta=f"{net_profit_data['net_profit_percent'] - row['avg_profit_gross']:.2f}%",
                delta_color="inverse",
                help=f"Après {net_profit_data['fees_percent']:.2f}% de frais"
            )

    # Détail des frais estimés
    st.subheader("💰 Détail des Frais de Trading (Estimation)")

    col1, col2, col3, col4 = st.columns(4)

    # Utiliser la taille de position moyenne
    avg_position_size = stats.iloc[0]['avg_amount_eth'] if not stats.empty and pd.notna(stats.iloc[0]['avg_amount_eth']) else 0.15
    fees_detail = calculate_trading_fees(avg_position_size, slippage_percent)

    with col1:
        st.metric("Frais Uniswap V3", f"{fees_detail['uniswap_percent']:.2f}%")
    with col2:
        st.metric("Slippage Moyen", f"{fees_detail['slippage_percent']:.2f}%")
    with col3:
        st.metric("Gas Fees", f"{fees_detail['gas_fees_eth']:.4f} ETH")
    with col4:
        st.metric("Total Frais", f"{fees_detail['total_fees_percent']:.2f}%")

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

    # Afficher les derniers trades (fermés uniquement) avec profit NET
    history_df = pd.read_sql_query("""
        SELECT
            symbol,
            entry_price,
            amount_in,
            amount_out,
            profit_loss as profit_gross,
            entry_time,
            exit_time,
            ROUND((JULIANDAY(exit_time) - JULIANDAY(entry_time)) * 24, 1) as duration_hours
        FROM trade_history
        WHERE exit_time IS NOT NULL
        ORDER BY exit_time DESC
        LIMIT 50
    """, conn)

    if not history_df.empty:
        # Calculer profit NET pour chaque trade
        history_df['profit_net'] = history_df.apply(
            lambda row: calculate_net_profit(
                row['profit_gross'] if pd.notna(row['profit_gross']) else 0,
                row['amount_in'] if pd.notna(row['amount_in']) else 0.15,
                slippage_percent
            )['net_profit_percent'],
            axis=1
        )

        # Calculer les frais pour chaque trade
        history_df['fees_percent'] = history_df.apply(
            lambda row: calculate_trading_fees(
                row['amount_in'] if pd.notna(row['amount_in']) else 0.15,
                slippage_percent
            )['total_fees_percent'],
            axis=1
        )

        # Calculer total des frais AVANT formatage (garder valeurs numériques)
        amount_in_numeric = history_df['amount_in'].copy()
        fees_percent_numeric = history_df['fees_percent'].copy()

        # Formater l'affichage
        history_df['entry_price_fmt'] = history_df['entry_price'].apply(lambda x: f"${x:.8f}" if pd.notna(x) else "N/A")
        history_df['amount_in_fmt'] = history_df['amount_in'].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "N/A")
        history_df['profit_gross_fmt'] = history_df['profit_gross'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        history_df['profit_net_fmt'] = history_df['profit_net'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        history_df['fees_fmt'] = history_df['fees_percent'].apply(lambda x: f"-{x:.2f}%" if pd.notna(x) else "N/A")
        history_df['duration_hours_fmt'] = history_df['duration_hours'].apply(lambda x: f"{x:.1f}h" if pd.notna(x) else "N/A")

        # Sélectionner et renommer les colonnes
        display_df = history_df[['symbol', 'entry_price_fmt', 'amount_in_fmt', 'profit_gross_fmt', 'fees_fmt', 'profit_net_fmt', 'duration_hours_fmt', 'entry_time', 'exit_time']]
        display_df.columns = ['Symbol', 'Prix Entrée', 'Montant (ETH)', 'P&L Brut', 'Frais', 'P&L Net', 'Durée', 'Entrée', 'Sortie']

        st.dataframe(display_df, use_container_width=True)

        # Résumé des frais totaux payés (utiliser valeurs numériques)
        total_fees_eth = (fees_percent_numeric * amount_in_numeric / 100).sum()
        if pd.notna(total_fees_eth):
            st.info(f"💸 **Frais totaux estimés sur ces trades:** {total_fees_eth:.4f} ETH")
        else:
            st.info(f"💸 **Frais totaux estimés:** N/A")
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
        st.subheader("🎯 Stratégie: Momentum Safe (Mod #6)")

        # Mode Trading
        paper_trading = config_data.get('PAPER_TRADING', 'true').lower() == 'true'
        mode = "📝 Paper Trading" if paper_trading else "💰 Real Trading"
        st.metric("Mode", mode)

        # Trader
        st.metric("Montant/Trade", f"${config_data.get('TRADE_AMOUNT_USD', 'N/A')}")
        st.metric("Stop Loss Standard", f"-{config_data.get('STOP_LOSS_PERCENT', 'N/A')}%")

        # Grace Period
        grace_enabled = config_data.get('GRACE_PERIOD_ENABLED', 'true').lower() == 'true'
        if grace_enabled:
            st.metric("⏱️ Grace Period",
                     f"{config_data.get('GRACE_PERIOD_MINUTES', 'N/A')}min @ -{config_data.get('GRACE_PERIOD_STOP_LOSS', 'N/A')}%")
        else:
            st.metric("⏱️ Grace Period", "Désactivée")

        st.markdown("---")

        # Filter - Fenêtre d'âge
        st.subheader("🔍 Filter - Fenêtre d'Âge")
        min_filter_age = config_data.get('MIN_AGE_HOURS', 'N/A')
        max_filter_age = config_data.get('MAX_AGE_HOURS', 'N/A')
        st.metric("Fenêtre Filtre", f"{min_filter_age}h - {max_filter_age}h",
                 help="Sweet spot: après scam check, avant pic retail")

        # Liquidité & Market Cap
        st.subheader("💧 Liquidité & Market Cap")
        min_liq = config_data.get('MIN_LIQUIDITY_USD', 'N/A')
        max_liq = config_data.get('MAX_LIQUIDITY_USD', 'N/A')
        st.text(f"Liquidité: ${min_liq} - ${max_liq}")

        min_mc = config_data.get('MIN_MARKET_CAP', 'N/A')
        max_mc = config_data.get('MAX_MARKET_CAP', 'N/A')
        st.text(f"Market Cap: ${min_mc} - ${max_mc}")

    with col2:
        st.subheader("📊 Scanner On-Chain (Mod #5)")
        st.text(f"Intervalle: {config_data.get('SCAN_INTERVAL_SECONDS', 'N/A')}s")

        min_scan_age = config_data.get('MIN_TOKEN_AGE_HOURS', 'N/A')
        max_scan_age = config_data.get('MAX_TOKEN_AGE_HOURS', 'N/A')
        st.text(f"Fenêtre Scanner: {min_scan_age}h - {max_scan_age}h")
        st.caption("Scanner détecte événements PairCreated")

        st.markdown("---")

        # Volume & Momentum
        st.subheader("📈 Volume & Momentum")
        vol_1h = config_data.get('MIN_VOLUME_1H_USD', config_data.get('MIN_VOLUME_1H', 'N/A'))
        vol_5m = config_data.get('MIN_VOLUME_5MIN_USD', config_data.get('MIN_VOLUME_5MIN', 'N/A'))
        ratio = config_data.get('MIN_VOLUME_RATIO_5M_1H', 'N/A')
        st.text(f"Volume 1h: ${vol_1h}")
        st.text(f"Volume 5min: ${vol_5m}")
        st.text(f"Ratio 5m/1h: ≥{ratio} (accélération)")

        pc_5m = config_data.get('MIN_PRICE_CHANGE_5MIN', 'N/A')
        pc_1h = config_data.get('MIN_PRICE_CHANGE_1H', 'N/A')
        st.text(f"Δ Prix 5min: ≥+{pc_5m}%")
        st.text(f"Δ Prix 1h: ≥+{pc_1h}%")

        st.markdown("---")

        # Distribution & Sécurité
        st.subheader("🛡️ Distribution & Sécurité")
        holders = config_data.get('MIN_HOLDERS', 'N/A')
        owner = config_data.get('MAX_OWNER_PERCENTAGE', 'N/A')
        st.text(f"Holders: ≥{holders}")
        st.text(f"Owner: ≤{owner}%")

        buy_tax = config_data.get('MAX_BUY_TAX', 'N/A')
        sell_tax = config_data.get('MAX_SELL_TAX', 'N/A')
        st.text(f"Buy Tax: ≤{buy_tax}%")
        st.text(f"Sell Tax: ≤{sell_tax}%")

        st.markdown("---")

        # Discipline & Retry Logic
        st.subheader("🔒 Discipline & Retry")
        losing_cooldown = config_data.get('LOSING_TOKEN_COOLDOWN_HOURS', 'N/A')
        st.text(f"Losing Token Cooldown: {losing_cooldown}h")
        st.caption("Évite revenge trading après perte")

        retry_enabled = config_data.get('ENABLE_RETRY_LOGIC', 'false').lower() == 'true'
        retry_status = "✅ Activé" if retry_enabled else "❌ Désactivé"
        st.text(f"Retry Logic: {retry_status}")
        if retry_enabled:
            st.caption("Tokens rejetés seront réanalysés si éligibles")

    # Résumé stratégie
    st.markdown("---")
    st.info("🎯 **Stratégie Momentum Safe (Mod #6)**: Fenêtre 3.5-8h, 12 critères stricts, cible 3-4 tokens/jour avec ≥70% win-rate")

    # Stats de sortie (raisons)
    st.subheader("📊 Raisons de Sortie")

    exit_reasons = pd.read_sql_query("""
        SELECT
            reason,
            COUNT(*) as count,
            ROUND(AVG(profit_loss_percent), 2) as avg_profit_pct
        FROM trade_history
        WHERE exit_time IS NOT NULL AND reason IS NOT NULL
        GROUP BY reason
        ORDER BY count DESC
        LIMIT 10
    """, conn)

    if not exit_reasons.empty:
        st.dataframe(exit_reasons, use_container_width=True)
    else:
        st.info("Aucun trailing stop déclenché pour le moment")

conn.close()

# Footer
st.markdown("---")
st.markdown("Base Trading Bot - Stratégie Unique avec Trailing Stop Dynamique")
