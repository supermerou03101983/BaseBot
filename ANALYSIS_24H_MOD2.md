# 📊 Analyse 24h - Modification #2

**Période**: 2025-11-26 19:48 → 2025-11-27 07:55 (12h)
**Status**: ❌ ÉCHEC - Win-rate 0%, Filtre bloquant

---

## 📈 Résultats

### Métriques Globales

| Métrique | Objectif Mod #2 | Résultat Réel | Écart |
|----------|-----------------|---------------|-------|
| **Win-rate** | ≥40% | **0%** | -40% ❌ |
| **Perte moyenne** | ≤-10% | **-14.53%** | -4.53% ❌ |
| **Perte maximale** | ≤-25% | **-18.85%** | +6.15% ✅ |
| **Trades/jour** | ≥2 | **0** (après 3 initiaux) | -2 ❌ |

### Trades Fermés

| ID | Symbol | Durée | P&L | Raison |
|----|--------|-------|-----|--------|
| 1 | FARSINO | 2.0h | **-10.2%** | Stop Loss |
| 3 | FARSINO | 4.4h | **-18.85%** | Stop Loss |

**Moyenne** : -14.53%

### Position Ouverte

| ID | Symbol | Durée | P&L Actuel |
|----|--------|-------|------------|
| 2 | bolivian | 12.1h | **+2.2%** |

---

## 🚨 Problèmes Critiques

### 1. Filtre Bloquant - 0 Token Approuvé en 24h

**Observation** :
```
Analyzed=30, Approved=0, Rejected=30
```

**Raisons de rejet** :
- **MC $0** / **Liquidity $0** / **Volume 24h $0** : 90% des cas
- **Volume 1h = $0** : 10% des cas (ex: LAZER avec MC $30K, Liq $21K, Vol24h $2.9K)

**Problème** : Les tokens scannés sont trop récents (< 1h) et n'ont pas encore de données DexScreener complètes.

### 2. Win-Rate 0% - Entrées sur Tokens en Chute

**Analyse des 2 trades fermés** :

#### FARSINO #1 (2h → -10.2%)
- Entry: 2025-11-26 19:48
- Exit: 2025-11-26 21:51 (Stop Loss -5%)
- **Hypothèse** : Token en chute depuis le pic, entrée trop tardive

#### FARSINO #3 (4.4h → -18.85%)
- Entry: 2025-11-26 21:51
- Exit: 2025-11-27 02:17 (Stop Loss -5% après grace period)
- **Hypothèse** : Re-entrée après sortie du #1, token continue de chuter

**Conclusion** : Le momentum +5% sur 1h n'est PAS suffisant. Un token peut avoir +5% sur 1h mais être en train de chuter depuis son ATH.

### 3. Manque de Diversité

**3 trades sur le même token (FARSINO)** :
- Trade #1 : FARSINO (-10.2%)
- Trade #3 : FARSINO (-18.85%)
- Position actuelle #2 : bolivian (+2.2%)

**Problème** : Re-trading sur FARSINO après une perte suggère que le filtre n'a pas assez d'options.

---

## 🔍 Analyse Approfondie

### Pourquoi le Filtre Bloque Tout ?

**Critères actuels (Mod #2)** :
```
MIN_VOLUME_24H=500
MIN_VOLUME_1H=100
MIN_AGE_HOURS=3
MIN_PRICE_CHANGE_1H=5
MIN_MARKET_CAP=5000
MIN_LIQUIDITY_USD=5000
```

**Problème** :
1. **MIN_AGE_HOURS=3** : Les tokens de 3h+ ont souvent déjà fait leur pump
2. **MIN_MARKET_CAP=5000** + **MIN_LIQUIDITY_USD=5000** : Trop strict pour tokens 3-6h
3. **Volume 1h = $0** : Même LAZER (MC $30K, Liq $21K, Vol24h $2.9K) est rejeté car pas de volume dans la dernière heure

### Pourquoi Win-Rate 0% ?

**Entrée basée sur momentum +5% 1h** :
- Un token peut avoir +5% sur 1h mais être en dump depuis son ATH
- Ex: Token pumpe à 100%, puis dumpe à 50%, puis reprend +5% → le bot entre à 50% alors que le token va continuer à dumper

**Solution** : Vérifier la tendance sur plusieurs périodes (5min, 15min, 1h) et s'assurer qu'on n'entre pas sur un rebond technique d'un dump.

---

## 💡 Modification #3 Proposée

### Objectif

**Débloquer le filtre** tout en **améliorant la qualité des entrées** :
- Assouplir MC/Liquidity pour permettre plus de trades
- Renforcer la vérification de momentum (multi-période)
- Ajouter cooldown sur tokens déjà tradés en perte

### Changements Proposés

#### A. Assouplir Market Cap / Liquidity

```bash
MIN_MARKET_CAP=2000      # Avant: 5000
MIN_LIQUIDITY_USD=2000   # Avant: 5000
```

**Rationale** : Tokens 3-6h atteignent souvent $2-3K avant $5K. Permet plus de candidats.

#### B. Réduire l'Âge Minimum

```bash
MIN_AGE_HOURS=2          # Avant: 3
```

**Rationale** : Tokens 2-3h sont dans leur phase de pump initiale, meilleure fenêtre d'opportunité.

#### C. Renforcer le Momentum Multi-Période

**Nouveau** : Ajouter vérification price_change_5m

```bash
MIN_PRICE_CHANGE_5M=2    # Nouveau: +2% sur 5min
MIN_PRICE_CHANGE_1H=3    # Avant: 5 (assouplir)
```

**Logique** :
- **5min +2%** : Confirme momentum haussier IMMÉDIAT
- **1h +3%** : Confirme tendance haussière générale (assoupli de 5% à 3%)
- **Combinaison** : Évite les rebonds techniques de dumps

#### D. Assouplir Volume 24h

```bash
MIN_VOLUME_24H=300       # Avant: 500
```

**Rationale** : Tokens 2-3h atteignent $300-500 de volume, pas encore $500+.

#### E. Garder Volume 1h Minimum

```bash
MIN_VOLUME_1H=50         # Avant: 100 (assouplir légèrement)
```

**Rationale** : $50 sur 1h = activité minimale, évite tokens complètement morts.

#### F. Cooldown sur Tokens Perdants

**Nouveau** : Ne pas re-trader sur un token perdu dans les 24h

```python
# Dans Trader.py
self.losing_tokens_cooldown = {}  # {token_address: timestamp}

# Avant d'acheter
if token_address in self.losing_tokens_cooldown:
    hours_since = (now - self.losing_tokens_cooldown[token_address]) / 3600
    if hours_since < 24:
        self.logger.info(f"❌ {symbol} en cooldown (perdu il y a {hours_since:.1f}h)")
        return
```

**Rationale** : Évite FARSINO #3 (re-trade après FARSINO #1 perdant).

---

## 📊 Impact Attendu

### Sur le Filtre

| Critère | Mod #2 | Mod #3 | Impact |
|---------|--------|--------|--------|
| MIN_MARKET_CAP | $5,000 | **$2,000** | +50% candidats |
| MIN_LIQUIDITY | $5,000 | **$2,000** | +50% candidats |
| MIN_AGE_HOURS | 3h | **2h** | +33% candidats |
| MIN_VOLUME_24H | $500 | **$300** | +20% candidats |
| MIN_VOLUME_1H | $100 | **$50** | +15% candidats |
| MIN_PRICE_CHANGE_1H | +5% | **+3%** | +25% candidats |
| **Nouveau** Momentum 5m | - | **+2%** | Meilleure qualité |

**Estimation** : De 0 tokens/jour → 2-5 tokens/jour

### Sur le Win-Rate

| Amélioration | Impact Attendu |
|--------------|----------------|
| Momentum 5m +2% | Évite rebonds techniques (-5% de faux signaux) |
| Cooldown 24h tokens perdants | Évite re-trades perdants (+10% win-rate) |
| Âge 2h vs 3h | Entre plus tôt dans le pump (+15% win-rate) |

**Objectif Mod #3** : **≥30% win-rate** en 10 trades (vs 0% actuellement)

---

## 🎯 Plan d'Action

### Étape 1 : Modifications en Local

1. ✅ Mettre à jour `.env` avec nouveaux critères
2. ✅ Ajouter filtre `price_change_5m` dans `Filter.py`
3. ✅ Ajouter cooldown tokens perdants dans `Trader.py`
4. ✅ Documenter dans `MODIFICATION_3_REPORT.md`

### Étape 2 : Git Workflow

```bash
# Local
git add config/.env src/Filter.py src/Trader.py
git commit -m "🔧 Modification #3: Assouplir critères + Momentum 5m + Cooldown perdants"
git push origin main

# VPS
cd /home/basebot/trading-bot
git pull origin main
sudo systemctl restart basebot-scanner basebot-filter basebot-trader
```

### Étape 3 : Validation

- Attendre 24h
- Vérifier : Approved > 0 (au moins 2-5 tokens/jour)
- Analyser win-rate après 10 nouveaux trades

---

## ✅ Checklist Modification #3

- [ ] Mettre à jour `.env` local
- [ ] Patcher `Filter.py` (price_change_5m)
- [ ] Patcher `Trader.py` (cooldown perdants)
- [ ] Tester syntaxe Python localement
- [ ] Créer `MODIFICATION_3_REPORT.md`
- [ ] Git commit + push
- [ ] Git pull sur VPS
- [ ] Redémarrer services VPS
- [ ] Nettoyer DB (reset pour Mod #3)
- [ ] Observer 24-48h

---

**Status** : 📋 ANALYSE TERMINÉE - PRÊT POUR MOD #3
