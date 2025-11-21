#!/bin/bash
# 🧹 Nettoyage rapide désynchronisation positions
# Usage: sudo bash cleanup_positions.sh

BOT_DIR="/home/basebot/trading-bot"
DATA_DIR="$BOT_DIR/data"
DB="$DATA_DIR/trading.db"

echo "🔍 Analyse désynchronisation..."

JSON_COUNT=$(find "$DATA_DIR" -name "position_*.json" 2>/dev/null | wc -l)
DB_COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM trade_history WHERE exit_time IS NULL;" 2>/dev/null || echo "0")

echo "   Fichiers JSON: $JSON_COUNT"
echo "   Positions DB:  $DB_COUNT"
echo ""

if [ $JSON_COUNT -eq $DB_COUNT ]; then
    echo "✅ Déjà synchronisé. Rien à faire."
    exit 0
fi

if [ $JSON_COUNT -gt $DB_COUNT ]; then
    # Cas 1: Plus de JSON que de DB → Supprimer JSON orphelins
    echo "🗑️  Suppression fichiers JSON orphelins..."
    rm -f "$DATA_DIR"/position_*.json
    echo "✅ Nettoyage terminé."
    echo ""
    echo "Redémarrage Dashboard..."
    systemctl restart basebot-dashboard
    echo "✅ Dashboard redémarré. Vérifiez dans 10 secondes."

elif [ $DB_COUNT -gt $JSON_COUNT ]; then
    # Cas 2: Plus de DB que de JSON
    echo "⚠️  Plus de positions DB que de fichiers JSON."
    echo ""

    # Vérifier âge des positions
    OLD_POSITIONS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM trade_history WHERE exit_time IS NULL AND (julianday('now') - julianday(entry_time)) * 24 > 1;" 2>/dev/null || echo "0")

    if [ $OLD_POSITIONS -gt 0 ]; then
        echo "🔴 Détecté $OLD_POSITIONS positions >1h sans JSON (probablement orphelines)"
        echo ""
        echo "Actions recommandées:"
        echo "  1. Vérifier wallet sur BaseScan: https://basescan.org/address/VOTRE_WALLET"
        echo "  2. Si positions vendues, fermer manuellement en DB:"
        echo ""
        sqlite3 "$DB" << 'EOF'
.mode column
.headers on
SELECT
    id,
    symbol,
    datetime(entry_time) as entry,
    ROUND((julianday('now') - julianday(entry_time)) * 24, 1) as hours
FROM trade_history
WHERE exit_time IS NULL
ORDER BY entry_time DESC;
EOF
        echo ""
        echo "  3. Fermer position: sqlite3 $DB \"UPDATE trade_history SET exit_time = datetime('now'), side = 'SELL' WHERE id = ID;\""
    else
        echo "🟡 Positions récentes (<1h). Recommandations:"
        echo "  1. Attendre 2-3 minutes (Trader va recréer JSON)"
        echo "  2. Ou redémarrer Trader: sudo systemctl restart basebot-trader"
    fi
fi

echo ""
echo "Status final:"
echo "  JSON: $(find "$DATA_DIR" -name "position_*.json" 2>/dev/null | wc -l)"
echo "  DB:   $(sqlite3 "$DB" "SELECT COUNT(*) FROM trade_history WHERE exit_time IS NULL;" 2>/dev/null || echo "0")"
