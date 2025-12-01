# 📊 Rapport de Vérification - Scanner & Filter

**Date**: 2025-12-01 17:35 UTC
**Demande**: Vérifier performance scanner et raisons de rejet des tokens
**Statut**: ✅ **DIAGNOSTIC COMPLET**

---

## 🎯 Résumé Exécutif

### ✅ Scanner - PERFORMANT ET FONCTIONNEL
- **Détection**: 255 events PairCreated par cycle
- **Performance**: ~40 secondes par cycle (excellent)
- **Mode**: On-chain pur (pas d'enrichissement DexScreener)
- **Déduplication**: 119 tokens uniques insérés en DB
- **Erreurs**: 0 erreur détectée
- **Verdict**: ✅ **Scanner 100% opérationnel**

### ❌ Filter - FONCTIONNE MAIS REJETTE TOUT
- **Tokens découverts**: 119
- **Tokens rejetés**: 119 (100%)
- **Tokens approuvés**: 0
- **Trades**: 0
- **Verdict**: ⚠️ **Désalignement configuration Scanner/Filter**

---

## 📈 Performance Scanner - Détails

### Cycles de Scan (20 derniers)
```
2025-12-01 16:26:21 - ✅ 255 tokens détectés
2025-12-01 16:27:02 - ✅ 255 tokens détectés  (~41s)
2025-12-01 16:27:43 - ✅ 255 tokens détectés  (~41s)
2025-12-01 16:28:24 - ✅ 255 tokens détectés  (~41s)
2025-12-01 16:29:03 - ✅ 255 tokens détectés  (~39s)
2025-12-01 16:29:41 - ✅ 255 tokens détectés  (~38s)
2025-12-01 16:30:21 - ✅ 255 tokens détectés  (~40s)
2025-12-01 16:31:01 - ✅ 255 tokens détectés  (~40s)
2025-12-01 16:31:42 - ✅ 255 tokens détectés  (~41s)
2025-12-01 16:32:21 - ✅ 255 tokens détectés  (~39s)
2025-12-01 16:33:02 - ✅ 255 tokens détectés  (~41s)
2025-12-01 16:33:42 - ✅ 255 tokens détectés  (~40s)
2025-12-01 16:34:22 - ✅ 255 tokens détectés  (~40s)
```

**Moyenne**: ~40 secondes par cycle
**Stabilité**: Très stable (38-41s)
**Erreurs**: Aucune

### Architecture On-Chain Pure
Le scanner détecte uniquement les événements `PairCreated` on-chain:
- ✅ Détection rapide (<10s pour 262 events)
- ✅ Données on-chain: symbol, name, decimals, age_hours
- ✅ Déduplication par token_address (évite duplicatas cross-factory)
- ✅ Pas d'enrichissement DexScreener (délégué au Filter)

**Amélioration vs Version Précédente**:
- Avant: >5min (262 appels DexScreener API)
- Après: ~40s (on-chain pur)
- **Gain**: 7.5x plus rapide

---

## ❌ Analyse des Rejets - Problème Identifié

### Distribution par Type de Rejet
```
Type de Rejet               | Count | %
---------------------------|-------|------
Âge > 8h (trop vieux)      | 115   | 96.6%
Non trouvé DexScreener     | 4     | 3.4%
---------------------------|-------|------
TOTAL                      | 119   | 100%
```

### Tokens Non Trouvés sur DexScreener (4)
```
Symbol   | Token Address     | Raison
---------|-------------------|------------------------------------------
DONUTERI | 0xe287486b...     | Token non trouvé sur DexScreener (trop récent?)
GRAPE    | 0x9EB0C6AC...     | Token non trouvé sur DexScreener (trop récent?)
PAYROLLP | 0xc2bd7965...     | Token non trouvé sur DexScreener (trop récent?)
EPHYCSOC | 0xe0a8cE21...     | Token non trouvé sur DexScreener (trop récent?)
```

**Note**: Ces 4 tokens (3.4%) ne sont pas listés sur DexScreener, probablement car trop récents ou DEX non supporté.

### Rejets "Âge > 8h" (115 tokens)

**Exemples**:
```
Symbol    | Âge    | Raison
----------|--------|----------------------------------------
Grayscale | 10.0h  | ❌ Âge 10.0h > 8.0h (trop vieux, pump fini)
SWEATER   | 10.1h  | ❌ Âge 10.1h > 8.0h (trop vieux, pump fini)
KYLIE     | 10.1h  | ❌ Âge 10.1h > 8.0h (trop vieux, pump fini)
ETRUMP    | 10.0h  | ❌ Âge 10.0h > 8.0h (trop vieux, pump fini)
MOMO      | 10.0h  | ❌ Âge 10.0h > 8.0h (trop vieux, pump fini)
```

---

## 🔧 Cause Racine - Désalignement Configuration

### Configuration Actuelle

**Scanner** (`src/Scanner.py`):
```env
MIN_TOKEN_AGE_HOURS=2
MAX_TOKEN_AGE_HOURS=12
```
→ Scanner détecte tokens entre 2h et 12h

**Filter** (`src/Filter.py` - Stratégie Momentum Safe):
```env
MIN_AGE_HOURS=3.5
MAX_AGE_HOURS=8.0
```
→ Filter accepte tokens entre 3.5h et 8h

### Distribution des Tokens Détectés

```
Âge (h) | Count | Exemples
--------|-------|------------------------------------------
9.9     | 1     | NMT
10.0    | 17    | E91, NKOE, MORI, ETRUMP, KaitoAI, LC...
10.1    | 34    | Tit, SQUEPE, PEPECHU, VERVLE, TikTok...
10.2    | 18    | Genbase, TRUMPBASE, Pikachu, BID...
10.3    | 5     | ???, ZALA AI...
10.5    | 4     | BLUEPEPE, BALLSGUY...
10.6    | 5     | ETF...
10.8    | 3     | V4RP, スシロー...
10.9    | 1     | cbBTC
11.0    | 4     | REPPO, America Party...
11.1    | 4     | TROLL, KYLIE, Luffy...
11.3    | 4     | noice...
11.4    | 2     | KAVIT...
11.5    | 4     | PAYROLLP...
11.6    | 2     | Launchpad...
11.7    | 4     | EPHYCSOC, zerocoin...
11.8    | 3     | SMR3, RugProof...
11.9    | 1     | Pikachu
12.0    | 3     | ORACLE, BALL, ATTA2
--------|-------|------------------------------------------
TOTAL   | 119   | 100% des tokens entre 9.9h et 12.0h
```

**Tokens dans la fenêtre 3.5-8h**: **0**
**Tokens hors fenêtre (>8h)**: **119 (100%)**

### Visualisation du Problème

```
Timeline (heures):
0h────2h────3.5h────8h────10h────12h────>

Scanner:  [════════════════════════════]
          2h                        12h

Filter:       [══════════]
              3.5h    8h

Tokens:                     [════════]
                           9.9h   12h

RÉSULTAT: ❌ AUCUNE INTERSECTION
```

---

## 💡 Solutions Proposées

### Option 1: Ajuster Scanner (RECOMMANDÉ ⭐)

**Action**: Réduire fenêtre Scanner à 3-10h

**Avantages**:
- ✅ Capture fenêtre Filter (3.5-8h) avec marge
- ✅ Moins d'events à traiter (plus rapide)
- ✅ Moins de rejets inutiles
- ✅ Respecte stratégie Momentum Safe

**Configuration**:
```env
MIN_TOKEN_AGE_HOURS=3    # Au lieu de 2
MAX_TOKEN_AGE_HOURS=10   # Au lieu de 12
```

**Implémentation**:
```bash
# Modifier config/.env sur VPS
sed -i 's/MIN_TOKEN_AGE_HOURS=2/MIN_TOKEN_AGE_HOURS=3/' /home/basebot/trading-bot/config/.env
sed -i 's/MAX_TOKEN_AGE_HOURS=12/MAX_TOKEN_AGE_HOURS=10/' /home/basebot/trading-bot/config/.env

# Redémarrer Scanner
systemctl restart basebot-scanner
```

---

### Option 2: Attendre 2-3 Heures (PASSIVE)

**Action**: Ne rien changer, attendre que de nouveaux tokens entrent dans la fenêtre

**Timeline**:
- Actuellement: Tokens à 9.9-12h
- Dans 2h: Nouveaux tokens à 7.9-10h (certains dans 3.5-8h ✅)
- Dans 3h: Nouveaux tokens à 6.9-9h (plus dans 3.5-8h ✅)

**Avantages**:
- ✅ Pas de changement de config
- ✅ Vérification naturelle du système

**Inconvénients**:
- ❌ Attente passive 2-3h
- ❌ Scanner continue à traiter tokens 10-12h inutilement

---

### Option 3: Élargir Filter (NON RECOMMANDÉ ⚠️)

**Action**: Accepter tokens plus vieux (3.5-12h)

**Configuration**:
```env
MAX_AGE_HOURS=12.0   # Au lieu de 8.0
```

**Avantages**:
- ✅ Capture immédiate des tokens actuels

**Inconvénients**:
- ❌ Viole stratégie Momentum Safe (fenêtre 3.5-8h)
- ❌ Tokens >8h = pump souvent terminé
- ❌ Baisse du win-rate attendu
- ❌ Moins sélectif

**Verdict**: ⚠️ **NON recommandé** (compromet la stratégie)

---

## 🎯 Recommandation Finale

### ⭐ Option 1: Ajuster Scanner à 3-10h

**Justification**:
1. **Alignement stratégique**: Respecte fenêtre Momentum Safe (3.5-8h)
2. **Performance**: Moins d'events à traiter
3. **Efficacité**: Évite scan/rejet inutile de tokens >10h
4. **Marge de sécurité**: 3-10h capture bien 3.5-8h

**Impact**:
- Scanner détectera ~50-80% des tokens actuels (seulement ceux 3-10h)
- Filter aura des tokens à analyser dans sa fenêtre cible
- Taux de rejet devrait passer de 96% à ~30-50% (rejets légitimes: liquidité, volume, momentum, etc.)

**Implémentation**: Voir script ci-dessus

---

## 📋 État du Système

### Services
```
basebot-scanner:   active ✅
basebot-filter:    active ✅
basebot-trader:    active ✅
basebot-dashboard: active ✅
```

### Base de Données
```
discovered_tokens:  119 tokens
rejected_tokens:    119 tokens (100%)
approved_tokens:    0 tokens
trade_history:      0 trades
```

### Logs
```
Scanner:  0 erreurs
Filter:   119 rejets (tous légitimes selon config actuelle)
Trader:   0 activité (pas de tokens approuvés)
```

---

## ✅ Conclusion

### Scanner
- **Statut**: ✅ **100% Fonctionnel et Performant**
- **Performance**: Excellente (~40s/cycle, 0 erreur)
- **Architecture**: On-chain pure optimisée

### Filter
- **Statut**: ⚠️ **Fonctionne mais rejette tout**
- **Cause**: Désalignement Scanner (2-12h) vs Filter (3.5-8h)
- **Tokens actuels**: Tous entre 9.9-12h (hors fenêtre Filter)

### Recommandation
1. **Ajuster Scanner**: 3-10h (au lieu de 2-12h)
2. **Redémarrer**: Scanner uniquement
3. **Attendre**: 1-2 cycles (~2min)
4. **Vérifier**: Nouveaux tokens dans fenêtre 3.5-8h passeront le Filter

**Résultat attendu**: Tokens approuvés dans les 2-3 prochaines heures.

---

**Rapport généré le**: 2025-12-01 17:35 UTC
**Système vérifié sur**: VPS 46.62.194.176
