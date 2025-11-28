#!/usr/bin/env python3
"""
Auto Strategy Optimizer - Analyse les performances et génère des recommandations
Analyse tous les trades de la base de données et évalue si la stratégie atteint les objectifs
"""

import sqlite3
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class StrategyOptimizer:
    """Analyseur de performance et optimiseur de stratégie"""

    # Objectifs de performance
    TARGET_WIN_RATE = 70.0  # %
    TARGET_AVG_PROFIT = 15.0  # % par trade gagnant
    TARGET_AVG_LOSS = 15.0  # % par trade perdant (max)
    MIN_TRADES = 5  # Minimum de trades pour évaluer
    TARGET_TRADES_PER_DAY = 3  # Objectif de trades par jour

    def __init__(self, db_path: str = "data/trading.db"):
        self.db_path = db_path
        self.trades = []
        self.analysis = {}

    def load_trades(self) -> bool:
        """Charge tous les trades fermés de la base de données"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Récupère tous les trades fermés (avec exit_time)
            cursor.execute("""
                SELECT
                    id,
                    token_address,
                    symbol,
                    entry_time,
                    exit_time,
                    amount_in,
                    amount_out,
                    price,
                    gas_used,
                    side
                FROM trade_history
                WHERE exit_time IS NOT NULL
                ORDER BY exit_time DESC
            """)

            rows = cursor.fetchall()

            for row in rows:
                # Calcul du P&L en %
                amount_in = float(row['amount_in'])
                amount_out = float(row['amount_out']) if row['amount_out'] else 0
                gas_used = float(row['gas_used']) if row['gas_used'] else 0

                # P&L net (incluant gas)
                net_pnl_eth = amount_out - amount_in - gas_used
                pnl_percent = (net_pnl_eth / amount_in * 100) if amount_in > 0 else 0

                # Durée du trade
                entry_time = datetime.fromisoformat(row['entry_time'])
                exit_time = datetime.fromisoformat(row['exit_time'])
                duration_hours = (exit_time - entry_time).total_seconds() / 3600

                trade = {
                    'id': row['id'],
                    'token_address': row['token_address'],
                    'token_symbol': row['symbol'],
                    'entry_time': entry_time,
                    'exit_time': exit_time,
                    'amount_in': amount_in,
                    'amount_out': amount_out,
                    'gas_used': gas_used,
                    'pnl_eth': net_pnl_eth,
                    'pnl_percent': pnl_percent,
                    'duration_hours': duration_hours,
                    'exit_reason': row['side'],  # side contient souvent la raison de sortie
                    'is_winner': pnl_percent > 0
                }

                self.trades.append(trade)

            conn.close()

            print(f"✓ {len(self.trades)} trades chargés depuis la base de données")
            return len(self.trades) >= self.MIN_TRADES

        except Exception as e:
            print(f"✗ Erreur lors du chargement des trades: {e}")
            return False

    def analyze_performance(self) -> Dict:
        """Analyse les performances globales"""
        if not self.trades:
            return {
                'error': 'Aucun trade à analyser',
                'meets_objectives': False
            }

        total_trades = len(self.trades)

        # Sépare winners et losers
        winners = [t for t in self.trades if t['is_winner']]
        losers = [t for t in self.trades if not t['is_winner']]

        # Métriques globales
        win_rate = (len(winners) / total_trades * 100) if total_trades > 0 else 0

        avg_profit = sum(t['pnl_percent'] for t in winners) / len(winners) if winners else 0
        avg_loss = sum(abs(t['pnl_percent']) for t in losers) / len(losers) if losers else 0

        total_pnl_eth = sum(t['pnl_eth'] for t in self.trades)
        total_pnl_percent = sum(t['pnl_percent'] for t in self.trades)

        # Expectancy (espérance mathématique)
        expectancy = (win_rate/100 * avg_profit) - ((100-win_rate)/100 * avg_loss)

        # Risk/Reward ratio
        risk_reward = avg_profit / avg_loss if avg_loss > 0 else 0

        # Durée moyenne
        avg_duration = sum(t['duration_hours'] for t in self.trades) / total_trades

        # Trades par jour
        if total_trades >= 2:
            first_trade = min(self.trades, key=lambda x: x['entry_time'])
            last_trade = max(self.trades, key=lambda x: x['entry_time'])
            days_active = (last_trade['entry_time'] - first_trade['entry_time']).days + 1
            trades_per_day = total_trades / days_active if days_active > 0 else 0
        else:
            trades_per_day = 0

        # Analyse des exit reasons
        exit_reasons = {}
        for trade in self.trades:
            reason = trade['exit_reason'] or 'unknown'
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        # Vérifie si les objectifs sont atteints
        meets_win_rate = win_rate >= self.TARGET_WIN_RATE
        meets_avg_profit = avg_profit >= self.TARGET_AVG_PROFIT
        meets_avg_loss = avg_loss <= self.TARGET_AVG_LOSS
        meets_trades_per_day = trades_per_day >= self.TARGET_TRADES_PER_DAY
        meets_min_trades = total_trades >= self.MIN_TRADES

        meets_all_objectives = all([
            meets_win_rate,
            meets_avg_profit,
            meets_avg_loss,
            meets_trades_per_day,
            meets_min_trades
        ])

        self.analysis = {
            'total_trades': total_trades,
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': round(win_rate, 2),
            'avg_profit_percent': round(avg_profit, 2),
            'avg_loss_percent': round(avg_loss, 2),
            'total_pnl_eth': round(total_pnl_eth, 6),
            'total_pnl_percent': round(total_pnl_percent, 2),
            'expectancy': round(expectancy, 2),
            'risk_reward_ratio': round(risk_reward, 2),
            'avg_duration_hours': round(avg_duration, 2),
            'trades_per_day': round(trades_per_day, 2),
            'exit_reasons': exit_reasons,
            'objectives': {
                'win_rate': {
                    'target': self.TARGET_WIN_RATE,
                    'current': round(win_rate, 2),
                    'met': meets_win_rate
                },
                'avg_profit': {
                    'target': self.TARGET_AVG_PROFIT,
                    'current': round(avg_profit, 2),
                    'met': meets_avg_profit
                },
                'avg_loss': {
                    'target': f'<{self.TARGET_AVG_LOSS}',
                    'current': round(avg_loss, 2),
                    'met': meets_avg_loss
                },
                'trades_per_day': {
                    'target': self.TARGET_TRADES_PER_DAY,
                    'current': round(trades_per_day, 2),
                    'met': meets_trades_per_day
                },
                'min_trades': {
                    'target': self.MIN_TRADES,
                    'current': total_trades,
                    'met': meets_min_trades
                }
            },
            'meets_objectives': meets_all_objectives
        }

        return self.analysis

    def analyze_losing_patterns(self) -> Dict:
        """Analyse les patterns de trades perdants pour identifier les problèmes"""
        losers = [t for t in self.trades if not t['is_winner']]

        if not losers:
            return {'message': 'Aucun trade perdant à analyser'}

        # Analyse des exit reasons pour losers
        exit_reasons = {}
        for trade in losers:
            reason = trade['exit_reason'] or 'unknown'
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        # Top 5 worst trades
        worst_trades = sorted(losers, key=lambda x: x['pnl_percent'])[:5]

        # Durée moyenne des losers
        avg_duration_losers = sum(t['duration_hours'] for t in losers) / len(losers)

        return {
            'total_losers': len(losers),
            'exit_reasons': exit_reasons,
            'avg_duration_hours': round(avg_duration_losers, 2),
            'worst_trades': [
                {
                    'symbol': t['token_symbol'],
                    'pnl_percent': round(t['pnl_percent'], 2),
                    'duration_hours': round(t['duration_hours'], 2),
                    'exit_reason': t['exit_reason']
                }
                for t in worst_trades
            ]
        }

    def get_current_config(self) -> Dict:
        """Récupère la configuration actuelle depuis .env"""
        config = {}
        env_path = Path("config/.env")

        if not env_path.exists():
            return config

        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()

            return config
        except Exception as e:
            print(f"✗ Erreur lecture .env: {e}")
            return config

    def print_analysis_report(self):
        """Affiche un rapport d'analyse formaté"""
        if not self.analysis:
            print("⚠ Aucune analyse disponible. Exécutez analyze_performance() d'abord.")
            return

        print("\n" + "="*80)
        print("📊 RAPPORT D'ANALYSE DE PERFORMANCE")
        print("="*80)

        print(f"\n📈 STATISTIQUES GLOBALES")
        print(f"   Total trades      : {self.analysis['total_trades']}")
        print(f"   Winners          : {self.analysis['winners']} ({self.analysis['win_rate']}%)")
        print(f"   Losers           : {self.analysis['losers']}")
        print(f"   Trades/jour      : {self.analysis['trades_per_day']}")

        print(f"\n💰 P&L")
        print(f"   Profit moyen     : +{self.analysis['avg_profit_percent']}% par trade gagnant")
        print(f"   Perte moyenne    : -{self.analysis['avg_loss_percent']}% par trade perdant")
        print(f"   P&L total        : {self.analysis['total_pnl_eth']} ETH ({self.analysis['total_pnl_percent']}%)")
        print(f"   Expectancy       : {self.analysis['expectancy']}%")
        print(f"   Risk/Reward      : {self.analysis['risk_reward_ratio']}")

        print(f"\n⏱ DURÉE")
        print(f"   Durée moyenne    : {self.analysis['avg_duration_hours']}h")

        print(f"\n🎯 OBJECTIFS")
        for name, obj in self.analysis['objectives'].items():
            status = "✓" if obj['met'] else "✗"
            print(f"   {status} {name:20} : {obj['current']} (cible: {obj['target']})")

        print(f"\n📉 EXIT REASONS")
        for reason, count in sorted(self.analysis['exit_reasons'].items(), key=lambda x: x[1], reverse=True):
            percent = count / self.analysis['total_trades'] * 100
            print(f"   {reason:25} : {count:3} ({percent:.1f}%)")

        print(f"\n{'='*80}")

        if self.analysis['meets_objectives']:
            print("✅ STRATÉGIE PERFORMANTE - Tous les objectifs sont atteints!")
        else:
            print("⚠️  STRATÉGIE À OPTIMISER - Certains objectifs ne sont pas atteints")

        print("="*80 + "\n")

    def generate_optimization_suggestions(self) -> List[str]:
        """Génère des suggestions d'optimisation basées sur l'analyse"""
        suggestions = []

        if not self.analysis or not self.analysis.get('objectives'):
            return ["Impossible de générer des suggestions - analyse non effectuée"]

        objs = self.analysis['objectives']

        # Win-rate trop faible
        if not objs['win_rate']['met']:
            current = objs['win_rate']['current']
            target = objs['win_rate']['target']
            gap = target - current

            suggestions.append(
                f"Win-rate à {current}% (cible: {target}%) - Écart de {gap:.1f}%\n"
                "  → Renforcer les critères d'entrée (augmenter MIN_HOLDERS, MIN_SAFETY_SCORE)\n"
                "  → Élargir la fenêtre d'âge des tokens (ex: 3-24h au lieu de 2-12h)\n"
                "  → Augmenter MIN_LIQUIDITY_USD pour plus de stabilité"
            )

        # Profit moyen trop faible
        if not objs['avg_profit']['met']:
            current = objs['avg_profit']['current']
            target = objs['avg_profit']['target']

            suggestions.append(
                f"Profit moyen à {current}% (cible: {target}%)\n"
                "  → Optimiser les trailing stops (espacer les niveaux)\n"
                "  → Augmenter TRAILING_ACTIVATION_PERCENT (ex: 20% au lieu de 12%)\n"
                "  → Réduire TRAILING_DISTANCE pour les niveaux élevés\n"
                "  → Allonger les timeouts pour laisser plus de temps aux positions"
            )

        # Perte moyenne trop élevée
        if not objs['avg_loss']['met']:
            current = objs['avg_loss']['current']
            target = objs['avg_loss']['target']

            suggestions.append(
                f"Perte moyenne à {current}% (cible: <{target}%)\n"
                "  → Réduire STOP_LOSS_PERCENT (ex: 3% au lieu de 5%)\n"
                "  → Réduire GRACE_PERIOD_STOP_LOSS (ex: -25% au lieu de -35%)\n"
                "  → Diminuer GRACE_PERIOD_MINUTES (ex: 2min au lieu de 3min)"
            )

        # Pas assez de trades par jour
        if not objs['trades_per_day']['met']:
            current = objs['trades_per_day']['current']
            target = objs['trades_per_day']['target']

            suggestions.append(
                f"Trades/jour à {current} (cible: {target})\n"
                "  → Assouplir les critères d'entrée (réduire MIN_HOLDERS, MIN_LIQUIDITY_USD)\n"
                "  → Élargir MIN_TOKEN_AGE_HOURS et MAX_TOKEN_AGE_HOURS\n"
                "  → Réduire MIN_SAFETY_SCORE et MIN_POTENTIAL_SCORE\n"
                "  → Augmenter MAX_POSITIONS (actuellement limité à 3)"
            )

        # Analyse des exit reasons
        exit_reasons = self.analysis.get('exit_reasons', {})

        # Trop de stop loss
        stop_loss_count = exit_reasons.get('stop_loss', 0) + exit_reasons.get('grace_period_stop_loss', 0)
        if stop_loss_count > len(self.trades) * 0.3:  # Plus de 30% en stop loss
            suggestions.append(
                f"Trop de trades fermés en stop loss ({stop_loss_count} trades)\n"
                "  → Ajuster STOP_LOSS_PERCENT (augmenter légèrement)\n"
                "  → Revoir GRACE_PERIOD_STOP_LOSS si trop strict"
            )

        # Trop de timeouts
        timeout_reasons = ['stagnation_exit', 'low_momentum_exit', 'max_time_exit', 'emergency_exit']
        timeout_count = sum(exit_reasons.get(r, 0) for r in timeout_reasons)
        if timeout_count > len(self.trades) * 0.3:
            suggestions.append(
                f"Trop de trades fermés par timeout ({timeout_count} trades)\n"
                "  → Allonger les timeouts (STAGNATION, LOW_MOMENTUM, MAX_TIME)\n"
                "  → Tokens peut-être trop lents - revoir MIN_VOLUME_24H_USD"
            )

        if not suggestions:
            suggestions.append("✅ Performance excellente - Aucune optimisation majeure requise")

        return suggestions

    def save_to_json(self, output_path: str = "data/performance_analysis.json"):
        """Sauvegarde l'analyse en JSON"""
        try:
            losing_patterns = self.analyze_losing_patterns()
            suggestions = self.generate_optimization_suggestions()

            output = {
                'timestamp': datetime.now().isoformat(),
                'analysis': self.analysis,
                'losing_patterns': losing_patterns,
                'suggestions': suggestions
            }

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(output, f, indent=2, default=str)

            print(f"✓ Analyse sauvegardée dans {output_path}")
            return True

        except Exception as e:
            print(f"✗ Erreur sauvegarde JSON: {e}")
            return False


def main():
    """Fonction principale"""
    print("\n🤖 AUTO STRATEGY OPTIMIZER - Analyse de performance\n")

    # Initialise l'analyseur
    optimizer = StrategyOptimizer()

    # Charge les trades
    if not optimizer.load_trades():
        print(f"⚠️  Moins de {optimizer.MIN_TRADES} trades disponibles - Analyse impossible")
        print("   Attendez d'avoir au moins 5 trades fermés pour évaluer la stratégie.\n")
        sys.exit(1)

    # Analyse les performances
    optimizer.analyze_performance()

    # Affiche le rapport
    optimizer.print_analysis_report()

    # Analyse les patterns de pertes
    losing_patterns = optimizer.analyze_losing_patterns()

    if losing_patterns.get('total_losers', 0) > 0:
        print("\n📉 ANALYSE DES TRADES PERDANTS")
        print("="*80)
        print(f"Total losers: {losing_patterns['total_losers']}")
        print(f"Durée moyenne: {losing_patterns['avg_duration_hours']}h")
        print("\nExit reasons:")
        for reason, count in losing_patterns['exit_reasons'].items():
            print(f"  - {reason}: {count}")

        print("\nPires trades:")
        for trade in losing_patterns['worst_trades']:
            print(f"  - {trade['symbol']}: {trade['pnl_percent']}% ({trade['duration_hours']:.1f}h) - {trade['exit_reason']}")
        print("="*80 + "\n")

    # Génère les suggestions
    suggestions = optimizer.generate_optimization_suggestions()

    print("\n💡 SUGGESTIONS D'OPTIMISATION")
    print("="*80)
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{i}. {suggestion}")
    print("\n" + "="*80 + "\n")

    # Sauvegarde en JSON
    optimizer.save_to_json()

    # Exit code basé sur si les objectifs sont atteints
    if optimizer.analysis['meets_objectives']:
        print("✅ Stratégie performante - Pas d'optimisation nécessaire\n")
        sys.exit(0)
    else:
        print("⚠️  Optimisation requise - Les objectifs ne sont pas tous atteints\n")
        sys.exit(2)


if __name__ == "__main__":
    main()
