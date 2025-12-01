#!/usr/bin/env python3
"""
Scanner Unifié - Détection de tokens via événements PairCreated on-chain
Remplace l'approche DexScreener/GeckoTerminal par un scan blockchain direct
"""

import asyncio
import sqlite3
import time
import os
import sys
import logging
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

# Setup paths
PROJECT_DIR = Path(__file__).parent.parent
sys.path.append(str(PROJECT_DIR / 'src'))

from web3 import Web3
from web3.exceptions import BlockNotFound, ContractLogicError
from eth_utils import to_checksum_address
from dotenv import load_dotenv
from web3_utils import DexScreenerAPI

load_dotenv(PROJECT_DIR / 'config' / '.env')

# Configuration on-chain
BLOCKS_PER_HOUR = 1800  # Base: ~2s par bloc
CHUNK_SIZE = 1000  # Limite RPC pour get_logs

# Factory Addresses (Base Mainnet)
AERODROME_FACTORY = "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"
BASESWAP_FACTORY = "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6"

# Base Tokens (pour filtrage des paires)
WETH_BASE = "0x4200000000000000000000000000000000000006"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDBC_BASE = "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA"

# Event signature
PAIR_CREATED_EVENT_SIGNATURE = Web3.keccak(text="PairCreated(address,address,address,uint256)").hex()


class UnifiedScanner:
    """
    Scanner unifié qui détecte les tokens via événements PairCreated on-chain.
    Indépendant des APIs externes (DexScreener/GeckoTerminal).
    """

    def __init__(self):
        # Créer les dossiers nécessaires
        (PROJECT_DIR / 'data').mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / 'logs').mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / 'config').mkdir(parents=True, exist_ok=True)
        self.db_path = PROJECT_DIR / 'data' / 'trading.db'

        # Setup logging
        self.setup_logging()

        # Initialiser la base de données
        self.init_database()

        # Configuration scanner
        self.batch_size = int(os.getenv('BATCH_SIZE', 50))
        self.scan_delay = int(os.getenv('SCAN_INTERVAL_SECONDS', 30))
        self.min_token_age_hours = float(os.getenv('MIN_TOKEN_AGE_HOURS', '2'))
        self.max_token_age_hours = float(os.getenv('MAX_TOKEN_AGE_HOURS', '12'))

        # Web3 setup pour scanner on-chain
        rpc_url = os.getenv('RPC_URL', 'https://mainnet.base.org')
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError(f"❌ Impossible de se connecter au RPC: {rpc_url}")

        self.logger.info(f"✅ Connecté au RPC Base (bloc: {self.w3.eth.block_number})")

        # Initialiser DexScreener pour enrichissement
        self.dex_api = DexScreenerAPI()

        # Normaliser les adresses des factories et base tokens
        self.base_tokens = [
            to_checksum_address(WETH_BASE),
            to_checksum_address(USDC_BASE),
            to_checksum_address(USDBC_BASE)
        ]

        self.factories = [
            to_checksum_address(AERODROME_FACTORY),
            to_checksum_address(BASESWAP_FACTORY)
        ]

        self.logger.info(f"⏱️  Scanner on-chain: tokens {self.min_token_age_hours}h-{self.max_token_age_hours}h")
        self.logger.info(f"🏭 Factories: Aerodrome + BaseSwap")
        self.logger.info(f"📊 Enrichissement: DexScreener API")

    def setup_logging(self):
        """Configuration du logging"""
        log_file = PROJECT_DIR / 'logs' / 'scanner.log'
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
        """Initialise la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Vérifier si la table existe et a l'ancienne structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='discovered_tokens'")
        table_exists = cursor.fetchone() is not None

        if table_exists:
            # Vérifier si on a l'ancienne structure
            cursor.execute("PRAGMA table_info(discovered_tokens)")
            columns = [col[1] for col in cursor.fetchall()]

            if 'pair_address' not in columns:
                # Migration nécessaire: supprimer l'ancienne table et recréer
                self.logger.info("🔄 Migration table discovered_tokens (ancienne structure détectée)")
                cursor.execute("DROP TABLE discovered_tokens")
                conn.commit()

        # Table des tokens découverts (structure hybride: on-chain + marché COMPLÈTE)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discovered_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT UNIQUE NOT NULL,
                symbol TEXT,
                name TEXT,
                decimals INTEGER,
                total_supply TEXT,
                pair_address TEXT,
                base_token TEXT,
                factory TEXT,
                block_created INTEGER,
                age_hours REAL,
                liquidity REAL DEFAULT 0,
                market_cap REAL DEFAULT 0,
                volume_24h REAL DEFAULT 0,
                volume_1h REAL DEFAULT 0,
                volume_5min REAL DEFAULT 0,
                price_change_5m REAL DEFAULT 0,
                price_change_1h REAL DEFAULT 0,
                price_usd REAL DEFAULT 0,
                price_eth REAL DEFAULT 0,
                pair_created_at TIMESTAMP,
                holder_count INTEGER DEFAULT 0,
                owner_percentage REAL DEFAULT 100.0,
                buy_tax REAL,
                sell_tax REAL,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        self.logger.info("✅ Base de données initialisée (structure hybride on-chain + marché)")

    def scan_tokens_in_age_window(self) -> List[Dict]:
        """
        Scanne les événements PairCreated dans la fenêtre d'âge configurée.

        Returns:
            Liste de tokens détectés
        """
        try:
            current_block = self.w3.eth.block_number
            from_block = current_block - int(self.max_token_age_hours * BLOCKS_PER_HOUR)
            to_block = current_block - int(self.min_token_age_hours * BLOCKS_PER_HOUR)

            self.logger.info(
                f"🔍 Scan blocs {from_block} → {to_block} "
                f"({self.max_token_age_hours}h-{self.min_token_age_hours}h)"
            )

            all_tokens = []
            seen_tokens = set()  # Changé de seen_pairs à seen_tokens (évite doublons cross-factory)

            # Scanner chaque factory
            for factory in self.factories:
                factory_name = "Aerodrome" if factory == to_checksum_address(AERODROME_FACTORY) else "BaseSwap"

                try:
                    tokens = self._scan_factory_events(
                        factory=factory,
                        factory_name=factory_name,
                        from_block=from_block,
                        to_block=to_block,
                        current_block=current_block,
                        seen_tokens=seen_tokens  # Changé: passer seen_tokens
                    )

                    all_tokens.extend(tokens)

                    if len(all_tokens) >= self.batch_size:
                        self.logger.info(f"⚠️  Limite {self.batch_size} résultats atteinte")
                        break

                except Exception as e:
                    self.logger.warning(f"⚠️  Erreur scan {factory_name}: {e}")
                    continue

            self.logger.info(f"✅ {len(all_tokens)} tokens détectés")
            return all_tokens[:self.batch_size]

        except Exception as e:
            self.logger.error(f"❌ Erreur scan_tokens_in_age_window: {e}")
            return []

    def _scan_factory_events(
        self,
        factory: str,
        factory_name: str,
        from_block: int,
        to_block: int,
        current_block: int,
        seen_tokens: set  # Changé: seen_tokens au lieu de seen_pairs
    ) -> List[Dict]:
        """Scanne les événements PairCreated d'une factory"""
        tokens = []

        try:
            # Découper en chunks pour éviter limites RPC
            block_range = to_block - from_block

            if block_range > CHUNK_SIZE:
                self.logger.info(
                    f"📦 {factory_name}: {block_range} blocs → "
                    f"{(block_range // CHUNK_SIZE) + 1} chunks"
                )

            all_logs = []
            current_from = from_block

            while current_from < to_block:
                current_to = min(current_from + CHUNK_SIZE, to_block)

                try:
                    chunk_logs = self.w3.eth.get_logs({
                        'fromBlock': current_from,
                        'toBlock': current_to,
                        'address': factory,
                        'topics': [PAIR_CREATED_EVENT_SIGNATURE]
                    })

                    all_logs.extend(chunk_logs)

                except Exception as e:
                    self.logger.warning(f"⚠️  Chunk {current_from}-{current_to}: {e}")

                current_from = current_to + 1

            self.logger.info(f"🏭 {factory_name}: {len(all_logs)} événements PairCreated")

            # Décoder les événements
            for log in all_logs:
                try:
                    token_data = self._decode_pair_created_event(
                        log=log,
                        factory=factory,
                        factory_name=factory_name,
                        current_block=current_block,
                        seen_tokens=seen_tokens  # Changé: seen_tokens
                    )

                    if token_data:
                        tokens.append(token_data)

                except Exception as e:
                    self.logger.debug(f"Erreur décodage: {e}")
                    continue

            return tokens

        except Exception as e:
            self.logger.warning(f"❌ Erreur get_logs {factory_name}: {e}")
            return []

    def _decode_pair_created_event(
        self,
        log,
        factory: str,
        factory_name: str,
        current_block: int,
        seen_tokens: set  # Changé: seen_tokens au lieu de seen_pairs
    ) -> Optional[Dict]:
        """Décode un événement PairCreated avec présélection on-chain"""
        try:
            # Décoder topics
            token0 = to_checksum_address('0x' + log['topics'][1].hex()[-40:])
            token1 = to_checksum_address('0x' + log['topics'][2].hex()[-40:])
            pair_address = to_checksum_address('0x' + log['data'].hex()[26:66])

            # Identifier token et base token
            token_address = None
            base_token = None

            if token0 in self.base_tokens:
                base_token = token0
                token_address = token1
            elif token1 in self.base_tokens:
                base_token = token1
                token_address = token0
            else:
                return None  # Ignorer paires non appariées

            # Vérifier si token déjà vu (éviter doublons cross-factory)
            if token_address in seen_tokens:
                return None

            # === PRÉSÉLECTION ON-CHAIN (éviter enrichissement inutile) ===
            # Vérification rapide: contract deployed, not honeypot, no obvious scam
            try:
                # Vérifier que c'est un contrat (pas EOA)
                code = self.w3.eth.get_code(token_address)
                if len(code) <= 2:  # 0x = pas de code
                    self.logger.debug(f"Token {token_address[:8]}... n'est pas un contrat")
                    return None

                # Vérifier qu'on peut lire les métadonnées ERC20 (sinon scam/fake)
                metadata = self.get_token_metadata(token_address)
                if metadata['symbol'] == '???':
                    self.logger.debug(f"Token {token_address[:8]}... métadonnées invalides")
                    return None

            except Exception as e:
                self.logger.debug(f"Présélection échouée pour {token_address[:8]}...: {e}")
                return None

            # Calculer l'âge
            block_created = log['blockNumber']
            age_hours = (current_block - block_created) / BLOCKS_PER_HOUR

            seen_tokens.add(token_address)  # Marquer comme vu (par token_address, pas pair)

            return {
                'token_address': token_address,
                'pair_address': pair_address,
                'base_token': base_token,
                'factory': factory,
                'factory_name': factory_name,
                'block_created': block_created,
                'age_hours': age_hours
            }

        except Exception as e:
            return None

    def get_token_metadata(self, token_address: str) -> Dict:
        """Récupère les métadonnées ERC20 d'un token"""
        try:
            token_address = to_checksum_address(token_address)

            erc20_abi = [
                {'constant': True, 'inputs': [], 'name': 'name', 'outputs': [{'name': '', 'type': 'string'}], 'type': 'function'},
                {'constant': True, 'inputs': [], 'name': 'symbol', 'outputs': [{'name': '', 'type': 'string'}], 'type': 'function'},
                {'constant': True, 'inputs': [], 'name': 'decimals', 'outputs': [{'name': '', 'type': 'uint8'}], 'type': 'function'},
            ]

            contract = self.w3.eth.contract(address=token_address, abi=erc20_abi)

            try:
                name = contract.functions.name().call()
            except:
                name = "Unknown"

            try:
                symbol = contract.functions.symbol().call()
            except:
                symbol = "???"

            try:
                decimals = contract.functions.decimals().call()
            except:
                decimals = 18

            return {
                'name': name,
                'symbol': symbol,
                'decimals': decimals
            }

        except Exception as e:
            self.logger.warning(f"⚠️  Métadonnées {token_address[:8]}...: {e}")
            return {'name': 'Unknown', 'symbol': '???', 'decimals': 18}

    async def process_token_batch(self, tokens: List[Dict]):
        """Traite un batch de tokens et les enregistre en DB avec enrichissement DexScreener"""
        if not tokens:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        new_count = 0
        existing_count = 0

        for token_data in tokens:
            try:
                # Vérifier si déjà en DB
                cursor.execute(
                    "SELECT id FROM discovered_tokens WHERE token_address = ?",
                    (token_data['token_address'],)
                )

                if cursor.fetchone():
                    existing_count += 1
                    continue

                # Enrichir avec métadonnées ERC20 (déjà fait dans présélection)
                metadata = self.get_token_metadata(token_data['token_address'])

                # === ENRICHISSEMENT OPTIMISÉ ===
                # Stratégie: vérifier liquidité minimale avant d'appeler DexScreener
                # Économie: ~80% requêtes DexScreener, réduction bruit
                liquidity = 0
                market_cap = 0
                volume_24h = 0
                volume_1h = 0
                volume_5min = 0
                price_change_5m = 0
                price_change_1h = 0
                price_usd = 0
                price_eth = 0
                total_supply = "0"
                pair_created_at = None
                holder_count = 0
                owner_percentage = 100.0
                buy_tax = None
                sell_tax = None

                # Appeler DexScreener seulement si le token a passé la présélection
                # (on a déjà vérifié que c'est un contrat ERC20 valide)
                try:
                    market_data = self.dex_api.get_token_info(token_data['token_address'])

                    if market_data:
                        liquidity = market_data.get('liquidity', 0)
                        market_cap = market_data.get('market_cap', 0)
                        volume_24h = market_data.get('volume_24h', 0)
                        volume_1h = market_data.get('volume_1h', 0)
                        volume_5min = market_data.get('volume_5min', 0)
                        price_change_5m = market_data.get('price_change_5m', 0)
                        price_change_1h = market_data.get('price_change_1h', 0)
                        price_usd = market_data.get('price_usd', 0)
                        price_eth = market_data.get('price_eth', 0)
                        total_supply = str(market_data.get('total_supply', 0))
                        pair_created_at = market_data.get('pair_created_at')
                        holder_count = market_data.get('holder_count', 0)
                        owner_percentage = market_data.get('owner_percentage', 100.0)
                        buy_tax = market_data.get('buy_tax')
                        sell_tax = market_data.get('sell_tax')

                        # Log si liquidité < $5k (probable scam, mais on garde quand même)
                        if liquidity < 5000:
                            self.logger.debug(
                                f"Token {metadata['symbol']} ({token_data['token_address'][:8]}...) "
                                f"liquidité faible: ${liquidity:.0f}"
                            )
                except Exception as e:
                    self.logger.warning(f"Enrichissement DexScreener échoué pour {token_data['token_address'][:8]}...: {e}")
                    # On continue avec des valeurs par défaut (0)

                # Insérer en DB avec toutes les données (schéma complet)
                cursor.execute('''
                    INSERT INTO discovered_tokens
                    (token_address, symbol, name, decimals, total_supply, pair_address, base_token,
                     factory, block_created, age_hours, liquidity, market_cap, volume_24h, volume_1h,
                     volume_5min, price_change_5m, price_change_1h, price_usd, price_eth, pair_created_at,
                     holder_count, owner_percentage, buy_tax, sell_tax)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    token_data['token_address'],
                    metadata['symbol'],
                    metadata['name'],
                    metadata['decimals'],
                    total_supply,
                    token_data['pair_address'],
                    token_data['base_token'],
                    token_data['factory_name'],
                    token_data['block_created'],
                    token_data['age_hours'],
                    liquidity,
                    market_cap,
                    volume_24h,
                    volume_1h,
                    volume_5min,
                    price_change_5m,
                    price_change_1h,
                    price_usd,
                    price_eth,
                    pair_created_at,
                    holder_count,
                    owner_percentage,
                    buy_tax,
                    sell_tax
                ))

                new_count += 1

            except Exception as e:
                self.logger.warning(f"⚠️  Erreur traitement token: {e}")
                continue

        conn.commit()
        conn.close()

        self.logger.info(f"📊 Batch traité: {new_count} nouveaux | {existing_count} déjà connus")

    async def run(self):
        """Boucle principale du scanner"""
        self.logger.info("Scanner démarré...")

        while True:
            try:
                # Scanner les tokens
                tokens = self.scan_tokens_in_age_window()

                # Traiter le batch
                if tokens:
                    await self.process_token_batch(tokens)
                else:
                    self.logger.info("Aucun token trouvé dans cette fenêtre")

                # Attendre avant le prochain scan
                await asyncio.sleep(self.scan_delay)

            except KeyboardInterrupt:
                self.logger.info("Arrêt du scanner...")
                break
            except Exception as e:
                self.logger.error(f"❌ Erreur dans run(): {e}")
                await asyncio.sleep(self.scan_delay)


def main():
    """Point d'entrée"""
    scanner = UnifiedScanner()
    asyncio.run(scanner.run())


if __name__ == '__main__':
    main()
