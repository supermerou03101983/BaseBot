#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trader - Trading reel avec strategie unique optimisee
"""

import sqlite3
import json
import time
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from pathlib import Path
from decimal import Decimal

PROJECT_DIR = Path(__file__).parent.parent
sys.path.append(str(PROJECT_DIR))

from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
from web3_utils import (
    BaseWeb3Manager, UniswapV3Manager,
    DexScreenerAPI, CoinGeckoAPI
)

load_dotenv(PROJECT_DIR / 'config' / '.env')

class Position:
    """Represente une position ouverte avec gestion avancee"""
    def __init__(self, token_address: str, symbol: str, entry_price: float, 
                 amount: float, amount_eth: float):
        self.token_address = token_address
        self.symbol = symbol
        self.entry_price = entry_price
        self.current_price = entry_price
        self.amount = amount
        self.amount_eth = amount_eth
        self.entry_time = datetime.now()
        self.max_price = entry_price
        self.current_level = 0
        self.stop_loss = entry_price * 0.95  # Stop loss fixe a -5%
        self.trailing_config = None
        self.trailing_active = False
        self.highest_price = entry_price

class RealTrader:
    def __init__(self):
        # Creer les dossiers necessaires
        (PROJECT_DIR / 'data').mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / 'logs').mkdir(parents=True, exist_ok=True)
        (PROJECT_DIR / 'config').mkdir(parents=True, exist_ok=True)
        
        self.db_path = PROJECT_DIR / 'data' / 'trading.db'
        self.setup_logging()
        
        # Web3 setup avec gestion d'erreur
        try:
            self.web3_manager = BaseWeb3Manager(
                rpc_url=os.getenv('RPC_URL', 'https://mainnet.base.org'),
                private_key=os.getenv('PRIVATE_KEY')
            )
            
            self.uniswap = UniswapV3Manager(self.web3_manager)
            self.dexscreener = DexScreenerAPI()
            self.coingecko = CoinGeckoAPI(os.getenv('COINGECKO_API_KEY'))
        except Exception as e:
            self.logger.error(f"Erreur initialisation Web3: {e}")
            raise
        
        # Configuration de trading
        self.load_config()
        self.positions = {}
        self.load_positions()
        self.daily_trades = 0
        self.last_trade_day = None
        
        # Router ABI pour Uniswap V3
        self.router_abi = json.loads('''[
            {
                "inputs": [
                    {
                        "components": [
                            {"internalType": "address", "name": "tokenIn", "type": "address"},
                            {"internalType": "address", "name": "tokenOut", "type": "address"},
                            {"internalType": "uint24", "name": "fee", "type": "uint24"},
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                        ],
                        "internalType": "struct ISwapRouter.ExactInputSingleParams",
                        "name": "params",
                        "type": "tuple"
                    }
                ],
                "name": "exactInputSingle",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function"
            }
        ]''')
        
        try:
            self.router = self.web3_manager.w3.eth.contract(
                address=Web3.to_checksum_address(self.uniswap.router),
                abi=self.router_abi
            )
        except Exception as e:
            self.logger.error(f"Erreur initialisation router: {e}")
            raise
    
    def setup_logging(self):
        """Configuration du logging"""
        log_file = PROJECT_DIR / 'logs' / 'trader.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_config(self):
        """Charge la configuration avec nouvelle strategie"""
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
            self.logger.error(f"Erreur chargement config: {e}")
            self.trading_mode = 'paper'
                
        # Configuration depuis l'environnement
        self.position_size_percent = float(os.getenv('POSITION_SIZE_PERCENT', 15))
        self.max_positions = int(os.getenv('MAX_POSITIONS', 2))
        self.max_trades_per_day = int(os.getenv('MAX_TRADES_PER_DAY', 3))
        self.stop_loss_percent = float(os.getenv('STOP_LOSS_PERCENT', 5))
        self.monitoring_interval = int(os.getenv('MONITORING_INTERVAL', 1))
        
        # Configuration trailing stop unique
        self.trailing_config = {
            'activation_threshold': float(os.getenv('TRAILING_ACTIVATION_THRESHOLD', 12)),
            'levels': [
                {'min_profit': 12, 'max_profit': 30, 'distance': 3},
                {'min_profit': 30, 'max_profit': 100, 'distance': 5},
                {'min_profit': 100, 'max_profit': 300, 'distance': 10},
                {'min_profit': 300, 'max_profit': 99999, 'distance': 30}
            ]
        }
        
        # Configuration Time Exit Intelligent
        self.time_exit_config = {
            'stagnation': {
                'hours': int(os.getenv('TIME_EXIT_STAGNATION_HOURS', 24)),
                'min_profit': float(os.getenv('TIME_EXIT_STAGNATION_MIN_PROFIT', 5))
            },
            'low_momentum': {
                'hours': int(os.getenv('TIME_EXIT_LOW_MOMENTUM_HOURS', 48)),
                'min_profit': float(os.getenv('TIME_EXIT_LOW_MOMENTUM_MIN_PROFIT', 20))
            },
            'maximum': {
                'hours': int(os.getenv('TIME_EXIT_MAXIMUM_HOURS', 72)),
                'force_exit': True
            },
            'emergency': {
                'hours': int(os.getenv('TIME_EXIT_EMERGENCY_HOURS', 120)),
                'force_exit': True
            }
        }
        
        # Metriques de performance
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit_percent': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'time_exits': 0,
            'trailing_exits': 0,
            'stoploss_exits': 0
        }
    
    def save_position_state(self, position):
        """Sauvegarde l'etat d'une position avec metadonnees etendues"""
        try:
            state_file = PROJECT_DIR / 'data' / f'position_{position.token_address}.json'
            with open(state_file, 'w') as f:
                json.dump({
                    'token_address': position.token_address,
                    'symbol': position.symbol,
                    'entry_price': position.entry_price,
                    'amount': position.amount,
                    'amount_eth': position.amount_eth,
                    'stop_loss': position.stop_loss,
                    'current_level': position.current_level,
                    'entry_time': position.entry_time.isoformat() if position.entry_time else None,
                    'max_price': position.max_price,
                    'highest_price': position.highest_price,
                    'trailing_active': position.trailing_active,
                    'trailing_config': position.trailing_config
                }, f)
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde position {position.symbol}: {e}")
            
    def load_positions(self):
        """Recupere les positions au demarrage"""
        state_dir = PROJECT_DIR / 'data'
        loaded_count = 0
        
        if not state_dir.exists():
            return
            
        for state_file in state_dir.glob('position_*.json'):
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    
                position = Position(
                    data['token_address'],
                    data['symbol'],
                    data['entry_price'],
                    data['amount'],
                    data['amount_eth']
                )
                
                position.stop_loss = data['stop_loss']
                position.current_level = data['current_level']
                position.max_price = data.get('max_price', data['entry_price'])
                position.highest_price = data.get('highest_price', data['entry_price'])
                position.trailing_active = data.get('trailing_active', False)
                position.trailing_config = data.get('trailing_config')
                
                if data.get('entry_time'):
                    position.entry_time = datetime.fromisoformat(data['entry_time'])
                    
                self.positions[data['token_address']] = position
                loaded_count += 1
                
                self.logger.info(f"Position recuperee: {data['symbol']}")
                
            except Exception as e:
                self.logger.error(f"Erreur chargement position {state_file}: {e}")
                
        if loaded_count > 0:
            self.logger.info(f"✅ {loaded_count} positions recuperees")
    
    def get_next_token(self) -> Optional[Dict]:
        """Recupere le prochain token a trader"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Recuperer depuis approved_tokens avec le schema valide
            cursor.execute("""
                SELECT at.token_address, at.symbol, at.name, at.score,
                       dt.liquidity, dt.market_cap, dt.price_usd, dt.volume_24h
                FROM approved_tokens at
                LEFT JOIN discovered_tokens dt ON at.token_address = dt.token_address
                WHERE at.token_address NOT IN (
                    SELECT token_address FROM trade_history WHERE exit_time IS NULL
                )
                ORDER BY at.score DESC, at.created_at DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'address': row[0],           # token_address
                    'symbol': row[1],            # symbol
                    'name': row[2],              # name
                    'score': row[3],             # score
                    'liquidity': row[4] or 0,    # liquidity depuis discovered_tokens
                    'market_cap': row[5] or 0,   # market_cap depuis discovered_tokens
                    'price_usd': row[6] or 0,    # price_usd depuis discovered_tokens
                    'volume_24h': row[7] or 0    # volume_24h depuis discovered_tokens
                }
            return None
        except Exception as e:
            self.logger.error(f"Erreur recuperation token: {e}")
            return None
        
    def get_eth_balance(self) -> float:
        """Recupere le balance ETH du wallet"""
        try:
            balance_wei = self.web3_manager.w3.eth.get_balance(self.web3_manager.account.address)
            return balance_wei / 10**18
        except Exception as e:
            self.logger.error(f"Erreur recuperation balance ETH: {e}")
            return 0
        
    def calculate_position_size(self) -> float:
        """Calcule la taille de position (15% du wallet)"""
        eth_balance = self.get_eth_balance()
        
        # Garder 0.01 ETH pour les frais de gas
        available = max(0, eth_balance - 0.01)
        
        # 15% du capital disponible
        position_size = available * (self.position_size_percent / 100)
        
        # Limiter entre 0.05 et 2 ETH
        return max(0.05, min(2.0, position_size))
        
    def get_token_balance(self, token_address: str) -> int:
        """Recupere le balance exact d'un token"""
        try:
            token_contract = self.web3_manager.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=self.web3_manager.erc20_abi
            )
            
            balance = token_contract.functions.balanceOf(
                self.web3_manager.account.address
            ).call()
            
            return balance
        except Exception as e:
            self.logger.error(f"Erreur recuperation balance token: {e}")
            return 0
    
    def update_trailing_stop(self, position: Position):
        """Strategie de trailing stop unique avec 4 niveaux"""
        # Protection contre division par zero
        if position.entry_price == 0:
            self.logger.error(f"Prix d'entree invalide pour {position.symbol}")
            return
            
        profit_percent = ((position.current_price - position.entry_price) / 
                         position.entry_price) * 100
        
        # Mettre a jour le plus haut
        if position.current_price > position.highest_price:
            position.highest_price = position.current_price
        
        # Activer le trailing stop a +12%
        if profit_percent >= self.trailing_config['activation_threshold'] and not position.trailing_active:
            position.trailing_active = True
            self.logger.info(
                f"⚡ Trailing active: {position.symbol} a +{profit_percent:.1f}% "
                f"Prix: ${position.current_price:.8f}"
            )
        
        # Si trailing actif, ajuster le stop loss dynamiquement
        if position.trailing_active:
            # Determiner la distance selon le niveau de profit ACTUEL (depuis highest_price)
            # Calculer le profit depuis le pic pour determiner le niveau
            profit_from_peak = ((position.current_price - position.entry_price) /
                               position.entry_price) * 100

            distance = 3  # Par defaut (niveau 1)
            current_level = position.current_level  # Ne JAMAIS descendre

            for i, level in enumerate(self.trailing_config['levels']):
                if level['min_profit'] <= profit_from_peak < level['max_profit']:
                    distance = level['distance']
                    # Le niveau ne peut QUE monter
                    if i + 1 > position.current_level:
                        current_level = i + 1
                    break

            # Calculer le nouveau stop
            new_stop = position.highest_price * (1 - distance / 100)

            # Ne mettre a jour que si le nouveau stop est meilleur
            if new_stop > position.stop_loss or current_level > position.current_level:
                old_stop = position.stop_loss
                position.stop_loss = new_stop
                position.current_level = current_level
                
                self.logger.info(
                    f"📈 Trailing update: {position.symbol} | "
                    f"Profit: +{profit_percent:.1f}% | "
                    f"Niveau: {current_level} | "
                    f"Stop: ${old_stop:.8f} → ${new_stop:.8f} | "
                    f"Distance: -{distance}% du pic (${position.highest_price:.8f})"
                )
                self.save_position_state(position)
    
    def check_time_exit(self, position: Position) -> Tuple[bool, str]:
        """Verifie si une position doit être fermee selon le temps ecoule"""
        if not position.entry_time or position.entry_price == 0:
            return False, ""
        
        hours_held = (datetime.now() - position.entry_time).total_seconds() / 3600
        profit_percent = ((position.current_price - position.entry_price) / 
                         position.entry_price) * 100
        
        # Stagnation: 24h avec profit entre 0% et 5% (ne pas vendre si négatif!)
        if hours_held >= self.time_exit_config['stagnation']['hours']:
            if 0 < profit_percent < self.time_exit_config['stagnation']['min_profit']:
                self.performance_metrics['time_exits'] += 1
                return True, f"Stagnation ({hours_held:.0f}h, +{profit_percent:.1f}%)"

        # Low momentum: 48h avec profit entre 0% et 20% (ne pas vendre si négatif!)
        if hours_held >= self.time_exit_config['low_momentum']['hours']:
            if 0 < profit_percent < self.time_exit_config['low_momentum']['min_profit']:
                self.performance_metrics['time_exits'] += 1
                return True, f"Low momentum ({hours_held:.0f}h, +{profit_percent:.1f}%)"
        
        # Maximum: 72h force exit
        if hours_held >= self.time_exit_config['maximum']['hours']:
            self.performance_metrics['time_exits'] += 1
            return True, f"Max time ({hours_held:.0f}h, +{profit_percent:.1f}%)"
        
        # Emergency: 120h force exit
        if hours_held >= self.time_exit_config['emergency']['hours']:
            self.performance_metrics['time_exits'] += 1
            return True, f"Emergency ({hours_held:.0f}h)"
        
        return False, ""
        
    def execute_buy(self, token: Dict) -> bool:
        """Execute un achat reel ou simule"""
        # Validation des donnees
        if not token.get('address') or not token.get('symbol'):
            self.logger.error("Token invalide: donnees manquantes")
            return False
            
        if token.get('price_usd', 0) <= 0:
            self.logger.error(f"Prix invalide pour {token['symbol']}: {token.get('price_usd')}")
            return False
            
        try:
            weth_address = "0x4200000000000000000000000000000000000006"
            
            if self.trading_mode == 'paper':
                # Mode simulation
                self.logger.info(f"[PAPER] Achat simule: {token['symbol']}")
                
                # Simuler la position
                position = Position(
                    token['address'],
                    token['symbol'],
                    token['price_usd'],
                    1000000,  # Amount simule
                    0.15  # 0.15 ETH simule (15%)
                )
                position.trailing_config = self.trailing_config
                
                self.positions[token['address']] = position
                self.save_position_state(position)
                
                # Enregistrer dans la DB
                self.save_trade_to_db(token, 'BUY', token['price_usd'], 0.15, 'paper')
                
                return True
                
            else:
                # Mode reel
                self.logger.info(f"[REAL] Preparation achat: {token['symbol']}")
                
                # Calculer la taille de position (15%)
                position_size_eth = self.calculate_position_size()
                position_size_wei = int(position_size_eth * 10**18)
                
                # Slippage 2%
                slippage = 0.02
                
                # Obtenir le prix actuel
                expected_amount = self.uniswap.get_token_price(
                    weth_address,
                    position_size_wei
                ) / position_size_eth
                
                min_amount = int(expected_amount * (1 - slippage))
                
                # Preparer la transaction
                deadline = int(time.time()) + 300  # 5 minutes
                
                params = {
                    'tokenIn': Web3.to_checksum_address(weth_address),
                    'tokenOut': Web3.to_checksum_address(token['address']),
                    'fee': 3000,  # 0.3%
                    'recipient': self.web3_manager.account.address,
                    'deadline': deadline,
                    'amountIn': position_size_wei,
                    'amountOutMinimum': min_amount,
                    'sqrtPriceLimitX96': 0
                }
                
                # Construire la transaction
                swap_txn = self.router.functions.exactInputSingle(params).build_transaction({
                    'from': self.web3_manager.account.address,
                    'value': position_size_wei,
                    'gas': 200000,
                    'gasPrice': self.web3_manager.w3.eth.gas_price,
                    'nonce': self.web3_manager.w3.eth.get_transaction_count(
                        self.web3_manager.account.address
                    )
                })
                
                # Signer et envoyer
                signed_txn = self.web3_manager.account.sign_transaction(swap_txn)
                tx_hash = self.web3_manager.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                
                self.logger.info(f"Transaction envoyee: {tx_hash.hex()}")
                
                # Attendre confirmation
                receipt = self.web3_manager.w3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt['status'] == 1:
                    self.logger.info(f"✅ Achat reussi: {token['symbol']}")
                    
                    # Creer la position
                    position = Position(
                        token['address'],
                        token['symbol'],
                        token['price_usd'],
                        expected_amount,
                        position_size_eth
                    )
                    position.trailing_config = self.trailing_config
                    
                    self.positions[token['address']] = position
                    self.save_position_state(position)
                    
                    # Enregistrer
                    self.save_trade_to_db(
                        token, 'BUY', token['price_usd'],
                        position_size_eth, 'real', tx_hash.hex()
                    )
                    
                    return True
                else:
                    self.logger.error("Transaction echouee")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Erreur execution achat: {e}")
            return False
            
    def execute_sell(self, position: Position, reason: str) -> bool:
        """Execute une vente complete avec approval et swap"""
        if position.entry_price == 0:
            self.logger.error(f"Prix d'entree invalide pour {position.symbol}")
            return False
            
        try:
            # Calculer le profit avant la vente
            profit_percent = ((position.current_price - position.entry_price) / 
                            position.entry_price) * 100
            
            # Mettre a jour les metriques
            self.performance_metrics['total_trades'] += 1
            if profit_percent > 0:
                self.performance_metrics['winning_trades'] += 1
            else:
                self.performance_metrics['losing_trades'] += 1
            
            self.performance_metrics['total_profit_percent'] += profit_percent
            
            if profit_percent > self.performance_metrics['best_trade']:
                self.performance_metrics['best_trade'] = profit_percent
            if profit_percent < self.performance_metrics['worst_trade']:
                self.performance_metrics['worst_trade'] = profit_percent
            
            # Compter le type de sortie
            if "Trailing" in reason:
                self.performance_metrics['trailing_exits'] += 1
            elif "Stop Loss" in reason:
                self.performance_metrics['stoploss_exits'] += 1
            
            if self.trading_mode == 'paper':
                # Mode simulation
                self.logger.info(
                    f"[PAPER] Vente: {position.symbol} | "
                    f"Profit: {profit_percent:.2f}% | "
                    f"Raison: {reason}"
                )
                
                self.save_sell_to_db(position, profit_percent, reason, 'paper')
                del self.positions[position.token_address]
                
                # Supprimer le fichier de sauvegarde
                state_file = PROJECT_DIR / 'data' / f'position_{position.token_address}.json'
                if state_file.exists():
                    state_file.unlink()

                return True
                
            else:
                # Mode reel - Vente complete
                self.logger.info(f"[REAL] Execution vente reelle: {position.symbol}")
                
                weth_address = "0x4200000000000000000000000000000000000006"
                router_address = self.uniswap.router
                
                # 1. APPROVE TOKEN POUR LE ROUTER
                self.logger.info("etape 1: Approval du token pour le router")
                
                approve_abi = json.loads('''[
                    {
                        "inputs": [
                            {"name": "_spender", "type": "address"},
                            {"name": "_value", "type": "uint256"}
                        ],
                        "name": "approve",
                        "outputs": [{"name": "", "type": "bool"}],
                        "type": "function"
                    }
                ]''')
                
                token_contract = self.web3_manager.w3.eth.contract(
                    address=Web3.to_checksum_address(position.token_address),
                    abi=approve_abi
                )
                
                amount_to_sell = int(position.amount)
                
                approve_txn = token_contract.functions.approve(
                    Web3.to_checksum_address(router_address),
                    amount_to_sell
                ).build_transaction({
                    'from': self.web3_manager.account.address,
                    'gas': 100000,
                    'gasPrice': self.web3_manager.w3.eth.gas_price,
                    'nonce': self.web3_manager.w3.eth.get_transaction_count(
                        self.web3_manager.account.address
                    )
                })
                
                signed_approve = self.web3_manager.account.sign_transaction(approve_txn)
                approve_hash = self.web3_manager.w3.eth.send_raw_transaction(
                    signed_approve.rawTransaction
                )
                
                self.logger.info(f"Approval envoyee: {approve_hash.hex()}")
                
                approve_receipt = self.web3_manager.w3.eth.wait_for_transaction_receipt(
                    approve_hash, timeout=120
                )
                
                if approve_receipt['status'] != 1:
                    self.logger.error("echec de l'approval")
                    return False
                    
                self.logger.info("✅ Token approuve pour la vente")
                
                # 2. EXeCUTER LE SWAP TOKEN -> WETH
                self.logger.info("etape 2: Swap token vers WETH")
                
                # Calculer le minimum acceptable (3% slippage)
                eth_price = self.coingecko.get_eth_price()
                if eth_price == 0:
                    eth_price = 3000  # Valeur par defaut si erreur API
                    
                expected_weth = (position.current_price * position.amount) / eth_price
                min_weth_out = int(expected_weth * 0.97 * 10**18)  # 3% slippage
                
                deadline = int(time.time()) + 300  # 5 minutes
                
                swap_params = {
                    'tokenIn': Web3.to_checksum_address(position.token_address),
                    'tokenOut': Web3.to_checksum_address(weth_address),
                    'fee': 3000,
                    'recipient': self.web3_manager.account.address,
                    'deadline': deadline,
                    'amountIn': amount_to_sell,
                    'amountOutMinimum': min_weth_out,
                    'sqrtPriceLimitX96': 0
                }
                
                swap_txn = self.router.functions.exactInputSingle(
                    swap_params
                ).build_transaction({
                    'from': self.web3_manager.account.address,
                    'gas': 250000,
                    'gasPrice': self.web3_manager.w3.eth.gas_price,
                    'nonce': self.web3_manager.w3.eth.get_transaction_count(
                        self.web3_manager.account.address
                    )
                })
                
                signed_swap = self.web3_manager.account.sign_transaction(swap_txn)
                swap_hash = self.web3_manager.w3.eth.send_raw_transaction(
                    signed_swap.rawTransaction
                )
                
                self.logger.info(f"Swap envoye: {swap_hash.hex()}")
                
                swap_receipt = self.web3_manager.w3.eth.wait_for_transaction_receipt(
                    swap_hash, timeout=120
                )
                
                if swap_receipt['status'] == 1:
                    self.logger.info(
                        f"✅ Vente reussie: {position.symbol} | "
                        f"Profit: {profit_percent:.2f}% | "
                        f"TX: {swap_hash.hex()}"
                    )
                    
                    self.save_sell_to_db(position, profit_percent, reason, 'real', swap_hash.hex())
                    
                    del self.positions[position.token_address]
                    
                    # Supprimer le fichier de sauvegarde
                    state_file = PROJECT_DIR / 'data' / f'position_{position.token_address}.json'
                    if state_file.exists():
                        state_file.unlink()
                        
                    return True
                else:
                    self.logger.error(f"echec du swap: {swap_receipt}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Erreur vente: {e}")
            if 'position' in locals():
                self.save_position_state(position)
            return False
                       
    def update_positions(self):
        """Met a jour toutes les positions avec checks complets et retry"""
        for address, position in list(self.positions.items()):
            try:
                # Recuperer le prix actuel avec retry
                dex_data = None
                max_retries = 3
                
                for attempt in range(max_retries):
                    try:
                        dex_data = self.dexscreener.get_token_info(address)
                        if dex_data:
                            break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            self.logger.error(f"Impossible de recuperer le prix apres {max_retries} tentatives: {e}")
                        else:
                            self.logger.warning(f"Tentative {attempt + 1}/{max_retries} echouee, retry dans 2s")
                            time.sleep(2)
                
                if dex_data:
                    new_price = dex_data.get('price_usd', position.current_price)

                    # Validation du prix: ne peut pas varier de plus de 1000x par rapport au prix d'entrée
                    if new_price > 0 and position.entry_price > 0:
                        price_change_ratio = new_price / position.entry_price
                        if price_change_ratio > 1000 or price_change_ratio < 0.001:
                            self.logger.warning(
                                f"⚠️ Prix aberrant pour {position.symbol}: "
                                f"Entry=${position.entry_price:.8f}, New=${new_price:.8f} "
                                f"(ratio: {price_change_ratio:.1f}x) - Prix ignoré"
                            )
                            # Garder le dernier prix connu
                        else:
                            position.current_price = new_price
                    else:
                        position.current_price = new_price

                    # Protection contre division par zero
                    if position.entry_price == 0:
                        self.logger.error(f"Prix d'entree invalide pour {position.symbol}")
                        continue
                        
                    # Calculer le profit actuel
                    profit_percent = ((position.current_price - position.entry_price) / 
                                    position.entry_price) * 100
                    
                    # 1. Verifier TIME EXIT
                    should_exit, exit_reason = self.check_time_exit(position)
                    if should_exit:
                        self.logger.info(f"⏱️ Time exit: {exit_reason}")
                        self.execute_sell(position, exit_reason)
                        continue
                    
                    # 2. Verifier STOP LOSS fixe (-5%)
                    if profit_percent <= -self.stop_loss_percent:
                        self.logger.info(f"🛑 Stop Loss: {profit_percent:.1f}%")
                        self.execute_sell(position, f"Stop Loss ({profit_percent:.1f}%)")
                        continue
                    
                    # 3. Mettre a jour TRAILING STOP
                    self.update_trailing_stop(position)
                    
                    # 4. Verifier TRAILING STOP
                    if position.trailing_active and position.current_price <= position.stop_loss:
                        self.logger.info(
                            f"📉 Trailing Stop: {position.symbol} | "
                            f"Niveau {position.current_level} | "
                            f"Profit final: {profit_percent:.1f}%"
                        )
                        self.execute_sell(position, f"Trailing Stop L{position.current_level}")
                else:
                    self.logger.warning(f"Pas de donnees de prix pour {position.symbol}, utilisation du dernier prix connu")
                        
            except Exception as e:
                self.logger.error(f"Erreur update position {address}: {e}")
                # Sauvegarder l'etat en cas d'erreur
                self.save_position_state(position)

    def save_trade_to_db(self, token: Dict, action: str, price: float,
                         amount_eth: float, mode: str, tx_hash: str = ''):
        """Sauvegarde un trade dans la DB"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Inserer dans trade_log avec le schema correct
            cursor.execute('''
                INSERT INTO trade_log
                (timestamp, level, message, token_address, tx_hash)
                VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?)
            ''', ('INFO', f'{action} {token["symbol"]} @ ${price:.8f}', token['address'], tx_hash))

            if action == 'BUY':
                # Inserer dans trade_history avec entry_time
                cursor.execute('''
                    INSERT INTO trade_history
                    (token_address, symbol, side, amount_in, price, entry_time, timestamp)
                    VALUES (?, ?, 'BUY', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (token['address'], token['symbol'], amount_eth, price))

            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde trade DB: {e}")
            if 'conn' in locals():
                conn.close()
       
    def save_sell_to_db(self, position: Position, profit: float, reason: str, mode: str, tx_hash: str = ''):
        """Sauvegarde une vente dans la DB en mettant a jour la ligne existante"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # MISE A JOUR de la ligne existante (BUY) avec les donnees de sortie
            cursor.execute('''
                UPDATE trade_history
                SET amount_out = ?,
                    exit_time = CURRENT_TIMESTAMP,
                    profit_loss = ?
                WHERE token_address = ?
                AND exit_time IS NULL
            ''', (position.amount_eth, profit, position.token_address))

            if cursor.rowcount == 0:
                self.logger.warning(f"Aucune position ouverte trouvee pour {position.symbol} dans trade_history")

            # Log la transaction
            cursor.execute('''
                INSERT INTO trade_log
                (timestamp, level, message, token_address, tx_hash)
                VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?)
            ''', ('INFO', f'SELL {position.symbol} - Profit: {profit:.2f}% - {reason}',
                  position.token_address, tx_hash))

            # Inserer dans trailing_level_stats si c'etait un trailing stop
            if position.trailing_active:
                cursor.execute('''
                    INSERT INTO trailing_level_stats
                    (token_address, level, activation_price, stop_loss_price, timestamp)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (position.token_address, position.current_level,
                      position.highest_price, position.stop_loss))

            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde vente DB: {e}")
            if 'conn' in locals():
                conn.close()
   
    def log_performance_metrics(self):
        """Affiche les metriques de performance"""
        if self.performance_metrics['total_trades'] > 0:
            win_rate = (self.performance_metrics['winning_trades'] / 
                       self.performance_metrics['total_trades'] * 100)
            avg_profit = (self.performance_metrics['total_profit_percent'] / 
                         self.performance_metrics['total_trades'])
        else:
            win_rate = 0
            avg_profit = 0
           
        self.logger.info(
            f"📊 PERFORMANCE - "
            f"Trades: {self.performance_metrics['total_trades']} | "
            f"Win Rate: {win_rate:.1f}% | "
            f"Avg: {avg_profit:.1f}% | "
            f"Best: +{self.performance_metrics['best_trade']:.1f}% | "
            f"Worst: {self.performance_metrics['worst_trade']:.1f}% | "
            f"Time Exits: {self.performance_metrics['time_exits']} | "
            f"Trailing: {self.performance_metrics['trailing_exits']} | "
            f"Stop Loss: {self.performance_metrics['stoploss_exits']}"
        )
    
    def cleanup(self):
        """Nettoie les ressources"""
        if hasattr(self, 'dexscreener'):
            self.dexscreener.close()
        if hasattr(self, 'coingecko'):
            self.coingecko.close()
       
    def run(self):
        """Boucle principale avec monitoring 1 seconde"""
        self.logger.info(f"🚀 Trader - Strategie unique activee")
        self.logger.info(
            f"⚙️ Config: {self.position_size_percent}% positions | "
            f"Max {self.max_positions} positions | "
            f"{self.max_trades_per_day} trades/jour | "
            f"Stop Loss: -{self.stop_loss_percent}% | "
            f"Trailing: {self.trailing_config['activation_threshold']}%+"
        )
        self.logger.info(
            f"⏱️ Time Exit: {self.time_exit_config['stagnation']['hours']}h/+{self.time_exit_config['stagnation']['min_profit']}% | "
            f"{self.time_exit_config['low_momentum']['hours']}h/+{self.time_exit_config['low_momentum']['min_profit']}% | "
            f"{self.time_exit_config['maximum']['hours']}h force | "
            f"{self.time_exit_config['emergency']['hours']}h emergency"
        )
        
        # Compteurs pour logs periodiques
        last_performance_log = time.time()
        monitoring_counter = 0
        
        try:
            while True:
                try:
                    # Verifier le mode de trading
                    mode_file = PROJECT_DIR / 'config' / 'trading_mode.json'
                    if mode_file.exists():
                        try:
                            with open(mode_file, 'r') as f:
                                data = json.load(f)
                                new_mode = data.get('mode', 'paper')
                                if new_mode != self.trading_mode:
                                    self.logger.info(f"🔄 Mode change: {self.trading_mode} → {new_mode}")
                                    self.trading_mode = new_mode
                        except Exception as e:
                            self.logger.error(f"Erreur lecture mode: {e}")
                            
                    # Mettre a jour les positions existantes
                    if self.positions:
                        self.update_positions()
                        
                        # Log rapide toutes les 10 secondes
                        monitoring_counter += 1
                        if monitoring_counter >= 10:
                            for addr, pos in self.positions.items():
                                if pos.entry_price > 0:
                                    profit = ((pos.current_price - pos.entry_price) / 
                                            pos.entry_price) * 100
                                    hours = (datetime.now() - pos.entry_time).total_seconds() / 3600
                                    
                                    status = "📈 Trailing" if pos.trailing_active else "⏳ Attente"
                                    self.logger.info(
                                        f"{status} {pos.symbol}: "
                                        f"+{profit:.1f}% | "
                                        f"{hours:.1f}h | "
                                        f"Stop: ${pos.stop_loss:.8f}"
                                    )
                            monitoring_counter = 0
                    
                    # Verifier limite quotidienne
                    today = datetime.now().date()
                    if self.last_trade_day != today:
                        self.daily_trades = 0
                        self.last_trade_day = today
                        self.logger.info(f"📅 Nouveau jour - Trades disponibles: {self.max_trades_per_day}")
                        
                    # Chercher nouvelle opportunite
                    if (len(self.positions) < self.max_positions and 
                        self.daily_trades < self.max_trades_per_day):
                        
                        token = self.get_next_token()
                        if token:
                            # Validation supplementaire
                            if token.get('price_usd', 0) <= 0:
                                self.logger.warning(f"Token {token.get('symbol')} avec prix invalide, ignore")
                                continue
                                
                            self.logger.info(
                                f"📊 Opportunite detectee: {token['symbol']} | "
                                f"Liq: ${token['liquidity']:,.0f} | "
                                f"Vol: ${token['volume_24h']:,.0f} | "
                                f"Score: {token['score']}"
                            )
                            
                            # Verification finale avant achat
                            if len(self.positions) < self.max_positions:
                                if self.execute_buy(token):
                                    self.daily_trades += 1
                                    self.logger.info(
                                        f"📈 Position {len(self.positions)}/{self.max_positions} | "
                                        f"Trades aujourd'hui: {self.daily_trades}/{self.max_trades_per_day}"
                                    )
                            else:
                                self.logger.warning("Positions maximum atteintes")
                                
                    # Log performance toutes les heures
                    if time.time() - last_performance_log > 3600:
                        self.log_performance_metrics()
                        last_performance_log = time.time()
                        
                    # Pause de 1 seconde (monitoring rapide)
                    time.sleep(self.monitoring_interval)
                    
                except KeyboardInterrupt:
                    self.logger.info("🛑 Arrêt demande par l'utilisateur")
                    self.log_performance_metrics()
                    
                    # Sauvegarder l'etat final
                    for position in self.positions.values():
                        self.save_position_state(position)
                        
                    break
                    
                except Exception as e:
                    self.logger.error(f"Erreur boucle principale: {e}")
                    # En cas d'erreur critique, sauvegarder les positions
                    for position in self.positions.values():
                        try:
                            self.save_position_state(position)
                        except:
                            pass
                    time.sleep(10)
        finally:
            self.cleanup()

if __name__ == "__main__":
    trader = RealTrader()
    try:
        trader.run()
    except Exception as e:
        trader.logger.error(f"Erreur fatale: {e}")
        # Sauvegarder les positions en cas de crash
        for position in trader.positions.values():
            try:
                trader.save_position_state(position)
            except:
                pass
        trader.cleanup()
