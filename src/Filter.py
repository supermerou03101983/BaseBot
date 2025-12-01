#!/usr/bin/env python3
"""
Filter - Analyse complète avec nouvelle stratégie de trading
"""

import sqlite3
import time
import os
import sys
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Set, List
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.append(str(PROJECT_DIR))

from dotenv import load_dotenv
from web3_utils import (
    BaseWeb3Manager, UniswapV3Manager,
    DexScreenerAPI, BaseScanAPI, CoinGeckoAPI
)

load_dotenv(PROJECT_DIR / 'config' / '.env')

class AdvancedFilter:
    def __init__(self):
        # Créer les dossiers nécessaires
        (PROJECT_DIR / 'data').mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / 'logs').mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / 'config').mkdir(parents=True, exist_ok=True)
        self.db_path = PROJECT_DIR / 'data' / 'trading.db'

        # Setup logging
        self.setup_logging()

        # Initialiser la base de données si nécessaire
        self.init_database()

        # Charger la configuration
        self.load_config()

        # Initialiser les clients API
        self.web3_manager = BaseWeb3Manager(
            rpc_url=os.getenv('RPC_URL', 'https://mainnet.base.org'),
            private_key=os.getenv('PRIVATE_KEY')
        )
        self.uniswap = UniswapV3Manager(self.web3_manager)
        self.dexscreener = DexScreenerAPI()
        self.basescan = BaseScanAPI(os.getenv('ETHERSCAN_API_KEY')) # Utilise la clé Etherscan
        self.coingecko = CoinGeckoAPI(os.getenv('COINGECKO_API_KEY'))

        # Système de blacklist
        self.blacklist_file = PROJECT_DIR / 'config' / 'blacklist.json'
        self.load_blacklist()

        # Statistiques de filtrage
        self.stats = {
            'total_analyzed': 0,
            'total_approved': 0,
            'total_rejected': 0
        }

    def setup_logging(self):
        """Configuration du logging"""
        log_file = PROJECT_DIR / 'logs' / 'filter.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def init_database(self):
        """Initialise la base de données si nécessaire"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table des tokens découverts (partagée avec Scanner)
        # ✅ SCHEMA UNIFIÉ avec pair_created_at (date blockchain) et discovered_at (date découverte)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discovered_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT UNIQUE NOT NULL,
                symbol TEXT,
                name TEXT,
                decimals INTEGER,
                total_supply TEXT,
                liquidity REAL,
                market_cap REAL,
                volume_24h REAL,
                price_usd REAL,
                price_eth REAL,
                pair_created_at TIMESTAMP,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table des tokens approuvés
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approved_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT UNIQUE NOT NULL,
                symbol TEXT,
                name TEXT,
                reason TEXT, -- Raison de l'approbation
                score REAL,  -- Score de qualité (0-100)
                analysis_data TEXT, -- JSON avec les détails de l'analyse
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table des tokens rejetés
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rejected_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT UNIQUE NOT NULL,
                symbol TEXT,
                name TEXT,
                reason TEXT, -- Raison du rejet
                analysis_data TEXT, -- JSON avec les détails de l'analyse
                rejected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table des règles de filtrage (optionnel, pour suivi)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS filter_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT UNIQUE NOT NULL,
                rule_config TEXT, -- JSON avec la configuration de la règle
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def load_config(self):
        """Charge la configuration avec nouvelle stratégie"""
        # Mode de trading
        mode_file = PROJECT_DIR / 'config' / 'trading_mode.json'
        try:
            if mode_file.exists():
                with open(mode_file, 'r') as f:
                    data = json.load(f)
                self.trading_mode = data.get('mode', 'paper')
            else:
                self.trading_mode = 'paper'
                with open(mode_file, 'w') as f:
                    json.dump({'mode': 'paper'}, f)
        except Exception as e:
            self.logger.error(f"Erreur chargement mode trading: {e}")
            self.trading_mode = 'paper' # Valeur par défaut

        # Règles de filtrage - Stratégie Momentum Safe (Mod #6)
        try:
            # Fenêtre d'âge stricte (3.5-8h)
            self.min_age_hours = float(os.getenv('MIN_AGE_HOURS', '3.5'))
            self.max_age_hours = float(os.getenv('MAX_AGE_HOURS', '8.0'))

            # Liquidité saine
            self.min_liquidity = float(os.getenv('MIN_LIQUIDITY_USD', '12000'))
            self.max_liquidity = float(os.getenv('MAX_LIQUIDITY_USD', '2000000'))

            # Market cap viable
            self.min_market_cap = float(os.getenv('MIN_MARKET_CAP', '80000'))
            self.max_market_cap = float(os.getenv('MAX_MARKET_CAP', '2500000'))

            # Volume momentum (1h et 5min)
            self.min_volume_1h = float(os.getenv('MIN_VOLUME_1H', '4000'))
            self.min_volume_5min = float(os.getenv('MIN_VOLUME_5MIN', '800'))
            self.min_volume_ratio_5m_1h = float(os.getenv('MIN_VOLUME_RATIO_5M_1H', '0.3'))
            self.min_volume_24h = float(os.getenv('MIN_VOLUME_24H', '0'))  # Optionnel pour Momentum Safe

            # Momentum prix
            self.min_price_change_5min = float(os.getenv('MIN_PRICE_CHANGE_5MIN', '4.0'))
            self.min_price_change_1h = float(os.getenv('MIN_PRICE_CHANGE_1H', '7.0'))

            # Distribution saine
            self.min_holders = int(os.getenv('MIN_HOLDERS', '120'))
            self.max_owner_percentage = float(os.getenv('MAX_OWNER_PERCENTAGE', '5.0'))

            # Taxes raisonnables
            self.max_buy_tax = float(os.getenv('MAX_BUY_TAX', '3.0'))
            self.max_sell_tax = float(os.getenv('MAX_SELL_TAX', '3.0'))

            # Scores
            self.min_safety_score = float(os.getenv('MIN_SAFETY_SCORE', '50.0'))
            self.min_potential_score = float(os.getenv('MIN_POTENTIAL_SCORE', '40.0'))
            self.score_threshold = float(os.getenv('MIN_SAFETY_SCORE', '50.0'))

        except ValueError as e:
            self.logger.error(f"Erreur parsing config filtre: {e}. Utilisation des valeurs par défaut Momentum Safe.")
            # Valeurs par défaut Momentum Safe
            self.min_age_hours = 3.5
            self.max_age_hours = 8.0
            self.min_liquidity = 12000
            self.max_liquidity = 2000000
            self.min_market_cap = 80000
            self.max_market_cap = 2500000
            self.min_volume_1h = 4000
            self.min_volume_5min = 800
            self.min_volume_ratio_5m_1h = 0.3
            self.min_volume_24h = 0
            self.min_price_change_5min = 4.0
            self.min_price_change_1h = 7.0
            self.min_holders = 120
            self.max_owner_percentage = 5.0
            self.max_buy_tax = 3.0
            self.max_sell_tax = 3.0
            self.min_safety_score = 50.0
            self.min_potential_score = 40.0
            self.score_threshold = 50.0


    def load_blacklist(self):
        """Charge la liste noire depuis le fichier JSON"""
        try:
            if self.blacklist_file.exists():
                with open(self.blacklist_file, 'r') as f:
                    self.blacklist = set(json.load(f))
            else:
                self.blacklist = set()
                # Créer un fichier vide si nécessaire
                with open(self.blacklist_file, 'w') as f:
                    json.dump([], f)
        except Exception as e:
            self.logger.error(f"Erreur chargement blacklist: {e}")
            self.blacklist = set()

    def is_blacklisted(self, token_address: str) -> bool:
        """Vérifie si un token est sur la liste noire"""
        return token_address.lower() in [addr.lower() for addr in self.blacklist]

    def calculate_score(self, token_data: Dict) -> Tuple[float, List[str]]:
        """
        Stratégie Momentum Safe (Modification #6)
        Filtre strict avec rejets automatiques AVANT tout calcul de score.
        Cible: 3-4 tokens/jour avec ≥70% win-rate
        """
        reasons = []

        # Vérifier la blacklist
        if self.is_blacklisted(token_data['token_address']):
            return 0.0, ["❌ REJET: Blacklisted"]

        # === FALLBACK VOLUME 5MIN ===
        # DexScreener ne retourne pas toujours volume_5min, on l'estime
        if "volume_5min" not in token_data or token_data.get("volume_5min", 0) == 0:
            token_data["volume_5min"] = token_data.get("volume_1h", 0) * 0.2

        # === PHASE 1: REJETS AUTOMATIQUES (Critères stricts) ===

        # 1. ÂGE (fenêtre stricte 3.5-8h)
        # PRIORITÉ: age_hours du Scanner on-chain (fiable) > pair_created_at DexScreener
        age_hours = token_data.get('age_hours', 0)

        if age_hours == 0:
            # Fallback: calculer depuis pair_created_at si age_hours manque
            pair_created_at = token_data.get('pair_created_at')
            if pair_created_at:
                try:
                    from datetime import timezone
                    if 'T' in pair_created_at:
                        token_creation_date = datetime.fromisoformat(pair_created_at.replace('Z', '+00:00'))
                    else:
                        token_creation_date = datetime.strptime(pair_created_at, '%Y-%m-%d %H:%M:%S')
                        token_creation_date = token_creation_date.replace(tzinfo=timezone.utc)

                    age_hours = (datetime.now(timezone.utc) - token_creation_date).total_seconds() / 3600
                except Exception as e:
                    reasons.append(f"❌ REJET: Âge non calculable (erreur: {str(e)[:50]})")
                    return 0, reasons
            else:
                reasons.append("❌ REJET: Âge non disponible (ni age_hours ni pair_created_at)")
                return 0, reasons

        # Vérifier fenêtre d'âge
        if age_hours < self.min_age_hours:
            reasons.append(f"❌ REJET: Âge {age_hours:.1f}h < {self.min_age_hours}h (trop jeune, risque scam)")
            return 0, reasons

        if age_hours > self.max_age_hours:
            reasons.append(f"❌ REJET: Âge {age_hours:.1f}h > {self.max_age_hours}h (trop vieux, pump fini)")
            return 0, reasons

        # 2. LIQUIDITÉ (fenêtre stricte $12k-$2M)
        liq = token_data.get('liquidity', 0)
        if liq < self.min_liquidity:
            reasons.append(f"❌ REJET: Liquidité ${liq:,.0f} < ${self.min_liquidity:,.0f} (trop faible, manipulation)")
            return 0, reasons
        if liq > self.max_liquidity:
            reasons.append(f"❌ REJET: Liquidité ${liq:,.0f} > ${self.max_liquidity:,.0f} (trop élevée, institutionnel)")
            return 0, reasons

        # 3. MARKET CAP (fenêtre stricte $80k-$2.5M)
        mc = token_data.get('market_cap', 0)
        if mc < self.min_market_cap:
            reasons.append(f"❌ REJET: Market Cap ${mc:,.0f} < ${self.min_market_cap:,.0f} (trop petit)")
            return 0, reasons
        if mc > self.max_market_cap:
            reasons.append(f"❌ REJET: Market Cap ${mc:,.0f} > ${self.max_market_cap:,.0f} (trop gros)")
            return 0, reasons

        # 4. VOLUME 1H (minimum activité)
        vol1h = token_data.get('volume_1h', 0)
        if vol1h < self.min_volume_1h:
            reasons.append(f"❌ REJET: Volume 1h ${vol1h:,.0f} < ${self.min_volume_1h:,.0f} (pas d'activité)")
            return 0, reasons

        # 5. VOLUME 5MIN (minimum activité immédiate)
        vol5m = token_data.get('volume_5min', 0)
        if vol5m < self.min_volume_5min:
            reasons.append(f"❌ REJET: Volume 5min ${vol5m:,.0f} < ${self.min_volume_5min:,.0f} (momentum mort)")
            return 0, reasons

        # 6. RATIO VOLUME 5M/1H (vérifier accélération)
        ratio_5m_1h = vol5m / vol1h if vol1h > 0 else 0
        if ratio_5m_1h < self.min_volume_ratio_5m_1h:
            reasons.append(f"❌ REJET: Ratio vol 5m/1h {ratio_5m_1h:.2f} < {self.min_volume_ratio_5m_1h} (ralentissement)")
            return 0, reasons

        # 7. MOMENTUM PRIX 5MIN (minimum momentum immédiat)
        pc5m = token_data.get('price_change_5m', 0)
        if pc5m < self.min_price_change_5min:
            reasons.append(f"❌ REJET: Δ Prix 5min {pc5m:+.1f}% < +{self.min_price_change_5min}% (pas de momentum)")
            return 0, reasons

        # 8. MOMENTUM PRIX 1H (minimum tendance confirmée)
        pc1h = token_data.get('price_change_1h', 0)
        if pc1h < self.min_price_change_1h:
            reasons.append(f"❌ REJET: Δ Prix 1h {pc1h:+.1f}% < +{self.min_price_change_1h}% (tendance faible)")
            return 0, reasons

        # 9. HOLDERS (minimum distribution)
        holders = token_data.get('holder_count', 0)
        if holders < self.min_holders:
            reasons.append(f"❌ REJET: Holders {holders} < {self.min_holders} (distribution insuffisante)")
            return 0, reasons

        # 10. OWNER PERCENTAGE (maximum concentration)
        owner_pct = token_data.get('owner_percentage', 100.0)
        if owner_pct > self.max_owner_percentage:
            if owner_pct < 100.0:
                reasons.append(f"❌ REJET: Owner {owner_pct:.1f}% > {self.max_owner_percentage}% (trop centralisé)")
                return 0, reasons
            else:
                # owner_pct == 100 → non détecté, traiter comme risque modéré
                self.logger.warning(f"Owner non détecté (100%) pour {token_data.get('symbol', '???')} - risque modéré")
                # Ne pas rejeter automatiquement, mais noter le risque
                reasons.append(f"⚠️ WARNING: Owner non détecté (donnée manquante)")
                pass

        # 11. TAXES (maximum frais)
        buy_tax = token_data.get('buy_tax', None)
        sell_tax = token_data.get('sell_tax', None)

        if buy_tax is not None and buy_tax > self.max_buy_tax:
            reasons.append(f"❌ REJET: Buy Tax {buy_tax:.1f}% > {self.max_buy_tax}% (trop élevé)")
            return 0, reasons

        if sell_tax is not None and sell_tax > self.max_sell_tax:
            reasons.append(f"❌ REJET: Sell Tax {sell_tax:.1f}% > {self.max_sell_tax}% (trop élevé)")
            return 0, reasons

        # 12. HONEYPOT CHECK (rejet automatique si honeypot)
        try:
            token_address = token_data['token_address']
            honeypot_check = self.web3_manager.check_honeypot(token_address)
            if honeypot_check.get('is_honeypot', True):
                reasons.append(f"❌ REJET: Honeypot détecté")
                return 0, reasons
        except Exception as e:
            self.logger.error(f"ÉCHEC CRITIQUE honeypot check pour {token_address}: {e}")
            # Sécurité maximale: rejet si impossible de vérifier
            reasons.append(f"❌ REJET: Impossible de vérifier honeypot (erreur critique)")
            return 0, reasons

        # === PHASE 1.5: VÉRIFICATIONS ON-CHAIN OBLIGATOIRES ===
        # Ces vérifications sont CRITIQUES pour atteindre 70%+ win-rate
        # Car elles détectent les scams que les APIs externes peuvent manquer
        try:
            addr = token_data['token_address']

            # Contract verified sur BaseScan ?
            try:
                is_verified = self.basescan.is_contract_verified(addr)
                if not is_verified:
                    reasons.append(f"❌ REJET: Contrat non vérifié sur BaseScan")
                    return 0, reasons
            except Exception as e:
                self.logger.warning(f"Impossible de vérifier contract verified pour {addr}: {e}")
                # Si BaseScan API échoue, on continue (pas critique)
                reasons.append(f"⚠️ WARNING: Vérification contract skipped (API BaseScan indisponible)")

            # Liquidity locked ?
            try:
                is_locked = self.basescan.is_liquidity_locked(addr, min_hours=72)
                if not is_locked:
                    reasons.append(f"❌ REJET: Liquidité non lockée (minimum 72h requis)")
                    return 0, reasons
            except Exception as e:
                self.logger.warning(f"Impossible de vérifier liquidity lock pour {addr}: {e}")
                # Lock non vérifiable → risque élevé → rejet par sécurité
                reasons.append(f"❌ REJET: Impossible de vérifier liquidity lock (sécurité)")
                return 0, reasons

            # No mint function ?
            try:
                has_mint = self.web3_manager.has_mint_function(addr)
                if has_mint:
                    reasons.append(f"❌ REJET: Fonction mint détectée (inflation possible)")
                    return 0, reasons
            except Exception as e:
                self.logger.warning(f"Impossible de vérifier mint function pour {addr}: {e}")
                # Si impossible de vérifier, on continue (fallback: honeypot check a déjà validé)
                reasons.append(f"⚠️ WARNING: Vérification mint function skipped")

        except Exception as e:
            self.logger.error(f"ÉCHEC CRITIQUE vérifications on-chain pour {token_address}: {e}")
            reasons.append(f"❌ REJET: Échec vérification sécurité on-chain")
            return 0, reasons

        # === PHASE 2: SCORING (Si le token a passé tous les rejets) ===
        score = 100.0  # Score parfait par défaut (tous critères passés)

        # Log d'approbation (pour debug)
        symbol = token_data.get('symbol', '???')
        self.logger.info(
            f"✅ APPROUVÉ: {symbol} | "
            f"age={age_hours:.1f}h | liq=${liq:,.0f} | mc=${mc:,.0f} | "
            f"vol1h=${vol1h:,.0f} | vol5m=${vol5m:,.0f} | "
            f"Δ5m={pc5m:+.1f}% | Δ1h={pc1h:+.1f}% | holders={holders}"
        )

        reasons.append(f"✅ Token approuvé: {symbol}")
        reasons.append(f"Âge: {age_hours:.1f}h")
        reasons.append(f"Liquidité: ${liq:,.0f}")
        reasons.append(f"Market Cap: ${mc:,.0f}")
        reasons.append(f"Volume 1h: ${vol1h:,.0f}")
        reasons.append(f"Volume 5min: ${vol5m:,.0f}")
        reasons.append(f"Ratio vol 5m/1h: {ratio_5m_1h:.2f}")
        reasons.append(f"Δ Prix 5min: {pc5m:+.1f}%")
        reasons.append(f"Δ Prix 1h: {pc1h:+.1f}%")
        reasons.append(f"Holders: {holders}")

        return score, reasons

    def approve_token(self, token_data: Dict, score: float, reasons: List[str]):
        """Enregistre un token comme approuvé"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        analysis_json = json.dumps({
            'score': score,
            'reasons': reasons,
            'details': token_data # Inclure les détails bruts pour référence
        })

        cursor.execute('''
            INSERT OR REPLACE INTO approved_tokens
            (token_address, symbol, name, reason, score, analysis_data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            token_data['token_address'],
            token_data['symbol'],
            token_data['name'],
            f"Score: {score:.2f} - {', '.join(reasons)}",
            score,
            analysis_json
        ))

        conn.commit()
        conn.close()
        self.stats['total_approved'] += 1
        self.logger.info(f"✅ Token APPROUVE: {token_data['symbol']} ({token_data['token_address']}) - Score: {score:.2f}")

    def reject_token(self, token_data: Dict, reasons: List[str]):
        """Enregistre un token comme rejeté"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        analysis_json = json.dumps({
            'reasons': reasons,
            'details': token_data
        })

        cursor.execute('''
            INSERT OR REPLACE INTO rejected_tokens
            (token_address, symbol, name, reason, analysis_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            token_data['token_address'],
            token_data['symbol'],
            token_data['name'],
            ', '.join(reasons),
            analysis_json
        ))

        conn.commit()
        conn.close()
        self.stats['total_rejected'] += 1
        self.logger.info(f"❌ Token REJETE: {token_data['symbol']} ({token_data['token_address']}) - Raisons: {', '.join(reasons)}")

    def run_filter_cycle(self):
        """Exécute un cycle de filtrage : récupère les tokens découverts, les analyse, les approuve/rejette"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Récupérer les tokens découverts non encore filtrés (ni approuvés ni rejetés)
            cursor.execute('''
                SELECT * FROM discovered_tokens
                WHERE token_address NOT IN (SELECT token_address FROM approved_tokens)
                AND token_address NOT IN (SELECT token_address FROM rejected_tokens)
            ''')
            new_tokens = cursor.fetchall()

            if not new_tokens:
                self.logger.info("Aucun nouveau token à filtrer pour le moment")
                conn.close()
                return

            # Récupérer les noms des colonnes pour reconstruire les dictionnaires
            col_names = [description[0] for description in cursor.description]

            self.logger.info(f"{len(new_tokens)} nouveau(x) token(s) à analyser")

            for row in new_tokens:
                token_dict = dict(zip(col_names, row))
                self.stats['total_analyzed'] += 1

                self.logger.info(f"Analyse du token: {token_dict.get('symbol', 'N/A')} ({token_dict['token_address']})")

                # === ENRICHISSEMENT DEXSCREENER ===
                # Scanner fournit seulement données on-chain (age_hours, symbol, name, decimals)
                # Filter enrichit avec données market DexScreener pour scoring
                try:
                    token_address = token_dict['token_address']
                    dex_data = self.dexscreener.get_token_info(token_address)

                    if dex_data:
                        # Enrichir token_dict avec données DexScreener
                        token_dict['liquidity'] = dex_data.get('liquidity', 0)
                        token_dict['market_cap'] = dex_data.get('market_cap', 0)
                        token_dict['volume_24h'] = dex_data.get('volume_24h', 0)
                        token_dict['volume_1h'] = dex_data.get('volume_1h', 0)
                        token_dict['volume_5min'] = dex_data.get('volume_5min', 0)
                        token_dict['price_change_5m'] = dex_data.get('price_change_5m', 0)
                        token_dict['price_change_1h'] = dex_data.get('price_change_1h', 0)
                        token_dict['price_usd'] = dex_data.get('price_usd', 0)
                        token_dict['holder_count'] = dex_data.get('holder_count', 0)
                        token_dict['owner_percentage'] = dex_data.get('owner_percentage', 100.0)
                        token_dict['buy_tax'] = dex_data.get('buy_tax')
                        token_dict['sell_tax'] = dex_data.get('sell_tax')
                        token_dict['pair_created_at'] = dex_data.get('pair_created_at')

                        self.logger.debug(f"✅ Enrichissement DexScreener réussi pour {token_dict['symbol']}")
                    else:
                        self.logger.warning(f"⚠️ DexScreener: Aucune donnée pour {token_address[:8]}... (token trop récent?)")
                        # Rejeter si DexScreener ne trouve rien (token non listé ou trop récent)
                        self.reject_token(token_dict, ["❌ REJET: Token non trouvé sur DexScreener (trop récent ou non listé)"])
                        continue

                except Exception as e:
                    self.logger.error(f"❌ Échec enrichissement DexScreener pour {token_address[:8]}...: {e}")
                    # Rejeter en cas d'échec enrichissement (sécurité)
                    self.reject_token(token_dict, [f"❌ REJET: Échec enrichissement données market ({str(e)[:50]})"])
                    continue

                # Calculer le score
                score, reasons = self.calculate_score(token_dict)

                if score >= self.score_threshold:
                    self.approve_token(token_dict, score, reasons)
                else:
                    self.reject_token(token_dict, reasons)

        except Exception as e:
            self.logger.error(f"Erreur lors du cycle de filtrage: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            conn.close()

    def run(self):
        """Boucle principale du filtre avec watchdog anti-freeze"""
        self.logger.info("Filter démarré...")
        self.logger.info(f"Mode: {self.trading_mode}")
        self.logger.info(f"Seuil de score: {self.score_threshold}")

        last_success = datetime.now()
        max_silence = timedelta(minutes=20)

        while True:
            try:
                self.logger.info("Démarrage d'un cycle de filtrage...")
                self.run_filter_cycle()
                last_success = datetime.now()  # Mise à jour si succès
                self.logger.info(f"Cycle terminé. Stats: Analyzed={self.stats['total_analyzed']}, Approved={self.stats['total_approved']}, Rejected={self.stats['total_rejected']}")

                # Attendre avant le prochain cycle
                filter_interval = int(os.getenv('FILTER_INTERVAL_SECONDS', '60'))
                time.sleep(filter_interval)

            except KeyboardInterrupt:
                self.logger.info("Filter arrêté par l'utilisateur.")
                break
            except Exception as e:
                self.logger.exception(f"Erreur critique dans run_filter_cycle: {e}")

                # Watchdog: vérifier si le bot est bloqué depuis trop longtemps
                silence_duration = datetime.now() - last_success
                if silence_duration > max_silence:
                    self.logger.critical(f"⚠️ WATCHDOG: Aucun cycle réussi depuis {silence_duration.total_seconds()/60:.1f} min → redémarrage forcé")
                    os.execv(sys.executable, ['python3'] + sys.argv)  # Redémarrage auto

                time.sleep(30)  # Attendre avant de réessayer

if __name__ == "__main__":
    filter_bot = AdvancedFilter()
    try:
        filter_bot.run()
    except KeyboardInterrupt:
        print("\nFilter arrêté.")
    except Exception as e:
        print(f"Erreur fatale: {e}")

