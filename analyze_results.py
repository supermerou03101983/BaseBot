#!/usr/bin/env python3
"""
Analyse approfondie des résultats de trading
"""
import csv
from datetime import datetime
from collections import defaultdict

def parse_percent(val):
    """Convertit '-13.81%' en -13.81"""
    return float(val.replace('%', ''))

def parse_price(val):
    """Convertit '$0.00244700' en 0.00244700"""
    return float(val.replace('$', ''))

def parse_duration(val):
    """Convertit '0.1h' en minutes"""
    hours = float(val.replace('h', ''))
    return hours * 60

def analyze_trades(csv_path):
    """Analyse complète des trades"""
    trades = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get('Symbol'):
                continue

            trade = {
                'symbol': row['Symbol'],
                'entry_price': parse_price(row['Prix Entrée']),
                'amount_eth': float(row['Montant (ETH)']),
                'pnl_gross': parse_percent(row['P&L Brut']),
                'fees': parse_percent(row['Frais']),
                'pnl_net': parse_percent(row['P&L Net']),
                'duration_min': parse_duration(row['Durée']),
                'entry_time': row['Entrée'],
                'exit_time': row['Sortie']
            }
            trades.append(trade)

    print(f"\n{'='*80}")
    print(f"📊 ANALYSE COMPLÈTE DES RÉSULTATS - {len(trades)} TRADES")
    print(f"{'='*80}\n")

    # 1. MÉTRIQUES GLOBALES
    print("1️⃣  MÉTRIQUES GLOBALES")
    print("-" * 80)

    winning_trades = [t for t in trades if t['pnl_net'] > 0]
    losing_trades = [t for t in trades if t['pnl_net'] <= 0]

    win_rate = len(winning_trades) / len(trades) * 100
    avg_win = sum(t['pnl_net'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t['pnl_net'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
    avg_pnl = sum(t['pnl_net'] for t in trades) / len(trades)

    print(f"Total trades:        {len(trades)}")
    print(f"Trades gagnants:     {len(winning_trades)} ({win_rate:.1f}%)")
    print(f"Trades perdants:     {len(losing_trades)} ({100-win_rate:.1f}%)")
    print(f"Win moyen:           +{avg_win:.2f}%")
    print(f"Loss moyen:          {avg_loss:.2f}%")
    print(f"P&L moyen NET:       {avg_pnl:.2f}%")

    risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    expectancy = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)

    print(f"Risk/Reward:         {risk_reward:.2f}x")
    print(f"Expectancy:          {expectancy:.2f}%")

    # 2. ANALYSE PAR TOKEN
    print(f"\n2️⃣  PERFORMANCE PAR TOKEN")
    print("-" * 80)

    by_token = defaultdict(lambda: {'trades': [], 'wins': 0, 'losses': 0, 'total_pnl': 0})

    for trade in trades:
        symbol = trade['symbol']
        by_token[symbol]['trades'].append(trade)
        by_token[symbol]['total_pnl'] += trade['pnl_net']
        if trade['pnl_net'] > 0:
            by_token[symbol]['wins'] += 1
        else:
            by_token[symbol]['losses'] += 1

    # Trier par P&L total
    sorted_tokens = sorted(by_token.items(), key=lambda x: x[1]['total_pnl'], reverse=True)

    print(f"{'Token':<15} {'Trades':<8} {'Win%':<8} {'P&L Net':<12} {'Avg/Trade':<12}")
    print("-" * 80)

    for symbol, data in sorted_tokens:
        count = len(data['trades'])
        win_pct = data['wins'] / count * 100
        total_pnl = data['total_pnl']
        avg_pnl = total_pnl / count

        emoji = "✅" if total_pnl > 0 else "❌"
        print(f"{emoji} {symbol:<13} {count:<8} {win_pct:>5.1f}%   {total_pnl:>+8.2f}%    {avg_pnl:>+8.2f}%")

    # 3. ANALYSE DES PERTES CATASTROPHIQUES
    print(f"\n3️⃣  PERTES CATASTROPHIQUES (>-30%)")
    print("-" * 80)

    catastrophic = [t for t in trades if t['pnl_net'] < -30]
    print(f"Nombre: {len(catastrophic)} trades ({len(catastrophic)/len(trades)*100:.1f}% du total)")

    if catastrophic:
        print(f"\n{'Symbol':<15} {'P&L Net':<12} {'Durée':<10} {'Heure':<20}")
        print("-" * 80)
        for t in sorted(catastrophic, key=lambda x: x['pnl_net']):
            print(f"{t['symbol']:<15} {t['pnl_net']:>+8.2f}%    {t['duration_min']:>5.1f}min   {t['entry_time']}")

        print(f"\n💡 Impact: Ces {len(catastrophic)} trades ont causé {sum(t['pnl_net'] for t in catastrophic):.2f}% de perte")

    # 4. ANALYSE DES DURÉES
    print(f"\n4️⃣  ANALYSE DES DURÉES DE TRADES")
    print("-" * 80)

    very_short = [t for t in trades if t['duration_min'] < 5]  # <5min
    short = [t for t in trades if 5 <= t['duration_min'] < 15]
    medium = [t for t in trades if 15 <= t['duration_min'] < 60]
    long = [t for t in trades if t['duration_min'] >= 60]

    def analyze_duration_bucket(trades_list, label):
        if not trades_list:
            return
        wins = len([t for t in trades_list if t['pnl_net'] > 0])
        win_rate = wins / len(trades_list) * 100
        avg_pnl = sum(t['pnl_net'] for t in trades_list) / len(trades_list)
        print(f"{label:<20} {len(trades_list):>3} trades   Win: {win_rate:>5.1f}%   Avg: {avg_pnl:>+7.2f}%")

    analyze_duration_bucket(very_short, "<5 minutes")
    analyze_duration_bucket(short, "5-15 minutes")
    analyze_duration_bucket(medium, "15-60 minutes")
    analyze_duration_bucket(long, "60+ minutes")

    # 5. PATTERNS TEMPORELS
    print(f"\n5️⃣  ANALYSE DES HORAIRES")
    print("-" * 80)

    by_hour = defaultdict(list)
    for trade in trades:
        hour = int(trade['entry_time'].split()[1].split(':')[0])
        by_hour[hour].append(trade)

    print(f"{'Heure':<10} {'Trades':<10} {'Win%':<10} {'Avg P&L':<12}")
    print("-" * 80)

    for hour in sorted(by_hour.keys()):
        trades_h = by_hour[hour]
        wins = len([t for t in trades_h if t['pnl_net'] > 0])
        win_rate = wins / len(trades_h) * 100
        avg_pnl = sum(t['pnl_net'] for t in trades_h) / len(trades_h)

        emoji = "🔥" if avg_pnl > 5 else "⚠️" if avg_pnl < -5 else "➡️"
        print(f"{emoji} {hour:02d}:00      {len(trades_h):<10} {win_rate:>5.1f}%     {avg_pnl:>+8.2f}%")

    # 6. PROBLÈMES IDENTIFIÉS
    print(f"\n6️⃣  PROBLÈMES IDENTIFIÉS")
    print("-" * 80)

    problems = []

    # Problème 1: Tokens avec multiples pertes
    bad_tokens = [sym for sym, data in by_token.items() if data['losses'] > data['wins'] and len(data['trades']) >= 3]
    if bad_tokens:
        problems.append(f"❌ Tokens perdants récurrents: {', '.join(bad_tokens)}")

    # Problème 2: Trades très courts perdants
    quick_losses = [t for t in trades if t['duration_min'] < 5 and t['pnl_net'] < -10]
    if len(quick_losses) > len(trades) * 0.2:
        problems.append(f"⚡ {len(quick_losses)} trades perdus <5min avec >-10% (sorties trop rapides)")

    # Problème 3: Win rate trop faible
    if win_rate < 55:
        problems.append(f"📉 Win rate {win_rate:.1f}% insuffisant (objectif: >60%)")

    # Problème 4: Pertes catastrophiques
    if len(catastrophic) > 0:
        problems.append(f"💥 {len(catastrophic)} pertes >-30% (honeypots ou protection insuffisante)")

    # Problème 5: Loss moyen trop élevé
    if avg_loss < -15:
        problems.append(f"📊 Loss moyen {avg_loss:.2f}% trop élevé (objectif: >-10%)")

    for i, problem in enumerate(problems, 1):
        print(f"{i}. {problem}")

    # 7. RECOMMANDATIONS
    print(f"\n7️⃣  RECOMMANDATIONS D'AMÉLIORATION")
    print("=" * 80)

    recommendations = []

    # Reco basée sur tokens perdants
    if bad_tokens:
        recommendations.append({
            'priority': '🔴 URGENT',
            'title': 'Blacklister les tokens perdants récurrents',
            'details': f"Tokens: {', '.join(bad_tokens[:3])}",
            'action': 'Ajouter ces tokens à BLACKLIST_TOKENS dans .env'
        })

    # Reco basée sur pertes catastrophiques
    if len(catastrophic) > 0:
        recommendations.append({
            'priority': '🔴 URGENT',
            'title': 'Renforcer la protection honeypot',
            'details': f'{len(catastrophic)} pertes >-30% détectées',
            'action': 'Augmenter MIN_LIQUIDITY_USD de $30k à $100k et MIN_HOLDERS de 30 à 100'
        })

    # Reco basée sur sorties rapides
    if len(quick_losses) > 5:
        avg_quick_loss = sum(t['pnl_net'] for t in quick_losses) / len(quick_losses)
        recommendations.append({
            'priority': '🟠 IMPORTANT',
            'title': 'Grace Period fonctionne mal',
            'details': f'{len(quick_losses)} sorties <5min avec {avg_quick_loss:.1f}% de perte moyenne',
            'action': 'Augmenter grace_period_stop_loss_percent de 35% à 50%'
        })

    # Reco basée sur loss moyen
    if avg_loss < -15:
        recommendations.append({
            'priority': '🟠 IMPORTANT',
            'title': 'Réduire le stop loss normal',
            'details': f'Loss moyen: {avg_loss:.2f}% (trop élevé)',
            'action': 'Réduire normal_stop_loss_percent de 5% à 3%'
        })

    # Reco basée sur horaires
    bad_hours = [h for h, trades_h in by_hour.items() if len(trades_h) >= 3 and sum(t['pnl_net'] for t in trades_h) / len(trades_h) < -10]
    if bad_hours:
        recommendations.append({
            'priority': '🟡 MOYEN',
            'title': 'Éviter certaines heures de trading',
            'details': f'Heures perdantes: {", ".join([f"{h:02d}:00" for h in bad_hours])}',
            'action': 'Implémenter TRADING_HOURS dans .env pour limiter aux heures profitables'
        })

    # Reco basée sur expectancy
    if expectancy < 5:
        recommendations.append({
            'priority': '🔴 URGENT',
            'title': 'Expectancy trop faible',
            'details': f'Expectancy actuelle: {expectancy:.2f}% (objectif: >10%)',
            'action': 'Appliquer TOUTES les recommandations ci-dessus'
        })

    for i, reco in enumerate(recommendations, 1):
        print(f"\n{i}. {reco['priority']} {reco['title']}")
        print(f"   └─ Détails: {reco['details']}")
        print(f"   └─ Action:  {reco['action']}")

    # 8. CONFIGURATION OPTIMALE SUGGÉRÉE
    print(f"\n8️⃣  CONFIGURATION .ENV OPTIMALE")
    print("=" * 80)
    print("""
# Stop Loss ajusté
STOP_LOSS_PERCENT=3                    # Réduit de 5% → 3%
GRACE_PERIOD_MINUTES=3                 # Conserver 3 min
GRACE_PERIOD_STOP_LOSS_PERCENT=50      # Augmenté de 35% → 50%

# Filtres renforcés
MIN_LIQUIDITY_USD=100000               # Augmenté de $30k → $100k
MIN_HOLDERS=100                        # Augmenté de 30 → 100
MIN_HONEYPOT_SCORE=80                  # Conserver

# Trailing stop optimisé
TRAILING_STOP_ACTIVATION_PERCENT=8     # Réduit de 12% → 8%
TRAILING_STOP_DISTANCE_PERCENT=5       # Conserver

# Blacklist tokens perdants
BLACKLIST_TOKENS=""" + ",".join(bad_tokens[:5]) if bad_tokens else "")

    print(f"\n{'='*80}")
    print("✅ Analyse terminée!")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    analyze_trades('Résultats trading.csv')
