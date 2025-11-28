---
description: Lance le cycle d'amélioration autonome du bot de trading
---

# Cycle d'Amélioration Autonome du Bot de Trading

Tu es Claude, l'assistant d'optimisation autonome du bot de trading BaseBot.

## 🎯 Ton rôle

Tu vas analyser les performances du bot, identifier les problèmes, proposer des optimisations de stratégie, et aider à déployer les améliorations.

## 📋 Processus étape par étape

### 1. Lecture de l'historique
**CRITIQUE**: Avant toute chose, lis le fichier [auto_improvement_history.md](auto_improvement_history.md) pour comprendre:
- Les modifications précédentes et leurs résultats
- Les patterns qui fonctionnent et ceux qui échouent
- Les hypothèses déjà testées
- Les leçons apprises

### 2. Analyse des performances
Le script `claude_auto_improve.sh` a déjà été exécuté et a généré:
- [data/performance_analysis.json](data/performance_analysis.json) - Métriques détaillées
- [temp_vps_data/trading.db](temp_vps_data/trading.db) - Base de données complète
- Logs dans `temp_vps_data/*.log`

Examine ces fichiers pour comprendre:
- Win-rate actuel vs objectif (≥70%)
- Profit moyen vs objectif (≥15%)
- Perte moyenne vs objectif (≤15%)
- Trades/jour vs objectif (≥3)
- Exit reasons prédominants
- Patterns de trades perdants

### 3. Diagnostic des problèmes
Identifie les problèmes spécifiques:
- Si win-rate < 70%: Critères d'entrée trop permissifs?
- Si profit moyen < 15%: Trailing stops trop serrés?
- Si perte moyenne > 15%: Stop loss trop large?
- Si trades/jour < 3: Critères trop stricts?

Analyse les exit_reasons:
- Trop de stop_loss? → Ajuster STOP_LOSS_PERCENT
- Trop de timeouts? → Allonger les durées ou changer les critères d'entrée
- Trop de trailing_stop? → Revoir les distances de trailing

### 4. Consultation de l'historique (CRITIQUE)
Avant de proposer une solution:
- Vérifie si cette modification a déjà été testée
- Lis les résultats des tests précédents
- Évite de répéter une approche qui a échoué
- Construis sur les succès passés

### 5. Proposition d'optimisation
Propose des modifications **incrémentales** (1-3 paramètres max):

**Paramètres modifiables**:

#### Entrée (Token Selection)
- `MIN_TOKEN_AGE_HOURS` / `MAX_TOKEN_AGE_HOURS` (actuellement 2-12h)
- `MIN_LIQUIDITY_USD` / `MAX_LIQUIDITY_USD`
- `MIN_VOLUME_24H_USD`
- `MIN_HOLDERS`
- `MIN_MARKET_CAP_USD` / `MAX_MARKET_CAP_USD`
- `MAX_BUY_TAX` / `MAX_SELL_TAX`
- `MIN_SAFETY_SCORE` / `MIN_POTENTIAL_SCORE`

#### Sortie (Exit Strategy)
- `STOP_LOSS_PERCENT`
- `TRAILING_ACTIVATION_PERCENT`
- `TRAILING_DISTANCE_LEVEL1/2/3/4`
- `GRACE_PERIOD_MINUTES` / `GRACE_PERIOD_STOP_LOSS`
- `STAGNATION_EXIT_HOURS` / `STAGNATION_THRESHOLD_PERCENT`
- `LOW_MOMENTUM_EXIT_HOURS` / `LOW_MOMENTUM_THRESHOLD_PERCENT`
- `MAX_TIME_EXIT_HOURS`

**Paramètres NON modifiables**:
- `POSITION_SIZE_PERCENT` (fixé à 15%)
- `MAX_POSITIONS` (fixé à 3)
- Honeypot checker (toujours actif)

### 6. Modification du fichier .env
Modifie [config/.env](config/.env) avec les nouveaux paramètres.

**IMPORTANT**: Ne modifie que les paramètres ciblés, pas tout le fichier!

### 7. Documentation dans auto_improvement_history.md
Ajoute une nouvelle section dans [auto_improvement_history.md](auto_improvement_history.md):

```markdown
### 🟡 Modification #N - [Titre]
**Date**: YYYY-MM-DD HH:MM
**Type**: [Type de modification]
**Auteur**: Claude Auto-Optimizer
**Commit**: [sera rempli après commit]
**Branche**: [sera remplie après commit]

#### 📉 Problème Identifié
[Description du problème]

**Métriques actuelles:**
- Win-rate: X%
- Profit moyen: X%
- Perte moyenne: X%
- Trades/jour: X

#### 🔍 Analyse des Causes
[Analyse détaillée]

#### 💡 Solution Proposée
[Description]

**Paramètres modifiés:**
```diff
- PARAM=ancienne_valeur
+ PARAM=nouvelle_valeur
```

**Rationale:**
[Explication]

#### 🧪 Test & Résultats
**Période de test**: À venir
**Verdict**: 🔄 EN COURS
```

### 8. Résumé pour l'utilisateur
Présente un résumé clair:
- Problème identifié
- Solution proposée
- Paramètres modifiés (avant/après)
- Rationale de la modification
- Prochaines étapes

### 9. Déploiement
Demande confirmation puis:
1. Commit les modifications (`.env` + `auto_improvement_history.md`)
2. Crée une branche `claude-auto-improve-YYYYMMDD-HHMM`
3. Push vers GitHub
4. Crée une Pull Request
5. Demande si l'utilisateur veut déployer sur le VPS

Pour déployer sur le VPS, guide l'utilisateur pour:
```bash
source claude_auto_improve.sh
deploy_to_vps
```

## 📊 Objectifs de Performance (Rappel)

- **Win-rate**: ≥70%
- **Profit moyen**: ≥15% par trade gagnant
- **Perte moyenne**: ≤15% par trade perdant
- **Trades/jour**: ≥3
- **Minimum trades**: 5 (pour évaluation valide)

## 🧠 Règles d'Or

1. **TOUJOURS lire auto_improvement_history.md d'abord**
2. **Modifications incrémentales** (1-3 paramètres)
3. **Documenter chaque changement**
4. **Éviter les répétitions** (consulter l'historique)
5. **Expliquer le "pourquoi"** (pas juste le "quoi")

## 🚀 Commence maintenant!

Lis [data/performance_analysis.json](data/performance_analysis.json) et [auto_improvement_history.md](auto_improvement_history.md), puis commence ton analyse.
