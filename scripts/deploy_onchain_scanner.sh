#!/bin/bash
# Script de déploiement automatique du scanner on-chain

set -e

VPS_HOST="root@46.62.194.176"
VPS_PASSWORD="000Rnella"
TRADING_BOT_DIR="/home/basebot/trading-bot"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔥 DÉPLOIEMENT SCANNER ON-CHAIN - Modification #5"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Pull depuis Git sur le VPS
echo "📥 1/5 - Pull depuis Git sur VPS..."
sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no $VPS_HOST << 'REMOTE'
cd /home/basebot/trading-bot
echo "  📍 Répertoire: $(pwd)"
echo "  🔄 Git pull..."
git pull origin main
if [ $? -eq 0 ]; then
    echo "  ✅ Git pull réussi"
else
    echo "  ❌ Erreur git pull"
    exit 1
fi
REMOTE

echo ""

# 2. Vérifier les fichiers déployés
echo "📋 2/5 - Vérification des fichiers..."
sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no $VPS_HOST << 'REMOTE'
cd /home/basebot/trading-bot

echo "  🔍 Vérification pair_event_window_scanner.py..."
if [ -f "src/pair_event_window_scanner.py" ]; then
    echo "  ✅ pair_event_window_scanner.py présent"
else
    echo "  ❌ pair_event_window_scanner.py MANQUANT"
    exit 1
fi

echo "  🔍 Vérification Scanner.py..."
if grep -q "PairEventWindowScanner" "src/Scanner.py"; then
    echo "  ✅ Scanner.py contient l'import PairEventWindowScanner"
else
    echo "  ❌ Scanner.py ne contient pas PairEventWindowScanner"
    exit 1
fi

echo "  🔍 Vérification syntaxe Python..."
source venv/bin/activate
python3 -m py_compile src/pair_event_window_scanner.py
python3 -m py_compile src/Scanner.py
if [ $? -eq 0 ]; then
    echo "  ✅ Syntaxe Python OK"
else
    echo "  ❌ Erreur de syntaxe Python"
    exit 1
fi
REMOTE

echo ""

# 3. Mettre à jour la configuration .env
echo "⚙️  3/5 - Mise à jour configuration .env..."
sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no $VPS_HOST << 'REMOTE'
cd /home/basebot/trading-bot/config

echo "  📝 Backup .env..."
cp .env .env.backup_mod5_$(date +%Y%m%d_%H%M%S)

echo "  🔧 Mise à jour MIN_TOKEN_AGE_HOURS..."
sed -i 's/MIN_TOKEN_AGE_HOURS=0.1/MIN_TOKEN_AGE_HOURS=2/' .env
sed -i 's/MIN_TOKEN_AGE_HOURS=0.5/MIN_TOKEN_AGE_HOURS=2/' .env

echo "  🔧 Mise à jour RPC_URL..."
sed -i 's|RPC_URL=https://base.drpc.org|RPC_URL=https://base.llamarpc.com|' .env
sed -i 's|RPC_URL=https://mainnet.base.org|RPC_URL=https://base.llamarpc.com|' .env

echo "  ✅ Configuration mise à jour:"
grep -E "MIN_TOKEN_AGE_HOURS|MAX_TOKEN_AGE_HOURS|RPC_URL" .env | head -n 3
REMOTE

echo ""

# 4. Redémarrer les services
echo "🔄 4/5 - Redémarrage du scanner..."
sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no $VPS_HOST << 'REMOTE'
echo "  ⏸️  Arrêt du scanner..."
systemctl stop basebot-scanner
sleep 3

echo "  ▶️  Démarrage du scanner..."
systemctl start basebot-scanner
sleep 5

echo "  📊 État du service:"
systemctl status basebot-scanner --no-pager | grep -E "Active:|Main PID:" | head -n 2
REMOTE

echo ""

# 5. Vérifier les logs
echo "📈 5/5 - Vérification des logs..."
sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no $VPS_HOST << 'REMOTE'
echo "  🔍 Recherche 'Scanner on-chain initialisé'..."
timeout 10 tail -f /home/basebot/trading-bot/logs/scanner.log 2>/dev/null | grep -m 1 "Scanner on-chain initialisé" || echo "  (attendre le prochain cycle...)"

echo ""
echo "  📋 Dernières lignes du log:"
tail -n 10 /home/basebot/trading-bot/logs/scanner.log
REMOTE

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DÉPLOIEMENT TERMINÉ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Commandes de monitoring:"
echo "   • Logs en temps réel:   ssh $VPS_HOST 'tail -f $TRADING_BOT_DIR/logs/scanner.log'"
echo "   • État services:        ssh $VPS_HOST 'systemctl status basebot-scanner basebot-filter'"
echo "   • Tokens détectés:      ssh $VPS_HOST 'grep \"tokens on-chain enrichis\" $TRADING_BOT_DIR/logs/scanner.log | tail -n 5'"
echo ""
