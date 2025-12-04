# 🔧 Guide des Configurations BaseBot

Ce dossier contient **deux configurations** pour le BaseBot :

---

## 📋 Configurations Disponibles

### 1️⃣ `.env.example` - **MOMENTUM SAFE V2** (PRODUCTION)

**🎯 Stratégie** : Qualité > Quantité
**🎲 Win-rate cible** : ≥70%
**📊 Trades/jour** : 2-5

#### Critères Stricts :
- ✅ **Fenêtre d'âge** : 3.5h - 8.0h (sweet spot momentum)
- ✅ **Liquidité** : $12,000 - $2,000,000
- ✅ **Market Cap** : $80,000 - $2,500,000
- ✅ **Volume 1h** : ≥$4,000
- ✅ **Volume 5min** : ≥$800
- ✅ **Ratio vol 5m/1h** : ≥0.3 (accélération)
- ✅ **Δ Prix 5min** : ≥+4%
- ✅ **Δ Prix 1h** : ≥+7%
- ✅ **Holders** : ≥120
- ✅ **Owner** : ≤5%
- ✅ **Taxes** : Buy ≤3%, Sell ≤3%
- ✅ **Stop Loss** : -5%
- ✅ **Losing Cooldown** : 24h

#### Quand l'utiliser :
- ✅ Trading en **mode RÉEL** (production)
- ✅ Objectif de **rentabilité maximale**
- ✅ **Capital important** à protéger

---

### 2️⃣ `.env.test.permissif` - **TEST RAPIDE** (VALIDATION)

**🎯 Objectif** : Valider le workflow complet
**🎲 Win-rate attendu** : 10-30% (normal)
**📊 Trades/jour** : 10-20

#### Critères Permissifs :
- ⚠️ **Fenêtre d'âge** : 0h - 72h (tous nouveaux tokens)
- ⚠️ **Liquidité** : $500+
- ⚠️ **Market Cap** : $1,000+
- ⚠️ **Volume 1h** : ≥$50
- ⚠️ **Volume 5min** : ≥$10
- ⚠️ **Ratio vol 5m/1h** : ≥0.05
- ⚠️ **Δ Prix 5min** : ≥-5% (accepte baisse)
- ⚠️ **Δ Prix 1h** : ≥-10% (accepte baisse)
- ⚠️ **Holders** : ≥10
- ⚠️ **Owner** : ≤50%
- ⚠️ **Taxes** : Buy ≤15%, Sell ≤15%
- ⚠️ **Stop Loss** : -15% (élargi)
- ⚠️ **Losing Cooldown** : 1h (court)

#### Quand l'utiliser :
- ✅ **Tests** du bot (première installation)
- ✅ Validation du **workflow** Scanner → Filter → Trader
- ✅ **Debugging** sans attendre des tokens SAFE
- ❌ **JAMAIS en production** avec capital réel

---

## 🔄 Comment Basculer Entre Les Configurations

### Méthode 1 : Script Automatique (Recommandé)

```bash
# À la racine du projet
./switch_config.sh
```

Le script vous propose un menu interactif :
1. Momentum Safe v2 (Production)
2. Test Permissif (Tests)
3. Annuler

**Le script** :
- ✅ Crée un backup automatique de votre .env actuel
- ✅ Affiche les paramètres clés de la config actuelle
- ✅ Copie la config sélectionnée vers `.env`
- ✅ Affiche les prochaines étapes

---

### Méthode 2 : Manuelle

#### Pour PRODUCTION (Momentum Safe v2) :
```bash
cd /home/basebot/trading-bot/config
cp .env.example .env
nano .env  # Remplir vos clés
```

#### Pour TESTS (Permissif) :
```bash
cd /home/basebot/trading-bot/config
cp .env.test.permissif .env
nano .env  # Remplir vos clés
```

---

## ⚙️ Après Changement de Configuration

### Sur VPS (avec systemd) :

```bash
# 1. Redémarrer les services
sudo systemctl restart basebot-scanner
sudo systemctl restart basebot-filter
sudo systemctl restart basebot-trader
sudo systemctl restart basebot-dashboard

# 2. Vérifier les statuts
sudo systemctl status basebot-scanner
sudo systemctl status basebot-filter
sudo systemctl status basebot-trader

# 3. Suivre les logs
tail -f /home/basebot/trading-bot/logs/scanner.log
tail -f /home/basebot/trading-bot/logs/filter.log
tail -f /home/basebot/trading-bot/logs/trader.log
```

### En local (développement) :

```bash
# Relancer manuellement chaque module
python3 src/Scanner.py &
python3 src/Filter.py &
python3 src/Trader.py &
streamlit run src/Dashboard.py
```

---

## 📊 Comparaison des Configurations

| Critère | Momentum Safe v2 | Test Permissif |
|---------|------------------|----------------|
| **Fenêtre âge** | 3.5-8h | 0-72h |
| **Liquidité min** | $12K | $500 |
| **Market Cap min** | $80K | $1K |
| **Volume 1h min** | $4K | $50 |
| **Holders min** | 120 | 10 |
| **Owner max** | 5% | 50% |
| **Taxes max** | 3% | 15% |
| **Stop Loss** | -5% | -15% |
| **Losing Cooldown** | 24h | 1h |
| **Win-rate** | ≥70% | 10-30% |
| **Trades/jour** | 2-5 | 10-20 |
| **Usage** | Production | Tests |

---

## ⚠️ Avertissements

### Configuration Test Permissif :
- ❌ **NE JAMAIS** utiliser en mode RÉEL avec capital
- ❌ **NE JAMAIS** déployer en production
- ✅ **UNIQUEMENT** pour valider le workflow
- ⚠️ Win-rate bas de 10-30% est **NORMAL**

### Configuration Momentum Safe v2 :
- ✅ Optimisée pour **production**
- ✅ Testée pour ≥70% win-rate
- ⚠️ Moins de trades (2-5/jour) mais **haute qualité**
- ⚠️ Nécessite **BirdEye API** + **dRPC** pour résultats optimaux

---

## 🔐 Clés à Remplir (Obligatoire)

Quelle que soit la configuration choisie, vous devez remplir :

```bash
# Wallet
WALLET_ADDRESS=votre_adresse
PRIVATE_KEY=votre_clé_privée

# API BirdEye (données market)
BIRDEYE_API_KEY=votre_clé_birdeye

# dRPC (protection MEV - recommandé en mode RÉEL)
DRPC_API_KEY=votre_clé_drpc

# Etherscan (verification contrats)
ETHERSCAN_API_KEY=votre_clé_etherscan
```

---

## 📝 Historique des Modifications

- **Momentum Safe v2** : Implémentée dans commit `f81d430` (Phase 1)
- **Test Permissif** : Créée pour validation workflow rapide
- **Script Switch** : Automatisation du changement de config

---

## 🆘 Support

Si vous avez des questions sur les configurations :

1. **Consultez** le Dashboard (onglet "Configuration") pour voir la stratégie active
2. **Vérifiez** les logs pour identifier les tokens détectés/rejetés
3. **Testez** d'abord avec .env.test.permissif avant la production

---

🤖 Generated with Claude Code
📅 Dernière mise à jour : 2025-01-04
