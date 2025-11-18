#!/bin/bash
# Quick Fix: Ajouter les colonnes manquantes à la DB existante

echo "🔧 Quick Fix: Ajout des colonnes pair_created_at et volume_24h"
echo "============================================================"

DB_PATH="/home/basebot/trading-bot/data/trading.db"

if [ ! -f "$DB_PATH" ]; then
    echo "❌ Base de données non trouvée: $DB_PATH"
    exit 1
fi

echo "📊 Vérification des colonnes actuelles..."
sqlite3 "$DB_PATH" "PRAGMA table_info(discovered_tokens);"

echo ""
echo "➕ Ajout de pair_created_at si manquante..."
sqlite3 "$DB_PATH" "ALTER TABLE discovered_tokens ADD COLUMN pair_created_at TIMESTAMP;" 2>/dev/null && echo "✅ Colonne pair_created_at ajoutée" || echo "ℹ️  Colonne pair_created_at déjà présente"

echo "➕ Ajout de volume_24h si manquante..."
sqlite3 "$DB_PATH" "ALTER TABLE discovered_tokens ADD COLUMN volume_24h REAL;" 2>/dev/null && echo "✅ Colonne volume_24h ajoutée" || echo "ℹ️  Colonne volume_24h déjà présente"

echo ""
echo "✅ Vérification finale:"
sqlite3 "$DB_PATH" "PRAGMA table_info(discovered_tokens);" | grep -E "(pair_created_at|volume_24h)"

echo ""
echo "🎉 Fix terminé! Redémarrez le scanner:"
echo "   sudo systemctl restart basebot-scanner"
