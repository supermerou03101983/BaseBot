# 🤖 Système d'Amélioration Autonome du Bot de Trading

> **Système intelligent d'optimisation continue de la stratégie de trading**
>
> Ce système permet à Claude de diagnostiquer, analyser, optimiser et déployer automatiquement des améliorations de votre stratégie de trading sur le VPS.

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Installation](#installation)
3. [Utilisation](#utilisation)
4. [Architecture](#architecture)
5. [Workflow complet](#workflow-complet)
6. [Configuration Telegram](#configuration-telegram)
7. [Fichiers créés](#fichiers-créés)
8. [FAQ](#faq)

---

## 🎯 Vue d'ensemble

### Objectifs de Performance

Le système optimise la stratégie pour atteindre ces objectifs:

- **Win-rate**: ≥70%
- **Profit moyen**: ≥15% par trade gagnant
- **Perte moyenne**: ≤15% par trade perdant
- **Trades par jour**: ≥3
- **Minimum de trades**: 5 (pour évaluation valide)

### Ce que fait le système

1. **Se connecte au VPS** via SSH
2. **Récupère les données** (base de données, logs)
3. **Analyse les performances** de tous les trades
4. **Identifie les problèmes** dans la stratégie actuelle
5. **Consulte l'historique** pour éviter de répéter les erreurs
6. **Propose des optimisations** avec Claude en mode interactif
7. **Modifie les paramètres** dans `config/.env`
8. **Commit & Push** sur GitHub (branche dédiée)
9. **Crée une Pull Request** automatiquement
10. **Déploie sur le VPS** après validation
11. **Notifie via Telegram** (optionnel)

---

## 🚀 Installation

### Prérequis

1. **Python 3** (déjà installé)
2. **sshpass** pour la connexion SSH automatisée
3. **gh CLI** pour les Pull Requests (optionnel)

```bash
# Installation sur macOS
brew install sshpass
brew install gh

# Authentification GitHub CLI (une seule fois)
gh auth login
```

### Configuration

1. **Credentials VPS** sont déjà configurés dans `vps_credentials.conf`
   - ⚠️ Ce fichier est dans `.gitignore` (ne sera jamais commité)

2. **Telegram** (optionnel mais recommandé)
   - Créez un bot Telegram via [@BotFather](https://t.me/botfather)
   - Obtenez votre chat ID via [@userinfobot](https://t.me/userinfobot)
   - Modifiez `vps_credentials.conf`:
   ```bash
   TELEGRAM_WEBHOOK=https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage?chat_id=<YOUR_CHAT_ID>
   ```

---

## 💻 Utilisation

### Méthode 1: Script direct (recommandé)

```bash
# Depuis le dossier BaseBot
./claude_auto_improve.sh
```

Le script va:
1. Se connecter au VPS
2. Vérifier les services
3. Récupérer les données
4. Analyser les performances
5. Afficher un rapport détaillé
6. Entrer en mode interactif avec Claude

### Méthode 2: Slash command dans VSCode

```bash
# Dans le terminal VSCode ou via Claude Code
/auto-improve
```

Cette commande lance Claude en mode optimisation guidée.

---

## 🏗️ Architecture

### Fichiers du système

```
BaseBot/
├── claude_auto_improve.sh          # Script principal d'amélioration
├── auto_strategy_optimizer.py      # Analyseur de performance Python
├── auto_improvement_history.md     # Historique des modifications (CRITIQUE)
├── vps_credentials.conf            # Credentials VPS/Telegram (NON COMMITÉ)
├── .claude/
│   └── commands/
│       └── auto-improve.md         # Slash command Claude
└── temp_vps_data/                  # Données téléchargées du VPS (temporaire)
    ├── trading.db                  # Base de données
    ├── trader.log                  # Logs
    ├── filter.log
    └── scanner.log
```

### Fichiers générés

```
data/
└── performance_analysis.json       # Résultats d'analyse détaillés
```

---

## 🔄 Workflow Complet

### Phase 1: Diagnostic (Automatique)

```
┌─────────────────────────────────────┐
│  ./claude_auto_improve.sh          │
└──────────────┬──────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Connexion SSH au VPS │
    └──────────┬───────────┘
               │
               ▼
    ┌────────────────────────────┐
    │ Vérification des services  │
    │ (scanner/filter/trader)    │
    └──────────┬─────────────────┘
               │
               ▼
    ┌─────────────────────────────┐
    │ Téléchargement des données  │
    │ - trading.db                │
    │ - logs/*.log                │
    │ - config/.env               │
    └──────────┬──────────────────┘
               │
               ▼
    ┌──────────────────────────────┐
    │ Analyse des performances     │
    │ (auto_strategy_optimizer.py) │
    └──────────┬───────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Génération du rapport           │
    │ (performance_analysis.json)     │
    └──────────┬──────────────────────┘
               │
               ▼
       Objectifs atteints?
               │
      ┌────────┴────────┐
      │                 │
     OUI               NON
      │                 │
      ▼                 ▼
   ✅ FIN      ⚠️ Mode Interactif
                        │
                        ▼
              ┌──────────────────────┐
              │  Phase 2: Claude     │
              └──────────────────────┘
```

### Phase 2: Optimisation (Interactive avec Claude)

```
┌──────────────────────────────────────┐
│ Claude lit:                          │
│ 1. auto_improvement_history.md      │
│ 2. performance_analysis.json        │
│ 3. temp_vps_data/trading.db         │
└──────────────┬───────────────────────┘
               │
               ▼
    ┌─────────────────────────┐
    │ Identification problème │
    │ - Win-rate trop bas?    │
    │ - Profit insuffisant?   │
    │ - Trop de pertes?       │
    │ - Pas assez de trades?  │
    └──────────┬────────────────┘
               │
               ▼
    ┌───────────────────────────────┐
    │ Analyse des exit_reasons      │
    │ Patterns de trades perdants   │
    └──────────┬────────────────────┘
               │
               ▼
    ┌──────────────────────────────────┐
    │ Consultation historique          │
    │ Cette modif a-t-elle été testée? │
    └──────────┬───────────────────────┘
               │
               ▼
    ┌────────────────────────────┐
    │ Proposition d'optimisation │
    │ (1-3 paramètres max)       │
    └──────────┬─────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Modification .env    │
    └──────────┬───────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Documentation dans              │
    │ auto_improvement_history.md     │
    └──────────┬──────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Validation utilisateur│
    └──────────┬────────────┘
               │
               ▼
       Déployer sur VPS?
               │
      ┌────────┴────────┐
      │                 │
     OUI               NON
      │                 │
      ▼                 ▼
   Phase 3          ✅ FIN
```

### Phase 3: Déploiement (Semi-automatique)

```
┌──────────────────────────────┐
│ Commit des modifications     │
│ - config/.env                │
│ - auto_improvement_history.md│
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Création branche Git             │
│ claude-auto-improve-YYYYMMDD-HHMM│
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────┐
│ Push vers GitHub     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────┐
│ Création Pull Request    │
└──────────┬───────────────┘
           │
           ▼
    Déployer maintenant?
           │
  ┌────────┴────────┐
  │                 │
 OUI               NON
  │                 │
  ▼                 ▼
┌──────────────┐  Déploiement
│ SSH vers VPS │  manuel
│ git pull     │  plus tard
│ restart bot  │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Notification     │
│ Telegram         │
└──────────────────┘
```

---

## 📱 Configuration Telegram

### Étape 1: Créer un bot Telegram

1. Ouvrez Telegram et cherchez **@BotFather**
2. Envoyez `/newbot`
3. Donnez un nom à votre bot (ex: "BaseBot Notifier")
4. Donnez un username (ex: "basebot_notifier_bot")
5. Copiez le **token** fourni (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Étape 2: Obtenir votre Chat ID

1. Cherchez **@userinfobot** dans Telegram
2. Envoyez `/start`
3. Copiez votre **Chat ID** (ex: `123456789`)

### Étape 3: Configurer le webhook

Modifiez `vps_credentials.conf`:

```bash
TELEGRAM_WEBHOOK=https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz/sendMessage?chat_id=123456789
```

### Étape 4: Tester

```bash
# Test rapide
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage?chat_id=<YOUR_CHAT_ID>&text=Test notification BaseBot"
```

Vous devriez recevoir un message Telegram!

---

## 📊 Fichiers Créés par le Système

### auto_improvement_history.md

**Le fichier le plus important du système!**

Ce fichier est la **mémoire empirique** de votre bot. Claude le consulte SYSTÉMATIQUEMENT avant toute modification pour:
- Éviter de répéter les mêmes erreurs
- Construire sur les succès passés
- Comprendre l'évolution de la stratégie
- Identifier les patterns qui fonctionnent

**Structure**:
- Configuration baseline
- Historique chronologique de toutes les modifications
- Résultats des tests (win-rate, profit, etc.)
- Leçons apprises
- Hypothèses testées vs non testées

### performance_analysis.json

Fichier JSON généré à chaque analyse contenant:

```json
{
  "timestamp": "2025-01-25T10:30:00",
  "analysis": {
    "total_trades": 15,
    "win_rate": 66.67,
    "avg_profit_percent": 12.5,
    "avg_loss_percent": 18.2,
    "trades_per_day": 2.5,
    "objectives": {
      "win_rate": {"target": 70, "current": 66.67, "met": false},
      "avg_profit": {"target": 15, "current": 12.5, "met": false},
      "avg_loss": {"target": 15, "current": 18.2, "met": false},
      "trades_per_day": {"target": 3, "current": 2.5, "met": false}
    },
    "exit_reasons": {
      "stop_loss": 3,
      "trailing_stop": 5,
      "stagnation_exit": 2
    }
  },
  "losing_patterns": {
    "total_losers": 5,
    "avg_duration_hours": 6.2,
    "worst_trades": [...]
  },
  "suggestions": [
    "Win-rate à 66.67% (cible: 70%) - Renforcer critères d'entrée...",
    "Profit moyen à 12.5% (cible: 15%) - Optimiser trailing stops..."
  ]
}
```

---

## 🎓 Règles d'Optimisation

### ✅ Paramètres Modifiables

#### Critères d'Entrée
- `MIN_TOKEN_AGE_HOURS` / `MAX_TOKEN_AGE_HOURS`
- `MIN_LIQUIDITY_USD` / `MAX_LIQUIDITY_USD`
- `MIN_VOLUME_24H_USD`
- `MIN_HOLDERS`
- `MIN_MARKET_CAP_USD` / `MAX_MARKET_CAP_USD`
- `MAX_BUY_TAX` / `MAX_SELL_TAX`
- `MIN_SAFETY_SCORE` / `MIN_POTENTIAL_SCORE`

#### Critères de Sortie
- `STOP_LOSS_PERCENT`
- `TRAILING_ACTIVATION_PERCENT`
- `TRAILING_DISTANCE_LEVEL1/2/3/4`
- `GRACE_PERIOD_MINUTES` / `GRACE_PERIOD_STOP_LOSS`
- `STAGNATION_EXIT_HOURS` / `STAGNATION_THRESHOLD_PERCENT`
- `LOW_MOMENTUM_EXIT_HOURS` / `LOW_MOMENTUM_THRESHOLD_PERCENT`
- `MAX_TIME_EXIT_HOURS`

### ❌ Paramètres NON Modifiables

- `POSITION_SIZE_PERCENT` = 15% (fixé)
- `MAX_POSITIONS` = 3 (fixé)
- Honeypot checker (toujours actif)
- Objectif de 3 trades/jour (immuable)

---

## 🔧 FAQ

### Q: Combien de trades faut-il avant d'optimiser?

**R:** Minimum 5 trades fermés. L'idéal est 10-20 trades pour avoir des statistiques fiables.

### Q: Que faire si les services VPS sont inactifs?

**R:** Le script vous demandera si vous voulez les redémarrer. Répondez `y` pour redémarrer automatiquement.

### Q: Puis-je lancer plusieurs optimisations en parallèle?

**R:** Non recommandé. Attendez que les modifications d'une itération soient testées (5+ trades) avant de relancer.

### Q: Comment annuler une modification?

**R:**
1. Dans GitHub, fermez la PR
2. Checkout la branche main: `git checkout main`
3. Supprimez la branche: `git branch -D claude-auto-improve-YYYYMMDD-HHMM`
4. Sur le VPS, re-checkout main: `ssh root@VPS_IP "cd /home/basebot/trading-bot && git checkout main"`

### Q: Le bot ne trouve pas assez de tokens (trades/jour < 3)?

**R:** Claude peut assouplir les critères:
- Réduire `MIN_HOLDERS`, `MIN_LIQUIDITY_USD`
- Élargir la fenêtre d'âge (`MIN_TOKEN_AGE_HOURS`, `MAX_TOKEN_AGE_HOURS`)
- Réduire `MIN_SAFETY_SCORE`, `MIN_POTENTIAL_SCORE`

### Q: Trop de pertes (win-rate < 70%)?

**R:** Claude peut renforcer les critères:
- Augmenter `MIN_HOLDERS`, `MIN_SAFETY_SCORE`
- Réduire `STOP_LOSS_PERCENT` (sortir plus tôt)
- Réduire `GRACE_PERIOD_STOP_LOSS` (limiter les grosses pertes initiales)

### Q: Les profits sont trop petits (profit moyen < 15%)?

**R:** Claude peut optimiser les sorties:
- Augmenter `TRAILING_ACTIVATION_PERCENT` (laisser plus de marge)
- Réduire les `TRAILING_DISTANCE` pour les niveaux élevés (serrer moins)
- Allonger les timeouts pour laisser plus de temps aux positions

### Q: Peut-on tester une stratégie sans déployer sur le VPS?

**R:** Oui! Après avoir modifié `config/.env`, vous pouvez:
1. Faire un commit local (sans push)
2. Attendre quelques jours
3. Re-lancer `./claude_auto_improve.sh` pour analyser
4. Si les résultats sont bons → déployer, sinon → rollback

### Q: Comment voir l'historique complet des modifications?

**R:** Lisez [auto_improvement_history.md](auto_improvement_history.md). C'est la bible du système.

### Q: Puis-je modifier manuellement les paramètres?

**R:** Oui, mais **documentez** toujours vos modifications dans `auto_improvement_history.md` pour que Claude puisse en tenir compte.

---

## 🚨 Troubleshooting

### Erreur: "sshpass command not found"

```bash
brew install sshpass
```

### Erreur: "Permission denied (publickey)"

Vérifiez que `vps_credentials.conf` contient le bon mot de passe.

### Erreur: "gh command not found"

Installez GitHub CLI:
```bash
brew install gh
gh auth login
```

Ou créez les PR manuellement via l'interface GitHub.

### Le script se bloque pendant le téléchargement des logs

Les logs sont volumineux (500MB+). C'est normal. Attendez quelques minutes.

### Les services VPS redémarrent mais restent inactifs

Connectez-vous au VPS et vérifiez les logs:
```bash
ssh root@46.62.194.176
journalctl -u basebot-trader -n 50
```

---

## 📞 Support

- **Documentation projet**: Voir les autres fichiers `.md` dans le dossier BaseBot
- **Historique des optimisations**: [auto_improvement_history.md](auto_improvement_history.md)
- **Logs du bot**: `temp_vps_data/*.log` (après exécution du script)
- **Analyse détaillée**: `data/performance_analysis.json`

---

**Version**: 1.0.0
**Dernière mise à jour**: 2025-01-25
**Auteur**: Claude Auto-Optimizer System
