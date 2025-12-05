#!/usr/bin/env python3
"""
On-Chain Data Fetcher - Récupération 100% on-chain sans dépendance API
Fonctionne même si toutes les APIs externes tombent (BirdEye, DexScreener, etc.)
"""

import time
from typing import Dict, Optional, List
from web3 import Web3
import json


class OnChainFetcher:
    """
    Récupère les données critiques directement depuis la blockchain Base
    - Liquidité via getReserves()
    - Volume via Swap events
    - Holders via Transfer events
    - Prix ETH via CoinGecko fallback
    """

    # ABIs essentiels
    UNISWAP_V2_PAIR_ABI = json.loads('''[
        {"constant":true,"inputs":[],"name":"getReserves","outputs":[{"name":"reserve0","type":"uint112"},{"name":"reserve1","type":"uint112"},{"name":"blockTimestampLast","type":"uint32"}],"type":"function"},
        {"constant":true,"inputs":[],"name":"token0","outputs":[{"name":"","type":"address"}],"type":"function"},
        {"constant":true,"inputs":[],"name":"token1","outputs":[{"name":"","type":"address"}],"type":"function"},
        {"anonymous":false,"inputs":[{"indexed":true,"name":"sender","type":"address"},{"indexed":false,"name":"amount0In","type":"uint256"},{"indexed":false,"name":"amount1In","type":"uint256"},{"indexed":false,"name":"amount0Out","type":"uint256"},{"indexed":false,"name":"amount1Out","type":"uint256"},{"indexed":true,"name":"to","type":"address"}],"name":"Swap","type":"event"}
    ]''')

    FACTORY_ABI = json.loads('''[
        {"constant":true,"inputs":[{"name":"","type":"address"},{"name":"","type":"address"}],"name":"getPair","outputs":[{"name":"","type":"address"}],"type":"function"}
    ]''')

    ERC20_ABI = json.loads('''[
        {"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"}
    ]''')

    # Adresses Base mainnet
    WETH = "0x4200000000000000000000000000000000000006"
    USDBC = "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA"
    USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

    # Factories
    UNISWAP_V3_FACTORY = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
    AERODROME_FACTORY = "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"
    BASESWAP_FACTORY = "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6"

    def __init__(self, w3: Web3):
        """
        Args:
            w3: Instance Web3 connectée à Base mainnet
        """
        self.w3 = w3
        self.eth_price_cache = {'price': 3000.0, 'timestamp': 0}  # Cache 5min
        self.cache_ttl = 300  # 5 minutes

    def get_pair_address(self, token_address: str, factory_address: str = None) -> Optional[str]:
        """
        Trouve l'adresse du pool pour un token
        Essaie WETH puis USDC puis USDbC
        """
        if factory_address is None:
            factory_address = self.AERODROME_FACTORY  # Par défaut Aerodrome

        factory = self.w3.eth.contract(
            address=Web3.to_checksum_address(factory_address),
            abi=self.FACTORY_ABI
        )

        token = Web3.to_checksum_address(token_address)

        # Essayer WETH, USDC, USDbC
        for base_token in [self.WETH, self.USDC, self.USDBC]:
            try:
                pair = factory.functions.getPair(token, Web3.to_checksum_address(base_token)).call()
                if pair != "0x0000000000000000000000000000000000000000":
                    return pair.lower()
            except Exception:
                continue

        return None

    def get_pool_liquidity_usd(self, token_address: str, pair_address: str = None) -> float:
        """
        Récupère la liquidité USD du pool via getReserves()

        Returns:
            Liquidité en USD (reserve de base * prix base)
        """
        try:
            # Si pas de pair fournie, la chercher
            if pair_address is None:
                pair_address = self.get_pair_address(token_address, self.AERODROME_FACTORY)
                if pair_address is None:
                    pair_address = self.get_pair_address(token_address, self.BASESWAP_FACTORY)
                if pair_address is None:
                    return 0.0

            pool = self.w3.eth.contract(
                address=Web3.to_checksum_address(pair_address),
                abi=self.UNISWAP_V2_PAIR_ABI
            )

            # Récupérer reserves
            reserves = pool.functions.getReserves().call()
            token0 = pool.functions.token0().call().lower()
            token1 = pool.functions.token1().call().lower()

            # Identifier quelle reserve est la base (WETH/USDC/USDbC)
            base_tokens = [self.WETH.lower(), self.USDC.lower(), self.USDBC.lower()]

            if token0 in base_tokens:
                base_reserve = reserves[0] / 10**18
                base_token = token0
            elif token1 in base_tokens:
                base_reserve = reserves[1] / 10**18
                base_token = token1
            else:
                # Pas de base token connu
                return 0.0

            # Prix de la base
            if base_token in [self.USDC.lower(), self.USDBC.lower()]:
                base_price = 1.0  # Stablecoins
            else:
                base_price = self.get_eth_price_onchain()  # WETH

            liquidity_usd = base_reserve * base_price

            return liquidity_usd

        except Exception as e:
            print(f"❌ Erreur get_pool_liquidity_usd: {e}")
            return 0.0

    def get_volume_last_minutes(self, pair_address: str, minutes: int = 5) -> float:
        """
        Calcule le volume USD des swaps sur les X dernières minutes
        via les événements Swap

        Args:
            pair_address: Adresse du pool
            minutes: Nombre de minutes à analyser (5 ou 60)

        Returns:
            Volume en USD
        """
        try:
            to_block = self.w3.eth.block_number
            # Base: ~2 secondes par bloc = 30 blocs/minute
            blocks_per_minute = 30
            from_block = max(0, to_block - int(minutes * blocks_per_minute))

            # Topic Swap = keccak256("Swap(address,uint256,uint256,uint256,uint256,address)")
            swap_topic = self.w3.keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)").hex()

            logs = self.w3.eth.get_logs({
                'address': Web3.to_checksum_address(pair_address),
                'fromBlock': from_block,
                'toBlock': to_block,
                'topics': [swap_topic]
            })

            if not logs:
                return 0.0

            # Récupérer token0/token1 du pool
            pool = self.w3.eth.contract(
                address=Web3.to_checksum_address(pair_address),
                abi=self.UNISWAP_V2_PAIR_ABI
            )
            token0 = pool.functions.token0().call().lower()
            token1 = pool.functions.token1().call().lower()

            # Identifier base token
            base_tokens = [self.WETH.lower(), self.USDC.lower(), self.USDBC.lower()]
            base_is_token0 = token0 in base_tokens

            total_volume_usd = 0.0
            eth_price = self.get_eth_price_onchain()

            for log in logs:
                # Décoder data (amount0In, amount1In, amount0Out, amount1Out)
                data = log['data']
                # 4 uint256 = 32 bytes chacun
                amount0In = int(data[2:66], 16)
                amount1In = int(data[66:130], 16)
                amount0Out = int(data[130:194], 16)
                amount1Out = int(data[194:258], 16)

                # Volume = somme des amounts de la base token
                if base_is_token0:
                    base_amount = (amount0In + amount0Out) / 10**18
                    base_token = token0
                else:
                    base_amount = (amount1In + amount1Out) / 10**18
                    base_token = token1

                # Convertir en USD
                if base_token in [self.USDC.lower(), self.USDBC.lower()]:
                    usd_value = base_amount
                else:
                    usd_value = base_amount * eth_price

                total_volume_usd += usd_value

            return total_volume_usd

        except Exception as e:
            print(f"❌ Erreur get_volume_last_minutes: {e}")
            return 0.0

    def get_price_change(self, pair_address: str, minutes_ago: int = 5, minutes_window: int = 5) -> float:
        """
        Calcule le changement de prix sur une période

        Args:
            pair_address: Adresse du pool
            minutes_ago: Il y a combien de minutes (5 pour 5min, 60 pour 1h)
            minutes_window: Fenêtre d'échantillonnage (5min)

        Returns:
            Pourcentage de changement (ex: 7.5 pour +7.5%)
        """
        try:
            current_block = self.w3.eth.block_number
            blocks_per_minute = 30

            # Prix actuel (derniers 5min)
            recent_from = current_block - int(minutes_window * blocks_per_minute)
            recent_price = self._get_avg_price_from_swaps(pair_address, recent_from, current_block)

            # Prix passé (minutes_ago - minutes_window à minutes_ago)
            past_to = current_block - int(minutes_ago * blocks_per_minute)
            past_from = past_to - int(minutes_window * blocks_per_minute)
            past_price = self._get_avg_price_from_swaps(pair_address, past_from, past_to)

            if past_price == 0 or recent_price == 0:
                return 0.0

            change_percent = ((recent_price / past_price) - 1) * 100
            return change_percent

        except Exception as e:
            print(f"❌ Erreur get_price_change: {e}")
            return 0.0

    def _get_avg_price_from_swaps(self, pair_address: str, from_block: int, to_block: int) -> float:
        """
        Calcule le prix moyen pondéré par volume à partir des swaps
        """
        try:
            swap_topic = self.w3.keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)").hex()

            logs = self.w3.eth.get_logs({
                'address': Web3.to_checksum_address(pair_address),
                'fromBlock': max(0, from_block),
                'toBlock': to_block,
                'topics': [swap_topic]
            })

            if not logs:
                return 0.0

            # Récupérer token0/token1
            pool = self.w3.eth.contract(
                address=Web3.to_checksum_address(pair_address),
                abi=self.UNISWAP_V2_PAIR_ABI
            )
            token0 = pool.functions.token0().call().lower()
            token1 = pool.functions.token1().call().lower()

            base_tokens = [self.WETH.lower(), self.USDC.lower(), self.USDBC.lower()]
            base_is_token0 = token0 in base_tokens

            total_base = 0.0
            total_token = 0.0

            for log in logs:
                data = log['data']
                amount0In = int(data[2:66], 16) / 10**18
                amount1In = int(data[66:130], 16) / 10**18
                amount0Out = int(data[130:194], 16) / 10**18
                amount1Out = int(data[194:258], 16) / 10**18

                if base_is_token0:
                    # Base = token0, Token = token1
                    base_amount = amount0In if amount0In > 0 else amount0Out
                    token_amount = amount1Out if amount0In > 0 else amount1In
                else:
                    # Base = token1, Token = token0
                    base_amount = amount1In if amount1In > 0 else amount1Out
                    token_amount = amount0Out if amount1In > 0 else amount0In

                total_base += base_amount
                total_token += token_amount

            if total_token == 0:
                return 0.0

            # Prix = base/token (combien de base pour 1 token)
            avg_price = total_base / total_token
            return avg_price

        except Exception:
            return 0.0

    def estimate_holders(self, token_address: str, hours: int = 2) -> int:
        """
        Estime le nombre de holders via les Transfer events (dernières X heures)
        Note: Estimation conservatrice, ne compte que les adresses actives récemment

        Returns:
            Nombre d'adresses uniques ayant reçu/envoyé le token
        """
        try:
            to_block = self.w3.eth.block_number
            blocks_per_hour = 1800  # ~2 sec par bloc
            from_block = max(0, to_block - int(hours * blocks_per_hour))

            # Topic Transfer = keccak256("Transfer(address,address,uint256)")
            transfer_topic = self.w3.keccak(text="Transfer(address,address,uint256)").hex()

            logs = self.w3.eth.get_logs({
                'address': Web3.to_checksum_address(token_address),
                'fromBlock': from_block,
                'toBlock': to_block,
                'topics': [transfer_topic]
            })

            if not logs:
                return 0

            # Collecter adresses uniques (from + to)
            addresses = set()
            for log in logs:
                # topics[1] = from, topics[2] = to
                if len(log['topics']) >= 3:
                    from_addr = log['topics'][1].hex()[-40:]  # Derniers 40 chars (20 bytes)
                    to_addr = log['topics'][2].hex()[-40:]
                    addresses.add(from_addr)
                    addresses.add(to_addr)

            # Exclure adresse 0x0 (mint/burn)
            addresses.discard('0' * 40)

            return len(addresses)

        except Exception as e:
            print(f"❌ Erreur estimate_holders: {e}")
            return 0

    def get_eth_price_onchain(self) -> float:
        """
        Récupère le prix ETH en USD via un pool stable (WETH/USDC)
        Cache de 5 minutes pour économiser les appels

        Returns:
            Prix ETH en USD (fallback 3000.0 si erreur)
        """
        try:
            # Vérifier cache
            now = time.time()
            if now - self.eth_price_cache['timestamp'] < self.cache_ttl:
                return self.eth_price_cache['price']

            # Chercher pool WETH/USDC sur Aerodrome ou BaseSwap
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.AERODROME_FACTORY),
                abi=self.FACTORY_ABI
            )

            weth = Web3.to_checksum_address(self.WETH)
            usdc = Web3.to_checksum_address(self.USDC)

            pair = factory.functions.getPair(weth, usdc).call()

            if pair == "0x0000000000000000000000000000000000000000":
                # Essayer BaseSwap
                factory = self.w3.eth.contract(
                    address=Web3.to_checksum_address(self.BASESWAP_FACTORY),
                    abi=self.FACTORY_ABI
                )
                pair = factory.functions.getPair(weth, usdc).call()

            if pair == "0x0000000000000000000000000000000000000000":
                # Fallback hardcodé
                return 3000.0

            # Récupérer reserves
            pool = self.w3.eth.contract(
                address=pair,
                abi=self.UNISWAP_V2_PAIR_ABI
            )

            reserves = pool.functions.getReserves().call()
            token0 = pool.functions.token0().call().lower()

            # Calculer prix
            if token0 == weth.lower():
                # reserve0 = WETH, reserve1 = USDC
                eth_reserve = reserves[0] / 10**18
                usdc_reserve = reserves[1] / 10**6  # USDC = 6 decimals
            else:
                # reserve0 = USDC, reserve1 = WETH
                usdc_reserve = reserves[0] / 10**6
                eth_reserve = reserves[1] / 10**18

            if eth_reserve == 0:
                return 3000.0

            eth_price = usdc_reserve / eth_reserve

            # Mettre à jour cache
            self.eth_price_cache = {'price': eth_price, 'timestamp': now}

            return eth_price

        except Exception as e:
            print(f"❌ Erreur get_eth_price_onchain: {e}")
            return 3000.0  # Fallback conservateur

    def get_token_data_onchain(self, token_address: str, pair_address: str = None) -> Dict:
        """
        Récupère toutes les données on-chain pour un token

        Returns:
            dict avec liquidity_usd, volume_5min, volume_1h, price_change_5min,
            price_change_1h, holders, eth_price
        """
        data = {
            'liquidity_usd': 0.0,
            'volume_5min': 0.0,
            'volume_1h': 0.0,
            'price_change_5min': 0.0,
            'price_change_1h': 0.0,
            'holders': 0,
            'eth_price': 3000.0
        }

        try:
            # 1. Trouver pair si non fournie
            if pair_address is None:
                pair_address = self.get_pair_address(token_address, self.AERODROME_FACTORY)
                if pair_address is None:
                    pair_address = self.get_pair_address(token_address, self.BASESWAP_FACTORY)
                if pair_address is None:
                    print(f"⚠️  Aucun pool trouvé pour {token_address}")
                    return data

            # 2. Prix ETH (cache 5min)
            data['eth_price'] = self.get_eth_price_onchain()

            # 3. Liquidité
            data['liquidity_usd'] = self.get_pool_liquidity_usd(token_address, pair_address)

            # Si liquidité trop faible, pas besoin d'aller plus loin
            if data['liquidity_usd'] < 500:
                return data

            # 4. Volume 5min et 1h
            data['volume_5min'] = self.get_volume_last_minutes(pair_address, 5)
            data['volume_1h'] = self.get_volume_last_minutes(pair_address, 60)

            # 5. Changements de prix
            data['price_change_5min'] = self.get_price_change(pair_address, 5, 5)
            data['price_change_1h'] = self.get_price_change(pair_address, 60, 5)

            # 6. Holders (estimation via Transfer events 2h)
            data['holders'] = self.estimate_holders(token_address, 2)

            return data

        except Exception as e:
            print(f"❌ Erreur get_token_data_onchain: {e}")
            return data


if __name__ == "__main__":
    # Test basique
    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
    fetcher = OnChainFetcher(w3)

    # Test sur un token connu (ex: BRETT)
    test_token = "0x532f27101965dd16442E59d40670FaF5eBB142E4"
    print(f"\n🧪 Test OnChainFetcher sur {test_token}\n")

    data = fetcher.get_token_data_onchain(test_token)

    print(f"📊 Résultats:")
    print(f"  • Liquidité: ${data['liquidity_usd']:,.0f}")
    print(f"  • Volume 5min: ${data['volume_5min']:,.0f}")
    print(f"  • Volume 1h: ${data['volume_1h']:,.0f}")
    print(f"  • Δ Prix 5min: {data['price_change_5min']:+.2f}%")
    print(f"  • Δ Prix 1h: {data['price_change_1h']:+.2f}%")
    print(f"  • Holders (2h): {data['holders']}")
    print(f"  • Prix ETH: ${data['eth_price']:,.2f}")
