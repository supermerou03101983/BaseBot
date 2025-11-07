# Fix de l'erreur Filter

## Problème rencontré

```
ERROR - Erreur dans la boucle principale du filter: no such column: token_address
```

## Cause du problème

Incohérence dans les noms de colonnes entre les différents fichiers :
- **Scanner.py** et **Filter.py** utilisent `token_address`
- **init_database.py** utilisait `address`

Cette différence causait une erreur SQL lorsque le Filter essayait de lire la table `discovered_tokens`.

## Solution appliquée

### 1. Harmonisation du schéma de base de données

**Fichier**: [src/init_database.py](src/init_database.py)

Toutes les tables utilisent maintenant `token_address` de manière cohérente :

```python
# discovered_tokens
CREATE TABLE IF NOT EXISTS discovered_tokens (
    token_address TEXT UNIQUE NOT NULL,  # Avant: address
    symbol TEXT,
    name TEXT,
    ...
)

# approved_tokens
CREATE TABLE IF NOT EXISTS approved_tokens (
    token_address TEXT UNIQUE NOT NULL,  # Avant: address
    symbol TEXT,
    name TEXT,
    ...
)

# rejected_tokens
CREATE TABLE IF NOT EXISTS rejected_tokens (
    token_address TEXT UNIQUE NOT NULL,  # Avant: address
    symbol TEXT,
    name TEXT,
    ...
)
```

### 2. Ajout de la table `discovered_tokens` dans Filter

**Fichier**: [src/Filter.py](src/Filter.py:85-100)

Le Filter crée maintenant la table `discovered_tokens` lors de son initialisation si elle n'existe pas :

```python
def init_database(self):
    """Initialise la base de données si nécessaire"""
    # Table des tokens découverts (partagée avec Scanner)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS discovered_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT UNIQUE NOT NULL,
            symbol TEXT,
            name TEXT,
            decimals INTEGER,
            total_supply TEXT,
            liquidity REAL,
            market_cap REAL,
            price_usd REAL,
            price_eth REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # ... autres tables
```

### 3. Amélioration de la gestion d'erreurs

**Fichier**: [src/Filter.py](src/Filter.py:347-390)

Ajout de gestion d'erreurs robuste dans `run_filter_cycle()` :

```python
def run_filter_cycle(self):
    try:
        # Requête SQL
        cursor.execute('''
            SELECT * FROM discovered_tokens
            WHERE token_address NOT IN (...)
        ''')

        if not new_tokens:
            self.logger.info("Aucun nouveau token à filtrer")
            return

        # Traitement des tokens...

    except Exception as e:
        self.logger.error(f"Erreur lors du cycle: {e}")
        import traceback
        self.logger.error(traceback.format_exc())
    finally:
        conn.close()
```

### 4. Script de migration

**Fichier**: [migrate_database.py](migrate_database.py)

Script créé pour migrer les bases de données existantes :

```bash
python migrate_database.py
```

Ce script :
- Détecte les anciennes colonnes `address`
- Crée de nouvelles tables avec `token_address`
- Migre toutes les données
- Recrée les index optimisés

## Déploiement du fix

### Sur un VPS existant avec données

```bash
# Arrêter les services
systemctl stop basebot-scanner basebot-filter basebot-trader

# Mettre à jour le code
su - basebot -c "cd /home/basebot/trading-bot && git pull"

# Migrer la base de données
su - basebot -c "cd /home/basebot/trading-bot && source venv/bin/activate && python migrate_database.py"

# Redémarrer les services
systemctl start basebot-scanner basebot-filter basebot-trader

# Vérifier les logs
journalctl -u basebot-filter -f
```

### Sur nouveau VPS

La nouvelle installation via `deploy.sh` inclut déjà le fix :

```bash
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
```

### Sur installation locale existante

```bash
# Sauvegarder la base de données
cp data/trading.db data/trading.db.backup

# Migrer
python migrate_database.py

# Ou réinitialiser complètement (ATTENTION: perd les données)
rm data/trading.db
python src/init_database.py
```

## Vérification

### 1. Vérifier que la migration a réussi

```bash
sqlite3 data/trading.db "PRAGMA table_info(discovered_tokens);"
```

Devrait afficher une colonne `token_address` (pas `address`).

### 2. Vérifier les logs du Filter

```bash
journalctl -u basebot-filter -n 50
```

Devrait afficher :
```
INFO - Filter démarré...
INFO - Démarrage d'un cycle de filtrage...
INFO - Aucun nouveau token à filtrer pour le moment
```

Ou si des tokens sont présents :
```
INFO - X nouveau(x) token(s) à analyser
INFO - Analyse du token: SYMBOL (0x...)
```

### 3. Tester manuellement

```bash
# Activer l'environnement
source venv/bin/activate

# Tester le Filter
python src/Filter.py
```

## Structure de la base de données

Après le fix, voici la structure cohérente :

```
discovered_tokens
├── token_address (TEXT) ← Utilisé partout
├── symbol (TEXT)
├── name (TEXT)
├── liquidity (REAL)
├── market_cap (REAL)
├── price_usd (REAL)
└── created_at (TIMESTAMP)

approved_tokens
├── token_address (TEXT) ← Utilisé partout
├── symbol (TEXT)
├── name (TEXT)
├── score (REAL)
└── created_at (TIMESTAMP)

rejected_tokens
├── token_address (TEXT) ← Utilisé partout
├── symbol (TEXT)
├── name (TEXT)
├── reason (TEXT)
└── rejected_at (TIMESTAMP)
```

## Fichiers modifiés

- ✅ [src/Filter.py](src/Filter.py) - Ajout table `discovered_tokens` + gestion erreurs
- ✅ [src/init_database.py](src/init_database.py) - Harmonisation `token_address`
- ✅ [migrate_database.py](migrate_database.py) - Nouveau script de migration

## Tests

Pour tester le fix complet :

```bash
# 1. Réinitialiser la DB
rm -f data/trading.db
python src/init_database.py

# 2. Vérifier le schéma
sqlite3 data/trading.db ".schema discovered_tokens"

# 3. Tester le Filter
python src/Filter.py
```

## Prévention

Pour éviter ce type de problème à l'avenir :

1. **Schéma centralisé** : Le fichier `init_database.py` est la source de vérité
2. **Tests d'intégration** : Vérifier la compatibilité Scanner/Filter/Trader
3. **Migration systématique** : Toujours fournir un script de migration pour les changements de schéma

## Support

Si le problème persiste :

1. Vérifier les logs : `journalctl -u basebot-filter -f`
2. Vérifier le schéma : `sqlite3 data/trading.db ".schema"`
3. Réinitialiser : `rm data/trading.db && python src/init_database.py`
4. Ouvrir une issue sur GitHub avec les logs complets

---

**Date du fix** : 2025-11-06
**Version** : 1.0.2
**Impact** : Scanner ✓ | Filter ✓ | Trader ⚠ (à vérifier) | Dashboard ⚠ (à vérifier)
