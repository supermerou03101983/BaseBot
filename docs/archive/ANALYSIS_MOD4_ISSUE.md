# 🔍 Problème Modification #4 - Scanner Bloquant

**Date**: 2025-11-28 07:50 UTC
**Status**: ❌ PROBLÈME CRITIQUE IDENTIFIÉ

---

## 🚨 Problème

**Scanner rejette 100% des tokens** avec "20 trop jeunes" à chaque batch.

### Logs Scanner
```
📊 Batch traité: 0 nouveaux | 0 déjà connus | 20 trop jeunes | 0 trop vieux
```

### État Base de Données
- **Discovered**: 63 tokens (anciens, avant nettoyage incomplet)
- **Approved**: 0
- **Analyzed récemment**: 2 (ZEUS, BlackBall) → Rejetés MC/Liq/Vol=$0

---

## 🔍 Cause Root

### GeckoTerminal API Endpoint

Le Scanner utilise : `https://api.geckoterminal.com/api/v2/networks/base/new_pools`

**Problème** : Cet endpoint retourne **UNIQUEMENT les NOUVEAUX pools** (< 30min typiquement).

**Test réalisé** :
1. `MIN_TOKEN_AGE_HOURS=4` → 100% "trop jeunes"
2. `MIN_TOKEN_AGE_HOURS=2` → 100% "trop jeunes"
3. Conclusion : **Tous les tokens GeckoTerminal sont < 2h**

### Pourquoi ?

GeckoTerminal `/new_pools` est conçu pour détecter les **pools fraîchement créés** :
- Mise à jour temps réel (quelques minutes après création)
- Parfait pour scanner les nouveaux listings
- **MAIS** pas pour trouver des tokens de 4h+

---

## 💡 Solution - Modification #4.1

### Changement Stratégique

**Avant (Mod #4)** :
```
Scanner découvre tokens à 4h → Filter vérifie 4h
Problème: GeckoTerminal ne retourne que tokens < 30min
```

**Après (Mod #4.1)** :
```
Scanner découvre tokens à 0.5h (30min) → Stocke en DB
→ Filter vérifie âge 4h (rejette si < 4h)
→ Tokens découverts à T+30min seront filtrés à T+4h (3.5h plus tard)
```

### Configuration

```bash
# Scanner.py (découverte précoce)
MIN_TOKEN_AGE_HOURS=0.5    # 30 minutes (accepter tokens GeckoTerminal)
MAX_TOKEN_AGE_HOURS=12     # Garder

# Filter.py (validation stricte)
MIN_AGE_HOURS=4            # Garder (rejette tokens < 4h)
```

### Logique

1. **T+30min** : Scanner découvre token via GeckoTerminal → Ajoute à `discovered_tokens`
2. **T+1h à T+3h59min** : Filter analyse token → Rejet car âge < 4h
3. **T+4h+** : Filter analyse token → Si MC/Liq/Vol/Momentum OK → Approuvé

**Avantage** :
- Scanner peut découvrir les tokens tôt
- Filter valide seulement quand données DexScreener disponibles (4h+)
- Pas de perte d'opportunité (tokens découverts restent en DB)

---

## 🔧 Modifications à Appliquer

### A. config/.env (LOCAL + VPS)

```bash
MIN_TOKEN_AGE_HOURS=0.5     # Avant: 2 (Scanner accepte tokens 30min+)
MIN_AGE_HOURS=4             # Garder (Filter rejette < 4h)
```

### B. Aucun changement code

La logique existe déjà :
- Scanner utilise `MIN_TOKEN_AGE_HOURS` pour découvrir
- Filter utilise `MIN_AGE_HOURS` pour valider

Il suffit de désynchroniser les deux !

---

## 📊 Impact Attendu

### Sur Scanner

**Avant** (MIN_TOKEN_AGE_HOURS=2-4h) :
```
20 tokens GeckoTerminal → 20 trop jeunes → 0 découverts
```

**Après** (MIN_TOKEN_AGE_HOURS=0.5h) :
```
20 tokens GeckoTerminal → 15-20 découverts (age 30min-2h)
```

### Sur Filter

**Logique** :
```python
if token_age < 4h:
    reject("Age insuffisant")
    return  # Token reste en DB, sera re-évalué plus tard
```

**Résultat** :
- Tokens découverts à T+30min → Rejetés jusqu'à T+4h
- À T+4h → DexScreener a données → Évaluation avec vraies métriques

### Timeline Exemple

```
T+0h     : Pool créé sur Uniswap
T+10min  : GeckoTerminal détecte → new_pools API
T+30min  : Scanner découvre → Ajoute à discovered_tokens
T+35min  : Filter analyse → Rejet (age 35min < 4h)
T+1h     : Filter analyse → Rejet (age 1h < 4h)
T+2h     : Filter analyse → Rejet (age 2h < 4h)
T+3h     : Filter analyse → Rejet (age 3h < 4h)
T+4h     : Filter analyse → age OK, vérifie MC/Liq/Vol/Momentum
           → Si OK → Approuvé !
```

---

## ✅ Validation

### Vérification après déploiement

**Scanner logs** (après 5min) :
```
📊 Batch traité: 10-15 nouveaux | 5 déjà connus | 0-5 trop jeunes
```
✅ Des tokens sont découverts

**Filter logs** (premières heures) :
```
❌ REJET: Age (0.8h) < min (4h)
❌ REJET: Age (1.2h) < min (4h)
❌ REJET: Age (2.5h) < min (4h)
```
✅ Tokens rejetés car trop jeunes (normal)

**Filter logs** (après 4-6h) :
```
✅ Age (4.2h) OK
✅ MC ($850) > min ($500)
✅ Volume 1h ($35) > min ($20)
✅ Momentum 1h (+12%) > min (+10%)
→ Token APPROUVE
```
✅ Premier token approuvé quand âge 4h+ atteint

---

## 🎯 Prochaines Étapes

1. ✅ Modifier `MIN_TOKEN_AGE_HOURS=0.5` en local
2. ✅ Git commit + push
3. ✅ Pull VPS + redémarrer Scanner
4. ⏳ Attendre 4-6h pour voir premier token approuvé
5. 📊 Analyser après 24h

---

**Status** : 📋 SOLUTION IDENTIFIÉE - PRÊT POUR MOD #4.1

Le problème n'est PAS les critères MC/Liq/Vol mais le fait que Scanner ne peut PAS découvrir de tokens 4h+ avec GeckoTerminal `/new_pools`. Solution : Découvrir tôt (30min), filtrer tard (4h).
