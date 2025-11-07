#!/usr/bin/env python3
"""
Utilitaires Web3 pour interactions blockchain reelles
"""

import json
import time
import threading
from typing import Dict, Optional
from web3 import Web3
from eth_account import Account
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class BaseWeb3Manager:
    """Gestionnaire Web3 pour Base Layer 2"""
    
    def __init__(self, rpc_url: str, private_key: str = None):
        # Support multi-endpoints pour failover
        self.rpc_urls = [
            rpc_url,
            "https://base.drpc.org",
            "https://mainnet.base.org",
            "https://base.publicnode.com",
            "https://base.meowrpc.com"
        ]
        
        # Tenter la connexion avec failover
        self.w3 = None
        for url in self.rpc_urls:
            try:
                self.w3 = Web3(Web3.HTTPProvider(url))
                if self.w3.is_connected():
                    print(f"Connecte a Base via {url}")
                    break
            except Exception:
                continue
                
        if not self.w3 or not self.w3.is_connected():
            raise Exception("Impossible de se connecter a Base")
            
        self.account = Account.from_key(private_key) if private_key else None
        self.chain_id = 8453  # Base Mainnet
        
        # ABIs essentiels
        self.erc20_abi = json.loads('''[
            {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
            {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},
            {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
            {"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"},
            {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
            {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},
            {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"}
        ]''')
        
    def get_token_info(self, token_address: str) -> Optional[Dict]:
        """Recupere les informations d'un token avec gestion d'erreur"""
        try:
            # Validation de l'adresse
            if not Web3.is_address(token_address):
                return None
                
            token = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=self.erc20_abi
            )
            
            # Appels avec timeout
            name = token.functions.name().call()
            symbol = token.functions.symbol().call()
            decimals = token.functions.decimals().call()
            total_supply = token.functions.totalSupply().call()
            
            return {
                'address': token_address.lower(),
                'name': name[:50] if name else 'Unknown',  # Limite la longueur
                'symbol': symbol[:20] if symbol else 'UNKNOWN',  # Limite la longueur
                'decimals': decimals,
                'total_supply': total_supply
            }
        except Exception as e:
            print(f"Erreur recuperation token info {token_address}: {e}")
            return None
            
    def get_balance(self, token_address: str, wallet_address: str = None) -> int:
        """Recupere le balance d'un token"""
        try:
            if wallet_address is None:
                if not self.account:
                    return 0
                wallet_address = self.account.address
                
            token = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=self.erc20_abi
            )
            
            return token.functions.balanceOf(wallet_address).call()
        except Exception as e:
            print(f"Erreur get_balance: {e}")
            return 0

class UniswapV3Manager:
    """Gestionnaire pour Uniswap V3 sur Base"""
    
    WETH_ADDRESS = "0x4200000000000000000000000000000000000006"
    
    def __init__(self, web3_manager: BaseWeb3Manager):
        self.w3 = web3_manager.w3
        self.account = web3_manager.account
        
        # Adresses Uniswap V3 sur Base
        self.factory = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
        self.router = "0x2626664c2603336E57B271c5C0b26F421741e481"
        self.quoter = "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a"
        
        # ABI Quoter V2 pour obtenir les prix
        self.quoter_abi = json.loads('''[
            {
                "inputs": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                ],
                "name": "quoteExactInputSingle",
                "outputs": [
                    {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceX96After", "type": "uint160"},
                    {"internalType": "uint32", "name": "initializedTicksCrossed", "type": "uint32"},
                    {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"}
                ],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]''')
        
        try:
            self.quoter_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.quoter),
                abi=self.quoter_abi
            )
        except Exception as e:
            print(f"Erreur initialisation quoter: {e}")
            self.quoter_contract = None
        
    def get_pool_address(self, token0: str, token1: str, fee: int = 3000) -> Optional[str]:
        """Calcule l'adresse d'une pool Uniswap V3"""
        try:
            # Validation des adresses
            if not Web3.is_address(token0) or not Web3.is_address(token1):
                return None
                
            factory_abi = json.loads('''[
                {
                    "inputs": [
                        {"internalType": "address", "name": "", "type": "address"},
                        {"internalType": "address", "name": "", "type": "address"},
                        {"internalType": "uint24", "name": "", "type": "uint24"}
                    ],
                    "name": "getPool",
                    "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]''')
            
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.factory),
                abi=factory_abi
            )
            
            # Ordonner les tokens
            if token0.lower() > token1.lower():
                token0, token1 = token1, token0
                
            pool = factory.functions.getPool(
                Web3.to_checksum_address(token0),
                Web3.to_checksum_address(token1),
                fee
            ).call()
            
            return pool if pool != "0x0000000000000000000000000000000000000000" else None
        except Exception as e:
            print(f"Erreur get_pool_address: {e}")
            return None
        
    def get_token_price(self, token_address: str, amount: int = None, is_sell: bool = False) -> float:
        """Recupere le prix d'un token en WETH"""
        try:
            if not self.quoter_contract:
                return 0
                
            if amount is None:
                amount = 10 ** 18  # 1 token par defaut
            
            # Inverser les tokens si c'est une vente
            if is_sell:
                token_in = Web3.to_checksum_address(token_address)
                token_out = Web3.to_checksum_address(self.WETH_ADDRESS)
            else:
                token_in = Web3.to_checksum_address(self.WETH_ADDRESS)
                token_out = Web3.to_checksum_address(token_address)
                
            # Essayer differents fee tiers
            for fee in [3000, 500, 10000, 100]:
                try:
                    result = self.quoter_contract.functions.quoteExactInputSingle(
                        token_in,
                        token_out,
                        amount,
                        fee,
                        0
                    ).call()
                    
                    if result[0] > 0:
                        # Convertir en prix decimal
                        if is_sell:
                            price_in_weth = result[0] / 10**18
                        else:
                            price_in_weth = amount / result[0] if result[0] > 0 else 0
                        return price_in_weth
                except Exception:
                    continue
                    
            return 0
        except Exception as e:
            print(f"Erreur get_token_price: {e}")
            return 0

class DexScreenerAPI:
    """Client pour l'API DexScreener avec retry"""
    
    def __init__(self):
        self.base_url = "https://api.dexscreener.com/latest/dex"
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Cree une session avec retry automatique"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def close(self) -> None:
        """Ferme la session HTTP"""
        if self.session:
            self.session.close()
        
    def get_token_info(self, token_address: str) -> Optional[Dict]:
        """Recupere les infos d'un token depuis DexScreener"""
        try:
            url = f"{self.base_url}/tokens/{token_address}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('pairs'):
                    # Filtrer les paires sur Base
                    base_pairs = [p for p in data['pairs'] if p.get('chainId') == 'base']
                    if not base_pairs:
                        base_pairs = data['pairs']
                        
                    # Prendre la paire avec le plus de liquidite
                    pairs = sorted(base_pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0)), reverse=True)
                    if pairs:
                        return self._parse_pair_data(pairs[0])
            return None
        except Exception as e:
            print(f"Erreur DexScreener API: {e}")
            return None
            
    def get_recent_pairs_on_chain(self, chain_id: str = 'base', limit: int = 50) -> list:
        """
        Recupere les paires recentes sur une blockchain donnee

        Args:
            chain_id: ID de la blockchain (ex: 'base', 'ethereum')
            limit: Nombre maximum de paires a retourner

        Returns:
            Liste de paires avec leurs donnees
        """
        try:
            # DexScreener n'a pas d'endpoint direct pour les paires recentes par chain
            # On utilise l'endpoint search avec des criteres larges
            url = f"{self.base_url}/search?q={chain_id}"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])

                # Filtrer par chainId et trier par creation recente
                filtered_pairs = [
                    p for p in pairs
                    if p.get('chainId', '').lower() == chain_id.lower()
                ]

                # Trier par volume 24h (proxy pour les paires actives/recentes)
                filtered_pairs = sorted(
                    filtered_pairs,
                    key=lambda x: float(x.get('volume', {}).get('h24', 0)),
                    reverse=True
                )

                # Formater les paires
                result = []
                for pair in filtered_pairs[:limit]:
                    parsed = self._parse_pair_data(pair)
                    if parsed:
                        # Ajouter les infos du token de base
                        parsed['tokenAddress'] = pair.get('baseToken', {}).get('address')
                        parsed['baseToken'] = pair.get('baseToken', {})
                        parsed['quoteToken'] = pair.get('quoteToken', {})
                        result.append(parsed)

                return result
            return []

        except Exception as e:
            print(f"Erreur get_recent_pairs_on_chain: {e}")
            return []

    def _parse_pair_data(self, pair: Dict) -> Dict:
        """Parse les donnees d'une paire avec validation"""
        try:
            return {
                'price_usd': float(pair.get('priceUsd', 0)),
                'price_native': float(pair.get('priceNative', 0)),
                'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0)),
                'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
                'volume_1h': float(pair.get('volume', {}).get('h1', 0)),
                'price_change_1h': float(pair.get('priceChange', {}).get('h1', 0)),
                'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)),
                'txns_24h': (pair.get('txns', {}).get('h24', {}).get('buys', 0) +
                           pair.get('txns', {}).get('h24', {}).get('sells', 0)),
                'fdv': float(pair.get('fdv', 0)),
                'market_cap': float(pair.get('marketCap', 0)),
                'pair_address': pair.get('pairAddress'),
                'dex_id': pair.get('dexId'),
                'chain_id': pair.get('chainId')
            }
        except Exception as e:
            print(f"Erreur parsing pair data: {e}")
            return {}

class BaseScanAPI:
    """Client pour Etherscan v2 API (Base chain)"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or "YourDefaultAPIKey"
        # NOUVELLE URL Etherscan v2 pour Base
        self.base_url = "https://api.etherscan.io/v2/api"
        self.chain_id = 8453  # Base chain ID
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Cree une session avec retry"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def close(self) -> None:
        """Ferme la session HTTP"""
        if self.session:
            self.session.close()
        
    def get_token_holders(self, token_address: str) -> int:
        """Recupere le nombre de holders d'un token"""
        try:
            params = {
                'chainid': self.chain_id,  # IMPORTANT: chainid pour Base
                'module': 'token',
                'action': 'tokenholderlist',
                'contractaddress': token_address,
                'apikey': self.api_key
            }
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == '1':
                    return len(data.get('result', []))
            return 0
        except Exception as e:
            print(f"Erreur get_token_holders: {e}")
            return 0
            
    def get_contract_verified(self, address: str) -> bool:
        """Verifie si un contrat est verifie"""
        try:
            params = {
                'chainid': self.chain_id,  # IMPORTANT: chainid pour Base
                'module': 'contract',
                'action': 'getsourcecode',
                'address': address,
                'apikey': self.api_key
            }
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == '1' and data.get('result'):
                    source = data['result'][0].get('SourceCode', '')
                    return source != '' and source != '0x'
            return False
        except Exception as e:
            print(f"Erreur get_contract_verified: {e}")
            return False
    
    def get_transaction_count(self, address: str) -> int:
        """Recupere le nombre de transactions d'une adresse"""
        try:
            # Utiliser txlist pour obtenir toutes les transactions
            all_transactions = 0
            page = 1
            
            while True:
                params = {
                    'chainid': self.chain_id,
                    'module': 'account',
                    'action': 'txlist',
                    'address': address,
                    'startblock': 0,
                    'endblock': 99999999,
                    'page': page,
                    'offset': 10000,  # Maximum par page
                    'sort': 'asc',
                    'apikey': self.api_key
                }
                
                response = self.session.get(self.base_url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == '1':
                        result = data.get('result', [])
                        if not result:
                            break
                        all_transactions += len(result)
                        if len(result) < 10000:
                            break
                        page += 1
                    else:
                        break
                else:
                    break
                    
            return all_transactions
        except Exception as e:
            print(f"Erreur get_transaction_count: {e}")
            return 0

class CoinGeckoAPI:
    """Client pour CoinGecko API avec cache thread-safe"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://pro-api.coingecko.com/api/v3" if api_key else "https://api.coingecko.com/api/v3"
        self.headers = {'x-cg-pro-api-key': api_key} if api_key else {}
        self.session = self._create_session()
        self.session.headers.update(self.headers)
        self._eth_price_cache = {'price': 3000, 'timestamp': 0}
        self._cache_lock = threading.Lock()
        
    def _create_session(self) -> requests.Session:
        """Cree une session avec retry"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def close(self) -> None:
        """Ferme la session HTTP"""
        if self.session:
            self.session.close()
        
    def get_eth_price(self) -> float:
        """Recupere le prix ETH en USD avec cache de 60 secondes"""
        try:
            # Utiliser le cache si recent (thread-safe)
            with self._cache_lock:
                if time.time() - self._eth_price_cache['timestamp'] < 60:
                    return self._eth_price_cache['price']
                
            url = f"{self.base_url}/simple/price"
            params = {'ids': 'ethereum', 'vs_currencies': 'usd'}
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = float(data.get('ethereum', {}).get('usd', 3000))
                # Mettre a jour le cache (thread-safe)
                with self._cache_lock:
                    self._eth_price_cache = {'price': price, 'timestamp': time.time()}
                return price
            return 3000  # Fallback
        except Exception as e:
            print(f"Erreur get_eth_price: {e}")
            with self._cache_lock:
                return self._eth_price_cache.get('price', 3000)  # Retourner la derniere valeur connue
