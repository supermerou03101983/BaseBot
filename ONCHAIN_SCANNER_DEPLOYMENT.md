# 🔥 Déploiement Scanner On-Chain

## Modification #5: Scanner par Événements PairCreated

**Date**: 28 Novembre 2025
**Objectif**: Remplacer l'approche DexScreener/GeckoTerminal par un scanner on-chain direct

---

## 📋 Changements Apportés

### 1. Nouveau Module: `pair_event_window_scanner.py`

Scanner autonome qui:
- Se connecte directement à la blockchain Base via RPC
- Scanne les événements `PairCreated` sur Aerodrome et BaseSwap
- Filtre les tokens par âge (2h à 12h par défaut)
- Découpe automatiquement les requêtes en chunks de 1000 blocs (limite RPC)
- Récupère les métadonnées ERC20 (symbol, name, decimals)

**Factories supportées:**
- Aerodrome: `0x420DD381b31aEf6683db6B902084cB0FFECe40Da`
- BaseSwap: `0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6`

**Tokens de base supportés:**
- WETH: `0x4200000000000000000000000000000000000006`
- USDC: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- USDbC: `0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA`

### 2. Modifications dans `Scanner.py`

#### Import ajouté:
```python
from pair_event_window_scanner import PairEventWindowScanner
```

#### Initialisation (dans `__init__`):
```python
# 🔥 Scanner on-chain par événements PairCreated
try:
    self.onchain_scanner = PairEventWindowScanner(
        rpc_url=os.getenv('RPC_URL', 'https://base.llamarpc.com'),
        logger=self.logger
    )
    self.logger.info("✅ Scanner on-chain initialisé")
except Exception as e:
    self.logger.error(f"❌ Erreur init scanner on-chain: {e}")
    self.onchain_scanner = None
```

#### Méthode `fetch_new_tokens()` réécrite:
- Utilise maintenant `onchain_scanner.scan_tokens_in_age_window()`
- Enrichit les tokens avec métadonnées ERC20
- Format compatible avec le pipeline existant
- Fallback vers DB en cas d'erreur

### 3. Configuration `.env`

Variables requises:
```bash
RPC_URL=https://base.llamarpc.com
MIN_TOKEN_AGE_HOURS=2
MAX_TOKEN_AGE_HOURS=12
```

---

## 🚀 Déploiement

### Fichiers à déployer:
1. `src/pair_event_window_scanner.py` ✅
2. `src/Scanner.py` ✅
3. Configuration `.env` mise à jour ✅

### Commandes de déploiement:

```bash
# 1. Depuis le repo local
cd /Users/vincentdoms/Documents/BaseBot
git add pair_event_window_scanner.py Scanner.py test_pair_scanner.py
git commit -m "🔥 Modification #5: Scanner on-chain par événements PairCreated"
git push origin main

# 2. Sur le VPS
ssh root@46.62.194.176
cd /home/basebot/trading-bot
git pull origin main

# 3. Mettre à jour .env
sed -i 's/MIN_TOKEN_AGE_HOURS=0.1/MIN_TOKEN_AGE_HOURS=2/' config/.env
sed -i 's|RPC_URL=https://base.drpc.org|RPC_URL=https://base.llamarpc.com|' config/.env

# 4. Redémarrer le scanner
systemctl restart basebot-scanner
systemctl status basebot-scanner

# 5. Vérifier les logs
tail -f logs/scanner.log | grep -E "Scanner on-chain|Scan on-chain|tokens on-chain"
```

---

## ✅ Avantages du Scanner On-Chain

### 🎯 Avantages:
1. **Indépendance**: Plus de dépendance aux APIs externes (DexScreener/GeckoTerminal)
2. **Fiabilité**: Données directement depuis la blockchain
3. **Précision**: Filtrage exact par âge de paire (blocs)
4. **Performance**: Scan rapide avec chunking automatique
5. **Exhaustivité**: Couvre Aerodrome ET BaseSwap
6. **Coût**: RPC gratuit (base.llamarpc.com)

### ⚡ Performance:
- **Scan 2-6h**: ~7200 blocs → 8 chunks → ~3-5 secondes
- **Scan 2-12h**: ~18000 blocs → 18 chunks → ~8-12 secondes
- **Limite**: 50 tokens par scan (configurable via `batch_size`)

---

## 🧪 Tests

### Test autonome:
```bash
cd /home/basebot/trading-bot
source venv/bin/activate
python3 test_pair_scanner.py
```

### Test du module:
```python
from src.pair_event_window_scanner import PairEventWindowScanner

scanner = PairEventWindowScanner()
tokens = scanner.scan_tokens_in_age_window(min_hours=2, max_hours=6, max_results=10)

for token in tokens:
    metadata = scanner.get_token_metadata(token['token_address'])
    print(f"{metadata['symbol']}: {token['age_hours']:.1f}h - {token['factory_name']}")
```

---

## 📊 Format des Données Retournées

### Données brutes (scanner on-chain):
```python
{
    'token_address': '0x...',
    'pair_address': '0x...',
    'base_token': '0x...',  # WETH/USDC/USDbC
    'factory': '0x...',
    'factory_name': 'Aerodrome' | 'BaseSwap',
    'block_created': 12345,
    'age_hours': 5.2,
    'discovered_at': 1732780800  # timestamp
}
```

### Données enrichies (après métadonnées):
```python
{
    'address': '0x...',
    'symbol': 'TOKEN',
    'name': 'Token Name',
    'decimals': 18,
    'pair_address': '0x...',
    'base_token': '0x...',
    'factory': 'Aerodrome',
    'block_created': 12345,
    'age_hours': 5.2,
    'discovered_at': 1732780800
}
```

---

## 🔧 Maintenance

### Logs à surveiller:
```bash
# Scanner on-chain initialisé ?
grep "Scanner on-chain initialisé" logs/scanner.log

# Nombre de tokens détectés
grep "tokens détectés dans la fenêtre" logs/scanner.log

# Erreurs RPC
grep "Erreur scan on-chain" logs/scanner.log
```

### Problèmes courants:

**1. RPC timeout**
- Solution: Réduire `MAX_TOKEN_AGE_HOURS` ou augmenter `CHUNK_SIZE`

**2. Aucun token trouvé**
- Vérifier que `MIN_TOKEN_AGE_HOURS` n'est pas trop élevé
- Vérifier la connectivité RPC

**3. Erreur de métadonnées**
- Certains tokens n'implémentent pas correctement ERC20
- Le scanner continue avec fallback (symbol="???")

---

## 📈 Évolutions Futures

### Possibles améliorations:
1. Support d'autres factories (Uniswap V3, etc.)
2. Cache des métadonnées en DB
3. Filtrage par volume de paire
4. Détection de honeypots on-chain
5. Multi-threading pour enrichissement parallèle

---

## 🎯 Résultat Attendu

Après déploiement, le scanner devrait:
- Détecter 10-50 nouveaux tokens toutes les 30 secondes
- Filtrer uniquement ceux entre 2h et 12h d'âge
- Les envoyer au Filter pour analyse
- Ne plus dépendre de DexScreener/GeckoTerminal

**Prochaine étape**: Observer les performances pendant 24h, puis ajuster `MIN_TOKEN_AGE_HOURS` si nécessaire.
