# 📁 Plan de Réorganisation - Structure Professionnelle

**Date**: 2025-12-02
**Objectif**: Nettoyer et organiser l'arborescence du projet

---

## 🎯 Diagnostic

### ❌ Problèmes Identifiés

1. **Doublon Scanner.py**
   - `/Scanner.py` (15K, 28 nov) - OBSOLÈTE
   - `/src/Scanner.py` (22K, 1er déc) - ACTIF ✅

2. **Scripts éparpillés**
   - `/activate.sh`, `/deploy.sh`, `/test_deploy.sh` à la racine
   - Devrait être dans `/scripts/`

3. **Fichiers de test/debug à la racine**
   - `/auto_strategy_optimizer.py`
   - `/pair_event_window_scanner.py`
   - `/test_filter.py`
   - Devrait être dans `/tools/` ou `/tests/`

4. **Scripts maintenance multiples**
   - `/maintenance_safe.sh`
   - `/setup_all_cron.sh`
   - `/claude_auto_improve.sh`
   - Devrait être dans `/tools/` ou `/scripts/`

5. **Rapports markdown à la racine**
   - `AJUSTEMENT_SCANNER_3-8H.md`
   - `CLEANUP_PLAN.md`
   - `RESTRUCTURATION_FINALE.md`
   - `VERIFICATION_SCANNER_FILTER.md`
   - Devrait être dans `/docs/reports/`

---

## ✅ Structure Cible Professionnelle

```
BaseBot/
├── .claude/                    # Configuration Claude Code
│   └── commands/
│       └── auto-improve.md
│
├── config/                     # Configuration
│   ├── .env                    # Config production (non commitée)
│   └── .env.example           # Template configuration
│
├── src/                        # Code source principal
│   ├── Scanner.py             # Scanner on-chain (ACTIF)
│   ├── Filter.py              # Filtre de sélection
│   ├── Trader.py              # Trader
│   ├── Dashboard.py           # Dashboard web
│   ├── web3_utils.py          # Utilitaires Web3/DexScreener
│   ├── config_manager.py      # Gestionnaire config
│   ├── honeypot_checker.py    # Vérification honeypot
│   └── init_database.py       # Initialisation DB
│
├── scripts/                    # Scripts déploiement/admin
│   ├── deploy.sh              # Déploiement principal
│   ├── deploy_onchain_scanner.sh
│   ├── start_all_services.sh
│   ├── stop_all_services.sh
│   ├── status.sh
│   ├── activate.sh            # (déplacé depuis racine)
│   └── test_pair_scanner.py
│
├── tools/                      # Outils maintenance/debug
│   ├── diagnose_scanner.sh
│   ├── maintenance_monthly.sh
│   ├── maintenance_safe.sh    # (déplacé depuis racine)
│   ├── quick_fix.sh
│   ├── test_honeypot.py
│   ├── verify_deployment.sh
│   ├── verify_honeypot_fix.sh
│   ├── watchdog.py
│   ├── setup_all_cron.sh      # (déplacé depuis racine)
│   └── claude_auto_improve.sh # (déplacé depuis racine)
│
├── tests/                      # Tests et expérimentations
│   ├── test_filter.py         # (déplacé depuis racine)
│   ├── auto_strategy_optimizer.py  # (déplacé depuis racine)
│   └── pair_event_window_scanner.py  # (déplacé depuis racine)
│
├── docs/                       # Documentation
│   ├── reports/               # Rapports d'analyse
│   │   ├── AJUSTEMENT_SCANNER_3-8H.md
│   │   ├── VERIFICATION_SCANNER_FILTER.md
│   │   └── REORGANISATION_STRUCTURE.md (ce fichier)
│   │
│   ├── deployment/            # Docs déploiement
│   │   ├── DATABASE_RESET_MOD5.md
│   │   ├── DEPLOYMENT_MOD5_ONCHAIN_SCANNER.md
│   │   └── ONCHAIN_SCANNER_DEPLOYMENT.md
│   │
│   └── archive/               # Archives historiques
│       ├── ANALYSIS_24H_MOD2.md
│       ├── ANALYSIS_MOD3_FAILURE.md
│       ├── ANALYSIS_MOD4_ISSUE.md
│       ├── CLEANUP_PLAN.md    # (déplacé depuis racine)
│       └── RESTRUCTURATION_FINALE.md  # (déplacé depuis racine)
│
├── data/                       # Données (non commité)
│   ├── trading.db
│   └── backups/
│
├── logs/                       # Logs (non commité)
│   ├── scanner.log
│   ├── filter.log
│   ├── trader.log
│   └── dashboard.log
│
├── .gitignore
├── README.md                   # Documentation principale
└── requirements.txt            # Dépendances Python

```

---

## 🔄 Actions à Réaliser

### 1. Supprimer Obsolètes
```bash
rm -f Scanner.py                # Doublon obsolète
rm -f deploy.sh                 # Doublon (existe dans scripts/)
rm -f test_deploy.sh           # Script de test obsolète
```

### 2. Déplacer vers scripts/
```bash
mv activate.sh scripts/
```

### 3. Déplacer vers tools/
```bash
mv maintenance_safe.sh tools/
mv setup_all_cron.sh tools/
mv claude_auto_improve.sh tools/
```

### 4. Déplacer vers tests/
```bash
mkdir -p tests
mv test_filter.py tests/
mv auto_strategy_optimizer.py tests/
mv pair_event_window_scanner.py tests/
```

### 5. Réorganiser Documentation
```bash
mkdir -p docs/reports docs/deployment
mv AJUSTEMENT_SCANNER_3-8H.md docs/reports/
mv VERIFICATION_SCANNER_FILTER.md docs/reports/
mv CLEANUP_PLAN.md docs/archive/
mv RESTRUCTURATION_FINALE.md docs/archive/
mv docs/DATABASE_RESET_MOD5.md docs/deployment/
mv docs/DEPLOYMENT_MOD5_ONCHAIN_SCANNER.md docs/deployment/
mv docs/ONCHAIN_SCANNER_DEPLOYMENT.md docs/deployment/
```

---

## 📊 Résultat Attendu

### Avant (Racine encombrée)
- 25 fichiers à la racine
- Structure confuse
- Doublons

### Après (Structure claire)
- 4 fichiers à la racine (README, .gitignore, requirements.txt, ce rapport)
- Tous les fichiers organisés par catégorie
- Pas de doublons
- Navigation facile

---

## ✅ Validation

- [ ] Tous les doublons supprimés
- [ ] Scripts déplacés dans /scripts/ ou /tools/
- [ ] Tests déplacés dans /tests/
- [ ] Documentation organisée dans /docs/
- [ ] Structure testée (services démarrent)
- [ ] Git commit avec message clair
- [ ] Déploiement VPS vérifié

