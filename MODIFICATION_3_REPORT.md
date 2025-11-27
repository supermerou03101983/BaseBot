# 🔧 Modification #3 - Déblocage Filtre + Momentum Multi-Période + Cooldown

**Date**: 2025-11-27
**Status**: ✅ APPLIQUÉ EN LOCAL - PRÊT POUR DÉPLOIEMENT

---

## 📊 Contexte

### Résultats Modification #2 (24h)

- **Win-rate**: 0% (2 trades fermés, 2 pertes)
- **Trades fermés**: FARSINO (-10.2%), FARSINO (-18.85%)
- **Position ouverte**: bolivian (+2.2% après 12.1h)
- **Problème critique**: Filtre bloquant 100% (Analyzed=30, Approved=0, Rejected=30)

### Analyse des Problèmes

1. **Filtre Trop Strict**
   - MIN_MARKET_CAP=$5K, MIN_LIQUIDITY=$5K rejettent tokens 2-3h
   - MIN_AGE_HOURS=3h → tokens déjà passé leur pump initial
   - MIN_VOLUME_1H=$100 → trop strict pour tokens récents
   - Résultat: 0 token approuvé en 24h

2. **Momentum Insuffisant**
   - MIN_PRICE_CHANGE_1H=+5% ne détecte pas les rebonds techniques
   - FARSINO tradé 2 fois en perte sur le même token
   - Besoin de vérifier momentum immédiat (5min) en plus du 1h

3. **Re-trading Perdant**
   - FARSINO #1: -10.2%
   - FARSINO #3: -18.85% (re-trade immédiat après perte #1)
   - Besoin d'un cooldown pour éviter re-trades perdants

---

## 🎯 Objectifs Modification #3

1. **Débloquer le filtre** : Passer de 0 token/jour à 2-5 tokens/jour
2. **Améliorer la qualité des entrées** : Momentum multi-période (5m + 1h)
3. **Éviter les re-trades perdants** : Cooldown 24h sur tokens perdus
4. **Atteindre ≥30% win-rate** en 10 nouveaux trades

---

## 🔧 Changements Appliqués

### A. Assouplissement des Critères (.env)

#### Avant (Modification #2)
```bash
MIN_MARKET_CAP=5000
MIN_LIQUIDITY_USD=5000
MIN_AGE_HOURS=3
MIN_VOLUME_24H=500
MIN_VOLUME_1H=100
MIN_PRICE_CHANGE_1H=5
```

#### Après (Modification #3)
```bash
MIN_MARKET_CAP=2000          # -60% (assouplir)
MIN_LIQUIDITY_USD=2000       # -60% (assouplir)
MIN_AGE_HOURS=2              # -33% (entrée plus précoce)
MIN_VOLUME_24H=300           # -40% (tokens 2-3h accessibles)
MIN_VOLUME_1H=50             # -50% (assouplir)
MIN_PRICE_CHANGE_5M=2        # NOUVEAU (momentum immédiat)
MIN_PRICE_CHANGE_1H=3        # -40% (assoupli de +5% à +3%)
```

**Impact attendu**: +50-200% de tokens candidats (de 0/jour → 2-5/jour)

### B. Momentum Multi-Période (Filter.py)

**Nouveau filtre**: Vérification du momentum sur 2 périodes

```python
# Momentum 5min (NOUVEAU - Modification #3)
min_price_change_5m = float(os.getenv('MIN_PRICE_CHANGE_5M', 2))
price_change_5m = token_data.get('price_change_5m', 0)

if price_change_5m < min_price_change_5m:
    reasons.append(f"❌ REJET: Prix 5min ({price_change_5m:+.2f}%) < min (+{min_price_change_5m:.0f}%) - Pas de momentum immédiat")
    return 0, reasons

score += 5  # Bonus momentum immédiat
reasons.append(f"✅ Momentum 5min ({price_change_5m:+.2f}%) OK - Momentum immédiat confirmé")

# Momentum 1h (ASSOUPLI - Modification #3)
min_price_change_1h = float(os.getenv('MIN_PRICE_CHANGE_1H', 3))
price_change_1h = token_data.get('price_change_1h', 0)

if price_change_1h < min_price_change_1h:
    reasons.append(f"❌ REJET: Prix 1h ({price_change_1h:+.2f}%) < min (+{min_price_change_1h:.0f}%) - Pas de tendance haussière")
    return 0, reasons

score += 10  # Bonus tendance générale
reasons.append(f"✅ Momentum 1h ({price_change_1h:+.2f}%) OK - Tendance haussière confirmée")
```

**Rationale**:
- **5min +2%**: Confirme que le token monte MAINTENANT (pas juste un rebond)
- **1h +3%**: Confirme tendance générale haussière (assoupli pour plus de candidats)
- **Combinaison**: Évite les faux signaux (rebonds techniques de dumps)

**Fichier modifié**: [src/Filter.py:293-315](src/Filter.py#L293-L315)

### C. Ajout price_change_5m dans APIs (web3_utils.py)

**DexScreener API** (ligne 438):
```python
'price_change_5m': float(pair.get('priceChange', {}).get('m5', 0)),
'price_change_1h': float(pair.get('priceChange', {}).get('h1', 0)),
```

**GeckoTerminal API** (ligne 802):
```python
'price_change_5m': float((attributes.get('price_change_percentage') or {}).get('m5') or 0),
'price_change_1h': float((attributes.get('price_change_percentage') or {}).get('h1') or 0),
```

**Fichiers modifiés**:
- [src/web3_utils.py:438](src/web3_utils.py#L438)
- [src/web3_utils.py:802](src/web3_utils.py#L802)

### D. Cooldown Tokens Perdants (Trader.py)

**1. Attribut dans __init__** (ligne 118):
```python
# Cooldown tokens perdants (Modification #3 - éviter re-trade immédiat)
self.losing_tokens_cooldown = {}  # {token_address: timestamp}
```

**2. Vérification avant achat** (ligne 738):
```python
# Cooldown tokens perdants (Modification #3)
token_address = token.get('address', '').lower()
if token_address in self.losing_tokens_cooldown:
    cooldown_end = self.losing_tokens_cooldown[token_address]
    hours_since = (time.time() - cooldown_end) / 3600
    if hours_since < 24:
        self.logger.info(
            f"❌ {token['symbol']} en cooldown perdant "
            f"(perdu il y a {hours_since:.1f}h, reste {24-hours_since:.1f}h)"
        )
        return False
    else:
        # Cooldown expiré, supprimer
        del self.losing_tokens_cooldown[token_address]
        self.logger.info(f"✅ Cooldown expiré pour {token['symbol']} ({hours_since:.1f}h)")
```

**3. Enregistrement après vente à perte** (ligne 971 PAPER + ligne 1130 REAL):
```python
# Cooldown tokens perdants (Modification #3)
if profit_percent < 0:
    token_address = position.token_address.lower()
    self.losing_tokens_cooldown[token_address] = time.time()
    self.logger.info(
        f"🔒 {position.symbol} ajouté au cooldown perdant (24h) "
        f"après perte de {profit_percent:.2f}%"
    )
```

**Fichiers modifiés**:
- [src/Trader.py:118-119](src/Trader.py#L118-L119) (init)
- [src/Trader.py:738-754](src/Trader.py#L738-L754) (vérification)
- [src/Trader.py:970-977](src/Trader.py#L970-L977) (enregistrement PAPER)
- [src/Trader.py:1129-1136](src/Trader.py#L1129-L1136) (enregistrement REAL)

---

## 📊 Impact Attendu

### Sur le Filtre (Nombre de Candidats)

| Critère | Mod #2 | Mod #3 | Variation |
|---------|--------|--------|-----------|
| MIN_MARKET_CAP | $5,000 | **$2,000** | -60% ✅ +50% candidats |
| MIN_LIQUIDITY | $5,000 | **$2,000** | -60% ✅ +50% candidats |
| MIN_AGE_HOURS | 3h | **2h** | -33% ✅ +33% candidats |
| MIN_VOLUME_24H | $500 | **$300** | -40% ✅ +20% candidats |
| MIN_VOLUME_1H | $100 | **$50** | -50% ✅ +15% candidats |
| MIN_PRICE_CHANGE_1H | +5% | **+3%** | -40% ✅ +25% candidats |

**Estimation**: De **0 tokens/jour** (Mod #2) → **2-5 tokens/jour** (Mod #3)

### Sur le Win-Rate (Qualité des Entrées)

| Amélioration | Impact Attendu |
|--------------|----------------|
| **Momentum 5min +2%** | Évite rebonds techniques (-5% faux signaux) |
| **Cooldown 24h perdants** | Évite re-trades perdants (+10% win-rate) |
| **Âge 2h vs 3h** | Entre plus tôt dans pump (+15% win-rate) |

**Objectif Mod #3**: **≥30% win-rate** en 10 trades (vs 0% Mod #2)

---

## 📁 Fichiers Modifiés

### Configuration
- ✅ [config/.env](config/.env) - Nouveaux critères Mod #3

### Code Source
- ✅ [src/Filter.py](src/Filter.py) - Momentum 5m + 1h multi-période
- ✅ [src/Trader.py](src/Trader.py) - Cooldown tokens perdants
- ✅ [src/web3_utils.py](src/web3_utils.py) - Ajout price_change_5m

### Documentation
- ✅ [ANALYSIS_24H_MOD2.md](ANALYSIS_24H_MOD2.md) - Analyse échec Mod #2
- ✅ [MODIFICATION_3_REPORT.md](MODIFICATION_3_REPORT.md) - Ce document

---

## ✅ Validation Syntaxe Python

```bash
$ python3 -m py_compile src/Filter.py
$ python3 -m py_compile src/Trader.py
$ python3 -m py_compile src/web3_utils.py
✅ Tous les fichiers syntaxiquement corrects
```

---

## 🚀 Plan de Déploiement

### Étape 1: Git Commit + Push (Local)

```bash
cd /Users/vincentdoms/Documents/BaseBot
git add config/.env src/Filter.py src/Trader.py src/web3_utils.py
git add ANALYSIS_24H_MOD2.md MODIFICATION_3_REPORT.md
git commit -m "🔧 Modification #3: Déblocage filtre + Momentum 5m + Cooldown perdants

- Assouplir critères: MC/Liq $5K→$2K, Age 3h→2h, Vol $500→$300
- Ajout momentum 5min (+2%) pour confirmer tendance immédiate
- Assoupli momentum 1h (+5%→+3%) pour plus de candidats
- Ajout cooldown 24h sur tokens tradés en perte
- Objectif: 2-5 tokens/jour, ≥30% win-rate en 10 trades

Fichiers modifiés:
- config/.env: Nouveaux critères
- src/Filter.py: Momentum multi-période (5m+1h)
- src/Trader.py: Cooldown tokens perdants
- src/web3_utils.py: price_change_5m

Résultats Mod #2: 0% win-rate, 0 tokens approuvés en 24h"
git push origin main
```

### Étape 2: Git Pull + Redémarrage (VPS)

```bash
# Connexion VPS
sshpass -p "000Rnella" ssh -o StrictHostKeyChecking=no root@46.62.194.176

# Pull dernières modifications
cd /home/basebot/trading-bot
git pull origin main

# Vérifier les modifications
git log -1 --stat

# Redémarrer les services
sudo systemctl restart basebot-scanner basebot-filter basebot-trader

# Vérifier les services
systemctl status basebot-scanner basebot-filter basebot-trader --no-pager

# Vérifier les logs (grace period doit être 5min, -25%)
tail -n 20 /home/basebot/trading-bot/logs/trader.log
tail -n 20 /home/basebot/trading-bot/logs/filter.log
```

### Étape 3: Nettoyage Database (Fresh Start Mod #3)

```bash
# Arrêter le trader
systemctl stop basebot-trader

# Nettoyer DB
sqlite3 /home/basebot/trading-bot/data/trading.db "DELETE FROM trade_history;"
sqlite3 /home/basebot/trading-bot/data/trading.db "DELETE FROM sqlite_sequence WHERE name='trade_history';"

# Nettoyer JSON
rm -f /home/basebot/trading-bot/data/position*.json
rm -f /home/basebot/trading-bot/data/positions*.json

# Redémarrer
systemctl start basebot-trader

# Vérifier
tail -n 10 /home/basebot/trading-bot/logs/trader.log
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT COUNT(*) FROM trade_history;"
```

### Étape 4: Monitoring (24-48h)

**Vérifications à faire**:

1. **Filtre débloqué** (dans les 2h):
```bash
tail -f /home/basebot/trading-bot/logs/filter.log | grep -E "Approved|Rejected"
# Attendre: Au moins 1-2 tokens Approved dans les 2h
```

2. **Nouveaux trades ouverts** (dans les 6h):
```bash
sqlite3 /home/basebot/trading-bot/data/trading.db "SELECT symbol, datetime(entry_time) FROM trade_history ORDER BY entry_time DESC LIMIT 5;"
# Attendre: 2-3 nouveaux trades dans les 6h
```

3. **Cooldown fonctionne** (après 1ère perte):
```bash
tail -f /home/basebot/trading-bot/logs/trader.log | grep -E "cooldown|Cooldown"
# Attendre: Message "ajouté au cooldown" après 1ère perte
```

4. **Win-rate amélioration** (après 10 trades):
```bash
# Après 10 nouveaux trades fermés
./claude_auto_improve.sh
# Analyser: Win-rate ≥30% attendu
```

---

## 🎯 Critères de Succès

### Court Terme (24h)

- ✅ Filtre débloqué: ≥2 tokens approuvés/jour
- ✅ Nouveaux trades: ≥2 positions ouvertes en 24h
- ✅ Cooldown actif: Logs "cooldown" après pertes
- ✅ Momentum 5m: Logs "Momentum 5min OK" dans filter.log

### Moyen Terme (10 trades)

- ✅ Win-rate: ≥30% (vs 0% Mod #2)
- ✅ Perte moyenne: ≤-10% (vs -14.53% Mod #2)
- ✅ Perte maximale: ≤-25% (grace period actif)
- ✅ Diversité: ≤2 trades sur même token en 24h (cooldown)

### Long Terme (50 trades)

- 🎯 Win-rate: ≥70% (objectif final)
- 🎯 Profit moyen: ≥+15%
- 🎯 Ratio Reward/Risk: ≥3:1

---

## 📝 Notes Techniques

### DexScreener API - Périodes Disponibles

```json
"priceChange": {
  "m5": -1.23,   // 5 minutes
  "h1": 5.67,    // 1 heure
  "h6": 12.34,   // 6 heures
  "h24": 45.67   // 24 heures
}
```

### GeckoTerminal API - Périodes Disponibles

```json
"price_change_percentage": {
  "m5": -1.23,
  "h1": 5.67,
  "h6": 12.34,
  "h24": 45.67
}
```

### Structure losing_tokens_cooldown

```python
{
  "0xtoken123...abc": 1732723200.0,  # timestamp Unix
  "0xtoken456...def": 1732726800.0
}
```

**Nettoyage automatique**: Cooldowns expirés (>24h) sont supprimés lors de la vérification avant achat.

---

## 🔄 Rollback si Nécessaire

Si Modification #3 ne fonctionne pas:

```bash
# Revenir à Modification #2
cd /home/basebot/trading-bot
git log --oneline -5
git revert <commit_hash_mod3>
sudo systemctl restart basebot-scanner basebot-filter basebot-trader
```

---

## 📚 Références

- **Analyse Mod #2**: [ANALYSIS_24H_MOD2.md](ANALYSIS_24H_MOD2.md)
- **Rapport Mod #2**: [MODIFICATION_2_REPORT.md](MODIFICATION_2_REPORT.md)
- **Nettoyage DB Mod #2**: [DATABASE_CLEANUP_MOD2.md](DATABASE_CLEANUP_MOD2.md)

---

**Status**: ✅ PRÊT POUR COMMIT + DÉPLOIEMENT

Tous les fichiers ont été modifiés localement, la syntaxe Python est validée, et le système est prêt à être déployé sur le VPS via Git.
