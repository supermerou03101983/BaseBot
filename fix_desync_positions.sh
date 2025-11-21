#!/bin/bash
# 🔧 Script diagnostic et fix désynchronisation positions JSON vs DB
# Usage: sudo bash fix_desync_positions.sh

echo "════════════════════════════════════════════════════════"
echo "  🔍 DIAGNOSTIC DÉSYNCHRONISATION POSITIONS"
echo "════════════════════════════════════════════════════════"
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BOT_DIR="/home/basebot/trading-bot"
DATA_DIR="$BOT_DIR/data"
DB="$DATA_DIR/trading.db"

# 1. Compter fichiers JSON
echo -e "${BLUE}📁 1. Fichiers position_*.json${NC}"
JSON_COUNT=$(find "$DATA_DIR" -name "position_*.json" 2>/dev/null | wc -l)
echo "   Fichiers trouvés: $JSON_COUNT"

if [ $JSON_COUNT -gt 0 ]; then
    echo "   Liste des fichiers:"
    find "$DATA_DIR" -name "position_*.json" -exec basename {} \; 2>/dev/null | while read file; do
        echo "     - $file"
    done
fi
echo ""

# 2. Compter positions ouvertes en DB
echo -e "${BLUE}💾 2. Positions ouvertes dans trade_history${NC}"
DB_OPEN_COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM trade_history WHERE exit_time IS NULL;" 2>/dev/null || echo "0")
echo "   Positions ouvertes (exit_time IS NULL): $DB_OPEN_COUNT"
echo ""

# 3. Afficher détails positions DB
if [ $DB_OPEN_COUNT -gt 0 ]; then
    echo -e "${BLUE}📊 3. Détails positions ouvertes en DB:${NC}"
    sqlite3 "$DB" << 'EOF'
.mode column
.headers on
SELECT
    id,
    symbol,
    side,
    datetime(entry_time) as entry,
    ROUND((julianday('now') - julianday(entry_time)) * 24, 1) as hours_open,
    ROUND(amount_in, 4) as amt_in,
    token_address
FROM trade_history
WHERE exit_time IS NULL
ORDER BY entry_time DESC;
EOF
    echo ""
fi

# 4. Lire contenu des fichiers JSON
if [ $JSON_COUNT -gt 0 ]; then
    echo -e "${BLUE}📄 4. Contenu fichiers JSON:${NC}"
    find "$DATA_DIR" -name "position_*.json" 2>/dev/null | while read json_file; do
        echo "   File: $(basename $json_file)"
        if command -v jq &> /dev/null; then
            # Si jq disponible, formater joliment
            jq -r '{"symbol": .symbol, "entry_time": .entry_time, "amount_in": .amount_in, "token_address": .token_address}' "$json_file" 2>/dev/null || cat "$json_file"
        else
            # Sinon, afficher brut
            cat "$json_file"
        fi
        echo ""
    done
fi

# 5. Analyser la désynchronisation
echo "════════════════════════════════════════════════════════"
echo -e "${YELLOW}  🔍 ANALYSE${NC}"
echo "════════════════════════════════════════════════════════"
echo ""

if [ $JSON_COUNT -eq $DB_OPEN_COUNT ]; then
    echo -e "${GREEN}✅ SYNCHRONISÉ: $JSON_COUNT fichiers JSON = $DB_OPEN_COUNT positions DB${NC}"
    echo ""
    echo "Aucune action requise."
else
    echo -e "${RED}❌ DÉSYNCHRONISATION DÉTECTÉE${NC}"
    echo "   Fichiers JSON: $JSON_COUNT"
    echo "   Positions DB:  $DB_OPEN_COUNT"
    echo ""

    # Diagnostiquer le type de désynchronisation
    if [ $JSON_COUNT -gt $DB_OPEN_COUNT ]; then
        echo -e "${YELLOW}⚠️  Type: Fichiers JSON orphelins (plus de JSON que de positions DB)${NC}"
        echo ""
        echo "Causes possibles:"
        echo "  • Trader a fermé position en DB mais pas supprimé le JSON"
        echo "  • Crash du Trader pendant fermeture de position"
        echo "  • Erreur d'écriture DB (position marquée fermée prématurément)"
        echo ""
        echo -e "${BLUE}Solutions proposées:${NC}"
        echo ""
        echo "Option 1: Supprimer fichiers JSON orphelins (RECOMMANDÉ)"
        echo "   Les positions sont fermées en DB, les JSON sont obsolètes"
        echo "   Commande: rm $DATA_DIR/position_*.json"
        echo ""
        echo "Option 2: Rouvrir positions en DB depuis JSON"
        echo "   Dangereux: peut créer fausses positions si tokens déjà vendus"
        echo "   À faire SEULEMENT si sûr que positions sont réellement actives"

    elif [ $DB_OPEN_COUNT -gt $JSON_COUNT ]; then
        echo -e "${YELLOW}⚠️  Type: Positions DB orphelines (plus de positions DB que de JSON)${NC}"
        echo ""
        echo "Causes possibles:"
        echo "  • Trader a créé position en DB mais pas encore écrit le JSON"
        echo "  • Fichiers JSON supprimés manuellement"
        echo "  • Permissions fichiers (Trader ne peut pas écrire JSON)"
        echo ""
        echo -e "${BLUE}Solutions proposées:${NC}"
        echo ""
        echo "Option 1: Attendre 1-2 minutes (Trader va recréer JSON)"
        echo "   Si positions sont récentes (<5min), c'est normal"
        echo ""
        echo "Option 2: Fermer positions orphelines en DB"
        echo "   Si positions sont vieilles (>1h) sans JSON, probablement déjà vendues"
        echo "   ATTENTION: Vérifier sur l'explorer blockchain avant!"
    fi

    echo ""
    echo "════════════════════════════════════════════════════════"
    echo -e "${YELLOW}  🛠️  ACTIONS CORRECTIVES${NC}"
    echo "════════════════════════════════════════════════════════"
    echo ""

    # Proposer actions en fonction du type
    if [ $JSON_COUNT -gt $DB_OPEN_COUNT ]; then
        # Plus de JSON que de DB → Supprimer JSON orphelins
        echo -e "${BLUE}Action automatique disponible: Nettoyer fichiers JSON orphelins${NC}"
        echo ""
        read -p "Voulez-vous supprimer les fichiers JSON orphelins? (o/N) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[OoYy]$ ]]; then
            echo "🗑️  Suppression des fichiers JSON..."
            rm -f "$DATA_DIR"/position_*.json
            REMAINING=$(find "$DATA_DIR" -name "position_*.json" 2>/dev/null | wc -l)
            if [ $REMAINING -eq 0 ]; then
                echo -e "${GREEN}✅ Fichiers JSON supprimés. Synchronisation rétablie!${NC}"
            else
                echo -e "${RED}❌ Erreur: $REMAINING fichiers restants${NC}"
            fi
        else
            echo "Action annulée."
        fi

    elif [ $DB_OPEN_COUNT -gt $JSON_COUNT ]; then
        # Plus de DB que de JSON → Plusieurs options
        echo -e "${YELLOW}⚠️  Actions manuelles requises${NC}"
        echo ""
        echo "Étape 1: Vérifier âge des positions DB orphelines"
        sqlite3 "$DB" << 'EOF'
SELECT
    symbol,
    ROUND((julianday('now') - julianday(entry_time)) * 24, 1) as hours_old,
    CASE
        WHEN (julianday('now') - julianday(entry_time)) * 24 < 0.1 THEN '🟢 Récente (<6min) - Normal'
        WHEN (julianday('now') - julianday(entry_time)) * 24 < 1 THEN '🟡 Modérée (<1h) - Attendre'
        ELSE '🔴 Ancienne (>1h) - Problème'
    END as status
FROM trade_history
WHERE exit_time IS NULL
ORDER BY entry_time DESC;
EOF
        echo ""
        echo "Étape 2: Décider action selon âge"
        echo "  • 🟢 Positions <6min: ATTENDRE (Trader va créer JSON)"
        echo "  • 🟡 Positions <1h: Redémarrer Trader"
        echo "  • 🔴 Positions >1h: Vérifier blockchain + fermer manuellement si vendues"
        echo ""
        echo "Commande vérification blockchain:"
        echo "  Explorer Base: https://basescan.org/address/0xVOTRE_WALLET"
        echo ""
        echo "Commande fermer position orpheline en DB (APRÈS VÉRIFICATION!):"
        echo "  sqlite3 $DB \"UPDATE trade_history SET exit_time = datetime('now'), side = 'SELL' WHERE id = ID_POSITION;\""
    fi
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo -e "${BLUE}  📋 RÉSUMÉ${NC}"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Fichiers JSON:      $JSON_COUNT"
echo "Positions DB:       $DB_OPEN_COUNT"
echo "Status:             $(if [ $JSON_COUNT -eq $DB_OPEN_COUNT ]; then echo -e "${GREEN}SYNC${NC}"; else echo -e "${RED}DESYNC${NC}"; fi)"
echo ""
echo "Après correction, redémarrer Dashboard:"
echo "  sudo systemctl restart basebot-dashboard"
echo ""
