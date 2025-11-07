# Résumé des corrections - Base Trading Bot

Toutes les corrections apportées pour résoudre les erreurs de base de données et d'API.

## 📋 Vue d'ensemble

| Service | Erreur | Status | Doc |
|---------|--------|--------|-----|
| Scanner | `'DexScreenerAPI' object has no attribute 'get_recent_pairs_on_chain'` | ✅ Corrigé | [FIX_SCANNER.md](FIX_SCANNER.md) |
| Filter | `no such column: token_address` | ✅ Corrigé | [FIX_FILTER.md](FIX_FILTER.md) |
| Trader | `no such column: exit_time` | ✅ Corrigé | [FIX_TRADER.md](FIX_TRADER.md) |

## 🔧 Corrections appliquées

### 1. Scanner - Méthode DexScreener manquante

**Problème** : La méthode `get_recent_pairs_on_chain()` n'existait pas dans `DexScreenerAPI`

**Solution** :
- ✅ Ajout de la méthode dans [src/web3_utils.py](src/web3_utils.py:281-331)
- ✅ Modification du Scanner pour utiliser l'API DexScreener en priorité
- ✅ Système de fallback sur la base de données locale
- ✅ Configuration du délai de scan via `SCAN_INTERVAL_SECONDS`

**Fichiers modifiés** :
- `src/web3_utils.py` - Nouvelle méthode `get_recent_pairs_on_chain()`
- `src/Scanner.py` - Refonte de `fetch_new_tokens()`

### 2. Filter - Colonne token_address manquante

**Problème** : Incohérence entre `address` et `token_address` dans les tables

**Solution** :
- ✅ Harmonisation : toutes les tables utilisent `token_address`
- ✅ Filter crée la table `discovered_tokens` s'elle n'existe pas
- ✅ Amélioration de la gestion d'erreurs avec traceback

**Fichiers modifiés** :
- `src/Filter.py` - Ajout création table + gestion erreurs
- `src/init_database.py` - Harmonisation `token_address`

### 3. Trader - Colonnes exit_time et entry_time manquantes

**Problème** : Table `trade_history` ne contenait pas les colonnes pour tracker les positions

**Solution** :
- ✅ Ajout de `entry_time` et `exit_time` dans `trade_history`
- ✅ Correction des requêtes SQL (`address` → `token_address`)
- ✅ Migration automatique des données existantes

**Fichiers modifiés** :
- `src/Trader.py` - Correction requêtes SQL
- `src/init_database.py` - Ajout colonnes

## 📦 Nouveaux fichiers

| Fichier | Description |
|---------|-------------|
| [migrate_database.py](migrate_database.py) | Script de migration automatique pour bases existantes |
| [test_scanner.py](test_scanner.py) | Tests pour vérifier le Scanner et DexScreener |
| [FIX_SCANNER.md](FIX_SCANNER.md) | Documentation détaillée du fix Scanner |
| [FIX_FILTER.md](FIX_FILTER.md) | Documentation détaillée du fix Filter |
| [FIX_TRADER.md](FIX_TRADER.md) | Documentation détaillée du fix Trader |
| [FIXES_SUMMARY.md](FIXES_SUMMARY.md) | Ce fichier - vue d'ensemble |

## 🗄️ Schéma de base de données final

### discovered_tokens
```sql
CREATE TABLE discovered_tokens (
    id INTEGER PRIMARY KEY,
    token_address TEXT UNIQUE NOT NULL,  -- ✅ Harmonisé
    symbol TEXT,
    name TEXT,
    decimals INTEGER,
    total_supply TEXT,
    liquidity REAL,
    market_cap REAL,
    price_usd REAL,
    price_eth REAL,
    created_at TIMESTAMP
)
```

### approved_tokens
```sql
CREATE TABLE approved_tokens (
    id INTEGER PRIMARY KEY,
    token_address TEXT UNIQUE NOT NULL,  -- ✅ Harmonisé
    symbol TEXT,
    name TEXT,
    reason TEXT,
    score REAL,
    analysis_data TEXT,
    created_at TIMESTAMP
)
```

### rejected_tokens
```sql
CREATE TABLE rejected_tokens (
    id INTEGER PRIMARY KEY,
    token_address TEXT UNIQUE NOT NULL,  -- ✅ Harmonisé
    symbol TEXT,
    name TEXT,
    reason TEXT,
    analysis_data TEXT,
    rejected_at TIMESTAMP
)
```

### trade_history
```sql
CREATE TABLE trade_history (
    id INTEGER PRIMARY KEY,
    token_address TEXT NOT NULL,
    symbol TEXT,
    side TEXT,
    amount_in REAL,
    amount_out REAL,
    price REAL,
    gas_used REAL,
    profit_loss REAL,
    entry_time TIMESTAMP,    -- ✅ Nouveau
    exit_time TIMESTAMP,     -- ✅ Nouveau
    timestamp TIMESTAMP
)
```

## 🚀 Déploiement complet

### Option 1 : Nouveau VPS (recommandé)

Une seule commande installe tout avec les fix :

```bash
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
```

### Option 2 : VPS existant avec données

```bash
# 1. Arrêter tous les services
systemctl stop basebot-scanner basebot-filter basebot-trader basebot-dashboard

# 2. Sauvegarder la base de données
su - basebot -c "cp /home/basebot/trading-bot/data/trading.db /home/basebot/trading-bot/backups/trading_$(date +%Y%m%d).db"

# 3. Mettre à jour le code
su - basebot -c "cd /home/basebot/trading-bot && git pull"

# 4. Activer l'environnement et migrer
su - basebot -c "cd /home/basebot/trading-bot && source venv/bin/activate && python migrate_database.py"

# 5. Redémarrer les services
systemctl start basebot-scanner
systemctl start basebot-filter
systemctl start basebot-trader
systemctl start basebot-dashboard

# 6. Vérifier les logs
journalctl -u basebot-scanner -f
journalctl -u basebot-filter -f
journalctl -u basebot-trader -f
```

### Option 3 : Installation locale

```bash
# Sauvegarder
cp data/trading.db data/trading.db.backup

# Migrer
python migrate_database.py

# Ou réinitialiser (ATTENTION: perd toutes les données)
rm data/trading.db
python src/init_database.py
```

## ✅ Vérification après déploiement

### 1. Vérifier le schéma de la base

```bash
sqlite3 data/trading.db << EOF
.schema discovered_tokens
.schema approved_tokens
.schema rejected_tokens
.schema trade_history
EOF
```

Toutes les tables doivent avoir `token_address` (pas `address`).
`trade_history` doit avoir `entry_time` et `exit_time`.

### 2. Vérifier les services

```bash
systemctl status basebot-scanner
systemctl status basebot-filter
systemctl status basebot-trader
systemctl status basebot-dashboard
```

Tous doivent être `active (running)`.

### 3. Vérifier les logs

```bash
# Scanner - doit récupérer des tokens depuis DexScreener
journalctl -u basebot-scanner -n 50

# Filter - doit analyser les tokens découverts
journalctl -u basebot-filter -n 50

# Trader - doit pouvoir récupérer les tokens approuvés
journalctl -u basebot-trader -n 50
```

Logs attendus :

**Scanner** :
```
INFO - Scanner démarré...
INFO - Récupération des nouveaux tokens depuis DexScreener...
INFO - X paires trouvées sur DexScreener
INFO - Token découvert: SYMBOL (0x...) - MC: $XXX
```

**Filter** :
```
INFO - Filter démarré...
INFO - Démarrage d'un cycle de filtrage...
INFO - X nouveau(x) token(s) à analyser
INFO - Analyse du token: SYMBOL (0x...)
```

**Trader** :
```
INFO - Trader démarré en mode: paper
INFO - Configuration chargée
INFO - Récupération du prochain token à trader...
```

### 4. Tests manuels

```bash
# Activer l'environnement
source venv/bin/activate

# Tester le Scanner
python test_scanner.py

# Tester l'initialisation
python src/init_database.py
```

## 🔄 Workflow complet après fix

```
┌─────────────────────────────────────────────────────────┐
│ 1. SCANNER                                              │
│    - Récupère paires via DexScreener API               │
│    - Enregistre dans discovered_tokens                 │
│    - Colonne: token_address ✅                          │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 2. FILTER                                               │
│    - Lit discovered_tokens                             │
│    - Analyse et score les tokens                       │
│    - Approuve → approved_tokens ✅                      │
│    - Rejette → rejected_tokens ✅                       │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 3. TRADER                                               │
│    - Lit approved_tokens avec token_address ✅          │
│    - Vérifie positions ouvertes (exit_time IS NULL) ✅  │
│    - Execute les trades                                │
│    - Enregistre dans trade_history avec entry/exit ✅   │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 4. DASHBOARD                                            │
│    - Affiche les données de toutes les tables          │
│    - Monitoring en temps réel                          │
└─────────────────────────────────────────────────────────┘
```

## 📊 Impact et bénéfices

### Avant les fix

- ❌ Scanner ne pouvait pas récupérer de nouveaux tokens
- ❌ Filter crashait au démarrage
- ❌ Trader ne pouvait pas lire les tokens approuvés
- ❌ Incohérence dans les noms de colonnes

### Après les fix

- ✅ Scanner récupère les tokens depuis DexScreener
- ✅ Filter analyse correctement les tokens
- ✅ Trader peut ouvrir et tracker les positions
- ✅ Base de données cohérente et documentée
- ✅ Migration automatique pour les installations existantes

## 🛠️ Outils de maintenance

### Script de migration

```bash
python migrate_database.py
```

Effectue automatiquement :
- Migration `address` → `token_address`
- Ajout `entry_time` et `exit_time`
- Recréation des index
- Validation du schéma

### Script de test

```bash
python test_scanner.py
```

Vérifie :
- API DexScreener fonctionne
- Méthode `get_recent_pairs_on_chain()` existe
- Scanner s'initialise correctement

### Réinitialisation complète

```bash
# ATTENTION: Perd toutes les données
rm data/trading.db
python src/init_database.py
```

## 📞 Support

En cas de problème :

1. **Vérifier les logs** :
   ```bash
   journalctl -u basebot-scanner -n 100
   journalctl -u basebot-filter -n 100
   journalctl -u basebot-trader -n 100
   ```

2. **Vérifier le schéma** :
   ```bash
   sqlite3 data/trading.db ".schema"
   ```

3. **Réexécuter la migration** :
   ```bash
   python migrate_database.py
   ```

4. **Consulter la documentation** :
   - [FIX_SCANNER.md](FIX_SCANNER.md)
   - [FIX_FILTER.md](FIX_FILTER.md)
   - [FIX_TRADER.md](FIX_TRADER.md)
   - [INSTALLATION.md](INSTALLATION.md)

5. **Ouvrir une issue** sur GitHub avec :
   - Logs complets
   - Résultat de `sqlite3 data/trading.db ".schema"`
   - Version du bot

---

**Date des fix** : 2025-11-06
**Version finale** : 1.0.3
**Statut** : ✅ Tous les services opérationnels
