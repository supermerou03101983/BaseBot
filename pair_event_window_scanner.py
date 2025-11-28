#!/usr/bin/env python3
"""
Scanner On-Chain de Paires par Événements PairCreated
Détecte les tokens entre 2h et 12h d'âge via les logs blockchain
Sans dépendance à DexScreener/GeckoTerminal
"""

import logging
from typing import List, Dict, Optional
from web3 import Web3
from web3.exceptions import BlockNotFound, ContractLogicError
from eth_utils import to_checksum_address

# Configuration RPC et Factories
RPC_URL = "https://base.llamarpc.com"
BLOCKS_PER_HOUR = 1800  # Base: ~2s par bloc

# Factory Addresses (Base Mainnet)
AERODROME_FACTORY = "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"
BASESWAP_FACTORY = "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6"

# Base Tokens (pour filtrage des paires)
WETH_BASE = "0x4200000000000000000000000000000000000006"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDBC_BASE = "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA"

# ABI PairCreated Event
# event PairCreated(address indexed token0, address indexed token1, address pair, uint256)
PAIR_CREATED_EVENT_SIGNATURE = Web3.keccak(text="PairCreated(address,address,address,uint256)").hex()

class PairEventWindowScanner:
    """
    Scanner qui détecte les paires créées dans une fenêtre temporelle donnée
    en analysant directement les événements PairCreated sur la blockchain.
    """

    def __init__(self, rpc_url: str = RPC_URL, logger: Optional[logging.Logger] = None):
        """
        Initialise le scanner avec connexion Web3.

        Args:
            rpc_url: URL du RPC endpoint Base
            logger: Logger optionnel (créé si non fourni)
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.logger = logger or self._setup_logger()

        # Vérifier la connexion
        if not self.w3.is_connected():
            raise ConnectionError(f"❌ Impossible de se connecter au RPC: {rpc_url}")

        self.logger.info(f"✅ Connecté au RPC Base (latest block: {self.w3.eth.block_number})")

        # Normaliser les adresses
        self.base_tokens = [
            to_checksum_address(WETH_BASE),
            to_checksum_address(USDC_BASE),
            to_checksum_address(USDBC_BASE)
        ]

        self.factories = [
            to_checksum_address(AERODROME_FACTORY),
            to_checksum_address(BASESWAP_FACTORY)
        ]

    def _setup_logger(self) -> logging.Logger:
        """Configure un logger basique si aucun n'est fourni."""
        logger = logging.getLogger("PairEventScanner")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def scan_tokens_in_age_window(
        self,
        min_hours: float = 2.0,
        max_hours: float = 12.0,
        max_results: int = 100
    ) -> List[Dict]:
        """
        Scanne les tokens dont la paire a été créée entre min_hours et max_hours.

        Args:
            min_hours: Âge minimum du token (heures)
            max_hours: Âge maximum du token (heures)
            max_results: Nombre maximum de résultats à retourner

        Returns:
            Liste de dicts contenant:
            {
                'token_address': '0x...',
                'pair_address': '0x...',
                'base_token': '0x...',  # WETH/USDC/USDbC
                'factory': '0x...',
                'block_created': 12345,
                'age_hours': 5.2
            }
        """
        try:
            # 1. Récupérer le bloc actuel
            current_block = self.w3.eth.block_number
            self.logger.info(f"🔍 Scan depuis bloc {current_block}")

            # 2. Calculer la plage de blocs
            from_block = current_block - int(max_hours * BLOCKS_PER_HOUR)
            to_block = current_block - int(min_hours * BLOCKS_PER_HOUR)

            self.logger.info(
                f"📊 Fenêtre temporelle: {max_hours}h à {min_hours}h "
                f"(blocs {from_block} → {to_block})"
            )

            # 3. Scanner chaque factory
            all_tokens = []
            seen_pairs = set()

            for factory in self.factories:
                factory_name = "Aerodrome" if factory == to_checksum_address(AERODROME_FACTORY) else "BaseSwap"

                try:
                    tokens = self._scan_factory_events(
                        factory=factory,
                        factory_name=factory_name,
                        from_block=from_block,
                        to_block=to_block,
                        current_block=current_block,
                        seen_pairs=seen_pairs,
                        max_results=max_results - len(all_tokens)
                    )

                    all_tokens.extend(tokens)

                    if len(all_tokens) >= max_results:
                        self.logger.info(f"⚠️ Limite de {max_results} résultats atteinte")
                        break

                except Exception as e:
                    self.logger.warning(f"⚠️ Erreur scan {factory_name}: {e}")
                    continue

            self.logger.info(f"✅ {len(all_tokens)} tokens détectés dans la fenêtre {min_hours}h-{max_hours}h")
            return all_tokens

        except Exception as e:
            self.logger.error(f"❌ Erreur critique dans scan_tokens_in_age_window: {e}")
            return []

    def _scan_factory_events(
        self,
        factory: str,
        factory_name: str,
        from_block: int,
        to_block: int,
        current_block: int,
        seen_pairs: set,
        max_results: int
    ) -> List[Dict]:
        """
        Scanne les événements PairCreated d'une factory spécifique.

        Args:
            factory: Adresse de la factory
            factory_name: Nom de la factory (pour logs)
            from_block: Bloc de départ
            to_block: Bloc de fin
            current_block: Bloc actuel
            seen_pairs: Set des paires déjà vues (pour éviter doublons)
            max_results: Nombre max de résultats

        Returns:
            Liste de dicts de tokens découverts
        """
        tokens = []

        try:
            # 🔧 Découper en chunks de 1000 blocs (limite RPC)
            CHUNK_SIZE = 1000
            block_range = to_block - from_block

            if block_range > CHUNK_SIZE:
                self.logger.info(
                    f"📦 {factory_name}: Découpage en chunks de {CHUNK_SIZE} blocs "
                    f"({block_range} blocs total)"
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

                    if chunk_logs:
                        self.logger.debug(
                            f"  Chunk {current_from}-{current_to}: {len(chunk_logs)} événements"
                        )

                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Erreur chunk {current_from}-{current_to}: {e}"
                    )

                current_from = current_to + 1

            logs = all_logs
            self.logger.info(f"🏭 {factory_name}: {len(logs)} événements PairCreated trouvés")

            # Décoder chaque événement
            for log in logs:
                try:
                    token_data = self._decode_pair_created_event(
                        log=log,
                        factory=factory,
                        factory_name=factory_name,
                        current_block=current_block,
                        seen_pairs=seen_pairs
                    )

                    if token_data:
                        tokens.append(token_data)

                        if len(tokens) >= max_results:
                            break

                except Exception as e:
                    self.logger.debug(f"Erreur décodage log: {e}")
                    continue

            return tokens

        except Exception as e:
            self.logger.warning(f"❌ Erreur get_logs sur {factory_name}: {e}")
            return []

    def _decode_pair_created_event(
        self,
        log,
        factory: str,
        factory_name: str,
        current_block: int,
        seen_pairs: set
    ) -> Optional[Dict]:
        """
        Décode un événement PairCreated et retourne les données du token.

        Args:
            log: Log event de Web3
            factory: Adresse de la factory
            factory_name: Nom de la factory
            current_block: Bloc actuel
            seen_pairs: Set des paires déjà vues

        Returns:
            Dict avec données du token, ou None si rejeté
        """
        try:
            # Décoder les topics
            # topics[0] = event signature (déjà filtré)
            # topics[1] = token0 (indexed)
            # topics[2] = token1 (indexed)
            token0 = to_checksum_address('0x' + log['topics'][1].hex()[-40:])
            token1 = to_checksum_address('0x' + log['topics'][2].hex()[-40:])

            # Décoder les données (pair address, uint256)
            # Les 32 premiers octets = pair address
            pair_address = to_checksum_address('0x' + log['data'].hex()[26:66])

            # Vérifier si déjà traité
            if pair_address in seen_pairs:
                return None

            # Identifier le token et le base token
            token_address = None
            base_token = None

            if token0 in self.base_tokens:
                base_token = token0
                token_address = token1
            elif token1 in self.base_tokens:
                base_token = token1
                token_address = token0
            else:
                # Paire non appariée avec WETH/USDC/USDbC → ignorer
                return None

            # Calculer l'âge
            block_created = log['blockNumber']
            age_hours = (current_block - block_created) / BLOCKS_PER_HOUR

            # Marquer comme vu
            seen_pairs.add(pair_address)

            self.logger.debug(
                f"✅ {factory_name}: Token {token_address[:8]}... "
                f"(âge: {age_hours:.1f}h, bloc: {block_created})"
            )

            return {
                'token_address': token_address,
                'pair_address': pair_address,
                'base_token': base_token,
                'factory': factory,
                'factory_name': factory_name,
                'block_created': block_created,
                'age_hours': age_hours,
                'discovered_at': self.w3.eth.get_block(block_created)['timestamp']
            }

        except Exception as e:
            self.logger.debug(f"Erreur décodage événement: {e}")
            return None

    def get_token_metadata(self, token_address: str) -> Dict:
        """
        Récupère les métadonnées basiques d'un token (nom, symbole, decimals).

        Args:
            token_address: Adresse du token

        Returns:
            Dict avec name, symbol, decimals
        """
        try:
            token_address = to_checksum_address(token_address)

            # ABI minimal pour ERC20
            erc20_abi = [
                {'constant': True, 'inputs': [], 'name': 'name', 'outputs': [{'name': '', 'type': 'string'}], 'type': 'function'},
                {'constant': True, 'inputs': [], 'name': 'symbol', 'outputs': [{'name': '', 'type': 'string'}], 'type': 'function'},
                {'constant': True, 'inputs': [], 'name': 'decimals', 'outputs': [{'name': '', 'type': 'uint8'}], 'type': 'function'},
            ]

            contract = self.w3.eth.contract(address=token_address, abi=erc20_abi)

            # Récupérer les données (avec fallback)
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
            self.logger.warning(f"⚠️ Erreur récupération metadata {token_address}: {e}")
            return {
                'name': 'Unknown',
                'symbol': '???',
                'decimals': 18
            }


def main():
    """Fonction de test autonome."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    scanner = PairEventWindowScanner()
    tokens = scanner.scan_tokens_in_age_window(min_hours=2, max_hours=12, max_results=20)

    print(f"\n{'='*80}")
    print(f"📊 RÉSULTATS DU SCAN: {len(tokens)} tokens détectés")
    print(f"{'='*80}\n")

    for i, token in enumerate(tokens, 1):
        metadata = scanner.get_token_metadata(token['token_address'])

        base_symbol = "WETH" if token['base_token'] == WETH_BASE else "USDC/USDbC"

        print(f"{i}. {metadata['symbol']} ({metadata['name']})")
        print(f"   Token: {token['token_address']}")
        print(f"   Pair: {token['pair_address']}")
        print(f"   Factory: {token['factory_name']}")
        print(f"   Base: {base_symbol}")
        print(f"   Âge: {token['age_hours']:.1f}h (bloc {token['block_created']})")
        print()


if __name__ == '__main__':
    main()
