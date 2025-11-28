#!/bin/bash

################################################################################
# CLAUDE AUTO-IMPROVE - Script d'amélioration autonome du bot de trading
#
# Ce script se connecte au VPS, récupère les données, analyse les performances,
# et guide Claude dans l'optimisation de la stratégie de trading.
#
# Usage: ./claude_auto_improve.sh
################################################################################

set -e  # Arrête le script en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_DIR="$SCRIPT_DIR/temp_vps_data"
ANALYSIS_FILE="$SCRIPT_DIR/data/performance_analysis.json"
HISTORY_FILE="$SCRIPT_DIR/auto_improvement_history.md"

# Credentials (seront chargés depuis vps_credentials.conf)
VPS_IP=""
VPS_USER=""
VPS_PASSWORD=""
TELEGRAM_WEBHOOK=""
HETZNER_API_TOKEN=""

################################################################################
# Fonctions utilitaires
################################################################################

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║          🤖 CLAUDE AUTO-IMPROVE - Trading Bot Optimizer          ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

################################################################################
# Chargement de la configuration
################################################################################

load_config() {
    print_step "Chargement de la configuration..."

    local config_file="$SCRIPT_DIR/vps_credentials.conf"

    if [[ ! -f "$config_file" ]]; then
        print_error "Fichier de configuration non trouvé: $config_file"
        echo ""
        echo "Créez le fichier vps_credentials.conf avec le contenu suivant:"
        echo ""
        echo "VPS_IP=46.62.194.176"
        echo "VPS_USER=root"
        echo "VPS_PASSWORD=000Rnella"
        echo "TELEGRAM_WEBHOOK=https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage?chat_id=<YOUR_CHAT_ID>"
        echo "HETZNER_API_TOKEN=s63k7xSJu34NTKHZ9iS3RmFQ6Gae2gRal1A7MIMb297DEI8oq8cSP9p1CinhsnYm"
        echo ""
        exit 1
    fi

    # Charge les variables
    source "$config_file"

    # Vérifie que les variables essentielles sont définies
    if [[ -z "$VPS_IP" || -z "$VPS_USER" || -z "$VPS_PASSWORD" ]]; then
        print_error "Configuration VPS incomplète dans $config_file"
        exit 1
    fi

    print_success "Configuration chargée"
    print_info "VPS: $VPS_USER@$VPS_IP"
}

################################################################################
# Connexion et diagnostic VPS
################################################################################

check_vps_connection() {
    print_step "Vérification de la connexion au VPS..."

    # Test de connexion SSH (avec timeout)
    if sshpass -p "$VPS_PASSWORD" ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
        "$VPS_USER@$VPS_IP" "echo 'Connection OK'" &>/dev/null; then
        print_success "Connexion VPS établie"
        return 0
    else
        print_error "Impossible de se connecter au VPS"
        print_info "Vérifiez que sshpass est installé: brew install sshpass"
        exit 1
    fi
}

check_vps_services() {
    print_step "Vérification des services sur le VPS..."

    local services_status=$(sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no \
        "$VPS_USER@$VPS_IP" << 'EOF'
echo "=== SERVICES STATUS ==="
systemctl is-active basebot-scanner 2>/dev/null || echo "scanner: INACTIVE"
systemctl is-active basebot-filter 2>/dev/null || echo "filter: INACTIVE"
systemctl is-active basebot-trader 2>/dev/null || echo "trader: INACTIVE"
systemctl is-active basebot-dashboard 2>/dev/null || echo "dashboard: INACTIVE"
echo ""
echo "=== RECENT ERRORS (last 20 lines) ==="
tail -n 20 /home/basebot/trading-bot/logs/trader_error.log 2>/dev/null || echo "No error log"
EOF
)

    echo "$services_status"

    # Vérifie si tous les services sont actifs
    if echo "$services_status" | grep -q "INACTIVE"; then
        print_warning "Certains services ne sont pas actifs"

        read -p "$(echo -e ${YELLOW}Voulez-vous redémarrer les services inactifs? [y/N]:${NC} )" -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            restart_vps_services
        fi
    else
        print_success "Tous les services sont actifs"
    fi
}

restart_vps_services() {
    print_step "Redémarrage des services sur le VPS..."

    sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no \
        "$VPS_USER@$VPS_IP" << 'EOF'
sudo systemctl restart basebot-scanner
sudo systemctl restart basebot-filter
sudo systemctl restart basebot-trader
sudo systemctl restart basebot-dashboard
echo "Services redémarrés"
EOF

    print_success "Services redémarrés"
    sleep 3  # Attend que les services démarrent
}

################################################################################
# Récupération des données du VPS
################################################################################

fetch_vps_data() {
    print_step "Récupération des données du VPS..."

    # Crée le répertoire temporaire
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"

    # Récupère la base de données
    print_info "Téléchargement de la base de données..."
    sshpass -p "$VPS_PASSWORD" scp -o StrictHostKeyChecking=no \
        "$VPS_USER@$VPS_IP:/home/basebot/trading-bot/data/trading.db" \
        "$TEMP_DIR/" || {
        print_warning "Impossible de récupérer trading.db"
    }

    # Récupère les logs
    print_info "Téléchargement des logs..."
    sshpass -p "$VPS_PASSWORD" scp -o StrictHostKeyChecking=no \
        "$VPS_USER@$VPS_IP:/home/basebot/trading-bot/logs/trader.log" \
        "$TEMP_DIR/" 2>/dev/null || print_warning "trader.log non disponible"

    sshpass -p "$VPS_PASSWORD" scp -o StrictHostKeyChecking=no \
        "$VPS_USER@$VPS_IP:/home/basebot/trading-bot/logs/trader_error.log" \
        "$TEMP_DIR/" 2>/dev/null || print_warning "trader_error.log non disponible"

    sshpass -p "$VPS_PASSWORD" scp -o StrictHostKeyChecking=no \
        "$VPS_USER@$VPS_IP:/home/basebot/trading-bot/logs/filter.log" \
        "$TEMP_DIR/" 2>/dev/null || print_warning "filter.log non disponible"

    sshpass -p "$VPS_PASSWORD" scp -o StrictHostKeyChecking=no \
        "$VPS_USER@$VPS_IP:/home/basebot/trading-bot/logs/scanner.log" \
        "$TEMP_DIR/" 2>/dev/null || print_warning "scanner.log non disponible"

    # Récupère le .env actuel
    print_info "Téléchargement de la configuration actuelle..."
    sshpass -p "$VPS_PASSWORD" scp -o StrictHostKeyChecking=no \
        "$VPS_USER@$VPS_IP:/home/basebot/trading-bot/config/.env" \
        "$TEMP_DIR/.env.vps" 2>/dev/null || print_warning "config/.env non disponible"

    print_success "Données récupérées dans $TEMP_DIR"
}

################################################################################
# Analyse des performances
################################################################################

analyze_performance() {
    print_step "Analyse des performances de trading..."

    # Copie la base de données téléchargée dans data/ pour l'analyse
    if [[ -f "$TEMP_DIR/trading.db" ]]; then
        cp "$TEMP_DIR/trading.db" "$SCRIPT_DIR/data/trading.db"
        print_success "Base de données copiée"
    else
        print_error "Base de données non trouvée dans $TEMP_DIR"
        return 1
    fi

    # Lance l'analyse Python
    print_info "Exécution de l'analyseur de performance..."

    if python3 "$SCRIPT_DIR/auto_strategy_optimizer.py"; then
        print_success "Analyse terminée - Objectifs atteints!"
        return 0
    else
        local exit_code=$?
        if [[ $exit_code -eq 2 ]]; then
            print_warning "Analyse terminée - Optimisation requise"
            return 2
        else
            print_error "Erreur lors de l'analyse"
            return 1
        fi
    fi
}

################################################################################
# Affichage des logs récents
################################################################################

show_recent_logs() {
    print_step "Logs récents du trader..."

    if [[ -f "$TEMP_DIR/trader.log" ]]; then
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        tail -n 30 "$TEMP_DIR/trader.log"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    fi

    if [[ -f "$TEMP_DIR/trader_error.log" ]] && [[ -s "$TEMP_DIR/trader_error.log" ]]; then
        print_step "Erreurs récentes..."
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        tail -n 20 "$TEMP_DIR/trader_error.log"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    fi
}

################################################################################
# Interface interactive avec Claude
################################################################################

interactive_optimization() {
    print_step "Mode d'optimisation interactif avec Claude"

    echo ""
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  L'analyse de performance est terminée.                          ║${NC}"
    echo -e "${YELLOW}║  Les données sont disponibles pour votre analyse.                ║${NC}"
    echo -e "${YELLOW}║                                                                   ║${NC}"
    echo -e "${YELLOW}║  Fichiers clés:                                                   ║${NC}"
    echo -e "${YELLOW}║  - data/performance_analysis.json (métriques)                     ║${NC}"
    echo -e "${YELLOW}║  - auto_improvement_history.md (historique)                       ║${NC}"
    echo -e "${YELLOW}║  - temp_vps_data/trading.db (base de données)                     ║${NC}"
    echo -e "${YELLOW}║  - temp_vps_data/*.log (logs du VPS)                              ║${NC}"
    echo -e "${YELLOW}║                                                                   ║${NC}"
    echo -e "${YELLOW}║  ${CYAN}Vous pouvez maintenant utiliser Claude Code pour:${YELLOW}            ║${NC}"
    echo -e "${YELLOW}║  1. Analyser les résultats en détail                             ║${NC}"
    echo -e "${YELLOW}║  2. Proposer des optimisations de stratégie                      ║${NC}"
    echo -e "${YELLOW}║  3. Modifier les paramètres dans config/.env                     ║${NC}"
    echo -e "${YELLOW}║  4. Committer et déployer les changements                        ║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Affiche un résumé de l'analyse si le fichier JSON existe
    if [[ -f "$ANALYSIS_FILE" ]]; then
        print_info "Résumé de l'analyse:"
        python3 -c "
import json
with open('$ANALYSIS_FILE') as f:
    data = json.load(f)
    analysis = data['analysis']

    print(f\"  Total trades: {analysis['total_trades']}\")
    print(f\"  Win-rate: {analysis['win_rate']}% (objectif: ≥70%)\")
    print(f\"  Profit moyen: {analysis['avg_profit_percent']}% (objectif: ≥15%)\")
    print(f\"  Perte moyenne: {analysis['avg_loss_percent']}% (objectif: ≤15%)\")
    print(f\"  Trades/jour: {analysis['trades_per_day']} (objectif: ≥3)\")
    print(f\"  P&L total: {analysis['total_pnl_eth']} ETH\")
    print()

    if analysis['meets_objectives']:
        print('  ✅ Tous les objectifs sont atteints!')
    else:
        print('  ⚠️  Optimisation requise:')
        for name, obj in analysis['objectives'].items():
            if not obj['met']:
                print(f\"     - {name}: {obj['current']} (cible: {obj['target']})\")
" 2>/dev/null || print_warning "Impossible de parser le JSON"
    fi

    echo ""
    print_info "Prochaines étapes suggérées:"
    echo "  1. Lisez auto_improvement_history.md pour voir l'historique"
    echo "  2. Examinez data/performance_analysis.json pour les détails"
    echo "  3. Consultez Claude pour des suggestions d'optimisation"
    echo "  4. Si vous modifiez config/.env, lancez deploy_to_vps() pour déployer"
    echo ""
}

################################################################################
# Déploiement vers le VPS
################################################################################

deploy_to_vps() {
    print_step "Déploiement des modifications vers le VPS..."

    # Crée une branche Git pour les modifications
    local branch_name="claude-auto-improve-$(date +%Y%m%d-%H%M%S)"

    print_info "Création de la branche $branch_name..."
    git checkout -b "$branch_name"

    # Commit des modifications
    print_info "Commit des modifications..."
    git add config/.env auto_improvement_history.md
    git commit -m "🤖 Auto-optimization: $(date +%Y-%m-%d\ %H:%M)

Modifications automatiques de la stratégie de trading.

Voir auto_improvement_history.md pour les détails.
"

    # Push vers GitHub
    print_info "Push vers GitHub..."
    git push -u origin "$branch_name"

    print_success "Code pushé sur la branche $branch_name"

    # Crée une Pull Request (nécessite gh CLI)
    if command -v gh &> /dev/null; then
        print_info "Création de la Pull Request..."
        gh pr create --title "🤖 Auto-optimization $(date +%Y-%m-%d)" \
                     --body "Optimisation automatique de la stratégie de trading par Claude.

Voir \`auto_improvement_history.md\` pour les détails des modifications.

**À reviewer avant merge!**" \
                     --base main \
                     --head "$branch_name"

        print_success "Pull Request créée"
    else
        print_warning "gh CLI non installé - Créez la PR manuellement"
        print_info "https://github.com/supermerou03101983/BaseBot/compare/$branch_name"
    fi

    # Demande confirmation pour déployer sur le VPS
    echo ""
    read -p "$(echo -e ${YELLOW}Voulez-vous déployer sur le VPS maintenant? [y/N]:${NC} )" -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Déploiement sur le VPS..."

        sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no \
            "$VPS_USER@$VPS_IP" << EOF
cd /home/basebot/trading-bot

# Pull les modifications
git fetch origin
git checkout $branch_name
git pull origin $branch_name

# Redémarre les services
sudo systemctl restart basebot-scanner
sudo systemctl restart basebot-filter
sudo systemctl restart basebot-trader

echo "Déploiement terminé"
EOF

        print_success "Déploiement terminé sur le VPS"

        # Envoie une notification Telegram si configuré
        send_telegram_notification "🚀 Déploiement sur VPS terminé\n\nBranche: $branch_name\nDate: $(date)"
    else
        print_info "Déploiement annulé - Mergez la PR manuellement puis déployez"
    fi

    # Retourne sur la branche main
    git checkout main
}

################################################################################
# Notification Telegram
################################################################################

send_telegram_notification() {
    local message="$1"

    if [[ -z "$TELEGRAM_WEBHOOK" ]]; then
        print_warning "Webhook Telegram non configuré - Notification ignorée"
        return
    fi

    print_info "Envoi de la notification Telegram..."

    # Encode le message pour l'URL
    local encoded_message=$(echo -e "$message" | python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read()))")

    # Envoie la notification
    curl -s -X POST "$TELEGRAM_WEBHOOK&text=$encoded_message" > /dev/null

    print_success "Notification envoyée"
}

################################################################################
# Nettoyage
################################################################################

cleanup() {
    print_step "Nettoyage..."

    # Garde les fichiers temporaires pour analyse
    print_info "Les données VPS sont conservées dans $TEMP_DIR"
    print_info "Supprimez manuellement si nécessaire: rm -rf $TEMP_DIR"
}

################################################################################
# Fonction principale
################################################################################

main() {
    print_banner

    # Charge la configuration
    load_config

    # Vérifie la connexion VPS
    check_vps_connection

    # Vérifie les services
    check_vps_services

    # Récupère les données
    fetch_vps_data

    # Affiche les logs récents
    show_recent_logs

    # Analyse les performances
    local analysis_result
    analyze_performance
    analysis_result=$?

    # Mode interactif avec Claude
    interactive_optimization

    # Si l'analyse indique qu'une optimisation est requise
    if [[ $analysis_result -eq 2 ]]; then
        echo ""
        print_warning "La stratégie nécessite une optimisation"
        print_info "Consultez Claude pour proposer des modifications de config/.env"
        echo ""
        print_info "Quand vous êtes prêt à déployer, tapez: deploy_to_vps"
    elif [[ $analysis_result -eq 0 ]]; then
        print_success "La stratégie performe bien - Aucune modification nécessaire"

        # Notification Telegram
        send_telegram_notification "✅ Analyse de performance: Tous les objectifs atteints!"
    fi

    # Note: cleanup() n'est pas appelé automatiquement pour permettre l'analyse
    print_success "Script terminé"
    echo ""
}

################################################################################
# Export des fonctions pour utilisation interactive
################################################################################

# Permet d'appeler deploy_to_vps() depuis le shell après l'exécution du script
export -f deploy_to_vps
export -f send_telegram_notification
export VPS_IP VPS_USER VPS_PASSWORD TELEGRAM_WEBHOOK

################################################################################
# Exécution
################################################################################

# Si le script est exécuté directement (pas sourcé)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
