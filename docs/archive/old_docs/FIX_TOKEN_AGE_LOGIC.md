# 🔧 FIX CRITIQUE: Logique de l'âge des tokens

## 🔴 PROBLÈME IDENTIFIÉ

**Date:** 2025-11-18
**Gravité:** 🔴 CRITIQUE
**Impact:** Le filtrage MIN_AGE_HOURS ne fonctionne PAS correctement

### 🔍 Analyse du Problème

**Configuration actuelle:**
```bash
MIN_AGE_HOURS=2  # Tokens doivent avoir >2h
```

**Comportement attendu:**
- Scanner découvre des tokens récents (0-24h d'âge réel)
- Filter rejette ceux avec <2h d'âge sur la blockchain
- Filter approuve ceux avec >2h d'âge sur la blockchain

**Comportement RÉEL (BUG):**
1. Scanner enregistre `created_at` = **timestamp de découverte** (maintenant)
2. Filter vérifie `created_at` vs MIN_AGE_HOURS
3. **Tous les tokens ont <5 minutes d'âge dans la DB**
4. Aucun token ne passe le filtre MIN_AGE_HOURS

---

## 📊 Code Actuel Problématique

### **1. Base de données - Schema**

```sql
CREATE TABLE discovered_tokens (
    ...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- ❌ Date d'insertion, pas date de création du token!
)
```

### **2. Scanner - Insertion**

```python
# Ligne 241-245 src/Scanner.py
cursor.execute('''
    INSERT OR IGNORE INTO discovered_tokens
    (token_address, symbol, name, decimals, total_supply, liquidity, market_cap, volume_24h, price_usd, price_eth)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (...))
# ❌ Pas de created_at fourni → Utilise DEFAULT CURRENT_TIMESTAMP
```

### **3. DexScreener API - Parse Pair Data**

```python
# Ligne 391-416 src/web3_utils.py
def _parse_pair_data(self, pair: Dict) -> Dict:
    return {
        'price_usd': ...,
        'liquidity_usd': ...,
        # ❌ 'pairCreatedAt' n'est PAS retourné !
    }
```

**L'API DexScreener retourne bien `pairCreatedAt`**, mais on ne le parse pas!

### **4. Filter - Vérification âge**

```python
# Ligne 256-277 src/Filter.py
created_at = token_data.get('created_at')  # ❌ Date de découverte, pas de création
if created_at:
    age_hours = (datetime.now(timezone.utc) - token_creation_date).total_seconds() / 3600
    if age_hours >= self.min_age_hours:  # ❌ Toujours False (age < 5 min)
        score += 10
```

---

## ✅ SOLUTION COMPLÈTE

### **Étape 1: Ajouter `pairCreatedAt` dans DexScreener**

**Fichier:** `src/web3_utils.py` ligne ~391-416

```python
def _parse_pair_data(self, pair: Dict) -> Dict:
    """Parse les donnees d'une paire avec validation"""
    try:
        return {
            'price_usd': float(pair.get('priceUsd', 0)),
            'price_native': float(pair.get('priceNative', 0)),
            'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0)),
            'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
            'volume_1h': float(pair.get('volume', {}).get('h1', 0)),
            'price_change_1h': float(pair.get('priceChange', {}).get('h1', 0)),
            'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)),
            'txns_24h': (pair.get('txns', {}).get('h24', {}).get('buys', 0) +
                       pair.get('txns', {}).get('h24', {}).get('sells', 0)),
            'txns': {
                'buys': pair.get('txns', {}).get('h24', {}).get('buys', 0),
                'sells': pair.get('txns', {}).get('h24', {}).get('sells', 0)
            },
            'fdv': float(pair.get('fdv', 0)),
            'market_cap': float(pair.get('marketCap', 0)),
            'pair_address': pair.get('pairAddress'),
            'dex_id': pair.get('dexId'),
            'chain_id': pair.get('chainId'),
            'pairCreatedAt': pair.get('pairCreatedAt')  # ✅ AJOUTER CETTE LIGNE
        }
    except Exception as e:
        print(f"Erreur parsing pair data: {e}")
        return {}
```

### **Étape 2: Modifier le schema de la DB**

**Fichier:** `src/Scanner.py` ligne ~86-90

```python
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
        volume_24h REAL,                              # ✅ Déjà ajouté
        pair_created_at TIMESTAMP,                    # ✅ AJOUTER: Date création blockchain
        discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  # ✅ RENOMMER: Date découverte
    )
''')
```

### **Étape 3: Modifier le Scanner pour enregistrer pair_created_at**

**Fichier:** `src/Scanner.py` ligne ~226-245

```python
# Récupérer les données de DexScreener
pair_data = self.dexscreener.get_token_info(token_address)

# Extraire les infos pertinentes
symbol = token_details.get('symbol', 'UNKNOWN')
name = token_details.get('name', 'Unknown Token')
decimals = token_details.get('decimals', 18)
total_supply = str(token_details.get('total_supply', 0))
price_usd = pair_data.get('price_usd') if pair_data else None
price_eth = pair_data.get('price_native') if pair_data else None
liquidity = pair_data.get('liquidity_usd', 0) if pair_data else 0
market_cap = pair_data.get('market_cap', 0) if pair_data else 0
volume_24h = pair_data.get('volume_24h', 0) if pair_data else 0
pair_created_at = pair_data.get('pairCreatedAt') if pair_data else None  # ✅ AJOUTER

# Convertir timestamp milliseconds en datetime
pair_created_at_str = None
if pair_created_at:
    from datetime import datetime
    try:
        dt = datetime.fromtimestamp(pair_created_at / 1000)
        pair_created_at_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        pass

# Insérer dans la base de données
cursor.execute('''
    INSERT OR IGNORE INTO discovered_tokens
    (token_address, symbol, name, decimals, total_supply, liquidity, market_cap, volume_24h, price_usd, price_eth, pair_created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (token_address, symbol, name, decimals, total_supply, liquidity, market_cap, volume_24h, price_usd, price_eth, pair_created_at_str))  # ✅ AJOUTER pair_created_at
```

### **Étape 4: Modifier le Filter pour utiliser pair_created_at**

**Fichier:** `src/Filter.py` ligne ~256-277

```python
# Age (si disponible) - Doit avoir AU MOINS min_age_hours
pair_created_at = token_data.get('pair_created_at')  # ✅ CHANGER: pair_created_at au lieu de created_at
if pair_created_at:
    try:
        from datetime import timezone
        # Parser le format "2025-11-09 11:51:36"
        if 'T' in pair_created_at:
            # Format ISO avec T
            token_creation_date = datetime.fromisoformat(pair_created_at.replace('Z', '+00:00'))
        else:
            # Format "YYYY-MM-DD HH:MM:SS"
            token_creation_date = datetime.strptime(pair_created_at, '%Y-%m-%d %H:%M:%S')
            token_creation_date = token_creation_date.replace(tzinfo=timezone.utc)

        age_hours = (datetime.now(timezone.utc) - token_creation_date).total_seconds() / 3600

        if age_hours >= self.min_age_hours:
            score += 10
            reasons.append(f"Age ({age_hours:.1f}h) >= min ({self.min_age_hours}h)")
        else:
            reasons.append(f"Age ({age_hours:.1f}h) < min ({self.min_age_hours}h)")  # ✅ Pas de rejet auto, juste pas de points
    except Exception as e:
        reasons.append(f"Age non vérifié (erreur: {str(e)[:50]})")
```

---

## 🧪 MIGRATION DE LA BASE DE DONNÉES

La colonne `pair_created_at` n'existe pas dans la DB actuelle. Il faut migrer:

**Créer:** `migrate_add_pair_created_at.py`

```python
#!/usr/bin/env python3
"""
Migration: Ajouter colonne pair_created_at à discovered_tokens
"""
import sqlite3
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / 'data' / 'trading.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Vérifier si la colonne existe déjà
        cursor.execute("PRAGMA table_info(discovered_tokens)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'pair_created_at' not in columns:
            print("Ajout de la colonne pair_created_at...")
            cursor.execute('''
                ALTER TABLE discovered_tokens
                ADD COLUMN pair_created_at TIMESTAMP
            ''')
            conn.commit()
            print("✅ Colonne pair_created_at ajoutée")
        else:
            print("ℹ️  Colonne pair_created_at existe déjà")

        # Renommer created_at en discovered_at (si possible)
        if 'created_at' in columns and 'discovered_at' not in columns:
            print("Note: SQLite ne supporte pas ALTER COLUMN RENAME directement")
            print("La colonne 'created_at' reste inchangée pour compatibilité")
            print("Les nouveaux inserts utiliseront 'pair_created_at'")

    except Exception as e:
        print(f"❌ Erreur migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
```

**Exécuter:**
```bash
python3 migrate_add_pair_created_at.py
```

---

## ⚠️ IMPACT ET COMPROMIS

### **Tokens déjà dans la DB**

Les tokens découverts AVANT cette migration n'auront **PAS** de `pair_created_at`.

**Solution:** Ils n'auront pas le bonus +10 pts pour l'âge, mais pourront quand même être approuvés si score >70.

### **MIN_AGE_HOURS = 2h**

Avec MIN_AGE_HOURS=2h:
- Scanner découvre tokens récents (0-24h)
- ~70-80% des tokens ont <2h d'âge
- Ces tokens n'auront pas le bonus +10 pts

**Options:**

1. **Réduire MIN_AGE_HOURS à 0.5h** (30 minutes)
   - Plus de tokens passent
   - Risque légèrement accru (moins de temps pour détecter honeypots)

2. **Garder MIN_AGE_HOURS=2h**
   - Moins de tokens passent
   - Meilleure qualité (tokens avec historique)
   - Score max sans âge: 100 pts (toujours >70 seuil)

**Recommandation:** Garder MIN_AGE_HOURS=2h pour la qualité

---

## 📊 Impact sur le Scoring

| Token | Age réel | Ancien (bug) | Nouveau (fix) | Delta |
|-------|----------|--------------|---------------|-------|
| Token A | 5h | 5min (découverte) | 5h (blockchain) | ✅ +10 pts |
| Token B | 1h | 3min (découverte) | 1h (blockchain) | = 0 pts (mais correct!) |
| Token C | 30min | 2min (découverte) | 30min (blockchain) | = 0 pts |

**Avant fix:** Aucun token n'avait >2h (tous rejetés ou score faible)
**Après fix:** Tokens avec >2h d'âge réel obtiennent +10 pts correctement

---

## 🚀 Plan de Déploiement

### **1. Modifier les fichiers**
- ✅ `src/web3_utils.py` - Ajouter pairCreatedAt dans _parse_pair_data
- ✅ `src/Scanner.py` - Enregistrer pair_created_at
- ✅ `src/Filter.py` - Utiliser pair_created_at au lieu de created_at
- ✅ `migrate_add_pair_created_at.py` - Script de migration DB

### **2. Tester localement**
```bash
# Valider syntaxe
python3 -m py_compile src/web3_utils.py
python3 -m py_compile src/Scanner.py
python3 -m py_compile src/Filter.py

# Migrer la DB
python3 migrate_add_pair_created_at.py
```

### **3. Commit et push**
```bash
git add -A
git commit -m "🔧 Fix token age logic: Use pair_created_at from blockchain"
git push origin main
```

### **4. Déployer sur VPS**
```bash
# Sur VPS
cd /home/basebot/trading-bot
git pull origin main

# Migrer la DB
python3 migrate_add_pair_created_at.py

# Redémarrer services
sudo systemctl restart basebot-scanner
sudo systemctl restart basebot-filter
```

### **5. Vérifier logs**
```bash
# Vérifier que pair_created_at est enregistré
sudo journalctl -u basebot-scanner -f | grep "découvert"

# Vérifier que l'âge est correctement vérifié
sudo journalctl -u basebot-filter -f | grep "Age"
```

---

## ✅ Critères de Validation

**Le fix sera validé si:**
- ✅ Scanner enregistre `pair_created_at` dans la DB
- ✅ Filter utilise `pair_created_at` pour calculer l'âge
- ✅ Tokens avec >2h d'âge réel obtiennent +10 pts
- ✅ Tokens avec <2h d'âge réel obtiennent 0 pts (pas de rejet)
- ✅ Score reste >70 pour approbation même sans bonus âge

---

## 📝 Conclusion

**Problème:** Logique de l'âge complètement cassée (utilisait date de découverte)

**Solution:** Utiliser `pairCreatedAt` de l'API DexScreener (date blockchain réelle)

**Impact:**
- Critère MIN_AGE_HOURS fonctionne correctement ✅
- Tokens récents (<2h) n'ont pas le bonus mais peuvent passer si excellents ailleurs
- Protection contre tokens trop nouveaux maintenue

**Prochaine étape:** Voulez-vous que j'applique ces modifications maintenant?

---

**Date:** 2025-11-18
**Auteur:** Claude Code
**Gravité:** 🔴 CRITIQUE
**Statut:** ⏳ Solution documentée - En attente d'application
