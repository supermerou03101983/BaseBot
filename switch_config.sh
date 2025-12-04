#!/bin/bash
# Script pour basculer entre les configurations .env

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$PROJECT_DIR/config"
ENV_FILE="$CONFIG_DIR/.env"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔄 BaseBot - Switch Configuration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier si .env existe déjà
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠️  Fichier .env existant détecté${NC}"
    echo ""

    # Afficher les paramètres clés de la config actuelle
    echo -e "${BLUE}📊 Configuration actuelle:${NC}"

    MIN_AGE=$(grep "^MIN_AGE_HOURS=" "$ENV_FILE" | cut -d'=' -f2 || echo "N/A")
    MAX_AGE=$(grep "^MAX_AGE_HOURS=" "$ENV_FILE" | cut -d'=' -f2 || echo "N/A")
    MIN_LIQ=$(grep "^MIN_LIQUIDITY_USD=" "$ENV_FILE" | cut -d'=' -f2 || echo "N/A")
    MIN_HOLDERS=$(grep "^MIN_HOLDERS=" "$ENV_FILE" | cut -d'=' -f2 || echo "N/A")

    echo "  • Fenêtre âge: ${MIN_AGE}h - ${MAX_AGE}h"
    echo "  • Liquidité min: \$${MIN_LIQ}"
    echo "  • Holders min: ${MIN_HOLDERS}"
    echo ""

    # Créer backup
    BACKUP_FILE="$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$ENV_FILE" "$BACKUP_FILE"
    echo -e "${GREEN}✅ Backup créé: $(basename $BACKUP_FILE)${NC}"
    echo ""
fi

# Menu de sélection
echo -e "${BLUE}📋 Configurations disponibles:${NC}"
echo ""
echo "  1) Momentum Safe v2 (PRODUCTION)"
echo "     • Fenêtre: 3.5-8h"
echo "     • Liquidité: \$12K-\$2M"
echo "     • Holders: ≥120"
echo "     • Win-rate cible: ≥70%"
echo "     • Trades/jour: 2-5"
echo ""
echo "  2) Test Permissif (TESTS RAPIDES)"
echo "     • Fenêtre: 0-72h (tous tokens)"
echo "     • Liquidité: \$500+"
echo "     • Holders: ≥10"
echo "     • Win-rate attendu: 10-30%"
echo "     • Trades/jour: 10-20"
echo ""
echo "  3) Annuler"
echo ""

read -p "Votre choix [1-3]: " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}📝 Application: Momentum Safe v2 (PRODUCTION)${NC}"
        cp "$CONFIG_DIR/.env.example" "$ENV_FILE"

        # Afficher rappel
        echo ""
        echo -e "${YELLOW}⚠️  N'oubliez pas de remplir:${NC}"
        echo "  • WALLET_ADDRESS"
        echo "  • PRIVATE_KEY"
        echo "  • BIRDEYE_API_KEY"
        echo "  • DRPC_API_KEY (pour protection MEV)"
        echo ""
        echo -e "${BLUE}Stratégie: Momentum Safe v2 (3.5-8h, critères stricts)${NC}"
        echo -e "${GREEN}✅ Configuration appliquée !${NC}"
        ;;

    2)
        echo ""
        echo -e "${GREEN}📝 Application: Test Permissif (TESTS RAPIDES)${NC}"
        cp "$CONFIG_DIR/.env.test.permissif" "$ENV_FILE"

        # Afficher rappel
        echo ""
        echo -e "${YELLOW}⚠️  N'oubliez pas de remplir:${NC}"
        echo "  • WALLET_ADDRESS"
        echo "  • PRIVATE_KEY"
        echo "  • BIRDEYE_API_KEY"
        echo ""
        echo -e "${RED}⚠️  MODE TEST: Win-rate bas attendu (10-30%)${NC}"
        echo -e "${YELLOW}🎯 Objectif: Valider workflow Scanner→Filter→Trader${NC}"
        echo -e "${GREEN}✅ Configuration appliquée !${NC}"
        ;;

    3)
        echo ""
        echo -e "${BLUE}❌ Annulé - Aucun changement effectué${NC}"
        exit 0
        ;;

    *)
        echo ""
        echo -e "${RED}❌ Choix invalide${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📌 Prochaines étapes:${NC}"
echo ""
echo "  1. Éditer le fichier .env avec vos clés:"
echo "     nano $ENV_FILE"
echo ""
echo "  2. Redémarrer les services (si VPS):"
echo "     sudo systemctl restart basebot-scanner"
echo "     sudo systemctl restart basebot-filter"
echo "     sudo systemctl restart basebot-trader"
echo ""
echo "  3. Vérifier les logs:"
echo "     tail -f /home/basebot/trading-bot/logs/scanner.log"
echo "     tail -f /home/basebot/trading-bot/logs/filter.log"
echo "     tail -f /home/basebot/trading-bot/logs/trader.log"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
