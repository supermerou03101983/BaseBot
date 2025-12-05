# ✅ Checklist Déploiement VPS - BaseBot Trading

**Date de création** : 2025-01-05
**Version** : v1.7 (Modification #7 incluse)
**Script de déploiement** : `deploy.sh`

---

## 🎯 Prérequis Minimum

### VPS/Serveur
- [ ] **OS** : Ubuntu 20.04+ ou Debian 11+
- [ ] **RAM** : ≥ 2GB (4GB recommandé)
- [ ] **CPU** : ≥ 2 cores
- [ ] **Disque** : ≥ 10GB libre
- [ ] **Accès root** : `sudo` ou compte root

### Clés API (Minimum)
- [ ] **WALLET_ADDRESS** : Adresse wallet Base (0x...)
- [ ] **PRIVATE_KEY** : Clé privée du wallet (0x...)
- [ ] **RPC_URL** : RPC Base (par défaut : `https://mainnet.base.org`)

### Clés API (Optionnelles)
- [ ] **BIRDEYE_API_KEY** : Pour holders précis (optionnel grâce à Mod #7)
- [ ] **ETHERSCAN_API_KEY** : Pour BaseScan API (gratuit)
- [ ] **COINGECKO_API_KEY** : Pour prix ETH fallback (gratuit)
- [ ] **DRPC_API_KEY** : Pour protection MEV en mode réel (optionnel)

---

## 🚀 Déploiement en 1 Commande

### Option 1 : Déploiement Direct depuis GitHub

```bash
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
```

### Option 2 : Déploiement Local

```bash
# Cloner le repo
git clone https://github.com/supermerou03101983/BaseBot.git
cd BaseBot

# Rendre exécutable
chmod +x deploy.sh

# Lancer le déploiement
sudo bash deploy.sh
```

---

## 📋 Ce que fait `deploy.sh` Automatiquement

### 1️⃣ Installation Système (5-10 min)
- [x] Mise à jour des paquets (`apt-get update`)
- [x] Installation Python 3.8+ + pip + venv
- [x] Installation git, curl, wget, sqlite3
- [x] Installation build-essential, libssl-dev, libffi-dev

### 2️⃣ Configuration Utilisateur
- [x] Création utilisateur dédié `basebot`
- [x] Home directory `/home/basebot`
- [x] Pas de mot de passe (gestion via systemd)

### 3️⃣ Clonage et Structure
- [x] Clone depuis GitHub dans `/home/basebot/trading-bot`
- [x] Création dossiers `/logs`, `/data`, `/config`, `/backups`
- [x] Permissions correctes (`chown basebot:basebot`)

### 4️⃣ Environnement Python
- [x] Création venv dans `/home/basebot/trading-bot/venv`
- [x] Installation toutes dépendances (`requirements.txt`)
- [x] Validation imports (web3, pandas, streamlit)

### 5️⃣ Configuration Fichiers
- [x] Création `/config/.env` avec template complet
- [x] Création `/config/trading_mode.json` (mode paper)
- [x] Création `/config/blacklist.json` (liste vide)
- [x] **Modification #7** : `ENABLE_ONCHAIN_FALLBACK=true` par défaut

### 6️⃣ Base de Données
- [x] Exécution `init_database.py`
- [x] Création `/data/trading.db` avec 10 tables
- [x] Table `losing_tokens_cooldown` (Mod #6)
- [x] Indexes optimisés

### 7️⃣ Services Systemd
- [x] Service `basebot-scanner.service`
- [x] Service `basebot-filter.service`
- [x] Service `basebot-trader.service`
- [x] Service `basebot-dashboard.service`
- [x] Auto-restart activé (Restart=always)
- [x] Logs journalctl disponibles

### 8️⃣ Pare-feu
- [x] Port 8501 ouvert (Dashboard Streamlit)
- [x] UFW ou firewalld détecté automatiquement

### 9️⃣ Maintenance Automatique
- [x] Backup quotidien 2h du matin
- [x] Maintenance hebdo dimanche 3h
- [x] Maintenance mensuelle 1er du mois 4h
- [x] Nettoyage logs quotidien 1h
- [x] Watchdog anti-freeze toutes les 15 min

### 🔟 Outils de Diagnostic
- [x] Alias `bot-status`, `bot-fix`, `bot-restart`, etc.
- [x] Scripts `diagnose_freeze.py`, `emergency_close_positions.py`
- [x] Guide rapide `/home/basebot/README_QUICKSTART.txt`

### 1️⃣1️⃣ Vérification Modification #7
- [x] Check `src/onchain_fetcher.py` présent
- [x] Check `src/api_fallbacks.py` présent
- [x] Check `src/data_aggregator.py` présent
- [x] Message si 3/3 OK ou warning si manquant

---

## ⚙️ Configuration Post-Déploiement

### Étape 1 : Éditer `.env` (OBLIGATOIRE)

```bash
nano /home/basebot/trading-bot/config/.env
```

**Remplir minimum** :
```bash
WALLET_ADDRESS=0xYOUR_WALLET_ADDRESS_HERE
PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE
```

**Optionnel (améliore performance)** :
```bash
BIRDEYE_API_KEY=your_birdeye_api_key_here      # Holders précis (optionnel)
ETHERSCAN_API_KEY=YOUR_ETHERSCAN_API_KEY       # Owner% via BaseScan (gratuit)
COINGECKO_API_KEY=your_coingecko_api_key       # Prix ETH fallback (gratuit)
DRPC_API_KEY=YOUR_DRPC_API_KEY_HERE            # Protection MEV mode réel (optionnel)
```

### Étape 2 : Choisir Configuration

**Option A : Configuration Test Permissive (Validation Workflow)**
```bash
cd /home/basebot/trading-bot
cp config/.env.test.permissif config/.env
nano config/.env  # Remplir clés
```

**Option B : Configuration Production (Momentum Safe v2)**
```bash
cd /home/basebot/trading-bot
cp config/.env.example config/.env
nano config/.env  # Remplir clés
```

**Option C : Script Interactif**
```bash
cd /home/basebot/trading-bot
./switch_config.sh  # Menu interactif
```

### Étape 3 : Démarrer Services

```bash
# Activer auto-démarrage
systemctl enable basebot-scanner
systemctl enable basebot-filter
systemctl enable basebot-trader
systemctl enable basebot-dashboard

# Démarrer maintenant
systemctl start basebot-scanner
systemctl start basebot-filter
systemctl start basebot-trader
systemctl start basebot-dashboard
```

### Étape 4 : Vérifier Statut

```bash
# Status services
systemctl status basebot-scanner
systemctl status basebot-filter
systemctl status basebot-trader
systemctl status basebot-dashboard

# Logs en direct
journalctl -u basebot-filter -f

# Ou avec alias
bot-status  # Diagnostic complet
bot-logs    # Dernières 50 lignes
bot-watch   # Suivre en temps réel
```

---

## 🔍 Vérification Modification #7

### Test 1 : Fichiers Présents

```bash
ls -lh /home/basebot/trading-bot/src/{onchain_fetcher,api_fallbacks,data_aggregator}.py
```

**Attendu** :
```
-rw-r--r-- 1 basebot basebot 19K  onchain_fetcher.py
-rw-r--r-- 1 basebot basebot 12K  api_fallbacks.py
-rw-r--r-- 1 basebot basebot 15K  data_aggregator.py
```

### Test 2 : Variable d'Environnement

```bash
grep ENABLE_ONCHAIN_FALLBACK /home/basebot/trading-bot/config/.env
```

**Attendu** :
```
ENABLE_ONCHAIN_FALLBACK=true
```

### Test 3 : Logs Filter (Après 5 min)

```bash
tail -n 50 /home/basebot/trading-bot/logs/filter.log | grep -E "DexScreener:|Sources"
```

**Attendu** :
```
✅ DexScreener: $151,046 liq, $11,724 vol 1h
✅ DexScreener: $221,521 liq, $420 vol 1h
```

Si vous voyez `✅ DexScreener:` avec des valeurs > 0 → **Modification #7 fonctionne** ✅

### Test 4 : Database Enrichissement

```bash
sqlite3 /home/basebot/trading-bot/data/trading.db "
SELECT
    COUNT(*) as total_discovered,
    COUNT(CASE WHEN liquidity > 0 THEN 1 END) as enriched_via_filter
FROM discovered_tokens;
"
```

**Attendu (après 1h)** :
```
50|50   (100% enrichis via DexScreener)
```

---

## 📊 Métriques de Succès

### Configuration Test Permissive

| Métrique | Objectif | Délai |
|----------|----------|-------|
| Tokens découverts | ≥ 50 | 30 min |
| Tokens enrichis (liquidité > 0) | ≥ 90% | 30 min |
| Tokens approuvés | ≥ 5 | 2 heures |
| Services actifs | 4/4 | Immédiat |
| Dashboard accessible | ✅ | Immédiat |

### Configuration Production (Momentum Safe v2)

| Métrique | Objectif | Délai |
|----------|----------|-------|
| Tokens découverts | ≥ 20 | 2 heures |
| Tokens enrichis | ≥ 95% | 2 heures |
| Tokens approuvés | 2-5 | 24 heures |
| Win-rate | ≥ 70% | 7 jours |
| Trades/jour | 2-5 | Stable |

---

## 🚨 Troubleshooting Rapide

### Problème 1 : Services ne démarrent pas

```bash
# Vérifier logs systemd
journalctl -u basebot-filter -n 50

# Vérifier permissions
ls -la /home/basebot/trading-bot/logs/

# Recréer logs
rm -f /home/basebot/trading-bot/logs/*.log
systemctl restart basebot-filter
```

### Problème 2 : Aucun token enrichi (liquidité = 0)

**Cause** : Modification #7 non installée ou erreur import

**Solution** :
```bash
# Vérifier fichiers Mod #7
ls /home/basebot/trading-bot/src/{onchain_fetcher,api_fallbacks,data_aggregator}.py

# Si manquants, pull GitHub
cd /home/basebot/trading-bot
git pull origin main

# Redémarrer
systemctl restart basebot-filter
```

### Problème 3 : Erreurs Python import

**Cause** : Venv corrompu ou dépendances manquantes

**Solution** :
```bash
cd /home/basebot/trading-bot
source venv/bin/activate
pip install --upgrade -r requirements.txt
deactivate
systemctl restart basebot-filter
```

### Problème 4 : Dashboard inaccessible

**Cause** : Port 8501 bloqué ou service down

**Solution** :
```bash
# Vérifier service
systemctl status basebot-dashboard

# Vérifier port
netstat -tulpn | grep 8501

# Ouvrir firewall
sudo ufw allow 8501/tcp
sudo systemctl restart basebot-dashboard
```

---

## 🛡️ Sécurité

### Recommandations Minimales

- [ ] **Clé privée** : Ne jamais commiter dans git
- [ ] **Fichier .env** : Permissions 600 (`chmod 600 config/.env`)
- [ ] **Backup .env** : Copie hors VPS (cloud chiffré)
- [ ] **Firewall** : Fermer ports inutiles (sauf 22, 8501)
- [ ] **Updates** : Appliquer mises à jour système mensuelles
- [ ] **Monitoring** : Vérifier watchdog.log régulièrement

### Mode Paper vs Real

**Mode Paper (Test)** :
```bash
TRADING_MODE=paper  # Dans .env
```
- Simule achats/ventes
- Pas de transactions blockchain réelles
- Idéal pour tests 7-14 jours

**Mode Real (Production)** :
```bash
TRADING_MODE=real   # Dans .env
```
- Transactions blockchain réelles
- Consomme ETH (gas fees)
- ⚠️ Tester d'abord en paper !

---

## 📈 Roadmap Modifications

| Modification | Statut | Description |
|--------------|--------|-------------|
| **#1** | ✅ Déployé | Critères assouplies ($3K volume, $5K liquidité) |
| **#5** | ✅ Déployé | Protection MEV/Frontrun avec dRPC |
| **#6** | ✅ Déployé | Système retry progressif (30min liq, 12min momentum) |
| **#7** | ✅ Déployé | Agrégateur multi-sources (DexScreener → On-chain → BirdEye) |
| **#8** | 🔄 Planifié | Honeypot checker on-chain (taxes buy/sell) |
| **#9** | 🔄 Planifié | Cache Redis multi-niveaux (performance) |
| **#10** | 🔄 Planifié | Dashboard monitoring sources (observabilité) |

---

## 📞 Support

### Commandes Utiles Alias

Après connexion SSH en tant que `basebot` :

```bash
bot-status        # Diagnostic complet
bot-fix           # Dépannage rapide
bot-restart       # Redémarrer trader
bot-logs          # 50 dernières lignes
bot-watch         # Suivre logs temps réel
bot-emergency     # Fermer positions d'urgence
bot-analyze       # Analyse performances simple
bot-analyze-full  # Analyse détaillée + recommandations
```

### Fichiers Clés

- **Configuration** : `/home/basebot/trading-bot/config/.env`
- **Database** : `/home/basebot/trading-bot/data/trading.db`
- **Logs** : `/home/basebot/trading-bot/logs/`
- **Backups** : `/home/basebot/trading-bot/data/backups/`
- **Guide rapide** : `/home/basebot/README_QUICKSTART.txt`

### Documentation

- **README principal** : `/home/basebot/trading-bot/README.md`
- **Quick Start Test** : `/home/basebot/trading-bot/QUICK_START_TEST.md`
- **Configs** : `/home/basebot/trading-bot/config/README_CONFIGS.md`
- **Modification #7** : `/home/basebot/trading-bot/docs/MODIFICATION_7_DATA_AGGREGATOR.md`

---

## ✅ Checklist Finale

### Déploiement Réussi Si :

- [x] 4 services systemd actifs (`systemctl is-active basebot-*`)
- [x] Dashboard accessible sur `http://VPS_IP:8501`
- [x] Logs filter montrent `✅ DexScreener:` avec valeurs > 0
- [x] Database contient tokens découverts (`sqlite3 ... "SELECT COUNT(*) FROM discovered_tokens"`)
- [x] Aucune erreur critique dans logs (`grep ERROR logs/*.log`)
- [x] Fichiers Mod #7 présents (3/3)
- [x] Configuration choisie (test ou prod)
- [x] `.env` rempli avec clés wallet minimum

### Prêt pour Production Si :

- [x] Tests en mode paper ≥ 7 jours
- [x] Win-rate ≥ 60% en paper
- [x] Aucun freeze/blocage observé
- [x] Configuration Momentum Safe v2 active
- [x] Wallet alimenté avec ETH Base (gas fees)
- [x] Protection MEV activée (dRPC)
- [x] Backups automatiques configurés
- [x] Monitoring watchdog actif

---

**🤖 Generated with Claude Code**
**📅 Dernière mise à jour** : 2025-01-05
**✅ Compatibilité** : deploy.sh v1.7+ (Modification #7 incluse)
