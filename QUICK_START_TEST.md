# 🚀 Quick Start - Configuration Test Permissive

Guide rapide pour tester le BaseBot avec la configuration permissive.

---

## 📋 Prérequis

- ✅ Bot déjà installé sur VPS ou en local
- ✅ Wallet configuré avec un peu d'ETH sur Base (pour gas fees)
- ✅ API BirdEye configurée
- ⚠️ **Mode PAPER** activé (pour tests sans risque)

---

## 🔄 Étape 1 : Basculer en Mode Test

### Sur VPS :

```bash
cd /home/basebot/trading-bot

# Utiliser le script interactif
./switch_config.sh

# Sélectionner: 2) Test Permissif
```

### Ou manuellement :

```bash
cd /home/basebot/trading-bot/config
cp .env.test.permissif .env
nano .env  # Vérifier WALLET_ADDRESS, PRIVATE_KEY, BIRDEYE_API_KEY
```

---

## ⚙️ Étape 2 : Redémarrer les Services

```bash
# Arrêter tous les services
sudo systemctl stop basebot-scanner
sudo systemctl stop basebot-filter
sudo systemctl stop basebot-trader

# Optionnel: Nettoyer la base (recommandé pour tests propres)
rm -f /home/basebot/trading-bot/data/trading.db
python3 /home/basebot/trading-bot/src/init_database.py

# Redémarrer les services
sudo systemctl start basebot-scanner
sudo systemctl start basebot-filter
sudo systemctl start basebot-trader
sudo systemctl start basebot-dashboard

# Vérifier les statuts
sudo systemctl status basebot-scanner
sudo systemctl status basebot-filter
sudo systemctl status basebot-trader
```

---

## 📊 Étape 3 : Observer l'Activité

### 1. Logs en temps réel (3 terminaux) :

**Terminal 1 - Scanner** :
```bash
tail -f /home/basebot/trading-bot/logs/scanner.log
```
Vous devriez voir rapidement des tokens détectés (0-72h)

**Terminal 2 - Filter** :
```bash
tail -f /home/basebot/trading-bot/logs/filter.log
```
Vous devriez voir des tokens approuvés/rejetés (critères permissifs)

**Terminal 3 - Trader** :
```bash
tail -f /home/basebot/trading-bot/logs/trader.log
```
Vous devriez voir des achats/ventes (paper mode)

### 2. Dashboard :

```bash
# Accéder au Dashboard
http://VOTRE_VPS_IP:8501
```

**Onglets à surveiller** :
- 📊 **Positions Actives** : Voir les positions ouvertes
- 📈 **Performance** : Win-rate, profit moyen
- 🎯 **Tokens Approuvés** : Liste des tokens validés
- 📜 **Historique** : Trades complétés
- ⚙️ **Configuration** : Vérifier paramètres test actifs

---

## 🎯 Résultats Attendus (Mode Test Permissif)

### ⏱️ Timeline :

- **0-5 min** : Scanner détecte 10-50 tokens (fenêtre 0-72h large)
- **5-10 min** : Filter approuve 5-15 tokens (critères permissifs)
- **10-15 min** : Trader achète 1-3 positions (paper mode)
- **15-30 min** : Premières sorties (stop loss ou trailing)

### 📊 Métriques attendues :

| Métrique | Valeur Attendue | Note |
|----------|----------------|------|
| **Tokens détectés** | 50-200 / heure | Fenêtre large 0-72h |
| **Tokens approuvés** | 10-30 / heure | Critères permissifs |
| **Trades** | 5-20 / jour | Volume élevé |
| **Win-rate** | 10-30% | **NORMAL** en mode test |
| **Profit moyen** | -5% à +10% | Volatilité haute |

⚠️ **Win-rate bas de 10-30% est NORMAL** en mode test permissif !

---

## 🔍 Vérifications Clés

### 1. Scanner fonctionne ?

```bash
# Vérifier tokens découverts
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM discovered_tokens;"
```
**Attendu** : 50-200 tokens après 30 minutes

### 2. Filter fonctionne ?

```bash
# Vérifier tokens approuvés
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM approved_tokens;"
```
**Attendu** : 10-30 tokens après 30 minutes

### 3. Trader fonctionne ?

```bash
# Vérifier trades
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM trade_history;"
```
**Attendu** : 5-20 trades après 4-6 heures

### 4. Vérifier les paramètres actifs :

```bash
grep -E "MIN_AGE_HOURS|MIN_LIQUIDITY_USD|MIN_HOLDERS" /home/basebot/trading-bot/config/.env
```

**Doit afficher** :
```
MIN_AGE_HOURS=0.0
MIN_LIQUIDITY_USD=500
MIN_HOLDERS=10
```

---

## 🐛 Problèmes Courants

### ❌ Aucun token détecté après 10 minutes

**Causes possibles** :
- RPC_URL ne répond pas
- MIN_TOKEN_AGE_HOURS trop élevé

**Solution** :
```bash
# Vérifier logs Scanner
tail -n 50 /home/basebot/trading-bot/logs/scanner.log | grep "Scan blocs"

# Vérifier RPC
curl -s https://mainnet.base.org
```

---

### ❌ Tokens détectés mais aucun approuvé

**Causes possibles** :
- BirdEye API key invalide
- Filter utilise l'ancienne config

**Solution** :
```bash
# Vérifier logs Filter
tail -n 50 /home/basebot/trading-bot/logs/filter.log | grep "REJET"

# Vérifier config active
grep "MIN_LIQUIDITY_USD" /home/basebot/trading-bot/config/.env
# Doit afficher: MIN_LIQUIDITY_USD=500 (et non 12000)

# Redémarrer Filter
sudo systemctl restart basebot-filter
```

---

### ❌ Tokens approuvés mais aucun trade

**Causes possibles** :
- Wallet sans ETH (gas fees)
- PRIVATE_KEY invalide

**Solution** :
```bash
# Vérifier logs Trader
tail -n 50 /home/basebot/trading-bot/logs/trader.log | grep "Achat"

# Vérifier solde wallet
# (Nécessite eth_getBalance via RPC)
```

---

## 🔄 Retour en Mode Production

Une fois les tests terminés :

```bash
cd /home/basebot/trading-bot

# Utiliser le script
./switch_config.sh
# Sélectionner: 1) Momentum Safe v2

# OU manuellement
cp config/.env.example config/.env
nano config/.env  # Vérifier les clés

# Nettoyer la DB (recommandé)
rm -f data/trading.db
python3 src/init_database.py

# Redémarrer
sudo systemctl restart basebot-scanner
sudo systemctl restart basebot-filter
sudo systemctl restart basebot-trader
```

---

## 📈 Analyse des Résultats Test

Après 24h de tests, analysez :

```bash
# Win-rate global
sqlite3 /home/basebot/trading-bot/data/trading.db "
  SELECT
    COUNT(*) as total_trades,
    COUNT(CASE WHEN profit_loss > 0 THEN 1 END) as winners,
    ROUND(COUNT(CASE WHEN profit_loss > 0 THEN 1 END) * 100.0 / COUNT(*), 1) as win_rate
  FROM trade_history
  WHERE exit_time IS NOT NULL;
"

# Raisons de sortie
sqlite3 /home/basebot/trading-bot/data/trading.db "
  SELECT reason, COUNT(*) as count
  FROM trade_history
  WHERE exit_time IS NOT NULL
  GROUP BY reason
  ORDER BY count DESC;
"

# Tokens les plus tradés
sqlite3 /home/basebot/trading-bot/data/trading.db "
  SELECT symbol, COUNT(*) as trades, AVG(profit_loss) as avg_profit
  FROM trade_history
  GROUP BY symbol
  ORDER BY trades DESC
  LIMIT 10;
"
```

---

## ✅ Critères de Validation

Le bot fonctionne correctement si :

- ✅ Scanner détecte **50+ tokens/heure**
- ✅ Filter approuve **10+ tokens/heure**
- ✅ Trader effectue **5+ trades/jour**
- ✅ Aucune erreur critique dans les logs
- ✅ Dashboard affiche les données en temps réel
- ✅ Base de données se remplit progressivement

**Note** : Win-rate de 10-30% en mode test est **PARFAITEMENT NORMAL**.

---

## 🎯 Objectif Final

**Validation complète du workflow** :
1. ✅ Scanner détecte tokens on-chain
2. ✅ Filter enrichit avec BirdEye/DexScreener
3. ✅ Filter applique critères et approuve/rejette
4. ✅ Trader achète positions (paper)
5. ✅ Trader surveille prix et applique trailing stops
6. ✅ Trader vend selon stratégie
7. ✅ Dashboard affiche tout en temps réel

**Une fois validé**, passez en **Momentum Safe v2** pour production ! 🚀

---

🤖 Generated with Claude Code
📅 Dernière mise à jour : 2025-01-04
