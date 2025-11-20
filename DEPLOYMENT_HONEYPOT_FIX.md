# 🐛 DÉPLOIEMENT FIX HONEYPOT - URGENT

**Date:** 2025-11-20
**Commit:** da77f25
**Priorité:** 🔴 CRITIQUE - Déployer immédiatement

---

## 🔴 PROBLÈME RÉSOLU

### **Symptômes Observés (36h production):**
- Token **SUR** tradé **3 fois** avec **100% pertes**
- Pertes: **-27.72%**, **-29.60%**, **-33.03%**
- Durée positions: **0.0h, 0.0h, 0.1h** (2-6 minutes)
- Même token re-tradé immédiatement (pas de cooldown)

### **Root Cause Identifiée:**
```python
# web3_utils.py - AVANT (ligne 142):
return {'is_honeypot': False}  # ❌ TOUJOURS False (stub!)

# Filter.py - AVANT (ligne 340):
else:
    reasons.append("Failed honeypot check")  # ⚠️ Pénalité mais pas de rejet!
```

**Résultat:** TOUS les tokens passaient, y compris honeypots/scams!

---

## ✅ SOLUTION IMPLÉMENTÉE

### **1. Intégration API Honeypot.is (Gratuite)**

**src/web3_utils.py (lignes 132-167):**
```python
# 🔧 FIX: Vraie vérification honeypot via API Honeypot.is
url = f"https://api.honeypot.is/v2/IsHoneypot?address={token_address}&chainID=8453"
response = requests.get(url, timeout=5)

if response.status_code == 200:
    data = response.json()
    is_honeypot = data.get('isHoneypot', False)
    simulation_success = data.get('simulationSuccess', False)

    return {
        'is_honeypot': is_honeypot or not simulation_success,  # ✅ Détection réelle
        'can_sell': simulation_success and not is_honeypot,
        'buy_tax': data.get('buyTax', 0),
        'sell_tax': data.get('sellTax', 0),
        'error': data.get('honeypotReason') if is_honeypot else None
    }
```

### **2. Auto-Rejet Honeypots dans Filter**

**src/Filter.py (lignes 333-348):**
```python
# 🔧 FIX: Honeypot = REJET AUTOMATIQUE (pas juste pénalité)
if not honeypot_check.get('is_honeypot', True):
    score += 15
    reasons.append("Passed honeypot check")
else:
    # ❌ REJET AUTOMATIQUE si honeypot détecté
    reasons.append(f"❌ REJET: Honeypot détecté (is_honeypot={honeypot_check.get('is_honeypot')})")
    return 0, reasons  # ✅ Sortie immédiate, score=0
```

---

## 🚀 DÉPLOIEMENT VPS

### **Étape 1: Mise à jour code**
```bash
cd /home/basebot/trading-bot
sudo -u basebot git pull origin main
```

**Attendu:**
```
From https://github.com/supermerou03101983/BaseBot
   1b17e6d..da77f25  main -> main
Updating 1b17e6d..da77f25
Fast-forward
 src/Filter.py      | 10 +++++--
 src/web3_utils.py  | 47 ++++++++++++++++++++++++------
 2 files changed, 41 insertions(+), 16 deletions(-)
```

---

### **Étape 2: Redémarrer services**
```bash
sudo systemctl restart basebot-filter
sudo systemctl restart basebot-trader
```

**Vérifier:**
```bash
sudo systemctl status basebot-filter
sudo systemctl status basebot-trader
```

**Attendu:** Tous "active (running)"

---

### **Étape 3: Vérifier logs Filter**
```bash
sudo journalctl -u basebot-filter -n 50 --follow
```

**CRITÈRE SUCCÈS #1 - Honeypot détecté:**
```
Nov 20 XX:XX:XX - INFO - 🔍 Analyse: SCAMTOKEN (0x1234...)
Nov 20 XX:XX:XX - INFO - ❌ REJET: Honeypot détecté (is_honeypot=True)
Nov 20 XX:XX:XX - INFO - ❌ Token rejeté: SCAMTOKEN - Score: 0.00
```

**CRITÈRE SUCCÈS #2 - Token légitime approuvé:**
```
Nov 20 XX:XX:XX - INFO - 🔍 Analyse: GOODTOKEN (0xabcd...)
Nov 20 XX:XX:XX - INFO - ✅ Token APPROUVE: GOODTOKEN - Score: 78.50 - Vol: $125,000
```

---

## 🎯 CONFIGURATION RECOMMANDÉE

### **Problème Identifié:**
Votre .env actuel a des seuils trop stricts pour volume **h6 réel** (pas extrapolé):

```bash
MIN_VOLUME_24H=10000      # ❌ Trop strict pour h6 réel
GRACE_PERIOD_ENABLED=false # ❌ Cause sorties immédiates
```

### **Configuration Optimale (Base Network):**

Éditez `/home/basebot/trading-bot/config/.env`:

```bash
# ===========================
# 🔧 PARAMÈTRES CRITIQUES
# ===========================

# Volume - Ajusté pour h6 réel (pas d'extrapolation)
MIN_VOLUME_24H=3000        # ✅ 3k-5k adapté au volume h6 réel
MAX_VOLUME_24H=5000000

# Liquidité - Assoupli pour Base Network
MIN_LIQUIDITY_USD=10000    # ✅ 10k-15k acceptable pour early tokens
MAX_LIQUIDITY_USD=10000000

# Safety Score - Assoupli
MIN_SAFETY_SCORE=55        # ✅ 55-65 pour tokens 2-12h

# ===========================
# ⏱️ GRACE PERIOD - CRITIQUE!
# ===========================
GRACE_PERIOD_ENABLED=true         # ✅ Essentiel pour éviter sorties immédiates
GRACE_PERIOD_MINUTES=5            # ✅ 5min tolérance (au lieu de 3)
GRACE_PERIOD_STOP_LOSS=45         # ✅ -45% pendant grace (au lieu de -35%)

# ===========================
# 📊 AUTRES PARAMÈTRES
# ===========================
MAX_BUY_TAX=15
MAX_SELL_TAX=15
MIN_HOLDERS=50             # ✅ Assoupli de 100 à 50
MIN_MARKET_CAP=5000
MAX_MARKET_CAP=500000

# Trading
TRADING_MODE=PAPER         # ✅ Garder PAPER jusqu'à validation!
MIN_PROFIT_PERCENT=15
STOP_LOSS_PERCENT=5        # ⚠️ Hors grace period
TRAILING_STOP_PERCENT=3
```

---

### **Étape 4: Appliquer nouvelle configuration**
```bash
sudo nano /home/basebot/trading-bot/config/.env

# Modifier les paramètres ci-dessus, puis:
sudo systemctl restart basebot-filter
sudo systemctl restart basebot-trader
```

---

## ✅ VALIDATION POST-DÉPLOIEMENT

### **Test 1: Vérifier honeypot rejection (30 min)**
```bash
sudo journalctl -u basebot-filter -n 100 | grep -i "honeypot"
```

**Attendu (si honeypots détectés):**
```
Nov 20 14:23:15 - INFO - ❌ REJET: Honeypot détecté (is_honeypot=True)
Nov 20 14:45:32 - INFO - ❌ REJET: Honeypot détecté (is_honeypot=True)
```

**Si aucun résultat:** Bon signe = pas de honeypots dans les derniers tokens!

---

### **Test 2: Vérifier approbations (1h)**
```bash
su - basebot
sqlite3 /home/basebot/trading-bot/data/trading.db << 'EOF'
SELECT
    symbol,
    ROUND(volume_24h, 0) as vol,
    ROUND(score, 1) as score,
    datetime(approved_at) as approved
FROM approved_tokens
WHERE datetime(approved_at) > datetime('now', '-1 hours')
ORDER BY approved_at DESC;
EOF
```

**Attendu:**
```
MORI|125000|78.5|2025-11-20 14:15:23
GALA|89000|72.3|2025-11-20 14:42:18
```

**Validation:** Tokens avec volume >3000 et score >55 approuvés

---

### **Test 3: Vérifier trades (24h)**
```bash
su - basebot
sqlite3 /home/basebot/trading-bot/data/trading.db << 'EOF'
SELECT
    token_symbol,
    ROUND(profit_loss_percent, 2) as pnl,
    ROUND((julianday(exit_time) - julianday(entry_time)) * 24, 1) as duration_h,
    exit_reason
FROM trades
WHERE datetime(entry_time) > datetime('now', '-24 hours')
ORDER BY entry_time DESC;
EOF
```

**CRITÈRE SUCCÈS:**
- ✅ Aucun honeypot dans trades (exit_reason != "Honeypot")
- ✅ Durées >0.1h (pas de sorties immédiates comme avant)
- ✅ Mix de gains/pertes (pas 100% pertes)

**FAIL si:**
- ❌ Même token tradé 3x avec pertes
- ❌ Toutes durées <0.1h
- ❌ 100% pertes

---

## 📊 MÉTRIQUES DE SUCCÈS (24h après fix)

**Critères validation:**
- ✅ **Taux approbation: 20-40%** (au lieu de 0%)
- ✅ **Honeypots détectés: >0** (preuve que check fonctionne)
- ✅ **Win rate: >40%** (au lieu de 0%)
- ✅ **Durée moyenne trades: >1h** (au lieu de <0.1h)
- ✅ **Pas de token re-tradé 3x immédiatement**

**Commande analyse complète:**
```bash
bot-analyze
```

---

## ⚠️ NOTES IMPORTANTES

### **API Honeypot.is:**
- **Gratuite** (pas de clé requise)
- **Rate limit:** ~60 requêtes/minute
- **Timeout:** 5 secondes (si fail → assume safe)
- **Base Network:** chainID=8453 supporté

### **Fallback en cas d'erreur API:**
```python
except requests.exceptions.Timeout:
    return {'is_honeypot': False, 'can_sell': True, ...}  # Assume safe
```

**Raison:** Évite de rejeter TOUS les tokens si API temporairement down.

### **Grace Period CRITIQUE:**
Sans grace period, sorties immédiates sur slippage/volatilité:
```
Entry: $0.00050
Slippage: -3%
Prix actuel: $0.000485
Stop loss -5%: $0.000475
→ ❌ SORTIE en 30 secondes!
```

**Avec grace period (5min @ -45%):**
```
Entry: $0.00050
Slippage: -3% → Prix: $0.000485
Grace period: accepte jusqu'à -45%
→ ✅ Position maintenue, le temps de stabiliser
```

---

## 🎉 RÉSUMÉ

**Problème:** check_honeypot() stub → 100% tokens passaient → SUR tradé 3x avec pertes

**Solution:**
1. API Honeypot.is pour détection réelle
2. Auto-rejet dans Filter (return 0)

**Config recommandée:**
- MIN_VOLUME_24H=3000 (ajusté pour h6 réel)
- GRACE_PERIOD_ENABLED=true (critique!)
- GRACE_PERIOD_MINUTES=5
- MIN_SAFETY_SCORE=55

**Impact attendu:**
- Honeypots bloqués AVANT trading
- Win rate s'améliore (actuellement 0% → cible 40-50%)
- Durée trades normale (>1h au lieu de <6min)

---

**Commande déploiement:**
```bash
cd /home/basebot/trading-bot && \
sudo -u basebot git pull origin main && \
sudo systemctl restart basebot-filter basebot-trader && \
sudo journalctl -u basebot-filter -n 50 --follow
```

**Puis éditer .env avec les paramètres recommandés ci-dessus!**

---

**Auteur:** Claude Code
**Date:** 2025-11-20
**Commit:** da77f25
**Priorité:** 🔴 CRITIQUE
