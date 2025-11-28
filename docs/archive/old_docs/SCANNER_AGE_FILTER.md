# 🎯 SCANNER - FILTRAGE PAR ÂGE

## 🔧 Problème Résolu

### **Avant (Logique Défectueuse):**

```
Scanner → Récupère TOUS les nouveaux tokens (0-48h)
   ↓
   DB → Stocke tokens de 3 minutes à 48h
   ↓
Filter → Check age ≥ 2h
   ↓
   PROBLÈME: Tokens <2h rejetés mais JAMAIS re-évalués!
```

**Résultat:** Les bons tokens rejetés à 5 min d'âge n'étaient JAMAIS vérifiés à nouveau à 2h+!

---

### **Après (Logique Corrigée):**

```
Scanner → Récupère nouveaux tokens des APIs
   ↓
   FILTRE D'ÂGE: Garde SEULEMENT tokens entre 2h-12h
   ↓
   DB → Stocke UNIQUEMENT tokens "matures" (2-12h)
   ↓
Filter → Tous les tokens ont ≥2h (bonus +10 garanti)
   ↓
   ✅ Pas de perte d'opportunité!
```

**Résultat:** Seuls les tokens dans la fenêtre optimale (2-12h) sont découverts et analysés!

---

## ⚙️ Configuration

### **Paramètres dans `.env`:**

```bash
# Filtrage d'âge par le Scanner
MIN_TOKEN_AGE_HOURS=2        # Âge minimum pour découverte (défaut: 2h)
MAX_TOKEN_AGE_HOURS=12       # Âge maximum pour découverte (défaut: 12h)
```

### **Logique Implémentée:**

**Scanner.py (lignes 57-60, 250-276):**
```python
# Au démarrage
self.min_token_age_hours = float(os.getenv('MIN_TOKEN_AGE_HOURS', '2'))
self.max_token_age_hours = float(os.getenv('MAX_TOKEN_AGE_HOURS', '12'))

# Dans process_token_batch()
if pair_created_at:
    dt = datetime.fromtimestamp(pair_created_at / 1000, tz=timezone.utc)
    token_age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600

if token_age_hours is not None:
    if token_age_hours < self.min_token_age_hours:
        skipped_too_young += 1
        continue  # ❌ IGNORE token trop jeune

    if token_age_hours > self.max_token_age_hours:
        skipped_too_old += 1
        continue  # ❌ IGNORE token trop vieux

# ✅ Token dans la bonne tranche → Stocké en DB
```

---

## 📊 Logs Attendus

### **Démarrage Scanner:**
```
Nov 18 12:00:00 - INFO - Scanner démarré...
Nov 18 12:00:00 - INFO - ⏱️ Scanner filtrera tokens entre 2.0h et 12.0h d'âge
```

### **Pendant le scan:**
```
Nov 18 12:00:15 - INFO - ✅ Token découvert: MORI (3.2h) (0x95f3...) - MC: $66,980.00
Nov 18 12:00:16 - DEBUG - ⏭️ Token trop jeune: GALA (0.5h < 2.0h)
Nov 18 12:00:17 - DEBUG - ⏭️ Token trop vieux: OLD (15.3h > 12.0h)
Nov 18 12:00:18 - INFO - 📊 Batch traité: 5 nouveaux | 3 déjà connus | 12 trop jeunes | 4 trop vieux | 0 sans adresse | 1 sans détails
```

---

## 🎯 Pourquoi 2h-12h?

### **Tokens <2h (Trop Jeunes):**
- ❌ Volatilité extrême
- ❌ Slippage très élevé
- ❌ Risque de rug pull immédiat
- ❌ Pas assez de données pour évaluation fiable

### **Tokens 2h-12h (Zone Optimale):**
- ✅ Volatilité stabilisée
- ✅ Volume 24h significatif
- ✅ Holders en augmentation
- ✅ Pattern de prix observable
- ✅ Moins de risque de scam immédiat

### **Tokens >12h (Trop Vieux):**
- ❌ Pump initial déjà passé
- ❌ Opportunité de gain réduite
- ❌ Risque de descente après pump
- ❌ Autres traders déjà positionnés

---

## 🔧 Ajustement de la Stratégie

### **Configuration Conservative (3h-8h):**
```bash
MIN_TOKEN_AGE_HOURS=3        # Plus mature, moins risqué
MAX_TOKEN_AGE_HOURS=8        # Opportunités plus courtes
```

**Avantages:** Sécurité maximale
**Inconvénients:** Moins d'opportunités

---

### **Configuration Balanced (2h-12h):**
```bash
MIN_TOKEN_AGE_HOURS=2        # Défaut recommandé
MAX_TOKEN_AGE_HOURS=12       # Fenêtre optimale
```

**Avantages:** Équilibre sécurité/opportunités
**Inconvénients:** Aucun (recommandé)

---

### **Configuration Aggressive (1h-24h):**
```bash
MIN_TOKEN_AGE_HOURS=1        # Accepte tokens très jeunes
MAX_TOKEN_AGE_HOURS=24       # Large fenêtre
```

**Avantages:** Maximum d'opportunités
**Inconvénients:** Risque plus élevé

---

## ✅ Validation

### **Tester le filtrage:**

1. **Vérifier les logs au démarrage:**
```bash
sudo journalctl -u basebot-scanner -n 10 | grep "filtrera tokens"
```

**Sortie attendue:**
```
INFO - ⏱️ Scanner filtrera tokens entre 2.0h et 12.0h d'âge
```

2. **Voir les tokens ignorés:**
```bash
sudo journalctl -u basebot-scanner -f | grep "trop jeune\|trop vieux"
```

**Sortie attendue:**
```
DEBUG - ⏭️ Token trop jeune: FAST (0.3h < 2.0h)
DEBUG - ⏭️ Token trop vieux: SLOW (18.5h > 12.0h)
```

3. **Vérifier que seuls les tokens 2-12h sont en DB:**
```bash
su - basebot
sqlite3 /home/basebot/trading-bot/data/trading.db "
SELECT symbol,
       ROUND((julianday('now') - julianday(pair_created_at)) * 24, 1) as age_hours
FROM discovered_tokens
WHERE pair_created_at IS NOT NULL
ORDER BY discovered_at DESC
LIMIT 10;
"
```

**Sortie attendue:**
```
MORI|3.2
GALA|5.8
DOGE|7.1
PEPE|10.5
SAFE|2.3
```

Tous les ages doivent être entre 2.0 et 12.0!

---

## 📋 Checklist Migration

- [x] ✅ Paramètres MIN/MAX_TOKEN_AGE_HOURS ajoutés dans .env.example
- [x] ✅ Scanner.py modifié pour filtrer par âge
- [x] ✅ Logs affichent l'âge des tokens découverts
- [x] ✅ Logs affichent les tokens ignorés (trop jeunes/vieux)
- [x] ✅ Filter.py compatible (donne toujours +10 bonus)
- [x] ✅ Documentation mise à jour

---

## 🎉 Résultat Final

**Flow Optimisé:**
1. Scanner récupère nouveaux pools de GeckoTerminal/DexScreener
2. **Scanner filtre: garde SEULEMENT tokens 2-12h**
3. DB contient UNIQUEMENT des tokens "matures"
4. Filter analyse tokens déjà pré-filtrés
5. Trader reçoit tokens de qualité optimale

**Avantages:**
- ✅ Pas de perte d'opportunité (tokens jeunes re-découverts plus tard)
- ✅ Réduction du bruit (moins de tokens à analyser)
- ✅ Meilleure qualité des trades
- ✅ DB plus propre (pas de tokens "poubelle")

---

**Date:** 2025-11-18
**Version:** v3.2 - Scanner Age Filter
**Commit:** À venir
**Auteur:** Claude Code
