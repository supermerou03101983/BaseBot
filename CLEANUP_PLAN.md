# Plan de Nettoyage et Réorganisation

## Fichiers à Supprimer (Scripts temporaires et patches)

### Scripts de patch/fix temporaires (déjà appliqués)
- add_losing_tokens_cooldown.py
- add_momentum_5m_filter.py
- add_momentum_check_v2.py
- add_momentum_filter.py
- add_momentum_safe.py
- add_volume_1h_filter.py
- apply_modification_2.sh
- fix_grace_period_defaults.py
- fix_grace_period_logs.py
- fix_grace_period_reference.py
- fix_paper_prices_v2.py
- fix_paper_prices_v3.py
- integrate_onchain_scanner.py
- manual_patch_scanner.py
- patch_paper_trading_prices.py
- patch_scanner_manual.sh
- patch_scanner_onchain.py

### Scripts de diagnostic obsolètes
- analyze_results.py (remplacé par Dashboard)
- analyze_trades.py (remplacé par Dashboard)
- analyze_trades_simple.py (remplacé par Dashboard)
- diagnose_freeze.py (debug ponctuel)
- emergency_close_positions.py (urgence ponctuelle)
- fix_amount_out.py (fix appliqué)
- test_scanner.py (tests temporaires)
- test_scanner_simple.py (tests temporaires)

### Scripts de maintenance redondants
- cleanup_positions.sh (fonctionnalité dans deploy.sh)
- fix_desync_positions.sh (fix appliqué)
- sync_positions.sh (intégré)

## Documentation à Archiver (docs/)

### Rapports d'analyse dépassés
- ANALYSIS_24H_MOD2.md
- ANALYSIS_MOD3_FAILURE.md
- ANALYSIS_MOD4_ISSUE.md

### Rapports de déploiement anciens
- DEPLOYMENT_REPORT_MOD1.md
- DEPLOYMENT_MOD3.md
- DEPLOYMENT_MOD4.1_FINAL.md
- DATABASE_CLEANUP_MOD2.md
- DEPLOY_SH_UPDATE.md

### Docs de modifications anciennes
- MODIFICATION_2_REPORT.md
- MODIFICATION_3_REPORT.md
- MODIFICATION_4_REPORT.md

### Docs de fix appliqués
- FIX_REAL_PRICES_VOLUME_1H.md
- PAPER_PRICE_SIMULATION_FIX.md
- PRICE_UPDATE_VERIFICATION.md
- FIX_DESYNC_DASHBOARD.md
- FIX_VOLUME_24H_FALLBACK.md
- DEPLOYMENT_HONEYPOT_FIX.md

### Docs de déploiement multiples (garder le principal)
- AUTO_MIGRATION_DEPLOY.md
- DEPLOY_FIXES.md
- DEPLOY_GUIDE.md
- DEPLOY_SH_VERIFICATION.md
- DEPLOY_VALIDATION.md

## Nouvelle Structure Proposée

```
BaseBot/
├── README.md                          # Guide principal
├── .gitignore
├── requirements.txt
│
├── src/                               # Code source
│   ├── Scanner.py
│   ├── Filter.py
│   ├── Trader.py
│   ├── Dashboard.py
│   ├── web3_utils.py
│   └── pair_event_window_scanner.py   # Scanner on-chain
│
├── config/                            # Configuration
│   └── .env.example
│
├── scripts/                           # Scripts utilitaires
│   ├── deploy.sh                      # Déploiement VPS
│   ├── start_all_services.sh
│   ├── stop_all_services.sh
│   ├── status.sh
│   └── test_pair_scanner.py
│
├── tools/                             # Outils de maintenance
│   ├── verify_deployment.sh
│   ├── maintenance_monthly.sh
│   ├── quick_fix.sh
│   ├── diagnose_scanner.sh
│   ├── test_honeypot.py
│   └── watchdog.py
│
├── docs/                              # Documentation
│   ├── DEPLOYMENT.md                  # Guide déploiement
│   ├── CONFIGURATION.md               # Guide configuration
│   ├── ONCHAIN_SCANNER.md            # Doc scanner on-chain
│   ├── TROUBLESHOOTING.md            # Dépannage
│   │
│   └── archive/                       # Anciens rapports
│       ├── modifications/
│       ├── deployments/
│       └── fixes/
│
├── data/                              # Données (gitignored)
│   └── trading.db
│
├── logs/                              # Logs (gitignored)
│
└── backups/                           # Sauvegardes (gitignored)
```

## Fichiers à Conserver à la Racine

### Essentiels
- Scanner.py (copie pour tests locaux)
- pair_event_window_scanner.py (copie pour tests locaux)
- requirements.txt
- .gitignore

### Scripts principaux
- deploy.sh
- deploy_onchain_scanner.sh (intégré dans deploy.sh)

### Documentation principale
- README.md (à créer/mettre à jour)
- DEPLOYMENT_MOD5_ONCHAIN_SCANNER.md (guide actuel)
- DATABASE_RESET_MOD5.md (procédure reset)
- ONCHAIN_SCANNER_DEPLOYMENT.md (doc scanner)
