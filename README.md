# 🤖 BaseBot - Trading Bot Autonome sur Base Chain

Bot de trading automatisé optimisé pour Base Chain avec scanner on-chain, filtrage multi-critères et gestion des positions.

## 🚀 Installation Rapide

### Installation VPS Vierge (Un Seul Commande)

```bash
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | bash
```

**Le bot sera opérationnel en ~5 minutes.**

### Installation Manuelle

```bash
# 1. Cloner le repo
git clone https://github.com/supermerou03101983/BaseBot.git
cd BaseBot

# 2. Déployer
chmod +x deploy.sh
./deploy.sh
```

---

## ⚙️ Configurations Disponibles

Le bot propose **2 configurations** :

### 1️⃣ **Momentum Safe v2** (PRODUCTION) - `.env.example`
- 🎯 Win-rate cible : **≥70%**
- 📊 Trades/jour : **2-5**
- ✅ Fenêtre : **3.5-8h** (sweet spot momentum)
- ✅ Critères stricts : Liquidité $12K+, MC $80K+, 120+ holders
- 💰 Usage : **Production avec capital réel**

### 2️⃣ **Test Permissif** (VALIDATION) - `.env.test.permissif`
- 🎯 Win-rate attendu : **10-30%** (normal)
- 📊 Trades/jour : **10-20**
- ⚠️ Fenêtre : **0-72h** (tous nouveaux tokens)
- ⚠️ Critères permissifs : Liquidité $500+, MC $1K+, 10+ holders
- 🧪 Usage : **Tests et validation workflow UNIQUEMENT**

### 🔄 Basculer Entre Configurations

```bash
# Script interactif
./switch_config.sh

# Ou manuellement
cp config/.env.example config/.env              # Production
cp config/.env.test.permissif config/.env       # Tests
```

📚 **Documentation complète** : [config/README_CONFIGS.md](config/README_CONFIGS.md)
🚀 **Guide test rapide** : [QUICK_START_TEST.md](QUICK_START_TEST.md)

---

## 📋 Fonctionnalités

### 🔍 Scanner On-Chain (Modification #5)
- Scan direct des événements `PairCreated` sur blockchain
- Support Uniswap V3 + Aerodrome + BaseSwap
- Filtrage par âge (3.5-8h en prod, 0-72h en test)
- RPC fallback automatique (4 RPC configurés)
- Indépendant des APIs externes pour la détection

### 🎯 Filtre Multi-Critères (Momentum Safe v2)
- **12 critères stricts** en production :
  - Fenêtre d'âge : 3.5-8h
  - Liquidité : $12K-$2M
  - Market Cap : $80K-$2.5M
  - Volume 1h/5min + ratio accélération
  - Momentum prix 5min/1h
  - Distribution : 120+ holders, owner ≤5%
  - Taxes : ≤3%
  - Honeypot detection
  - Contract verified
  - Liquidity locked
- **Enrichissement** : BirdEye (prioritaire) + DexScreener + on-chain fallback
- **Retry logic** : Réanalyse progressive des tokens rejetés

### 💰 Trader Intelligent
- **Grace period** configurable (3min, -35% SL par défaut)
- **Stop-loss** dynamique (-5% après grace period)
- **Trailing stop** multi-niveaux (L1-L4)
- **Time exits** : Stagnation, low momentum, maximum duration
- **Losing token cooldown** : 24h anti-revenge trading
- **Paper trading** / Real trading avec protection MEV (dRPC)
- Gestion positions en JSON + DB

### 📊 Dashboard Temps Réel (Streamlit)
- Stats performance (win-rate brut/net, profit moyen)
- Positions actives avec détails
- Historique trades avec calcul frais
- Affichage complet de la stratégie active
- Métriques losing cooldown et retry logic

---

## ⚙️ Configuration

### Variables Essentielles (.env)

```bash
# Wallet
PRIVATE_KEY=0x...                      # Clé privée wallet

# RPC
RPC_URL=https://mainnet.base.org       # RPC Base stable

# Scanner On-Chain
MIN_TOKEN_AGE_HOURS=2                  # Âge min tokens
MAX_TOKEN_AGE_HOURS=12                 # Âge max tokens
SCAN_INTERVAL_SECONDS=30               # Fréquence scan

# Filter
MIN_VOLUME_24H=10000                   # Volume 24h min (USD)
MIN_VOLUME_1H=1000                     # Volume 1h min (USD)
MIN_LIQUIDITY_USD=5000                 # Liquidité min (USD)
MIN_HOLDERS=50                         # Holders min
MIN_AGE_HOURS=2                        # Âge min (heures)
MIN_PRICE_CHANGE_5M=5                  # Momentum 5min (%)

# Trader
PAPER_TRADING=true                     # true = simulation, false = réel
TRADE_AMOUNT_USD=10                    # Montant par trade (USD)
STOP_LOSS_PERCENT=15                   # Stop-loss (%)
TAKE_PROFIT_PERCENT=30                 # Take-profit (%)
GRACE_PERIOD_ENABLED=true              # Grace period actif
GRACE_PERIOD_MINUTES=5                 # Durée grace (min)
GRACE_PERIOD_STOP_LOSS=25              # SL grace period (%)
```

---

## 🛠️ Commandes

### Déploiement
```bash
./scripts/deploy.sh                    # Installation complète VPS
```

### Gestion Services
```bash
./scripts/start_all_services.sh        # Démarrer tous les services
./scripts/stop_all_services.sh         # Arrêter tous les services
./scripts/status.sh                    # État des services
```

### Maintenance
```bash
./tools/verify_deployment.sh           # Vérifier installation
./tools/maintenance_monthly.sh         # Maintenance mensuelle
./tools/quick_fix.sh                   # Fix rapide
```

### Monitoring
```bash
# Logs temps réel
tail -f logs/scanner.log
tail -f logs/filter.log
tail -f logs/trader.log

# Dashboard
systemctl status basebot-dashboard
# Accès: http://VPS_IP:3000
```

---

## 📊 Architecture

```
Scanner (on-chain) → Filter (multi-critères) → Trader (positions) → Dashboard (stats)
        ↓                    ↓                       ↓
  discovered_tokens   approved_tokens        trade_history
```

### Scanner On-Chain
- Scan événements `PairCreated` toutes les 30s
- Filtre tokens 2h-12h d'âge
- Enrichit métadonnées ERC20
- Enregistre dans `discovered_tokens`

### Filter
- Analyse chaque token découvert
- Applique critères multi-facteurs
- Détecte honeypots
- Enregistre approuvés dans `approved_tokens`

### Trader
- Ouvre positions sur tokens approuvés
- Applique grace period (5min, -25% SL)
- Gère SL/TP adaptatifs
- Enregistre dans `trade_history`

### Dashboard
- Affiche stats en temps réel
- Historique complet
- Métriques de performance

---

## 🔧 Troubleshooting

### Scanner ne détecte pas de tokens
```bash
# Vérifier RPC
grep RPC_URL config/.env

# Vérifier logs
tail -n 50 logs/scanner.log | grep "tokens détectés"

# Vérifier fenêtre d'âge
grep -E "MIN_TOKEN_AGE|MAX_TOKEN_AGE" config/.env
```

### Filter rejette tous les tokens
```bash
# Vérifier critères
grep -E "MIN_VOLUME|MIN_LIQUIDITY|MIN_HOLDERS" config/.env

# Vérifier logs rejets
tail -n 100 logs/filter.log | grep "REJET"

# Assouplir critères temporairement
sed -i 's/MIN_VOLUME_24H=10000/MIN_VOLUME_24H=5000/' config/.env
systemctl restart basebot-filter
```

### Trader ne passe pas d'ordres
```bash
# Vérifier mode
grep PAPER_TRADING config/.env

# Vérifier wallet
grep PRIVATE_KEY config/.env | wc -c  # Doit être > 66

# Vérifier logs
tail -n 50 logs/trader.log | grep -E "Achat|Erreur"
```

### Dashboard ne s'affiche pas
```bash
# Vérifier service
systemctl status basebot-dashboard

# Vérifier port
netstat -tlnp | grep 3000

# Redémarrer
systemctl restart basebot-dashboard
```

---

## 📚 Documentation Complète

- **[DEPLOYMENT](docs/DEPLOYMENT.md)** - Guide déploiement détaillé
- **[CONFIGURATION](docs/CONFIGURATION.md)** - Configuration avancée
- **[ONCHAIN_SCANNER](docs/ONCHAIN_SCANNER.md)** - Scanner on-chain
- **[TROUBLESHOOTING](docs/TROUBLESHOOTING.md)** - Dépannage complet

---

## 🎯 Performance

### Métriques Actuelles (Modification #5)
- **Scan**: 50 tokens/cycle (~40s)
- **Filter**: ~70% taux approbation
- **Trader**: Grace period actif (5min, -25%)
- **RPC**: mainnet.base.org (stable)

### Historique Modifications
- **Mod #1**: Filtrage âge tokens
- **Mod #2**: Critères volume/momentum
- **Mod #3**: Cooldown perdants
- **Mod #4**: Âge minimum réduit
- **Mod #5**: Scanner on-chain ✅

---

## 🔐 Sécurité

- ✅ Clé privée chiffrée dans `.env`
- ✅ `.env` dans `.gitignore`
- ✅ Paper trading par défaut
- ✅ Stop-loss obligatoire
- ✅ Détection honeypots
- ✅ Rate limit RPC géré

---

## 📞 Support

- **Issues**: https://github.com/supermerou03101983/BaseBot/issues
- **Docs**: [docs/](docs/)
- **Logs**: `logs/`

---

## 📜 Licence

Propriétaire - Tous droits réservés

---

**🔥 Modification #5: Scanner On-Chain Actif**

Le bot utilise maintenant un scanner on-chain direct analysant les événements `PairCreated` sur Aerodrome et BaseSwap, offrant une indépendance totale des APIs externes et une précision maximale.
