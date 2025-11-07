# Fix de l'erreur Trader

## Problème rencontré

```
ERROR - Erreur recuperation token: no such column: exit_time
```

## Cause du problème

Deux problèmes d'incohérence de schéma :

1. **Colonne `exit_time` manquante** : Le Trader cherche `exit_time` dans `trade_history` mais la table n'avait pas cette colonne
2. **Colonne `address` vs `token_address`** : Le Trader utilisait `at.address` mais la table `approved_tokens` utilise `token_address`

## Solution appliquée

### 1. Ajout des colonnes dans trade_history

**Fichier**: [src/init_database.py](src/init_database.py:86-102)

Ajout de `entry_time` et `exit_time` pour tracker les positions ouvertes/fermées :

```python
CREATE TABLE IF NOT EXISTS trade_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT NOT NULL,
    symbol TEXT,
    side TEXT,
    amount_in REAL,
    amount_out REAL,
    price REAL,
    gas_used REAL,
    profit_loss REAL,
    entry_time TIMESTAMP,      # Nouveau: quand la position est ouverte
    exit_time TIMESTAMP,       # Nouveau: quand la position est fermée
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### 2. Correction des requêtes SQL dans Trader.py

**Fichier**: [src/Trader.py](src/Trader.py:269-280)

Harmonisation des noms de colonnes :

```python
# AVANT
SELECT at.address, at.symbol, at.name, at.decimals,
       at.liquidity_usd, at.volume_24h, at.holders, at.risk_score,
       dt.price_usd
FROM approved_tokens at
LEFT JOIN discovered_tokens dt ON at.address = dt.address
WHERE at.address NOT IN (...)

# APRÈS
SELECT at.token_address, at.symbol, at.name, at.score,
       dt.liquidity, dt.market_cap, dt.price_usd
FROM approved_tokens at
LEFT JOIN discovered_tokens dt ON at.token_address = dt.token_address
WHERE at.token_address NOT IN (...)
```

### 3. Mise à jour du script de migration

**Fichier**: [migrate_database.py](migrate_database.py:160-207)

Ajout de la migration pour `trade_history` :

```python
# Vérifier trade_history
cursor.execute("PRAGMA table_info(trade_history)")
columns = {col[1] for col in cursor.fetchall()}

if 'exit_time' not in columns:
    # Créer nouvelle table avec entry_time et exit_time
    # Copier les données existantes
    # Pour les BUY: entry_time = timestamp, exit_time = NULL
    # Pour les SELL: entry_time = NULL, exit_time = timestamp
```

## Schéma de la table trade_history

Après le fix :

```
trade_history
├── id (INTEGER PRIMARY KEY)
├── token_address (TEXT)
├── symbol (TEXT)
├── side (TEXT) - 'BUY' ou 'SELL'
├── amount_in (REAL) - Montant en ETH pour BUY
├── amount_out (REAL) - Montant en tokens pour SELL
├── price (REAL)
├── gas_used (REAL)
├── profit_loss (REAL)
├── entry_time (TIMESTAMP) - Quand position ouverte (BUY)
├── exit_time (TIMESTAMP) - Quand position fermée (SELL)
└── timestamp (TIMESTAMP)

Index:
- idx_trade_history_token ON token_address
- idx_trade_history_exit ON exit_time
```

### Usage des colonnes

```sql
-- Positions actuellement ouvertes (non fermées)
SELECT * FROM trade_history WHERE exit_time IS NULL AND side = 'BUY'

-- Positions fermées
SELECT * FROM trade_history WHERE exit_time IS NOT NULL

-- Historique complet d'un token
SELECT * FROM trade_history WHERE token_address = '0x...' ORDER BY timestamp
```

## Déploiement du fix

### Sur VPS existant

```bash
# Arrêter les services
systemctl stop basebot-trader basebot-scanner basebot-filter

# Mettre à jour le code
su - basebot -c "cd /home/basebot/trading-bot && git pull"

# Migrer la base de données
su - basebot -c "cd /home/basebot/trading-bot && source venv/bin/activate && python migrate_database.py"

# Redémarrer les services
systemctl start basebot-scanner basebot-filter basebot-trader

# Vérifier les logs
journalctl -u basebot-trader -f
```

### Nouveau déploiement

```bash
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
```

### Installation locale

```bash
# Sauvegarder
cp data/trading.db data/trading.db.backup

# Migrer
python migrate_database.py

# Ou réinitialiser (perd les données)
rm data/trading.db
python src/init_database.py
```

## Vérification

### 1. Vérifier le schéma

```bash
sqlite3 data/trading.db "PRAGMA table_info(trade_history);"
```

Doit afficher les colonnes `entry_time` et `exit_time`.

### 2. Vérifier les logs du Trader

```bash
journalctl -u basebot-trader -n 50
```

Doit afficher :
```
INFO - Trader démarré en mode: paper
INFO - Configuration chargée
INFO - Récupération du prochain token à trader...
```

Sans l'erreur `no such column: exit_time`.

### 3. Tester manuellement

```bash
source venv/bin/activate
python src/Trader.py
```

## Impact du fix

### Tables modifiées

- ✅ **trade_history** : Ajout `entry_time`, `exit_time`
- ✅ **Index** : Ajout index sur `exit_time`

### Fichiers modifiés

- ✅ [src/Trader.py](src/Trader.py:269-280) - Correction requêtes SQL
- ✅ [src/init_database.py](src/init_database.py:86-102) - Ajout colonnes
- ✅ [migrate_database.py](migrate_database.py:160-207) - Migration automatique

### Compatibilité

- ✅ **Données existantes** : Préservées et migrées automatiquement
- ✅ **Scanner** : Non affecté
- ✅ **Filter** : Non affecté
- ✅ **Dashboard** : Peut nécessiter adaptation pour afficher entry_time/exit_time

## Logique de trading

Avec le nouveau schéma, le Trader peut :

1. **Ouvrir une position (BUY)** :
   ```sql
   INSERT INTO trade_history
   (token_address, side, amount_in, price, entry_time)
   VALUES (?, 'BUY', ?, ?, CURRENT_TIMESTAMP)
   ```

2. **Fermer une position (SELL)** :
   ```sql
   UPDATE trade_history
   SET exit_time = CURRENT_TIMESTAMP,
       amount_out = ?,
       profit_loss = ?
   WHERE token_address = ? AND exit_time IS NULL
   ```

3. **Trouver positions ouvertes** :
   ```sql
   SELECT * FROM trade_history
   WHERE exit_time IS NULL
   ORDER BY entry_time DESC
   ```

## Tests

Script de test complet :

```bash
# Test du schéma
sqlite3 data/trading.db << EOF
.schema trade_history
SELECT * FROM trade_history LIMIT 5;
EOF

# Test du Trader
python src/Trader.py --test  # Si mode test existe
```

## Support

Si le problème persiste :

1. Vérifier les logs : `journalctl -u basebot-trader -f`
2. Vérifier le schéma : `sqlite3 data/trading.db ".schema trade_history"`
3. Réinitialiser : `python src/init_database.py`
4. Contacter le support avec les logs

---

**Date du fix** : 2025-11-06
**Version** : 1.0.3
**Modules affectés** : Trader ✅ | trade_history ✅
