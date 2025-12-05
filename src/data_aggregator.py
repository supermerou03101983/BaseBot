#!/usr/bin/env python3
"""
Data Aggregator - Orchestrateur des sources de données
Hiérarchie: On-chain (prioritaire) → DexScreener (gratuit) → BirdEye (optionnel) → CoinGecko (fallback)
"""

import os
from typing import Dict, Optional
from web3 import Web3
import logging

from onchain_fetcher import OnChainFetcher
from api_fallbacks import DexScreenerFreeAPI, CoinGeckoFreeAPI, BlockchairAPI, BaseScanAPI


class DataAggregator:
    """
    Agrégateur de données multi-sources avec fallbacks intelligents

    Architecture:
    1. On-Chain (prioritaire) - Toujours disponible, pas de rate limit
    2. DexScreener (gratuit) - 300 req/min, pas de clé
    3. BirdEye (optionnel) - Nécessite clé API valide
    4. CoinGecko (fallback) - 10-50 req/min gratuit
    5. Blockchair/BaseScan (fallback holders) - 1-5 req/sec gratuit
    """

    def __init__(self, w3: Web3, birdeye_api_key: str = None, basescan_api_key: str = None,
                 coingecko_api_key: str = None, enable_onchain_fallback: bool = True):
        """
        Args:
            w3: Instance Web3 connectée à Base
            birdeye_api_key: Clé API BirdEye (optionnel)
            basescan_api_key: Clé API BaseScan (optionnel)
            coingecko_api_key: Clé API CoinGecko (optionnel)
            enable_onchain_fallback: Activer les fallbacks on-chain (True recommandé)
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        # Source primaire: On-chain
        self.onchain = OnChainFetcher(w3) if enable_onchain_fallback else None

        # Sources secondaires: APIs gratuites
        self.dexscreener = DexScreenerFreeAPI()
        self.coingecko = CoinGeckoFreeAPI(api_key=coingecko_api_key)
        self.blockchair = BlockchairAPI()
        self.basescan = BaseScanAPI(api_key=basescan_api_key) if basescan_api_key else None

        # Source tertiaire: BirdEye (optionnel)
        self.birdeye = None
        if birdeye_api_key and birdeye_api_key not in ['your_birdeye_api_key_here', 'YOUR_BIRDEYE_API_KEY_HERE', '']:
            try:
                # Import dynamique pour éviter erreur si BirdEye non disponible
                from web3_utils import BirdEyeAPI
                self.birdeye = BirdEyeAPI(api_key=birdeye_api_key)
                self.logger.info("✅ BirdEye API activée")
            except Exception as e:
                self.logger.warning(f"⚠️  BirdEye API non disponible: {e}")

        self.enable_onchain = enable_onchain_fallback

        # Statistiques d'utilisation
        self.stats = {
            'onchain_success': 0,
            'dexscreener_success': 0,
            'birdeye_success': 0,
            'coingecko_success': 0,
            'blockchair_success': 0,
            'basescan_success': 0,
            'total_queries': 0,
            'failed_queries': 0
        }

    def get_enriched_token_data(self, token_address: str, pair_address: str = None) -> Dict:
        """
        Récupère les données enrichies d'un token via toutes les sources disponibles

        Stratégie de fallback:
        1. DexScreener (priorité 1) - Données complètes, gratuit, rapide
        2. On-chain (priorité 2) - Si DexScreener échoue ou données incomplètes
        3. BirdEye (priorité 3) - Si disponible, compléter les données manquantes
        4. CoinGecko (priorité 4) - Données basiques si tout échoue
        5. Blockchair/BaseScan (priorité 5) - Holders uniquement

        Args:
            token_address: Adresse du token
            pair_address: Adresse du pool (optionnel, accélère on-chain)

        Returns:
            Dict avec toutes les données disponibles
        """
        self.stats['total_queries'] += 1

        result = {
            # Données de base
            'token_address': token_address.lower(),
            'pair_address': pair_address.lower() if pair_address else '',

            # Liquidité
            'liquidity_usd': 0.0,

            # Volume
            'volume_24h': 0.0,
            'volume_1h': 0.0,
            'volume_5min': 0.0,

            # Prix
            'price_usd': 0.0,
            'price_eth': 0.0,

            # Momentum
            'price_change_5min': 0.0,
            'price_change_1h': 0.0,
            'price_change_24h': 0.0,

            # Distribution
            'holder_count': 0,
            'owner_percentage': 100.0,

            # Market data
            'market_cap': 0.0,
            'fdv': 0.0,

            # Metadata
            'dex_id': '',
            'data_sources': [],
            'timestamp': int(time.time())
        }

        # 1️⃣ DEXSCREENER (Priorité 1 - Gratuit, complet, rapide)
        try:
            dex_data = self.dexscreener.get_token_info(token_address, chain="base")

            if dex_data:
                self.stats['dexscreener_success'] += 1
                result['data_sources'].append('dexscreener')

                # Mise à jour avec données DexScreener
                result['pair_address'] = dex_data.get('pair_address', result['pair_address'])
                result['dex_id'] = dex_data.get('dex_id', '')
                result['liquidity_usd'] = dex_data.get('liquidity_usd', 0.0)
                result['volume_24h'] = dex_data.get('volume_24h', 0.0)
                result['volume_1h'] = dex_data.get('volume_1h', 0.0)
                result['price_usd'] = dex_data.get('price_usd', 0.0)
                result['price_eth'] = dex_data.get('price_native', 0.0)
                result['price_change_5min'] = dex_data.get('price_change_5m', 0.0)
                result['price_change_1h'] = dex_data.get('price_change_1h', 0.0)
                result['price_change_24h'] = dex_data.get('price_change_24h', 0.0)
                result['market_cap'] = dex_data.get('market_cap', 0.0)
                result['fdv'] = dex_data.get('fdv', 0.0)

                self.logger.info(f"✅ DexScreener: ${result['liquidity_usd']:,.0f} liq, ${result['volume_1h']:,.0f} vol 1h")

                # Si données complètes (liquidité + volume_1h > 0), continuer pour enrichir holders
                # Sinon essayer on-chain
                if result['liquidity_usd'] > 0 and result['volume_1h'] > 0:
                    pass  # DexScreener suffit, on complète juste les holders
                else:
                    self.logger.warning("⚠️  DexScreener données incomplètes, fallback on-chain")

        except Exception as e:
            self.logger.warning(f"⚠️  DexScreener failed: {e}")

        # 2️⃣ ON-CHAIN FALLBACK (Si DexScreener incomplet ou erreur)
        if self.enable_onchain and self.onchain and (result['liquidity_usd'] == 0 or result['volume_1h'] == 0):
            try:
                onchain_data = self.onchain.get_token_data_onchain(token_address, result['pair_address'] or None)

                if onchain_data and onchain_data['liquidity_usd'] > 0:
                    self.stats['onchain_success'] += 1
                    result['data_sources'].append('onchain')

                    # Compléter/Remplacer avec données on-chain
                    if result['liquidity_usd'] == 0:
                        result['liquidity_usd'] = onchain_data['liquidity_usd']
                    if result['volume_1h'] == 0:
                        result['volume_1h'] = onchain_data['volume_1h']
                    if result['volume_5min'] == 0:
                        result['volume_5min'] = onchain_data['volume_5min']
                    if result['price_change_1h'] == 0:
                        result['price_change_1h'] = onchain_data['price_change_1h']
                    if result['price_change_5min'] == 0:
                        result['price_change_5min'] = onchain_data['price_change_5min']
                    if result['holder_count'] == 0:
                        result['holder_count'] = onchain_data['holders']

                    self.logger.info(f"✅ On-chain: ${result['liquidity_usd']:,.0f} liq, {result['holder_count']} holders")

            except Exception as e:
                self.logger.warning(f"⚠️  On-chain fallback failed: {e}")

        # 3️⃣ BIRDEYE (Si disponible et données encore incomplètes)
        if self.birdeye and (result['volume_1h'] == 0 or result['holder_count'] == 0):
            try:
                birdeye_data = self.birdeye.get_token_overview(token_address)

                if birdeye_data:
                    self.stats['birdeye_success'] += 1
                    result['data_sources'].append('birdeye')

                    # Compléter avec BirdEye
                    if result['liquidity_usd'] == 0:
                        result['liquidity_usd'] = birdeye_data.get('liquidity', 0.0)
                    if result['volume_24h'] == 0:
                        result['volume_24h'] = birdeye_data.get('v24hUSD', 0.0)
                    if result['price_usd'] == 0:
                        result['price_usd'] = birdeye_data.get('price', 0.0)
                    if result['holder_count'] == 0:
                        result['holder_count'] = birdeye_data.get('holder', 0)
                    if result['market_cap'] == 0:
                        result['market_cap'] = birdeye_data.get('mc', 0.0)

                    self.logger.info(f"✅ BirdEye: {result['holder_count']} holders")

            except Exception as e:
                self.logger.warning(f"⚠️  BirdEye failed: {e}")

        # 4️⃣ COINGECKO (Fallback données market cap et prix si tout échoue)
        if result['market_cap'] == 0 or result['price_usd'] == 0:
            try:
                cg_data = self.coingecko.get_token_data(token_address, platform="base")

                if cg_data:
                    self.stats['coingecko_success'] += 1
                    result['data_sources'].append('coingecko')

                    if result['market_cap'] == 0:
                        result['market_cap'] = cg_data.get('market_cap', 0.0)
                    if result['volume_24h'] == 0:
                        result['volume_24h'] = cg_data.get('volume_24h', 0.0)
                    if result['price_usd'] == 0:
                        result['price_usd'] = cg_data.get('price_usd', 0.0)
                    if result['price_change_24h'] == 0:
                        result['price_change_24h'] = cg_data.get('price_change_24h', 0.0)

                    self.logger.info(f"✅ CoinGecko: ${result['market_cap']:,.0f} mcap")

            except Exception as e:
                self.logger.warning(f"⚠️  CoinGecko failed: {e}")

        # 5️⃣ BLOCKCHAIR/BASESCAN (Fallback holders uniquement)
        if result['holder_count'] < 20:  # Seuil suspicieusement bas
            try:
                # Essayer Blockchair (gratuit, pas de clé)
                blockchair_holders = self.blockchair.get_holder_count(token_address)
                if blockchair_holders > result['holder_count']:
                    self.stats['blockchair_success'] += 1
                    result['data_sources'].append('blockchair')
                    result['holder_count'] = blockchair_holders
                    self.logger.info(f"✅ Blockchair: {result['holder_count']} holders")

                # Si BaseScan disponible et holders toujours bas
                if self.basescan and result['holder_count'] < 50:
                    basescan_data = self.basescan.get_token_holder_list(token_address, limit=100)
                    if basescan_data:
                        self.stats['basescan_success'] += 1
                        result['data_sources'].append('basescan')
                        result['holder_count'] = basescan_data.get('holder_count', result['holder_count'])
                        result['owner_percentage'] = basescan_data.get('owner_percentage', result['owner_percentage'])
                        self.logger.info(f"✅ BaseScan: {result['holder_count']} holders, {result['owner_percentage']:.1f}% owner")

            except Exception as e:
                self.logger.warning(f"⚠️  Holders fallback failed: {e}")

        # Validation finale
        if result['liquidity_usd'] == 0 and result['volume_1h'] == 0:
            self.stats['failed_queries'] += 1
            self.logger.error(f"❌ Aucune donnée disponible pour {token_address}")
            result['data_sources'].append('failed')

        return result

    def get_stats(self) -> Dict:
        """Retourne les statistiques d'utilisation des sources"""
        return self.stats.copy()

    def reset_stats(self):
        """Réinitialise les statistiques"""
        for key in self.stats:
            self.stats[key] = 0


# Import time pour timestamp
import time


if __name__ == "__main__":
    # Test avec configuration réelle
    import os
    from dotenv import load_dotenv

    load_dotenv()

    print("\n🧪 Test DataAggregator\n")

    # Connexion Web3
    rpc_url = os.getenv('RPC_URL', 'https://mainnet.base.org')
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        print("❌ Connexion Web3 échouée")
        exit(1)

    print(f"✅ Connecté à Base via {rpc_url}\n")

    # Initialiser aggregator
    aggregator = DataAggregator(
        w3=w3,
        birdeye_api_key=os.getenv('BIRDEYE_API_KEY'),
        basescan_api_key=os.getenv('ETHERSCAN_API_KEY'),
        coingecko_api_key=os.getenv('COINGECKO_API_KEY'),
        enable_onchain_fallback=True
    )

    # Test sur BRETT (token connu)
    test_token = "0x532f27101965dd16442E59d40670FaF5eBB142E4"
    print(f"🔍 Test sur BRETT: {test_token}\n")

    data = aggregator.get_enriched_token_data(test_token)

    print(f"📊 Résultats:")
    print(f"  • Sources: {', '.join(data['data_sources'])}")
    print(f"  • Liquidité: ${data['liquidity_usd']:,.0f}")
    print(f"  • Volume 24h: ${data['volume_24h']:,.0f}")
    print(f"  • Volume 1h: ${data['volume_1h']:,.0f}")
    print(f"  • Volume 5min: ${data['volume_5min']:,.0f}")
    print(f"  • Prix: ${data['price_usd']:.8f}")
    print(f"  • Δ 5min: {data['price_change_5min']:+.2f}%")
    print(f"  • Δ 1h: {data['price_change_1h']:+.2f}%")
    print(f"  • Δ 24h: {data['price_change_24h']:+.2f}%")
    print(f"  • Market Cap: ${data['market_cap']:,.0f}")
    print(f"  • Holders: {data['holder_count']}")
    print(f"  • Owner%: {data['owner_percentage']:.1f}%")

    print(f"\n📈 Stats Aggregator:")
    stats = aggregator.get_stats()
    for key, value in stats.items():
        print(f"  • {key}: {value}")
