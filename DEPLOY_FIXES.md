# 🚀 DÉPLOIEMENT DES FIXES CRITIQUES SUR VPS

## ✅ Fixes appliqués et pushés sur GitHub

**Commit:** 2e75bc2
**Date:** 2025-11-18
**Branch:** main

---

## 📋 COMMANDES DE DÉPLOIEMENT

### **Étape 1: Connexion au VPS**

```bash
ssh user@votre-vps
```

### **Étape 2: Basculer sur utilisateur basebot**

```bash
su - basebot
```

### **Étape 3: Aller dans le répertoire du bot**

```bash
cd /home/basebot/trading-bot
```

### **Étape 4: Pull des dernières modifications**

```bash
git pull origin main
```

**Sortie attendue:**
```
remote: Enumerating objects: 10, done.
remote: Counting objects: 100% (10/10), done.
remote: Compressing objects: 100% (7/7), done.
remote: Total 8 (delta 2), reused 8 (delta 2), pack-reused 0
Unpacking objects: 100% (8/8), done.
From https://github.com/supermerou03101983/BaseBot
   2aac272..2e75bc2  main       -> origin/main
Updating 2aac272..2e75bc2
Fast-forward
 FIXES_APPLIED.md           | 387 ++++++++++++++++++++++++++++++++++++++++++
 OPTIMIZATIONS_CRITIQUES.md | 512 ++++++++++++++++++++++++++++++++++++++++++++++++++
 Résultats trading.csv      |  52 ++++++
 VERIFICATION_CRITERES.md   | 502 ++++++++++++++++++++++++++++++++++++++++++++++++
 analyze_results.py         | 316 ++++++++++++++++++++++++++++++++
 src/Filter.py              |  58 ++++--
 6 files changed, 1549 insertions(+), 19 deletions(-)
```

### **Étape 5: Vérifier les modifications du Filter**

```bash
git show HEAD:src/Filter.py | grep -A5 "Volume 24h"
```

**Sortie attendue:**
```
# Volume 24h (CRITIQUE - Fix #1)
volume_24h = token_data.get('volume_24h', 0)
if volume_24h >= self.min_volume_24h:
    score += 10
    reasons.append(f"Volume 24h (${volume_24h:,.2f}) OK")
```

### **Étape 6: Valider la syntaxe Python**

```bash
python3 -m py_compile src/Filter.py && echo "✅ Syntaxe OK"
```

### **Étape 7: Redémarrer le service Filter**

```bash
exit  # Quitter basebot
sudo systemctl restart basebot-filter
```

### **Étape 8: Vérifier que le service démarre correctement**

```bash
sudo systemctl status basebot-filter
```

**Sortie attendue:**
```
● basebot-filter.service - BaseBot Filter Service
     Loaded: loaded (/etc/systemd/system/basebot-filter.service; enabled)
     Active: active (running) since Mon 2025-11-18 10:30:00 UTC; 5s ago
   Main PID: 12345 (python3)
      Tasks: 1 (limit: 4915)
     Memory: 45.2M
```

### **Étape 9: Surveiller les logs en temps réel**

```bash
sudo journalctl -u basebot-filter -f
```

**Logs attendus (nouveaux rejets):**

```
Nov 18 10:31:15 - INFO - Analyse de TOKEN1...
Nov 18 10:31:16 - INFO - ❌ Volume 24h ($12,345.00) < min ($50,000.00)
Nov 18 10:31:16 - INFO - Token TOKEN1 rejeté (score: 45/100)

Nov 18 10:31:20 - INFO - Analyse de TOKEN2...
Nov 18 10:31:21 - INFO - ❌ REJET: Nombre de holders inconnu (API échec)
Nov 18 10:31:21 - INFO - Token TOKEN2 rejeté (score: 0/100)

Nov 18 10:31:25 - INFO - Analyse de TOKEN3...
Nov 18 10:31:26 - INFO - ❌ REJET: Taxes inconnues (API échec)
Nov 18 10:31:26 - INFO - Token TOKEN3 rejeté (score: 0/100)

Nov 18 10:31:30 - INFO - Analyse de TOKEN4...
Nov 18 10:31:35 - INFO - ✅ Token TOKEN4 approuvé (score: 85/100)
```

---

## 📊 SURVEILLANCE POST-DÉPLOIEMENT

### **Vérification #1: Nombre de rejets (1h après déploiement)**

```bash
# Compter les rejets Volume 24h
sudo journalctl -u basebot-filter --since "1 hour ago" | grep -c "Volume 24h.*< min"

# Compter les rejets Holders
sudo journalctl -u basebot-filter --since "1 hour ago" | grep -c "holders inconnu"

# Compter les rejets Taxes
sudo journalctl -u basebot-filter --since "1 hour ago" | grep -c "Taxes inconnues"

# Compter les tokens approuvés
sudo journalctl -u basebot-filter --since "1 hour ago" | grep -c "approuvé"
```

**Résultats attendus:**
- Volume rejets: 10-20 tokens/heure
- Holders rejets: 5-15 tokens/heure
- Taxes rejets: 5-15 tokens/heure
- Tokens approuvés: **3-8 tokens/heure** (qualité > quantité)

---

### **Vérification #2: Tokens spécifiques interdits (24h après)**

```bash
# Vérifier qu'aucun token de la blacklist n'a été approuvé
sudo journalctl -u basebot-filter --since "24 hours ago" | grep -E "BRO|RUNES|INX|Fireside" | grep "approuvé"
```

**Résultat attendu:** AUCUNE LIGNE (ces tokens doivent être rejetés)

Si un de ces tokens apparaît: ❌ **PROBLÈME - Les fixes ne fonctionnent pas correctement**

---

### **Vérification #3: Analyse des trades après 24h**

```bash
su - basebot
cd /home/basebot/trading-bot
python3 analyze_results.py
```

**Métriques à surveiller:**

| Métrique | Avant fixes | Objectif 24h | Objectif 48h |
|----------|-------------|--------------|--------------|
| Win Rate | 42.0% | >50% | >60% |
| Expectancy | -2.97% | >0% | >5% |
| Pertes >-30% | 6 trades | <3 trades | 0 trades |
| Loss Moyen | -22.66% | <-18% | <-15% |

---

## ⚠️ PROBLÈMES POTENTIELS

### **Problème #1: Trop peu de tokens approuvés (<2/heure)**

**Cause:** Les APIs (DexScreener/BaseScan) ne retournent pas les données requises

**Solutions:**

**Option A: Assouplir UN critère (ex: holders)**

```bash
# Éditer Filter.py sur VPS
nano src/Filter.py

# Remplacer ligne 281-283:
if holders == 0:
    reasons.append(f"❌ REJET: Nombre de holders inconnu")
    return 0, reasons

# Par:
if holders == 0:
    score += 5  # Bonus partiel
    reasons.append(f"Holders inconnu (bonus partiel)")
```

**Option B: Réduire les seuils**

```bash
# Éditer .env sur VPS
nano config/.env

# Réduire:
MIN_HOLDERS=150    →  MIN_HOLDERS=50
MIN_VOLUME_24H=50000  →  MIN_VOLUME_24H=20000
```

---

### **Problème #2: Win rate toujours <50% après 48h**

**Cause:** D'autres problèmes dans la stratégie (stop loss, trailing, etc.)

**Solutions:** Appliquer les optimisations de [OPTIMIZATIONS_CRITIQUES.md](OPTIMIZATIONS_CRITIQUES.md):

1. **Blacklist tokens perdants:**
   ```bash
   nano config/.env
   # Ajouter:
   BLACKLIST_TOKENS=BRO,RUNES,INX,Fireside,fomo,BUSHTIT,hamptonism,FEY
   ```

2. **Renforcer filtres:**
   ```bash
   MIN_LIQUIDITY_USD=100000     # de $30k → $100k
   MIN_HOLDERS=100              # de 150 → 100 (compromis)
   MIN_HONEYPOT_SCORE=90        # de 80 → 90
   ```

3. **Ajuster stop loss:**
   - Modifier [src/Trader.py](src/Trader.py) lignes 50-54:
   ```python
   self.grace_period_minutes = 5              # de 3 → 5
   self.grace_period_stop_loss_percent = 60   # de 35 → 60
   self.normal_stop_loss_percent = 3          # de 5 → 3
   ```

---

### **Problème #3: Erreurs API dans les logs**

**Logs:**
```
ERROR - DexScreener API error: 429 Too Many Requests
ERROR - BaseScan API error: Invalid API key
```

**Solutions:**

1. **Vérifier les clés API dans .env:**
   ```bash
   nano config/.env
   # Vérifier:
   ETHERSCAN_API_KEY=838DJAH413N7EBAUSK34JJPNRCTYDCG92H
   COINGECKO_API_KEY=CG-H8HkWbFx9E35iQFjUhahJDb7
   ```

2. **Implémenter rate limiting:**
   - Réduire SCAN_INTERVAL_SECONDS de 30 → 60 secondes
   - Réduire FILTER_INTERVAL_SECONDS de 60 → 120 secondes

---

## 📈 CRITÈRES DE SUCCÈS (7 jours)

**Le bot sera considéré comme OPTIMISÉ si:**

- ✅ Win Rate ≥ 60%
- ✅ Expectancy ≥ 10%
- ✅ Aucune perte >-30%
- ✅ Loss moyen ≤ -12%
- ✅ Aucun token de la blacklist tradé
- ✅ 3-8 tokens approuvés par heure (qualité)

**Si ces critères sont atteints:**
→ Envisager passage en mode REAL avec petit capital ($100-500)

**Si non atteints après 7 jours:**
→ Appliquer les optimisations supplémentaires de [OPTIMIZATIONS_CRITIQUES.md](OPTIMIZATIONS_CRITIQUES.md)

---

## 🎯 CHECKLIST POST-DÉPLOIEMENT

- [ ] Git pull réussi
- [ ] Syntaxe Python validée
- [ ] Service basebot-filter redémarré
- [ ] Logs montrent les nouveaux rejets
- [ ] Aucun token blacklisté n'est approuvé (vérifier après 2h)
- [ ] 3+ tokens approuvés par heure (vérifier après 2h)
- [ ] Analyser résultats après 24h avec analyze_results.py
- [ ] Comparer métriques avant/après fixes
- [ ] Décider si ajustements nécessaires (48h)
- [ ] Valider succès ou appliquer optimisations supplémentaires (7 jours)

---

## 📞 COMMANDES RAPIDES

```bash
# Status tous les services
systemctl status basebot-*

# Logs filter en temps réel
journalctl -u basebot-filter -f

# Logs trader en temps réel
journalctl -u basebot-trader -f

# Analyser performance
su - basebot
cd /home/basebot/trading-bot
python3 analyze_results.py

# Vérifier positions actuelles
bot-status

# Redémarrer tout
sudo systemctl restart basebot-scanner basebot-filter basebot-trader
```

---

**Créé:** 2025-11-18
**Commit:** 2e75bc2
**Auteur:** Claude Code

**Bon déploiement! 🚀**
