# 📖 GUIDE DE CONFIGURATION COMPLÈTE

## 🎯 Stratégie Totalement Configurable depuis .env

**Tous les paramètres de trading et de sélection de tokens sont configurables via le fichier `.env`** sans modifier le code!

---

## ✅ Paramètres Actuellement Configurables

### **1. 🎯 Stratégie de Trading**

| Paramètre | Valeur Défaut | Description | Configurable |
|-----------|---------------|-------------|--------------|
| `TRADING_MODE` | `paper` | Mode: `paper` (simulation) ou `real` (production) | ✅ |
| `POSITION_SIZE_PERCENT` | `15` | Taille de position en % du capital | ✅ |
| `MAX_POSITIONS` | `2` | Nombre max de positions simultanées | ✅ |
| `MAX_TRADES_PER_DAY` | `3` | Nombre max de trades par jour | ✅ |
| `STOP_LOSS_PERCENT` | `5` | Stop loss normal en % | ✅ |
| `TRAILING_ACTIVATION_THRESHOLD` | `12` | Activation du trailing à +12% | ✅ |
| `MONITORING_INTERVAL` | `1` | Intervalle monitoring (secondes) | ✅ |
| `TOKEN_APPROVAL_MAX_AGE_HOURS` | `12` | Expiration tokens approuvés (heures) | ✅ |
| `REJECTED_TOKEN_COOLDOWN_MINUTES` | `30` | Cooldown tokens rejetés (minutes) | ✅ |

---

### **2. ⏱️ GRACE PERIOD** ✨ **NOUVEAU!**

**La Grace Period est maintenant totalement configurable!**

| Paramètre | Valeur Défaut | Description | Exemple |
|-----------|---------------|-------------|---------|
| `GRACE_PERIOD_ENABLED` | `true` | Activer/désactiver grace period | `true` ou `false` |
| `GRACE_PERIOD_MINUTES` | `3` | Durée de la grace period (minutes) | `3`, `5`, `10` |
| `GRACE_PERIOD_STOP_LOSS` | `35` | Stop loss pendant grace period (%) | `35`, `50`, `60` |

**Exemple de configuration:**
```bash
# Activer grace period de 5 minutes avec SL à -50%
GRACE_PERIOD_ENABLED=true
GRACE_PERIOD_MINUTES=5
GRACE_PERIOD_STOP_LOSS=50

# Ou désactiver complètement
GRACE_PERIOD_ENABLED=false
```

**Comment ça fonctionne:**
- Pendant les `X` premières minutes (ex: 3 min), le SL est élargi à `-Y%` (ex: -35%)
- Après la grace period, le SL normal s'applique (ex: -5%)
- **Objectif:** Éviter les sorties prématurées dues au slippage initial

**Affichage dans le Dashboard:**
- ✅ Status: Activée ou Désactivée
- ✅ Durée: X minutes
- ✅ SL temporaire: -Y%

---

### **3. 🔍 Scanner Configuration**

| Paramètre | Valeur Défaut | Description | Configurable |
|-----------|---------------|-------------|--------------|
| `SCAN_INTERVAL_SECONDS` | `30` | Intervalle entre scans (secondes) | ✅ |
| `MAX_BLOCKS_PER_SCAN` | `100` | Nombre max de blocs par scan | ✅ |
| `SCANNER_START_BLOCK` | `0` | Bloc de départ | ✅ |

---

### **4. 🎯 Filter - Critères de Sélection**

**Tous les critères de filtrage sont configurables!**

| Paramètre | Valeur Défaut | Description | Configurable |
|-----------|---------------|-------------|--------------|
| `MIN_AGE_HOURS` | `2` | Âge minimum du token (heures) | ✅ |
| `MIN_LIQUIDITY_USD` | `30000` | Liquidité minimum (USD) | ✅ |
| `MAX_LIQUIDITY_USD` | `10000000` | Liquidité maximum (USD) | ✅ |
| `MIN_VOLUME_24H` | `50000` | Volume 24h minimum (USD) | ✅ |
| `MIN_HOLDERS` | `150` | Nombre minimum de holders | ✅ |
| `MIN_MARKET_CAP` | `25000` | Market cap minimum (USD) | ✅ |
| `MAX_MARKET_CAP` | `10000000` | Market cap maximum (USD) | ✅ |
| `MAX_OWNER_PERCENTAGE` | `10.0` | % max détenu par owner | ✅ |
| `MAX_BUY_TAX` | `5` | Taxe d'achat maximum (%) | ✅ |
| `MAX_SELL_TAX` | `5` | Taxe de vente maximum (%) | ✅ |
| `MIN_SAFETY_SCORE` | `70` | Score de sécurité minimum | ✅ |
| `MIN_POTENTIAL_SCORE` | `60` | Score de potentiel minimum | ✅ |

**Exemple - Stratégie Conservative:**
```bash
MIN_AGE_HOURS=6              # Tokens plus établis
MIN_LIQUIDITY_USD=100000     # Liquidité élevée
MIN_VOLUME_24H=200000        # Volume élevé
MIN_HOLDERS=500              # Beaucoup de holders
MAX_BUY_TAX=2                # Taxes faibles
MAX_SELL_TAX=2
```

**Exemple - Stratégie Aggressive:**
```bash
MIN_AGE_HOURS=0.5            # Tokens très récents
MIN_LIQUIDITY_USD=10000      # Liquidité faible OK
MIN_VOLUME_24H=10000         # Volume faible OK
MIN_HOLDERS=50               # Peu de holders OK
MAX_BUY_TAX=10               # Taxes élevées OK
MAX_SELL_TAX=10
```

---

### **5. 📈 Trailing Stop - 4 Niveaux**

**Chaque niveau est configurable!**

| Niveau | Paramètres | Valeurs Défaut | Description |
|--------|-----------|----------------|-------------|
| **Niveau 1** | `TRAILING_L1_MIN`<br>`TRAILING_L1_MAX`<br>`TRAILING_L1_DISTANCE` | `12`<br>`30`<br>`3` | Profit 12-30% → Trailing -3% |
| **Niveau 2** | `TRAILING_L2_MIN`<br>`TRAILING_L2_MAX`<br>`TRAILING_L2_DISTANCE` | `30`<br>`100`<br>`5` | Profit 30-100% → Trailing -5% |
| **Niveau 3** | `TRAILING_L3_MIN`<br>`TRAILING_L3_MAX`<br>`TRAILING_L3_DISTANCE` | `100`<br>`300`<br>`10` | Profit 100-300% → Trailing -10% |
| **Niveau 4** | `TRAILING_L4_MIN`<br>`TRAILING_L4_MAX`<br>`TRAILING_L4_DISTANCE` | `300`<br>`99999`<br>`30` | Profit 300%+ → Trailing -30% |

**Exemple - Trailing Plus Serré:**
```bash
TRAILING_L1_DISTANCE=2      # -2% au lieu de -3%
TRAILING_L2_DISTANCE=3      # -3% au lieu de -5%
TRAILING_L3_DISTANCE=5      # -5% au lieu de -10%
```

---

### **6. ⏱️ Time Exit Configuration**

| Paramètre | Valeur Défaut | Description | Configurable |
|-----------|---------------|-------------|--------------|
| `TIME_EXIT_STAGNATION_HOURS` | `24` | Sortie si profit < X% après 24h | ✅ |
| `TIME_EXIT_STAGNATION_MIN_PROFIT` | `5` | Profit minimum pour éviter sortie stagnation | ✅ |
| `TIME_EXIT_LOW_MOMENTUM_HOURS` | `48` | Sortie si profit < X% après 48h | ✅ |
| `TIME_EXIT_LOW_MOMENTUM_MIN_PROFIT` | `20` | Profit minimum pour éviter sortie low momentum | ✅ |
| `TIME_EXIT_MAXIMUM_HOURS` | `72` | Sortie forcée après 72h | ✅ |
| `TIME_EXIT_EMERGENCY_HOURS` | `120` | Sortie forcée après 120h | ✅ |

---

### **7. 🔧 Advanced Settings**

| Paramètre | Valeur Défaut | Description | Configurable |
|-----------|---------------|-------------|--------------|
| `MAX_GAS_PRICE_GWEI` | `50` | Prix gas maximum (Gwei) | ✅ |
| `GAS_LIMIT_BUY` | `250000` | Gas limit pour achat | ✅ |
| `GAS_LIMIT_SELL` | `300000` | Gas limit pour vente | ✅ |
| `MAX_SLIPPAGE_PERCENT` | `3` | Slippage maximum (%) | ✅ |
| `EMERGENCY_SLIPPAGE_PERCENT` | `5` | Slippage d'urgence (%) | ✅ |
| `MAX_RETRIES` | `3` | Nombre max de tentatives | ✅ |
| `RETRY_DELAY_SECONDS` | `2` | Délai entre tentatives (secondes) | ✅ |

---

## 📋 Checklist de Configuration

### **Avant de démarrer:**

- [ ] Copier `config/.env.example` vers `config/.env`
- [ ] Remplir `WALLET_ADDRESS` et `PRIVATE_KEY`
- [ ] Remplir `ETHERSCAN_API_KEY` et `COINGECKO_API_KEY`
- [ ] Choisir `TRADING_MODE=paper` ou `real`
- [ ] Ajuster les critères de filtrage selon votre stratégie
- [ ] Configurer la grace period selon vos besoins
- [ ] Vérifier les paramètres de trailing stop
- [ ] Tester en mode PAPER pendant 24-48h minimum

---

## 🎯 Exemples de Configurations Prêtes

### **Configuration Conservative (Sécurité Max)**

```bash
# Trading
POSITION_SIZE_PERCENT=10      # Positions plus petites
MAX_POSITIONS=1               # Une position à la fois
MAX_TRADES_PER_DAY=2          # Peu de trades
STOP_LOSS_PERCENT=3           # SL serré

# Grace Period
GRACE_PERIOD_ENABLED=true
GRACE_PERIOD_MINUTES=5        # Plus longue
GRACE_PERIOD_STOP_LOSS=50     # Plus large

# Filtrage
MIN_AGE_HOURS=6               # Tokens établis
MIN_LIQUIDITY_USD=100000      # Liquidité élevée
MIN_VOLUME_24H=200000         # Volume élevé
MIN_HOLDERS=500               # Beaucoup de holders
MAX_BUY_TAX=2                 # Taxes faibles
MAX_SELL_TAX=2
```

### **Configuration Balanced (Défaut Recommandé)**

```bash
# Trading
POSITION_SIZE_PERCENT=15
MAX_POSITIONS=2
MAX_TRADES_PER_DAY=3
STOP_LOSS_PERCENT=5

# Grace Period
GRACE_PERIOD_ENABLED=true
GRACE_PERIOD_MINUTES=3
GRACE_PERIOD_STOP_LOSS=35

# Filtrage
MIN_AGE_HOURS=2
MIN_LIQUIDITY_USD=30000
MIN_VOLUME_24H=50000
MIN_HOLDERS=150
MAX_BUY_TAX=5
MAX_SELL_TAX=5
```

### **Configuration Aggressive (Risque Élevé)**

```bash
# Trading
POSITION_SIZE_PERCENT=25      # Positions plus grosses
MAX_POSITIONS=3               # Plusieurs positions
MAX_TRADES_PER_DAY=10         # Beaucoup de trades
STOP_LOSS_PERCENT=8           # SL plus large

# Grace Period
GRACE_PERIOD_ENABLED=false    # Désactivée

# Filtrage
MIN_AGE_HOURS=0.5             # Tokens très récents
MIN_LIQUIDITY_USD=10000       # Liquidité faible OK
MIN_VOLUME_24H=10000          # Volume faible OK
MIN_HOLDERS=50                # Peu de holders OK
MAX_BUY_TAX=10                # Taxes élevées OK
MAX_SELL_TAX=10
```

---

## 📊 Dashboard - Visualisation Config

**Toute la configuration est visible dans le Dashboard!**

**Section "⚙️ Configuration":**
- ✅ Mode de trading
- ✅ Taille des positions
- ✅ Stop Loss
- ✅ **Grace Period** (nouveau!) - Status, durée, SL temporaire
- ✅ Trailing stop (tous les niveaux)
- ✅ Time exit
- ✅ Critères de filtrage

**Accès Dashboard:**
```
http://VOTRE_VPS_IP:8501
```

---

## 🔄 Modifier la Configuration en Cours

**Pour changer la configuration:**

1. Éditer le fichier .env:
```bash
sudo nano /home/basebot/trading-bot/config/.env
```

2. Modifier les valeurs souhaitées

3. Redémarrer les services:
```bash
sudo systemctl restart basebot-trader
sudo systemctl restart basebot-filter  # Si critères modifiés
```

4. Vérifier dans le Dashboard que les changements sont pris en compte

---

## ✅ Validation

**Vérifier que la configuration est appliquée:**

```bash
# Voir les logs du Trader
sudo journalctl -u basebot-trader -n 50

# Vérifier grace period (si activée)
# Devrait afficher: "Grace period: X min @ -Y%"
```

**Dans le Dashboard:**
- Aller dans l'onglet "⚙️ Configuration"
- Vérifier que tous les paramètres affichés correspondent au .env
- **Grace Period** doit afficher "Xmin @ -Y%" ou "Désactivée"

---

## 📝 Résumé

**✅ Stratégie 100% Configurable:**
- Tous les paramètres de trading dans .env
- Tous les critères de sélection dans .env
- Grace period activable/configurable dans .env
- Dashboard affiche toute la configuration

**✅ Aucune modification de code nécessaire!**

**✅ Changements appliqués en redémarrant les services!**

---

**Date:** 2025-11-18
**Version:** v3.1 - Configuration Totalement Flexible
**Auteur:** Claude Code
