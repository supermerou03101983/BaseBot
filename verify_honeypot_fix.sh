#!/bin/bash
# 🔍 Script de vérification du fix Honeypot
# Usage: sudo bash verify_honeypot_fix.sh

echo "════════════════════════════════════════════════════════"
echo "  🔍 VÉRIFICATION FIX HONEYPOT"
echo "════════════════════════════════════════════════════════"
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Vérifier version code
echo "📦 1. Version du code..."
cd /home/basebot/trading-bot
COMMIT=$(git rev-parse --short HEAD)
if [ "$COMMIT" == "da77f25" ] || git log --oneline | grep -q "FIX CRITIQUE: Implémentation vraie détection Honeypot"; then
    echo -e "${GREEN}✅ Code à jour (commit: $COMMIT)${NC}"
else
    echo -e "${RED}❌ Code pas à jour! Faire: git pull origin main${NC}"
    exit 1
fi
echo ""

# 2. Vérifier services actifs
echo "🔧 2. Status des services..."
for service in basebot-filter basebot-trader; do
    if systemctl is-active --quiet $service; then
        echo -e "${GREEN}✅ $service: running${NC}"
    else
        echo -e "${RED}❌ $service: not running${NC}"
        echo "   Lancer: sudo systemctl start $service"
    fi
done
echo ""

# 3. Vérifier code honeypot dans Filter.py
echo "📝 3. Vérification code Filter.py..."
if grep -q "REJET: Honeypot détecté" /home/basebot/trading-bot/src/Filter.py; then
    echo -e "${GREEN}✅ Auto-rejet honeypot présent dans Filter.py${NC}"
else
    echo -e "${RED}❌ Code auto-rejet manquant!${NC}"
fi
echo ""

# 4. Vérifier code API Honeypot.is dans web3_utils.py
echo "📝 4. Vérification code web3_utils.py..."
if grep -q "api.honeypot.is" /home/basebot/trading-bot/src/web3_utils.py; then
    echo -e "${GREEN}✅ API Honeypot.is intégrée dans web3_utils.py${NC}"
else
    echo -e "${RED}❌ API Honeypot.is manquante!${NC}"
fi
echo ""

# 5. Vérifier logs Filter (30 dernières minutes)
echo "📊 5. Analyse logs Filter (30 dernières minutes)..."
HONEYPOT_REJECTS=$(journalctl -u basebot-filter --since "30 minutes ago" | grep -c "REJET: Honeypot" || echo "0")
TOKEN_ANALYSES=$(journalctl -u basebot-filter --since "30 minutes ago" | grep -c "Analyse:" || echo "0")
APPROVED=$(journalctl -u basebot-filter --since "30 minutes ago" | grep -c "Token APPROUVE" || echo "0")

echo "   Tokens analysés: $TOKEN_ANALYSES"
echo "   Honeypots rejetés: $HONEYPOT_REJECTS"
echo "   Tokens approuvés: $APPROVED"

if [ "$TOKEN_ANALYSES" -gt 0 ]; then
    echo -e "${GREEN}✅ Filter fonctionne (tokens analysés)${NC}"
    if [ "$HONEYPOT_REJECTS" -gt 0 ]; then
        echo -e "${GREEN}✅ Honeypots détectés et rejetés!${NC}"
    else
        echo -e "${YELLOW}⚠️  Aucun honeypot détecté (normal si tokens légitimes)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Aucun token analysé dans les 30 dernières minutes${NC}"
fi
echo ""

# 6. Vérifier configuration .env
echo "⚙️  6. Configuration .env..."
ENV_FILE="/home/basebot/trading-bot/config/.env"

MIN_VOL=$(grep "^MIN_VOLUME_24H=" $ENV_FILE | cut -d'=' -f2)
GRACE_ENABLED=$(grep "^GRACE_PERIOD_ENABLED=" $ENV_FILE | cut -d'=' -f2)
GRACE_MINUTES=$(grep "^GRACE_PERIOD_MINUTES=" $ENV_FILE | cut -d'=' -f2)

echo "   MIN_VOLUME_24H: $MIN_VOL"
echo "   GRACE_PERIOD_ENABLED: $GRACE_ENABLED"
echo "   GRACE_PERIOD_MINUTES: $GRACE_MINUTES"

if [ "$MIN_VOL" -le 5000 ]; then
    echo -e "${GREEN}✅ MIN_VOLUME_24H adapté pour h6 réel${NC}"
else
    echo -e "${YELLOW}⚠️  MIN_VOLUME_24H=$MIN_VOL peut être trop strict (recommandé: 3000-5000)${NC}"
fi

if [ "$GRACE_ENABLED" == "true" ]; then
    echo -e "${GREEN}✅ Grace period activée${NC}"
else
    echo -e "${RED}❌ CRITIQUE: Grace period désactivée! Risque de sorties immédiates${NC}"
    echo "   Modifier dans .env: GRACE_PERIOD_ENABLED=true"
fi
echo ""

# 7. Vérifier base de données
echo "💾 7. Analyse base de données..."
DB="/home/basebot/trading-bot/data/trading.db"

if [ -f "$DB" ]; then
    # Tokens approuvés dernière heure
    APPROVED_1H=$(sqlite3 $DB "SELECT COUNT(*) FROM approved_tokens WHERE datetime(approved_at) > datetime('now', '-1 hours');" 2>/dev/null || echo "0")

    # Trades dernières 24h
    TRADES_24H=$(sqlite3 $DB "SELECT COUNT(*) FROM trades WHERE datetime(entry_time) > datetime('now', '-24 hours');" 2>/dev/null || echo "0")

    # Trades avec pertes <0.1h (suspect honeypot)
    SUSPECT_TRADES=$(sqlite3 $DB "SELECT COUNT(*) FROM trades WHERE datetime(entry_time) > datetime('now', '-24 hours') AND (julianday(exit_time) - julianday(entry_time)) * 24 < 0.1 AND profit_loss_percent < 0;" 2>/dev/null || echo "0")

    echo "   Tokens approuvés (1h): $APPROVED_1H"
    echo "   Trades (24h): $TRADES_24H"
    echo "   Trades suspects (<0.1h + perte): $SUSPECT_TRADES"

    if [ "$SUSPECT_TRADES" -eq 0 ]; then
        echo -e "${GREEN}✅ Aucun trade suspect (honeypot bloqué)${NC}"
    else
        echo -e "${YELLOW}⚠️  $SUSPECT_TRADES trades suspects détectés${NC}"
    fi
else
    echo -e "${RED}❌ Base de données non trouvée!${NC}"
fi
echo ""

# 8. Résumé final
echo "════════════════════════════════════════════════════════"
echo "  📋 RÉSUMÉ"
echo "════════════════════════════════════════════════════════"

CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Compter les checks
[ "$COMMIT" == "da77f25" ] || git log --oneline | grep -q "FIX CRITIQUE" && ((CHECKS_PASSED++)) || ((CHECKS_FAILED++))
systemctl is-active --quiet basebot-filter && ((CHECKS_PASSED++)) || ((CHECKS_FAILED++))
systemctl is-active --quiet basebot-trader && ((CHECKS_PASSED++)) || ((CHECKS_FAILED++))
grep -q "REJET: Honeypot" /home/basebot/trading-bot/src/Filter.py && ((CHECKS_PASSED++)) || ((CHECKS_FAILED++))
grep -q "api.honeypot.is" /home/basebot/trading-bot/src/web3_utils.py && ((CHECKS_PASSED++)) || ((CHECKS_FAILED++))
[ "$GRACE_ENABLED" == "true" ] && ((CHECKS_PASSED++)) || ((CHECKS_FAILED++))

echo ""
echo -e "${GREEN}✅ Checks réussis: $CHECKS_PASSED${NC}"
echo -e "${RED}❌ Checks échoués: $CHECKS_FAILED${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════"
    echo "  ✅ FIX HONEYPOT VALIDÉ - SYSTÈME OPÉRATIONNEL"
    echo "════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "📊 Surveillance recommandée (24h):"
    echo "   sudo journalctl -u basebot-filter --follow"
    echo ""
    echo "📈 Analyse performance:"
    echo "   bot-analyze"
else
    echo -e "${RED}════════════════════════════════════════════════════════"
    echo "  ❌ PROBLÈMES DÉTECTÉS - CORRIGER AVANT PRODUCTION"
    echo "════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Actions recommandées:"
    echo "   1. git pull origin main"
    echo "   2. systemctl restart basebot-filter basebot-trader"
    echo "   3. Vérifier .env (GRACE_PERIOD_ENABLED=true)"
fi

echo ""
