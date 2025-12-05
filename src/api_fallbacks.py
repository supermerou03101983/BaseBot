#!/usr/bin/env python3
"""
API Fallbacks - APIs gratuites sans clé ou avec rate limits généreux
Utilisé en complément de l'on-chain fetcher quand les données sont incomplètes
"""

import time
import requests
from typing import Dict, Optional
import threading


class BlockchairAPI:
    """
    Blockchair API - Données blockchain gratuites
    Rate limit: 1 req/sec gratuit (pas de clé nécessaire)
    """

    BASE_URL = "https://api.blockchair.com/base"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'BaseBot/1.0'})
        self.last_call = 0
        self.min_delay = 1.0  # 1 req/sec

    def _rate_limit(self):
        """Respecte le rate limit de 1 req/sec"""
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_call = time.time()

    def get_holder_count(self, token_address: str) -> int:
        """
        Récupère le nombre de holders via Blockchair

        Returns:
            Nombre de holders (0 si erreur)
        """
        try:
            self._rate_limit()

            url = f"{self.BASE_URL}/erc-20/{token_address}/dashboards/addresses"
            params = {'limit': 1}  # On veut juste le count

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and token_address.lower() in data['data']:
                    token_data = data['data'][token_address.lower()]
                    return token_data.get('holders', 0)

            return 0

        except Exception as e:
            print(f"❌ Blockchair API error: {e}")
            return 0


class CoinGeckoFreeAPI:
    """
    CoinGecko API gratuite (sans clé)
    Rate limit: 10-50 req/min (généreux)
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: Optionnel, si fourni utilise l'API Pro
        """
        self.api_key = api_key
        self.session = requests.Session()

        if api_key:
            self.session.headers.update({'x-cg-pro-api-key': api_key})
            self.base_url = "https://pro-api.coingecko.com/api/v3"
        else:
            self.base_url = self.BASE_URL

        self.session.headers.update({'User-Agent': 'BaseBot/1.0'})

        # Cache pour ETH price (5min)
        self.eth_price_cache = {'price': 3000.0, 'timestamp': 0}
        self.cache_ttl = 300

    def get_eth_price(self) -> float:
        """
        Récupère le prix ETH en USD avec cache de 5min

        Returns:
            Prix ETH en USD (fallback 3000.0)
        """
        try:
            # Vérifier cache
            now = time.time()
            if now - self.eth_price_cache['timestamp'] < self.cache_ttl:
                return self.eth_price_cache['price']

            # Appel API
            url = f"{self.base_url}/simple/price"
            params = {'ids': 'ethereum', 'vs_currencies': 'usd'}

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'ethereum' in data and 'usd' in data['ethereum']:
                    price = float(data['ethereum']['usd'])

                    # Mettre à jour cache
                    self.eth_price_cache = {'price': price, 'timestamp': now}

                    return price

            return 3000.0  # Fallback

        except Exception as e:
            print(f"❌ CoinGecko API error: {e}")
            return 3000.0

    def get_token_data(self, token_address: str, platform: str = "base") -> Optional[Dict]:
        """
        Récupère les données d'un token via CoinGecko

        Args:
            token_address: Adresse du token
            platform: Blockchain (default: "base")

        Returns:
            Dict avec market_cap, volume_24h, price_change_24h, holders, etc.
            None si token non trouvé
        """
        try:
            # CoinGecko nécessite l'ID du token (pas l'adresse directement)
            # Endpoint /coins/{platform}/contract/{address}
            url = f"{self.base_url}/coins/{platform}/contract/{token_address}"

            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                market_data = data.get('market_data', {})

                return {
                    'name': data.get('name', ''),
                    'symbol': data.get('symbol', '').upper(),
                    'market_cap': market_data.get('market_cap', {}).get('usd', 0),
                    'volume_24h': market_data.get('total_volume', {}).get('usd', 0),
                    'price_usd': market_data.get('current_price', {}).get('usd', 0),
                    'price_change_24h': market_data.get('price_change_percentage_24h', 0),
                    'price_change_7d': market_data.get('price_change_percentage_7d', 0),
                    'holders': data.get('community_data', {}).get('reddit_accounts_active_48h', 0)  # Pas exact
                }

            return None

        except Exception as e:
            print(f"❌ CoinGecko token data error: {e}")
            return None


class BaseScanAPI:
    """
    BaseScan API (Etherscan pour Base)
    Rate limit: 5 req/sec gratuit avec clé API
    """

    BASE_URL = "https://api.basescan.org/api"

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: Clé API BaseScan (gratuite)
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'BaseBot/1.0'})

        # Rate limiting (5 req/sec)
        self.last_calls = []
        self.max_calls_per_second = 4  # Conservateur (5 officiellement)

    def _rate_limit(self):
        """Respecte le rate limit de 5 req/sec"""
        now = time.time()

        # Supprimer appels > 1 sec
        self.last_calls = [t for t in self.last_calls if now - t < 1.0]

        # Si limite atteinte, attendre
        if len(self.last_calls) >= self.max_calls_per_second:
            sleep_time = 1.0 - (now - self.last_calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)

        self.last_calls.append(time.time())

    def get_token_holder_list(self, token_address: str, limit: int = 100) -> Optional[Dict]:
        """
        Récupère la liste des holders d'un token

        Returns:
            Dict avec nombre de holders et distribution
        """
        if not self.api_key:
            return None

        try:
            self._rate_limit()

            params = {
                'module': 'token',
                'action': 'tokenholderlist',
                'contractaddress': token_address,
                'page': 1,
                'offset': limit,
                'apikey': self.api_key
            }

            response = self.session.get(self.BASE_URL, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data['status'] == '1' and 'result' in data:
                    holders = data['result']

                    # Calculer owner percentage (top holder)
                    if holders:
                        total_supply = sum(int(h['TokenHolderQuantity']) for h in holders)
                        top_holder_balance = int(holders[0]['TokenHolderQuantity']) if holders else 0

                        owner_percentage = (top_holder_balance / total_supply * 100) if total_supply > 0 else 0

                        return {
                            'holder_count': len(holders),  # Approximatif (limité par offset)
                            'top_holder_balance': top_holder_balance,
                            'owner_percentage': owner_percentage
                        }

            return None

        except Exception as e:
            print(f"❌ BaseScan API error: {e}")
            return None


class DexScreenerFreeAPI:
    """
    DexScreener API - 100% gratuite, pas de clé nécessaire
    Rate limit: 300 req/min (généreux)
    """

    BASE_URL = "https://api.dexscreener.com/latest/dex"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'BaseBot/1.0'})

    def get_token_info(self, token_address: str, chain: str = "base") -> Optional[Dict]:
        """
        Récupère les infos d'un token via DexScreener

        Returns:
            Dict avec liquidity, volume_24h, price_usd, price_change_5m/1h/24h, etc.
        """
        try:
            url = f"{self.BASE_URL}/tokens/{token_address}"

            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'pairs' in data and data['pairs'] and len(data['pairs']) > 0:
                    # Prendre le pool avec le plus de liquidité sur Base
                    base_pairs = [p for p in data['pairs'] if p.get('chainId') == chain]

                    if not base_pairs:
                        return None

                    # Trier par liquidité
                    pair = sorted(base_pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0), reverse=True)[0]

                    liquidity = pair.get('liquidity', {})
                    volume = pair.get('volume', {})
                    price_change = pair.get('priceChange', {})

                    return {
                        'pair_address': pair.get('pairAddress', ''),
                        'dex_id': pair.get('dexId', ''),
                        'liquidity_usd': float(liquidity.get('usd', 0)),
                        'liquidity_base': float(liquidity.get('base', 0)),
                        'liquidity_quote': float(liquidity.get('quote', 0)),
                        'volume_24h': float(volume.get('h24', 0)),
                        'volume_6h': float(volume.get('h6', 0)),
                        'volume_1h': float(volume.get('h1', 0)),
                        'price_usd': float(pair.get('priceUsd', 0)),
                        'price_native': float(pair.get('priceNative', 0)),
                        'price_change_5m': float(price_change.get('m5', 0)),
                        'price_change_1h': float(price_change.get('h1', 0)),
                        'price_change_6h': float(price_change.get('h6', 0)),
                        'price_change_24h': float(price_change.get('h24', 0)),
                        'fdv': float(pair.get('fdv', 0)),
                        'market_cap': float(pair.get('marketCap', 0)),
                        'pair_created_at': pair.get('pairCreatedAt', 0),
                        'info': pair.get('info', {}),
                        'boosts': pair.get('boosts', {})
                    }

            return None

        except Exception as e:
            print(f"❌ DexScreener API error: {e}")
            return None


if __name__ == "__main__":
    # Tests basiques
    print("\n🧪 Test API Fallbacks\n")

    # Test CoinGecko
    print("1️⃣ CoinGecko - Prix ETH:")
    cg = CoinGeckoFreeAPI()
    eth_price = cg.get_eth_price()
    print(f"   ETH = ${eth_price:,.2f}\n")

    # Test DexScreener
    print("2️⃣ DexScreener - BRETT sur Base:")
    dex = DexScreenerFreeAPI()
    brett = "0x532f27101965dd16442E59d40670FaF5eBB142E4"
    data = dex.get_token_info(brett)
    if data:
        print(f"   • Liquidité: ${data['liquidity_usd']:,.0f}")
        print(f"   • Volume 24h: ${data['volume_24h']:,.0f}")
        print(f"   • Volume 1h: ${data['volume_1h']:,.0f}")
        print(f"   • Prix: ${data['price_usd']:.8f}")
        print(f"   • Δ 5min: {data['price_change_5m']:+.2f}%")
        print(f"   • Δ 1h: {data['price_change_1h']:+.2f}%")
    else:
        print("   ❌ Token non trouvé")

    print("\n✅ Tests terminés")
