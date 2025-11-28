# 🔧 FIX: Désynchronisation Dashboard "1 fichiers JSON mais 2 dans la DB"

**Date:** 2025-11-20
**Commit:** 8a229ac
**Problème:** Dashboard affiche désynchronisation positions après redémarrage Trader

---

## 🔴 PROBLÈME

**Symptôme Dashboard:**
```
⚠️ Désynchronisation: 1 fichiers JSON mais 2 dans la DB.
Redémarrez le Trader pour synchroniser.
```

**Après redémarrage Trader:**
```
Rien ne change - message persiste
```

---

## 🔍 CAUSE ROOT

Le Dashboard compare **2 sources de vérité** pour les positions actives:

1. **Fichiers JSON** (`/home/basebot/trading-bot/data/position_*.json`)
   - Créés par Trader quand position ouverte
   - Supprimés par Trader quand position fermée
   - Utilisés par Trader pour restaurer positions après crash

2. **Base de données** (`trade_history` WHERE `exit_time IS NULL`)
   - Position insérée à l'achat
   - `exit_time` = NULL tant que position ouverte
   - `exit_time` rempli à la vente

**Désynchronisation si:**
- ❌ Trader ferme position en DB mais **crash avant suppression JSON**
- ❌ Fichiers JSON supprimés manuellement mais **positions encore en DB**
- ❌ Erreur permissions → Trader ne peut pas écrire/supprimer JSON
- ❌ Trader fermé brutalement (`kill -9`) pendant transaction

---

## ✅ SOLUTION RAPIDE (1 commande)

### **Sur ton VPS:**

```bash
cd /home/basebot/trading-bot
sudo -u basebot git pull origin main
sudo bash cleanup_positions.sh
```

**Le script va:**
1. Compter fichiers JSON vs positions DB
2. **Si JSON > DB:** Supprimer JSON orphelins automatiquement
3. **Si DB > JSON:** Afficher positions + recommandations
4. Redémarrer Dashboard

**Durée:** 10 secondes

---

## 🔍 DIAGNOSTIC COMPLET (optionnel)

Si tu veux comprendre **exactement** ce qui s'est passé:

```bash
cd /home/basebot/trading-bot
sudo bash fix_desync_positions.sh
```

**Le script affiche:**
- Liste complète fichiers JSON avec contenu
- Liste positions DB avec détails (symbol, âge, montants)
- Type de désynchronisation détecté
- Causes possibles
- Actions correctives proposées (mode interactif)

---

## 📋 CAS COURANTS

### **Cas 1: Plus de JSON que DB (1 JSON, 0 DB)**

**Diagnostic:**
```
Fichiers JSON: 1
Positions DB:  0
Type: Fichiers JSON orphelins
```

**Explication:**
- Trader a vendu la position (DB: `exit_time` rempli)
- Mais JSON pas supprimé (crash/erreur I/O)

**Solution:**
```bash
# Automatique:
sudo bash cleanup_positions.sh

# OU Manuel:
rm /home/basebot/trading-bot/data/position_*.json
sudo systemctl restart basebot-dashboard
```

**Résultat:** ✅ Dashboard affichera "0 positions actives" (correct)

---

### **Cas 2: Plus de DB que JSON (0 JSON, 2 DB)**

**Diagnostic:**
```
Fichiers JSON: 0
Positions DB:  2
Type: Positions DB orphelines
```

**Explication possible #1 (positions récentes <1h):**
- Trader vient d'ouvrir positions
- JSON pas encore écrits (timing normal)

**Solution:**
```bash
# Attendre 2-3 minutes, ou:
sudo systemctl restart basebot-trader
```

**Explication possible #2 (positions anciennes >1h):**
- Fichiers JSON supprimés manuellement
- Ou Trader crashé après achat, avant écriture JSON
- Positions peut-être déjà vendues sur blockchain

**Solution (ATTENTION!):**
```bash
# 1. Vérifier positions sur BaseScan
https://basescan.org/address/0xA7bf677ecFe14E3E14a79210598Afb36B6910Ccd

# 2. Si positions vendues, fermer en DB:
sqlite3 /home/basebot/trading-bot/data/trading.db << 'EOF'
-- Lister positions orphelines
SELECT id, symbol, datetime(entry_time),
       ROUND((julianday('now') - julianday(entry_time)) * 24, 1) as hours
FROM trade_history
WHERE exit_time IS NULL;

-- Fermer position ID (remplacer 123 par vrai ID)
UPDATE trade_history
SET exit_time = datetime('now'),
    side = 'SELL',
    profit_loss = 0
WHERE id = 123;
EOF
```

---

### **Cas 3: Synchronisé mais message persiste**

**Diagnostic:**
```
Fichiers JSON: 2
Positions DB:  2
Status: SYNC
```

**Cause:** Cache Dashboard pas rafraîchi

**Solution:**
```bash
sudo systemctl restart basebot-dashboard
# Attendre 10s, puis F5 sur http://VPS_IP:8501
```

---

## 🛠️ OUTILS DISPONIBLES

### **1. cleanup_positions.sh** (Recommandé)

**Usage:**
```bash
cd /home/basebot/trading-bot
sudo bash cleanup_positions.sh
```

**Fait:**
- Détection automatique du type de désync
- Nettoyage automatique si JSON orphelins
- Recommandations si DB orphelines
- Redémarrage Dashboard

**Quand utiliser:**
- Fix rapide sans diagnostic détaillé
- Après crash/redémarrage serveur
- Message Dashboard désynchronisation

---

### **2. fix_desync_positions.sh** (Diagnostic)

**Usage:**
```bash
cd /home/basebot/trading-bot
sudo bash fix_desync_positions.sh
```

**Fait:**
- Liste fichiers JSON avec contenu complet
- Liste positions DB avec âge/montants
- Identifie cause root
- Propose actions (mode interactif)
- Affiche commandes exactes à lancer

**Quand utiliser:**
- Première fois que problème arrive
- Désync récurrent (comprendre cause)
- Positions suspectes (>1h sans JSON)
- Avant fermeture manuelle positions DB

---

### **3. Vérification manuelle rapide**

**Compter fichiers JSON:**
```bash
ls -la /home/basebot/trading-bot/data/position_*.json | wc -l
```

**Compter positions DB:**
```bash
sqlite3 /home/basebot/trading-bot/data/trading.db \
  "SELECT COUNT(*) FROM trade_history WHERE exit_time IS NULL;"
```

**Lister détails:**
```bash
sqlite3 /home/basebot/trading-bot/data/trading.db << 'EOF'
.mode column
.headers on
SELECT id, symbol, side,
       datetime(entry_time) as entry,
       ROUND((julianday('now') - julianday(entry_time)) * 24, 1) as hours
FROM trade_history
WHERE exit_time IS NULL;
EOF
```

---

## ⚠️ PRÉVENTION

### **Éviter désynchronisation future:**

1. **Graceful shutdown du Trader:**
   ```bash
   # ✅ BON:
   sudo systemctl stop basebot-trader

   # ❌ MAUVAIS:
   sudo kill -9 $(pgrep -f Trader.py)
   ```

2. **Monitoring logs I/O errors:**
   ```bash
   sudo journalctl -u basebot-trader | grep -i "permission\|I/O\|JSON"
   ```

3. **Vérifier permissions data/:**
   ```bash
   ls -la /home/basebot/trading-bot/data/
   # Doit être: drwxr-xr-x basebot basebot
   ```

4. **Backup régulier DB:**
   ```bash
   # Déjà configuré dans maintenance_safe.sh
   sudo bash /home/basebot/trading-bot/maintenance_safe.sh
   ```

---

## 📊 VÉRIFICATION POST-FIX

**Après cleanup/fix, vérifier Dashboard:**

1. Ouvrir: `http://VPS_IP:8501`
2. Onglet "Positions Actives"
3. Vérifier:
   - ✅ "Positions en mémoire (JSON)" = "Positions en base (DB)"
   - ✅ Message "Désynchronisation" disparu
   - ✅ Liste positions cohérente

**Si message persiste:**
```bash
# Redémarrer Dashboard
sudo systemctl restart basebot-dashboard

# Vider cache navigateur
Ctrl+Shift+R (Chrome/Firefox)
```

---

## 🔧 COMMANDES UTILES

**Supprimer TOUS les fichiers JSON (positions fermées):**
```bash
rm /home/basebot/trading-bot/data/position_*.json
```

**Fermer TOUTES positions orphelines en DB:**
```bash
sqlite3 /home/basebot/trading-bot/data/trading.db \
  "UPDATE trade_history SET exit_time = datetime('now'), side = 'SELL', profit_loss = 0 WHERE exit_time IS NULL;"
```

**Lister historique trades récents:**
```bash
sqlite3 /home/basebot/trading-bot/data/trading.db << 'EOF'
SELECT symbol, side,
       datetime(entry_time) as entry,
       datetime(exit_time) as exit,
       ROUND(profit_loss, 2) as pnl
FROM trade_history
WHERE datetime(entry_time) > datetime('now', '-24 hours')
ORDER BY entry_time DESC
LIMIT 20;
EOF
```

---

## 🎯 RÉSUMÉ ACTION IMMÉDIATE

**Pour ton cas "1 JSON, 2 DB":**

```bash
# Étape 1: Mise à jour code
cd /home/basebot/trading-bot
sudo -u basebot git pull origin main

# Étape 2: Diagnostic + Fix
sudo bash fix_desync_positions.sh

# OU si tu veux juste fix rapide:
sudo bash cleanup_positions.sh

# Étape 3: Vérifier Dashboard
# Ouvrir http://VPS_IP:8501
# Message désync devrait avoir disparu
```

**Temps total:** 1-2 minutes

---

## 📞 SI ÇA NE FONCTIONNE PAS

**Logs à fournir:**

```bash
# 1. Output script diagnostic
sudo bash fix_desync_positions.sh > desync_debug.txt 2>&1

# 2. Logs Trader récents
sudo journalctl -u basebot-trader -n 100 > trader_logs.txt

# 3. Contenu data/
ls -la /home/basebot/trading-bot/data/ > data_dir.txt

# 4. Dernières transactions wallet
# Copier de: https://basescan.org/address/0xA7bf677ecFe14E3E14a79210598Afb36B6910Ccd
```

---

**Auteur:** Claude Code
**Date:** 2025-11-20
**Commit:** 8a229ac
**Fichiers:** fix_desync_positions.sh, cleanup_positions.sh
