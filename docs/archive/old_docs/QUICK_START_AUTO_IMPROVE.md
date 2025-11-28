# 🚀 Guide de Démarrage Rapide - Système d'Amélioration Autonome

## ✅ Test de Connexion VPS - RÉUSSI

Le système a été testé avec succès :
- ✓ Connexion SSH au VPS établie (46.62.194.176)
- ✓ Base de données accessible
- ✓ Structure du projet correcte
- ✓ Script principal fonctionnel

## ⚠️ État Actuel

**Services VPS**: INACTIFS (arrêtés)
**Trades dans la DB**: 0

Le bot n'a pas encore de données de trading à analyser.

---

## 📋 Prochaines Étapes

### Étape 1: Démarrer le Bot sur le VPS

```bash
# Méthode 1: Via SSH direct
ssh root@46.62.194.176
cd /home/basebot/trading-bot
sudo systemctl start basebot-scanner
sudo systemctl start basebot-filter
sudo systemctl start basebot-trader
sudo systemctl start basebot-dashboard

# Vérifier que tout fonctionne
systemctl status basebot-trader

# Quitter SSH
exit
```

**OU**

```bash
# Méthode 2: Via script existant (depuis votre Mac)
sshpass -p "000Rnella" ssh root@46.62.194.176 << 'EOF'
cd /home/basebot/trading-bot
sudo systemctl start basebot-scanner
sudo systemctl start basebot-filter
sudo systemctl start basebot-trader
sudo systemctl start basebot-dashboard
echo "✓ Services démarrés"
EOF
```

### Étape 2: Vérifier que le Bot Trade

```bash
# Suivre les logs en temps réel
ssh root@46.62.194.176
tail -f /home/basebot/trading-bot/logs/trader.log

# Ou depuis votre Mac
sshpass -p "000Rnella" ssh root@46.62.194.176 "tail -f /home/basebot/trading-bot/logs/trader.log"
```

**Ce que vous devriez voir**:
- Scanner découvre des tokens
- Filter approuve/rejette des tokens
- Trader entre en position sur les tokens approuvés

### Étape 3: Attendre 5+ Trades

Le système a besoin d'au moins **5 trades fermés** pour faire une analyse statistiquement valide.

**Durée estimée**:
- Configuration actuelle : Maximum 3 trades/jour
- Temps minimum : **2 jours** (pour avoir 5-6 trades)

**Pendant ce temps**, vous pouvez:
- Monitorer le dashboard : `http://46.62.194.176:8501`
- Suivre les logs
- Vérifier que tout fonctionne bien

### Étape 4: Lancer votre Premier Cycle d'Amélioration

Une fois que vous avez **5+ trades fermés** :

```bash
cd /Users/vincentdoms/Documents/BaseBot
./claude_auto_improve.sh
```

Le script va :
1. Se connecter au VPS
2. Récupérer les données (DB + logs)
3. Analyser les performances
4. Si les objectifs ne sont pas atteints → Mode interactif avec Claude
5. Claude propose des optimisations
6. Déploiement automatisé

---

## 🎯 Objectifs de Performance (Rappel)

Le système optimise pour atteindre :
- **Win-rate**: ≥70%
- **Profit moyen**: ≥15% par trade gagnant
- **Perte moyenne**: ≤15% par trade perdant
- **Trades/jour**: ≥3

---

## 🔧 Commandes Utiles

### Vérifier l'état du bot

```bash
# Status complet
sshpass -p "000Rnella" ssh root@46.62.194.176 "cd /home/basebot/trading-bot && ./status.sh"

# Nombre de trades
sshpass -p "000Rnella" ssh root@46.62.194.176 "sqlite3 /home/basebot/trading-bot/data/trading.db 'SELECT COUNT(*) FROM trade_history WHERE exit_time IS NOT NULL;'"
```

### Voir les derniers trades

```bash
sshpass -p "000Rnella" ssh root@46.62.194.176 "sqlite3 /home/basebot/trading-bot/data/trading.db 'SELECT symbol, entry_time, exit_time, profit_loss FROM trade_history WHERE exit_time IS NOT NULL ORDER BY exit_time DESC LIMIT 10;'"
```

### Redémarrer le bot

```bash
sshpass -p "000Rnella" ssh root@46.62.194.176 << 'EOF'
cd /home/basebot/trading-bot
sudo systemctl restart basebot-scanner
sudo systemctl restart basebot-filter
sudo systemctl restart basebot-trader
echo "✓ Bot redémarré"
EOF
```

### Arrêter le bot

```bash
sshpass -p "000Rnella" ssh root@46.62.194.176 << 'EOF'
sudo systemctl stop basebot-scanner
sudo systemctl stop basebot-filter
sudo systemctl stop basebot-trader
echo "✓ Bot arrêté"
EOF
```

---

## 📊 Tableau de Bord

Une fois le bot démarré, accédez au dashboard :

**URL**: http://46.62.194.176:8501

Le dashboard affiche :
- Positions ouvertes en temps réel
- Historique des trades
- Performance globale
- Graphiques de P&L

---

## 🐛 Troubleshooting

### Le bot ne trouve aucun token

**Problème**: Critères trop stricts

**Solution**:
- Vérifiez les logs du filter : `tail -f /home/basebot/trading-bot/logs/filter.log`
- Si tous les tokens sont rejetés, les critères sont peut-être trop stricts
- Attendez le premier cycle d'amélioration, Claude ajustera automatiquement

### Le bot trouve des tokens mais ne trade pas

**Problème**: Paper trading activé OU pas assez de capital

**Solution**:
```bash
# Vérifier le mode de trading
sshpass -p "000Rnella" ssh root@46.62.194.176 "cat /home/basebot/trading-bot/config/trading_mode.json"

# Si paper mode, passer en real trading via le dashboard
# Ou modifier directement :
sshpass -p "000Rnella" ssh root@46.62.194.176 "echo '{\"mode\": \"real\"}' > /home/basebot/trading-bot/config/trading_mode.json"
```

### Services qui crashent

**Problème**: Erreur dans le code ou configuration

**Solution**:
```bash
# Voir les logs d'erreur
sshpass -p "000Rnella" ssh root@46.62.194.176 "journalctl -u basebot-trader -n 50"

# Voir les erreurs Python
sshpass -p "000Rnella" ssh root@46.62.194.176 "tail -n 50 /home/basebot/trading-bot/logs/trader_error.log"
```

---

## 📱 Configuration Telegram (Optionnel)

Votre webhook Telegram est déjà configuré dans `vps_credentials.conf`.

Pour tester :
```bash
source vps_credentials.conf
curl -X POST "${TELEGRAM_WEBHOOK}&text=Test notification BaseBot"
```

Vous devriez recevoir un message Telegram !

---

## 🔄 Cycle d'Amélioration Continue

Une fois que vous avez des trades :

```
1. ./claude_auto_improve.sh
   ↓
2. Analyse automatique
   ↓
3. Claude propose optimisations
   ↓
4. Validation manuelle
   ↓
5. Déploiement automatique
   ↓
6. Attendre 5+ nouveaux trades
   ↓
7. Retour à l'étape 1
```

Chaque cycle améliore la stratégie de manière empirique, en apprenant des résultats précédents.

---

## 📚 Documentation Complète

- **Guide complet**: [AUTO_IMPROVEMENT_README.md](AUTO_IMPROVEMENT_README.md)
- **Historique des modifications**: [auto_improvement_history.md](auto_improvement_history.md)
- **Configuration initiale**: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)

---

## ✅ Checklist de Démarrage

- [x] Connexion VPS testée
- [x] Script d'amélioration créé
- [x] Credentials configurés
- [ ] Services VPS démarrés
- [ ] Bot en train de trader
- [ ] 5+ trades fermés dans la DB
- [ ] Premier cycle d'optimisation lancé

---

**Prochaine action**: Démarrer les services sur le VPS et laisser le bot accumuler des trades !

```bash
# Commande rapide pour tout démarrer
sshpass -p "000Rnella" ssh root@46.62.194.176 << 'EOF'
cd /home/basebot/trading-bot
sudo systemctl start basebot-scanner
sudo systemctl start basebot-filter
sudo systemctl start basebot-trader
sudo systemctl start basebot-dashboard
sleep 3
systemctl status basebot-trader | head -n 10
echo ""
echo "✓ Bot démarré ! Dashboard: http://46.62.194.176:8501"
EOF
```

---

**Date**: 2025-11-25
**Status**: Système prêt, en attente de données de trading
