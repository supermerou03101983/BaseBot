# ✅ INSTALLATION PROPRE - VPS VIERGE

## 🎯 Une Seule Commande Suffit!

```bash
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
```

**C'est tout!** La base de données sera créée **PARFAITE** dès l'installation.

---

## ✅ Pourquoi C'est Propre Maintenant?

### **Avant (complexe):**
1. Git pull récupère nouveau code
2. Scanner crée DB avec ancien schema (sans `pair_created_at`)
3. Migration script s'exécute pour ajouter colonnes manquantes
4. Risque d'erreur si migration échoue

### **Maintenant (simple):**
1. Git pull récupère nouveau code
2. Scanner crée DB avec **schema complet et correct** dès le départ
3. **C'est tout!** Pas de migration nécessaire

---

## 🔧 Schema Unifié

**Tous les fichiers créent le même schema:**
- ✅ `src/init_database.py` - Schema unifié
- ✅ `src/Scanner.py` - Schema unifié
- ✅ `src/Filter.py` - Schema unifié

**Colonnes `discovered_tokens`:**
```sql
CREATE TABLE IF NOT EXISTS discovered_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT UNIQUE NOT NULL,
    symbol TEXT,
    name TEXT,
    decimals INTEGER,
    total_supply TEXT,
    liquidity REAL,
    market_cap REAL,
    volume_24h REAL,                          -- ✅ Présent dès la création
    price_usd REAL,
    price_eth REAL,
    pair_created_at TIMESTAMP,                -- ✅ Date blockchain (DexScreener)
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- ✅ Date découverte
)
```

---

## 📋 Étapes d'Installation (VPS Vierge)

### **1. Lancer l'installation (5-10 minutes)**

```bash
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
```

**Sortie attendue:**
```
════════════════════════════════════════════════════════
  ✅ Installation terminée !
════════════════════════════════════════════════════════

Le Base Trading Bot a été installé avec succès !

📍 Installation:
  • Répertoire: /home/basebot/trading-bot
  • Utilisateur: basebot
  • Python: v3.10.12

✅ Base de données créée avec schema complet
✅ Toutes les colonnes présentes (pair_created_at, volume_24h)
✅ Services systemd configurés
```

---

### **2. Configurer le .env (5 minutes)**

```bash
sudo nano /home/basebot/trading-bot/config/.env
```

**Remplir les clés obligatoires:**
```bash
WALLET_ADDRESS=0xVotre_Adresse
PRIVATE_KEY=Votre_Clé_Sans_0x

ETHERSCAN_API_KEY=Votre_Clé_Etherscan
COINGECKO_API_KEY=Votre_Clé_CoinGecko
```

**Sauvegarder:** `Ctrl+O` puis `Entrée`, puis `Ctrl+X`

---

### **3. Démarrer les services**

```bash
sudo systemctl enable --now basebot-scanner
sudo systemctl enable --now basebot-filter
sudo systemctl enable --now basebot-trader
sudo systemctl enable --now basebot-dashboard
```

---

### **4. Vérifier que tout fonctionne**

```bash
# Vérifier les services
sudo systemctl status basebot-scanner
sudo systemctl status basebot-filter
sudo systemctl status basebot-trader

# Voir les logs
su - basebot
bot-watch  # Alias pour tail -f logs
```

**Logs attendus (Scanner):**
```
Nov 18 10:00:00 - INFO - Scanner démarré...
Nov 18 10:00:00 - INFO - ⏱️ Scanner filtrera tokens entre 2.0h et 12.0h d'âge
Nov 18 10:00:15 - INFO - ✅ Token découvert: MORI (3.2h) (0x95f3...) - MC: $66,980.00
Nov 18 10:00:16 - INFO - ✅ Token découvert: GALA (5.1h) (0x5553...) - MC: $33,678.00
Nov 18 10:00:17 - DEBUG - ⏭️ Token trop jeune: FAST (0.3h < 2.0h)
Nov 18 10:00:18 - INFO - 📊 Batch traité: 18 nouveaux | 2 déjà connus | 12 trop jeunes | 3 trop vieux
```

**Logs attendus (Filter):**
```
Nov 18 10:01:30 - INFO - Analyse du token: MORI (0x95f3...)
Nov 18 10:01:31 - INFO - MC ($66,980) OK
Nov 18 10:01:31 - INFO - Volume 24h ($123,397) OK
Nov 18 10:01:31 - INFO - Age (3.5h) >= min (2.0h)  # ✅ Age check fonctionne!
Nov 18 10:01:32 - INFO - ✅ Token APPROUVE: MORI - Score: 85.00
```

---

## 🔍 Vérification du Schema DB

Pour vérifier que la DB a été créée correctement:

```bash
su - basebot
sqlite3 /home/basebot/trading-bot/data/trading.db "PRAGMA table_info(discovered_tokens);"
```

**Sortie attendue:**
```
0|id|INTEGER|0||1
1|token_address|TEXT|1||0
2|symbol|TEXT|0||0
3|name|TEXT|0||0
4|decimals|INTEGER|0||0
5|total_supply|TEXT|0||0
6|liquidity|REAL|0|0|0
7|market_cap|REAL|0|0|0
8|volume_24h|REAL|0|0|0              ✅ Présent!
9|price_usd|REAL|0|0|0
10|price_eth|REAL|0|0|0
11|pair_created_at|TIMESTAMP|0||0    ✅ Présent!
12|discovered_at|TIMESTAMP|0|CURRENT_TIMESTAMP|0  ✅ Présent!
```

**Si vous voyez les 3 colonnes ✅, c'est parfait!**

---

## 🚀 Dashboard

**URL:** `http://VOTRE_VPS_IP:8501`

**Credentials (par défaut):**
- Username: `admin`
- Password: `000Rnella`

(Changez dans .env si besoin)

---

## 📊 Commandes Utiles

```bash
# Diagnostic complet
bot-status

# Analyse des performances
bot-analyze-full

# Logs en temps réel
bot-watch          # Scanner + Filter + Trader
bot-scan           # Scanner uniquement
bot-filter         # Filter uniquement
bot-trader         # Trader uniquement

# Contrôle
bot-restart        # Redémarrer trader
bot-emergency      # Fermeture urgence positions

# Services
sudo systemctl status basebot-scanner
sudo systemctl restart basebot-filter
sudo journalctl -u basebot-trader -f
```

---

## ✅ Checklist Post-Installation

**Après 15 minutes:**
- [ ] Scanner découvre des tokens (bot-scan)
- [ ] Filter analyse des tokens (bot-filter)
- [ ] Pas d'erreur "no such column: pair_created_at"
- [ ] Age check fonctionne (logs montrent "Age (X.Xh) >= min (2.0h)")

**Après 1 heure:**
- [ ] Au moins 1 token approuvé (bot-analyze)
- [ ] Filter rejette les mauvais tokens (volume faible, age <2h)
- [ ] Dashboard accessible sur port 8501

**Après 24 heures:**
- [ ] Win rate >50% (bot-analyze-full)
- [ ] Expectancy >0%
- [ ] Aucune perte >-30%

---

## 🎉 Conclusion

**Installation complète en 3 étapes:**
1. ✅ Une commande: `curl -s ... | sudo bash`
2. ✅ Configuration .env (5 min)
3. ✅ Démarrage services (1 min)

**Base de données créée PARFAITE:**
- ✅ Schema complet avec `pair_created_at` et `volume_24h`
- ✅ Pas de migration nécessaire
- ✅ Token age check fonctionnel dès le départ
- ✅ Tous les filtres opérationnels

**Prêt pour le trading!** 🚀

---

**Date:** 2025-11-18
**Version:** v3.0 - Clean Install
**Commit:** 97535f4
**Auteur:** Claude Code
