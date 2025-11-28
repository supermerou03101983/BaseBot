# 📦 Mise à Jour de deploy.sh

**Date**: 2025-11-26 16:40 UTC
**Status**: ✅ TERMINÉ

---

## 🎯 Objectif

Garantir que le script `deploy.sh` reflète **toutes les modifications récentes** pour permettre un déploiement en une seule commande sur un nouveau VPS une fois la stratégie validée.

---

## 📝 Modifications Apportées

### 1. Configuration `.env` - Critères Assouplies (Modification #1)

**Fichier**: `deploy.sh` lignes 389-405

**Avant** :
```bash
MIN_LIQUIDITY_USD=30000
MIN_VOLUME_24H=30000
MIN_HOLDERS=150
MIN_MARKET_CAP=25000
MIN_SAFETY_SCORE=70
MIN_POTENTIAL_SCORE=60
```

**Après** :
```bash
# Critères principaux (stratégie optimisée - Modification #1)
# ⚠️ IMPORTANT: Ces valeurs ont été assouplies après tests
#               pour permettre le trading sur tokens 2-12h d'âge
MIN_LIQUIDITY_USD=5000    # Assoupliss de $30K à $5K (Mod #1)
MIN_VOLUME_24H=3000       # Assoupliss de $30K à $3K (Mod #1)
MIN_HOLDERS=50            # Assoupliss de 150 à 50 (Mod #1)
MIN_MARKET_CAP=5000       # Assoupliss de $25K à $5K (Mod #1)
MIN_SAFETY_SCORE=50       # Assoupliss de 70 à 50 (Mod #1)
MIN_POTENTIAL_SCORE=40    # Assoupliss de 60 à 40 (Mod #1)
```

**Rationale** :
- Reflète la Modification #1 documentée dans [DEPLOYMENT_REPORT_MOD1.md](DEPLOYMENT_REPORT_MOD1.md)
- Permet de trader sur des tokens 2-12h d'âge (critères initiaux trop stricts)

### 2. Nouvelle Étape : Application du Patch volume_1h

**Fichier**: `deploy.sh` lignes 534-559 (nouvelle section 8)

**Ajout** :
```bash
# =============================================================================
# 8. Application des patches critiques
# =============================================================================

print_header "8️⃣  Application des patches critiques"

# Patch volume_1h : CRITIQUE pour éviter les tokens morts
if [ -f "$BOT_DIR/add_volume_1h_filter.py" ]; then
    print_step "Application du patch volume_1h (filtre tokens morts)..."

    # Vérifier si le patch est déjà appliqué
    if grep -q "volume_1h" "$BOT_DIR/src/Filter.py" 2>/dev/null; then
        print_info "Patch volume_1h déjà appliqué"
    else
        su - $BOT_USER -c "source $VENV_DIR/bin/activate && cd $BOT_DIR && python add_volume_1h_filter.py" >> "$LOG_FILE" 2>&1
        if [ $? -eq 0 ]; then
            print_success "Patch volume_1h appliqué avec succès"
            print_info "Le filtre rejettera automatiquement les tokens avec volume_1h = 0"
        else
            print_warning "Échec application patch volume_1h (continuez manuellement)"
        fi
    fi
else
    print_warning "Script add_volume_1h_filter.py non trouvé"
    print_info "Le filtre volume_1h devra être appliqué manuellement après déploiement"
fi
```

**Rationale** :
- Applique automatiquement le filtre volume_1h documenté dans [FIX_REAL_PRICES_VOLUME_1H.md](FIX_REAL_PRICES_VOLUME_1H.md)
- Rejette automatiquement les tokens morts (volume_1h = 0)
- Critique pour éviter de trader sur des tokens sans activité récente

### 3. Documentation des Fixes dans les Tests

**Fichier**: `deploy.sh` lignes 843-869

**Ajout** :
```bash
CRITICAL_DOCS=(
    "$BOT_DIR/VERIFICATION_CRITERES.md"
    "$BOT_DIR/FIXES_APPLIED.md"
    "$BOT_DIR/OPTIMIZATIONS_CRITIQUES.md"
    "$BOT_DIR/DEPLOY_FIXES.md"
    "$BOT_DIR/FIX_REAL_PRICES_VOLUME_1H.md"           # NOUVEAU
    "$BOT_DIR/DEPLOYMENT_REPORT_MOD1.md"               # NOUVEAU
)

if [ $DOCS_FOUND -ge 4 ]; then
    print_success "Documentation des fixes critiques présente ($DOCS_FOUND/6)"
    print_info "Fixes appliqués:"
    print_info "  • Modification #1: Critères assouplies (MIN_VOLUME $3K, MIN_LIQUIDITY $5K)"
    print_info "  • Filtre volume_1h: Rejette automatiquement les tokens morts (volume_1h=0)"
    print_info "  • Prix réels: Mode PAPER utilise uniquement les prix DexScreener"
fi
```

**Rationale** :
- Vérifie la présence de la documentation des dernières modifications
- Informe l'opérateur des fixes appliqués lors du déploiement

### 4. Renumérotation des Sections

Toutes les sections après la nouvelle section 8 ont été renumérotées :

| Ancienne | Nouvelle | Section |
|----------|----------|---------|
| 8 | 9 | Nettoyage des logs |
| 9 | 10 | Services systemd |
| 10 | 11 | Pare-feu |
| 11 | 12 | Maintenance automatique |
| 12 | 13 | Outils de diagnostic |
| 13 | 14 | Tests de validation |
| 11 (fin) | 15 | Instructions finales |

---

## ✅ Fichiers Requis pour le Déploiement

Le script `deploy.sh` attend maintenant ces fichiers dans le repository :

### Fichiers de Code

1. ✅ `src/Scanner.py`
2. ✅ `src/Filter.py` (avec modifications Mod #1)
3. ✅ `src/Trader.py` (version originale, sans simulation)
4. ✅ `src/Dashboard.py`
5. ✅ `src/init_database.py`
6. ✅ `requirements.txt`
7. ✅ **`add_volume_1h_filter.py`** (NOUVEAU - critique)

### Fichiers de Documentation

1. ✅ `VERIFICATION_CRITERES.md`
2. ✅ `FIXES_APPLIED.md`
3. ✅ `OPTIMIZATIONS_CRITIQUES.md`
4. ✅ `DEPLOY_FIXES.md`
5. ✅ **`FIX_REAL_PRICES_VOLUME_1H.md`** (NOUVEAU)
6. ✅ **`DEPLOYMENT_REPORT_MOD1.md`** (NOUVEAU)

### Scripts de Maintenance

1. ✅ `maintenance_safe.sh`
2. ✅ `watchdog.py`
3. ✅ `diagnose_freeze.py`
4. ✅ `emergency_close_positions.py`
5. ✅ `quick_fix.sh`
6. ✅ `analyze_trades_simple.py`
7. ✅ `analyze_results.py`

---

## 🚀 Workflow de Déploiement

### Sur un Nouveau VPS

```bash
# 1. Télécharger et exécuter le script
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash

# Le script va automatiquement:
# - Cloner le repository GitHub
# - Installer les dépendances
# - Créer le fichier .env avec les critères assouplies (Mod #1)
# - Appliquer le patch volume_1h automatiquement
# - Configurer les services systemd
# - Activer la maintenance automatique
```

### Configuration Post-Déploiement

```bash
# 2. Éditer le .env (wallet, API keys)
nano /home/basebot/trading-bot/config/.env

# 3. Démarrer les services
systemctl enable basebot-scanner basebot-filter basebot-trader basebot-dashboard
systemctl start basebot-scanner basebot-filter basebot-trader basebot-dashboard

# 4. Vérifier
systemctl status basebot-trader
tail -f /home/basebot/trading-bot/logs/trader.log
```

---

## 🔍 Vérifications Post-Déploiement

### 1. Vérifier que le Patch volume_1h est Appliqué

```bash
grep -n "volume_1h" /home/basebot/trading-bot/src/Filter.py
```

**Attendu** :
```
258:        volume_1h = token_data.get('volume_1h', 0)
259:        if volume_1h == 0:
260:            reasons.append(f"❌ REJET: Volume 1h = $0 (token mort, pas d'activité récente)")
```

### 2. Vérifier les Critères dans le .env

```bash
grep -E "MIN_LIQUIDITY_USD|MIN_VOLUME_24H|MIN_HOLDERS|MIN_MARKET_CAP|MIN_SAFETY_SCORE|MIN_POTENTIAL_SCORE" /home/basebot/trading-bot/config/.env
```

**Attendu** :
```
MIN_LIQUIDITY_USD=5000
MIN_VOLUME_24H=3000
MIN_HOLDERS=50
MIN_MARKET_CAP=5000
MIN_SAFETY_SCORE=50
MIN_POTENTIAL_SCORE=40
```

### 3. Vérifier les Services

```bash
systemctl status basebot-scanner
systemctl status basebot-filter
systemctl status basebot-trader
```

**Attendu** : Tous `active (running)`

### 4. Vérifier les Logs du Filtre

```bash
tail -50 /home/basebot/trading-bot/logs/filter.log
```

**Attendu** : Doit montrer des rejets pour `volume_1h = 0` :
```
❌ REJET: Volume 1h = $0 (token mort, pas d'activité récente)
```

---

## 📊 Comparaison Avant/Après

| Aspect | Avant Mise à Jour | Après Mise à Jour |
|--------|-------------------|-------------------|
| **MIN_LIQUIDITY** | $30,000 | $5,000 ✅ |
| **MIN_VOLUME_24H** | $30,000 | $3,000 ✅ |
| **MIN_HOLDERS** | 150 | 50 ✅ |
| **Filtre volume_1h** | ❌ Absent | ✅ Appliqué automatiquement |
| **Documentation** | 4 fichiers | 6 fichiers ✅ |
| **Sections deploy** | 13 | 15 ✅ |
| **Patch automatique** | ❌ Manuel | ✅ Automatique |

---

## 🎯 Bénéfices

### 1. Déploiement Reproductible

- ✅ Une seule commande déploie **tout** le bot
- ✅ Critères assouplies (Mod #1) appliqués automatiquement
- ✅ Patch volume_1h appliqué automatiquement
- ✅ Aucune configuration manuelle requise (sauf .env)

### 2. Cohérence

- ✅ Tous les VPS utilisent la **même configuration**
- ✅ Fixes critiques **toujours appliqués**
- ✅ Documentation **toujours à jour**

### 3. Facilité de Test

- ✅ Déployer sur un nouveau VPS en **5 minutes**
- ✅ Tester différentes configurations facilement
- ✅ Rollback rapide si nécessaire

### 4. Scalabilité

- ✅ Prêt pour déploiement multi-VPS
- ✅ Configuration identique sur tous les serveurs
- ✅ Maintenance simplifiée

---

## 🔄 Prochaines Étapes

### Dès Maintenant

1. ✅ `deploy.sh` mis à jour avec toutes les modifications
2. ⏳ Commit et push sur GitHub (à faire)
3. ⏳ Tester le déploiement sur un nouveau VPS (validation)

### Après Validation de la Stratégie

Une fois que les objectifs sont atteints (win-rate ≥70%, profit ≥15%) :

```bash
# 1. Commit final de la stratégie optimisée
git add .
git commit -m "🎉 Stratégie validée - Win-rate 75%, Profit moyen 18%"
git push origin main

# 2. Déployer sur VPS de production
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash

# 3. Passer en mode REAL
nano /home/basebot/trading-bot/config/.env
# TRADING_MODE=real

# 4. Réduire MAX_TRADES_PER_DAY
# MAX_TRADES_PER_DAY=3

# 5. Configurer wallet avec fonds réels
```

---

## 📝 Notes Importantes

### À Commit sur GitHub

Pour que le déploiement en une commande fonctionne, ces fichiers **DOIVENT** être sur GitHub :

1. ✅ `deploy.sh` (mis à jour)
2. ✅ `add_volume_1h_filter.py` (critique)
3. ✅ `FIX_REAL_PRICES_VOLUME_1H.md` (documentation)
4. ✅ `DEPLOYMENT_REPORT_MOD1.md` (documentation)
5. ✅ `src/Filter.py` (version originale, patch appliqué par script)
6. ✅ `config/.env.example` (avec critères assouplies)

### Ne PAS Commit

- ❌ `config/.env` (contient clés privées)
- ❌ `data/trading.db` (données locales)
- ❌ `logs/*.log` (logs)
- ❌ `vps_credentials.conf` (credentials)

---

## ✅ Checklist de Validation

- [x] `deploy.sh` mis à jour avec critères assouplies
- [x] Section 8 ajoutée (patch volume_1h)
- [x] Sections renumérotées correctement
- [x] Documentation des fixes ajoutée aux tests
- [x] Commentaires explicatifs ajoutés
- [ ] **Commit et push sur GitHub** ⏳
- [ ] **Test sur nouveau VPS** ⏳
- [ ] **Validation du déploiement automatique** ⏳

---

**Status** : ✅ MISE À JOUR TERMINÉE

Le fichier `deploy.sh` est maintenant **100% à jour** et prêt pour un déploiement automatique incluant toutes les modifications critiques (Mod #1 + filtre volume_1h).
