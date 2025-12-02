# 📁 Structure du Projet BaseBot

**Date**: 2025-12-02
**Version**: Après réorganisation professionnelle

---

## 📂 Arborescence

```
BaseBot/
│
├── 📄 README.md                  # Documentation principale du projet
├── 📄 requirements.txt           # Dépendances Python
├── 🔧 deploy.sh                 # Script de déploiement principal (VPS)
├── 🔧 test_deploy.sh            # Script de test déploiement
│
├── 📁 src/                      # 💻 CODE SOURCE PRINCIPAL
│   ├── Scanner.py               # Scanner on-chain (événements PairCreated)
│   ├── Filter.py                # Filtre de sélection tokens
│   ├── Trader.py                # Gestionnaire de trading
│   ├── Dashboard.py             # Dashboard web (port 3000)
│   ├── web3_utils.py            # Utilitaires Web3 + DexScreener API
│   ├── config_manager.py        # Gestionnaire configuration
│   ├── honeypot_checker.py      # Vérification honeypot
│   └── init_database.py         # Initialisation base de données
│
├── 📁 config/                   # ⚙️ CONFIGURATION
│   ├── .env                     # Configuration production (NON commité)
│   └── .env.example            # Template configuration
│
├── 📁 scripts/                  # 🚀 SCRIPTS DÉPLOIEMENT/ADMIN
│   ├── deploy.sh                # Déploiement complet
│   ├── deploy_onchain_scanner.sh
│   ├── start_all_services.sh
│   ├── stop_all_services.sh
│   ├── status.sh
│   ├── activate.sh              # Activation environnement virtuel
│   └── test_pair_scanner.py
│
├── 📁 tools/                    # 🔧 OUTILS MAINTENANCE/DEBUG
│   ├── diagnose_scanner.sh
│   ├── maintenance_monthly.sh
│   ├── maintenance_safe.sh
│   ├── quick_fix.sh
│   ├── test_honeypot.py
│   ├── verify_deployment.sh
│   ├── verify_honeypot_fix.sh
│   ├── watchdog.py
│   ├── setup_all_cron.sh
│   └── claude_auto_improve.sh
│
├── 📁 tests/                    # 🧪 TESTS ET EXPÉRIMENTATIONS
│   ├── test_filter.py
│   ├── auto_strategy_optimizer.py
│   └── pair_event_window_scanner.py
│
├── 📁 docs/                     # 📚 DOCUMENTATION
│   ├── reports/                 # Rapports d'analyse
│   │   ├── AJUSTEMENT_SCANNER_3-8H.md
│   │   ├── VERIFICATION_SCANNER_FILTER.md
│   │   └── REORGANISATION_STRUCTURE.md
│   │
│   ├── deployment/              # Documentation déploiement
│   │   ├── DATABASE_RESET_MOD5.md
│   │   ├── DEPLOYMENT_MOD5_ONCHAIN_SCANNER.md
│   │   └── ONCHAIN_SCANNER_DEPLOYMENT.md
│   │
│   └── archive/                 # Archives historiques
│       ├── modifications/
│       ├── fixes/
│       ├── deployments/
│       └── old_docs/
│
├── 📁 data/                     # 💾 DONNÉES (NON commité)
│   ├── trading.db
│   └── backups/
│
└── 📁 logs/                     # 📝 LOGS (NON commité)
    ├── scanner.log
    ├── filter.log
    ├── trader.log
    └── dashboard.log
```

---

## 🎯 Organisation par Fonction

### 💻 Développement
- **Code source** : `/src/`
- **Tests** : `/tests/`
- **Configuration** : `/config/`

### 🚀 Déploiement
- **Scripts déploiement** : `/scripts/`
- **Docs déploiement** : `/docs/deployment/`
- **Déploiement principal** : `deploy.sh` (racine)

### 🔧 Maintenance
- **Outils** : `/tools/`
- **Logs** : `/logs/`

### 📚 Documentation
- **Rapports** : `/docs/reports/`
- **Déploiement** : `/docs/deployment/`
- **Archives** : `/docs/archive/`

---

## 🔑 Fichiers Clés

| Fichier | Description | Localisation |
|---------|-------------|--------------|
| **Scanner.py** | Scanner on-chain (événements PairCreated) | `src/` |
| **Filter.py** | Filtre Momentum Safe | `src/` |
| **Trader.py** | Gestionnaire trading + positions | `src/` |
| **web3_utils.py** | API DexScreener + Web3 | `src/` |
| **deploy.sh** | Déploiement VPS principal | racine |
| **.env.example** | Template configuration | `config/` |

---

## 📊 Services Systemd (VPS)

```bash
basebot-scanner   # src/Scanner.py
basebot-filter    # src/Filter.py
basebot-trader    # src/Trader.py
basebot-dashboard # src/Dashboard.py (port 3000)
```

**Commandes** :
```bash
systemctl status basebot-scanner
systemctl restart basebot-filter
journalctl -u basebot-trader -f
```

---

## 🚀 Démarrage Rapide

### Développement Local
```bash
# Activer environnement virtuel
source scripts/activate.sh

# Lancer Scanner
python src/Scanner.py

# Lancer Filter
python src/Filter.py
```

### Déploiement VPS
```bash
# Déploiement complet
./deploy.sh

# Test déploiement
./test_deploy.sh

# Vérifier services
bash scripts/status.sh
```

---

## 📝 Notes

- **`.env`** : NON commité (contient clés privées)
- **`data/`** : NON commité (base de données)
- **`logs/`** : NON commité (fichiers de logs)
- **`deploy.sh`** : Conservé à la racine pour facilité d'utilisation
- **Doublon Scanner.py** : Supprimé (seul `src/Scanner.py` est valide)

---

**Dernière mise à jour** : 2025-12-02
**Commit** : `1cc54d2` - "🗂️ Réorganisation structure projet"
