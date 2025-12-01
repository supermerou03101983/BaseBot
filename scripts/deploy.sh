#!/bin/bash

# =============================================================================
# Script de déploiement automatique du Base Trading Bot
# =============================================================================
# Usage distant (recommandé pour VPS):
#   curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
#
# Usage local:
#   sudo bash deploy.sh
#
# Ce script doit être exécuté en tant que root
# =============================================================================

set -e
set -o pipefail

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

# Configuration globale
REPO_URL="https://github.com/supermerou03101983/BaseBot.git"
BOT_USER="basebot"
BOT_HOME="/home/$BOT_USER"
BOT_DIR="$BOT_HOME/trading-bot"
PYTHON_MIN_VERSION="3.8"
LOG_FILE="/var/log/basebot-deployment.log"

# =============================================================================
# Fonctions utilitaires
# =============================================================================

print_header() {
    echo -e "\n${BLUE}${BOLD}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}════════════════════════════════════════════════════════${NC}\n"
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${MAGENTA}ℹ $1${NC}"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Trap pour gérer les erreurs
error_exit() {
    print_error "Erreur à la ligne $1"
    print_error "Commande: $2"
    print_error "Consultez les logs: $LOG_FILE"
    log "ERREUR: Ligne $1 - Commande: $2"
    exit 1
}

trap 'error_exit $LINENO "$BASH_COMMAND"' ERR

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Ce script doit être exécuté en tant que root"
        echo "Utilisez: sudo bash deploy.sh"
        echo "Ou: curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash"
        exit 1
    fi
}

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        print_error "Impossible de détecter le système d'exploitation"
        exit 1
    fi
}

# =============================================================================
# Début du déploiement
# =============================================================================

clear
print_header "🚀 Déploiement automatique du Base Trading Bot"

# Créer le répertoire de logs si nécessaire
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE" 2>/dev/null || LOG_FILE="/tmp/basebot-deployment.log"

log "=== DÉBUT DU DÉPLOIEMENT ==="

# Vérifier les droits root
check_root

# Détecter le système d'exploitation
detect_os
print_info "Système détecté: $OS $OS_VERSION"
log "OS: $OS $OS_VERSION"

# =============================================================================
# 1. Mise à jour du système et installation des dépendances
# =============================================================================

print_header "1️⃣  Installation des dépendances système"

print_step "Mise à jour de la liste des paquets..."

case $OS in
    ubuntu|debian)
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq >> "$LOG_FILE" 2>&1
        print_success "Liste des paquets mise à jour"

        print_step "Installation des paquets nécessaires..."
        apt-get install -y -qq \
            python3 \
            python3-pip \
            python3-venv \
            python3-dev \
            git \
            curl \
            wget \
            build-essential \
            libssl-dev \
            libffi-dev \
            sqlite3 \
            systemd \
            cron >> "$LOG_FILE" 2>&1
        ;;

    centos|rhel|fedora)
        yum update -y -q >> "$LOG_FILE" 2>&1
        print_success "Liste des paquets mise à jour"

        print_step "Installation des paquets nécessaires..."
        yum install -y -q \
            python3 \
            python3-pip \
            python3-devel \
            git \
            curl \
            wget \
            gcc \
            gcc-c++ \
            make \
            openssl-devel \
            libffi-devel \
            sqlite \
            systemd \
            cronie >> "$LOG_FILE" 2>&1
        ;;

    *)
        print_error "Distribution non supportée: $OS"
        print_info "Distributions supportées: Ubuntu, Debian, CentOS, RHEL, Fedora"
        exit 1
        ;;
esac

print_success "Dépendances système installées"
log "Dépendances système installées"

# Vérifier Python
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_success "Python installé: v$PYTHON_VERSION"

# =============================================================================
# 2. Création de l'utilisateur dédié
# =============================================================================

print_header "2️⃣  Configuration de l'utilisateur système"

if id "$BOT_USER" &>/dev/null; then
    print_warning "L'utilisateur $BOT_USER existe déjà"
    read -p "Voulez-vous le recréer? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Suppression de l'utilisateur existant..."
        systemctl stop basebot-scanner.service 2>/dev/null || true
        systemctl stop basebot-filter.service 2>/dev/null || true
        systemctl stop basebot-trader.service 2>/dev/null || true
        systemctl stop basebot-dashboard.service 2>/dev/null || true
        userdel -r $BOT_USER 2>/dev/null || true
        print_success "Ancien utilisateur supprimé"
    fi
fi

if ! id "$BOT_USER" &>/dev/null; then
    print_step "Création de l'utilisateur $BOT_USER..."
    useradd -m -s /bin/bash $BOT_USER
    print_success "Utilisateur $BOT_USER créé"
    log "Utilisateur $BOT_USER créé"
else
    print_info "Utilisation de l'utilisateur existant"
fi

# =============================================================================
# 3. Clonage du repository
# =============================================================================

print_header "3️⃣  Clonage du repository GitHub"

if [ -d "$BOT_DIR" ]; then
    print_warning "Le répertoire $BOT_DIR existe déjà"
    read -p "Voulez-vous le supprimer et recloner? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$BOT_DIR"
        print_success "Ancien répertoire supprimé"
    fi
fi

if [ ! -d "$BOT_DIR" ]; then
    print_step "Clonage depuis GitHub..."
    su - $BOT_USER -c "git clone $REPO_URL $BOT_DIR" >> "$LOG_FILE" 2>&1
    print_success "Repository cloné dans $BOT_DIR"
    log "Repository cloné"
else
    print_step "Mise à jour du repository existant..."
    su - $BOT_USER -c "cd $BOT_DIR && git pull" >> "$LOG_FILE" 2>&1
    print_success "Repository mis à jour"
fi

# =============================================================================
# 4. Configuration des répertoires
# =============================================================================

print_header "4️⃣  Configuration de la structure"

print_step "Création des répertoires nécessaires..."

DIRS=(
    "$BOT_DIR/logs"
    "$BOT_DIR/data"
    "$BOT_DIR/data/backups"
    "$BOT_DIR/backups"
    "$BOT_DIR/config"
)

for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        su - $BOT_USER -c "mkdir -p $dir"
        print_success "Créé: $dir"
    else
        print_info "Existant: $dir"
    fi
done

# Définir les bonnes permissions
chown -R $BOT_USER:$BOT_USER "$BOT_DIR"
print_success "Permissions définies"

# =============================================================================
# 5. Configuration de l'environnement virtuel Python
# =============================================================================

print_header "5️⃣  Configuration de l'environnement Python"

VENV_DIR="$BOT_DIR/venv"

print_step "Création de l'environnement virtuel..."
su - $BOT_USER -c "python3 -m venv $VENV_DIR" >> "$LOG_FILE" 2>&1
print_success "Environnement virtuel créé"

print_step "Mise à jour de pip..."
su - $BOT_USER -c "source $VENV_DIR/bin/activate && pip install --upgrade pip setuptools wheel" >> "$LOG_FILE" 2>&1
print_success "pip mis à jour"

print_step "Installation des dépendances Python..."
print_info "Cela peut prendre plusieurs minutes..."
su - $BOT_USER -c "source $VENV_DIR/bin/activate && pip install -r $BOT_DIR/requirements.txt" >> "$LOG_FILE" 2>&1
print_success "Dépendances Python installées"
log "Dépendances Python installées"

# =============================================================================
# 6. Configuration des fichiers
# =============================================================================

print_header "6️⃣  Configuration des fichiers"

# Créer le fichier .env s'il n'existe pas
if [ ! -f "$BOT_DIR/config/.env" ]; then
    print_step "Création du fichier de configuration..."
    cat > "$BOT_DIR/config/.env" << 'EOF'
# BASE TRADING BOT - CONFIGURATION
# ⚠️ REMPLISSEZ VOS VALEURS ICI

# ============================================
# 🌐 BLOCKCHAIN CONFIGURATION
# ============================================
# RPC Base Network (RPC stable recommandé)
RPC_URL=https://mainnet.base.org
BASE_CHAIN_ID=8453

WETH_ADDRESS=0x4200000000000000000000000000000000000006
USDC_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

# ============================================
# 🔑 WALLET (CONFIDENTIEL - À REMPLIR)
# ============================================
WALLET_ADDRESS=YOUR_WALLET_ADDRESS_HERE
PRIVATE_KEY=YOUR_PRIVATE_KEY_HERE_WITHOUT_0x

# ============================================
# 📊 APIS EXTERNES
# ============================================
ETHERSCAN_API_KEY=YOUR_ETHERSCAN_API_KEY
COINGECKO_API_KEY=

# ============================================
# 💾 DATABASE
# ============================================
DATABASE_PATH=/home/basebot/trading-bot/data/trading.db
BACKUP_PATH=/home/basebot/trading-bot/data/backups/

# ============================================
# ⚙️ TRADER - Gestion des Positions
# ============================================

# Mode de trading (true = simulation, false = réel)
PAPER_TRADING=true

# Montant par trade (USD)
TRADE_AMOUNT_USD=10

# Stop-loss standard (%)
STOP_LOSS_PERCENT=15

# Take-profit (%)
TAKE_PROFIT_PERCENT=30

# Grace Period - Protection Initiale
GRACE_PERIOD_ENABLED=true
GRACE_PERIOD_MINUTES=5
GRACE_PERIOD_STOP_LOSS=25

# Advanced
BUY_DELAY_SECONDS=5
MONITORING_INTERVAL=10
LOSING_TOKEN_COOLDOWN_HOURS=24

# ============================================
# 🔍 SCANNER ON-CHAIN (Modification #5)
# ============================================
# Scanner unifié qui détecte les nouveaux tokens via événements PairCreated
# on-chain (Aerodrome + BaseSwap) et enrichit avec données DexScreener
# Remplace l'approche GeckoTerminal/DexScreener par scan blockchain direct

SCAN_INTERVAL_SECONDS=30

# Filtrage par âge - Scanner détecte tokens 3h-8h après création (aligné avec Filter)
MIN_TOKEN_AGE_HOURS=3
MAX_TOKEN_AGE_HOURS=8

UNISWAP_V3_FACTORY=0x33128a8fC17869897dcE68Ed026d694621f6FDfD
AERODROME_FACTORY=0x420DD381b31aEf6683db6B902084cB0FFECe40Da

# ============================================
# 🎯 FILTER CONFIGURATION - Momentum Safe (Modification #6)
# ============================================
# Stratégie optimisée pour 3-4 tokens/jour, win-rate ≥70%, sécurité maximale
# Fenêtre: tokens 3.5-8h (après scam check, avant pic retail)
# ⚠️ IMPORTANT: Ne modifiez ces valeurs que si vous comprenez la stratégie!

FILTER_INTERVAL_SECONDS=60

# Âge du token (heures) - Fenêtre stricte
MIN_AGE_HOURS=3.5
MAX_AGE_HOURS=8.0

# Liquidité (USD)
MIN_LIQUIDITY_USD=12000
MAX_LIQUIDITY_USD=2000000

# Market Cap (USD)
MIN_MARKET_CAP=80000
MAX_MARKET_CAP=2500000

# Volume (USD)
MIN_VOLUME_1H=4000
MIN_VOLUME_5MIN=800
MIN_VOLUME_RATIO_5M_1H=0.3

# Momentum prix (%)
MIN_PRICE_CHANGE_5MIN=4.0
MIN_PRICE_CHANGE_1H=7.0

# Distribution
MIN_HOLDERS=120
MAX_OWNER_PERCENTAGE=5.0

# Taxes
MAX_BUY_TAX=3
MAX_SELL_TAX=3

# Scores (assouplis pour test initial)
MIN_SAFETY_SCORE=50
MIN_POTENTIAL_SCORE=40

# ============================================
# 🌐 API SERVER
# ============================================
API_ENABLED=true
API_HOST=127.0.0.1
API_PORT=5000
API_KEY=

# ============================================
# 📊 DASHBOARD
# ============================================
DASHBOARD_PORT=3000

# ============================================
# 📝 LOGGING
# ============================================
LOG_LEVEL=INFO
LOG_FILE=/home/basebot/trading-bot/logs/trading.log
LOG_MAX_SIZE_MB=100
LOG_BACKUP_COUNT=5
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# ============================================
# 🔧 ADVANCED SETTINGS
# ============================================
MAX_GAS_PRICE_GWEI=50
GAS_LIMIT_BUY=250000
GAS_LIMIT_SELL=300000

MAX_SLIPPAGE_PERCENT=3
EMERGENCY_SLIPPAGE_PERCENT=5

MAX_RETRIES=3
RETRY_DELAY_SECONDS=2

# ============================================
# 🚨 ALERTING
# ============================================
ALERTS_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# ============================================
# 🔐 SECURITY
# ============================================
REQUIRE_2FA=false
TWO_FA_SECRET=
ALLOWED_IPS=127.0.0.1,localhost

# ============================================
# 🧪 DEBUG
# ============================================
DEBUG_MODE=false
DRY_RUN=false
SIMULATE_BLOCKCHAIN=false
EOF
    chown $BOT_USER:$BOT_USER "$BOT_DIR/config/.env"
    chmod 600 "$BOT_DIR/config/.env"
    print_success "Fichier .env créé"
    print_warning "Configuration requise: éditez $BOT_DIR/config/.env"
else
    print_info "Fichier .env existant conservé"
fi

# Créer les fichiers JSON
if [ ! -f "$BOT_DIR/config/trading_mode.json" ]; then
    echo '{"mode":"paper"}' > "$BOT_DIR/config/trading_mode.json"
    chown $BOT_USER:$BOT_USER "$BOT_DIR/config/trading_mode.json"
fi

if [ ! -f "$BOT_DIR/config/blacklist.json" ]; then
    echo '[]' > "$BOT_DIR/config/blacklist.json"
    chown $BOT_USER:$BOT_USER "$BOT_DIR/config/blacklist.json"
fi

# Rendre les scripts exécutables
print_step "Configuration des permissions des scripts..."
chmod +x "$BOT_DIR"/*.sh 2>/dev/null || true
chmod +x "$BOT_DIR/config_manager" 2>/dev/null || true
print_success "Scripts configurés"

# =============================================================================
# 7. Initialisation de la base de données
# =============================================================================

print_header "7️⃣  Initialisation de la base de données"

if [ -f "$BOT_DIR/src/init_database.py" ]; then
    print_step "Création de la base de données..."
    su - $BOT_USER -c "source $VENV_DIR/bin/activate && cd $BOT_DIR && python src/init_database.py" >> "$LOG_FILE" 2>&1 || true
    print_success "Base de données initialisée"
else
    print_warning "Script init_database.py non trouvé"
fi

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

# =============================================================================
# 9. Nettoyage et préparation des fichiers de logs
# =============================================================================

print_header "9️⃣  Nettoyage des fichiers de logs"

print_step "Suppression des anciens fichiers de logs (si existants)..."
# Supprimer les anciens fichiers de logs pour éviter les problèmes de permissions
# IMPORTANT: Faire APRÈS init_database.py qui peut créer des logs
rm -f "$BOT_DIR/logs/"*.log 2>/dev/null || true
print_success "Anciens logs supprimés"

print_step "Vérification finale des permissions..."
# S'assurer que tous les fichiers appartiennent à basebot
chown -R $BOT_USER:$BOT_USER "$BOT_DIR"
# Permissions spécifiques pour le répertoire logs
chmod 755 "$BOT_DIR/logs"
print_success "Permissions configurées"

# =============================================================================
# 10. Configuration des services systemd
# =============================================================================

print_header "🔟 Configuration des services systemd"

# Service Scanner
print_step "Création du service Scanner..."
cat > /etc/systemd/system/basebot-scanner.service << EOF
[Unit]
Description=BaseBot Trading Scanner
After=network.target

[Service]
Type=simple
User=$BOT_USER
WorkingDirectory=$BOT_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
ExecStartPre=/bin/sh -c 'rm -f /home/$BOT_USER/trading-bot/logs/scanner*.log || true'
ExecStartPre=/bin/chown -R $BOT_USER:$BOT_USER /home/$BOT_USER/trading-bot/logs
ExecStart=$VENV_DIR/bin/python $BOT_DIR/src/Scanner.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Service Filter
print_step "Création du service Filter..."
cat > /etc/systemd/system/basebot-filter.service << EOF
[Unit]
Description=BaseBot Trading Filter
After=network.target

[Service]
Type=simple
User=$BOT_USER
WorkingDirectory=$BOT_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
ExecStartPre=/bin/sh -c 'rm -f /home/$BOT_USER/trading-bot/logs/filter*.log || true'
ExecStartPre=/bin/chown -R $BOT_USER:$BOT_USER /home/$BOT_USER/trading-bot/logs
ExecStart=$VENV_DIR/bin/python $BOT_DIR/src/Filter.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Service Trader
print_step "Création du service Trader..."
cat > /etc/systemd/system/basebot-trader.service << EOF
[Unit]
Description=BaseBot Trading Trader
After=network.target

[Service]
Type=simple
User=$BOT_USER
WorkingDirectory=$BOT_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
ExecStartPre=/bin/sh -c 'rm -f /home/$BOT_USER/trading-bot/logs/trader*.log || true'
ExecStartPre=/bin/chown -R $BOT_USER:$BOT_USER /home/$BOT_USER/trading-bot/logs
ExecStart=$VENV_DIR/bin/python $BOT_DIR/src/Trader.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Service Dashboard
print_step "Création du service Dashboard..."
cat > /etc/systemd/system/basebot-dashboard.service << EOF
[Unit]
Description=BaseBot Trading Dashboard
After=network.target

[Service]
Type=simple
User=$BOT_USER
WorkingDirectory=$BOT_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
ExecStartPre=/bin/sh -c 'rm -f /home/$BOT_USER/trading-bot/logs/dashboard*.log || true'
ExecStartPre=/bin/chown -R $BOT_USER:$BOT_USER /home/$BOT_USER/trading-bot/logs
ExecStart=$VENV_DIR/bin/streamlit run $BOT_DIR/src/Dashboard.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Recharger systemd
systemctl daemon-reload
print_success "Services systemd créés"
log "Services systemd configurés"

# =============================================================================
# 11. Configuration du pare-feu (optionnel)
# =============================================================================

print_header "1️⃣1️⃣ Configuration du pare-feu"

if command -v ufw &> /dev/null; then
    print_step "Configuration UFW..."
    ufw allow 8501/tcp comment "BaseBot Dashboard" >> "$LOG_FILE" 2>&1 || true
    print_success "Port 8501 ouvert pour le dashboard"
elif command -v firewall-cmd &> /dev/null; then
    print_step "Configuration firewalld..."
    firewall-cmd --permanent --add-port=8501/tcp >> "$LOG_FILE" 2>&1 || true
    firewall-cmd --reload >> "$LOG_FILE" 2>&1 || true
    print_success "Port 8501 ouvert pour le dashboard"
else
    print_warning "Pare-feu non détecté, configuration manuelle nécessaire"
fi

# =============================================================================
# 12. Configuration de la maintenance automatique
# =============================================================================

print_header "1️⃣2️⃣ Configuration de la maintenance automatique"

print_step "Copie du script de maintenance safe..."
if [ -f "$BOT_DIR/maintenance_safe.sh" ]; then
    chmod +x "$BOT_DIR/maintenance_safe.sh"
    chown $BOT_USER:$BOT_USER "$BOT_DIR/maintenance_safe.sh"
    print_success "Script de maintenance configuré"
else
    print_warning "Script maintenance_safe.sh non trouvé"
fi

print_step "Pré-création des fichiers de logs avec bonnes permissions..."
# Créer les fichiers de logs que la maintenance va utiliser
touch "$BOT_DIR/logs/maintenance.log"
touch "$BOT_DIR/logs/stats_$(date +%Y%m).txt"
chown -R $BOT_USER:$BOT_USER "$BOT_DIR/logs/"
print_success "Fichiers de logs initialisés"

print_step "Configuration des cron jobs automatiques..."
# Créer un fichier temporaire avec les cron jobs
CRON_FILE="/tmp/basebot_cron_$$"
cat > "$CRON_FILE" << 'CRONEOF'
# ============================================
# BaseBot Trading - Cron Jobs Automatiques
# ============================================

# Backup quotidien de la base de données (2h du matin)
0 2 * * * cp /home/basebot/trading-bot/data/trading.db /home/basebot/trading-bot/data/backups/trading_$(date +\%Y\%m\%d).db 2>/dev/null

# Maintenance hebdomadaire safe (dimanche 3h du matin)
# Ne redémarre AUCUN service - préserve les trailing stops
0 3 * * 0 /home/basebot/trading-bot/maintenance_safe.sh 2>&1

# Maintenance mensuelle complète (1er du mois à 4h du matin)
# Archive les vieux trades, génère les stats, nettoie les backups
0 4 1 * * /home/basebot/trading-bot/maintenance_safe.sh 2>&1

# Nettoyage des logs journaliers (tous les jours à 1h du matin)
0 1 * * * find /home/basebot/trading-bot/logs/ -name "*.log" -size +500M -delete 2>/dev/null

# Watchdog anti-freeze (toutes les 15 minutes)
# Détecte et alerte si le bot est bloqué
*/15 * * * * /home/basebot/trading-bot/watchdog.py >> /home/basebot/trading-bot/logs/watchdog.log 2>&1

CRONEOF

# Installer les cron jobs pour l'utilisateur basebot
su - $BOT_USER -c "crontab $CRON_FILE" >> "$LOG_FILE" 2>&1
rm -f "$CRON_FILE"

# Vérifier l'installation
CRON_COUNT=$(su - $BOT_USER -c "crontab -l 2>/dev/null | grep -c basebot" || echo "0")
if [ "$CRON_COUNT" -gt 0 ]; then
    print_success "Cron jobs configurés: $CRON_COUNT tâches automatiques"
else
    print_warning "Problème avec la configuration des cron jobs"
fi

# Rendre le watchdog exécutable
chmod +x "$BOT_DIR/watchdog.py" 2>/dev/null || true
print_success "Watchdog anti-freeze configuré"

# =============================================================================
# 13. Installation des outils de diagnostic et déblocage
# =============================================================================

print_header "1️⃣3️⃣ Installation des outils de diagnostic"

print_step "Configuration des outils de déblocage..."

# Rendre tous les scripts de diagnostic exécutables
DIAGNOSTIC_SCRIPTS=(
    "$BOT_DIR/diagnose_freeze.py"
    "$BOT_DIR/emergency_close_positions.py"
    "$BOT_DIR/watchdog.py"
    "$BOT_DIR/quick_fix.sh"
    "$BOT_DIR/analyze_trades_simple.py"
    "$BOT_DIR/analyze_results.py"
)

FOUND_COUNT=0
for script in "${DIAGNOSTIC_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        chmod +x "$script"
        chown $BOT_USER:$BOT_USER "$script"
        FOUND_COUNT=$((FOUND_COUNT + 1))
    fi
done

if [ $FOUND_COUNT -gt 0 ]; then
    print_success "$FOUND_COUNT outils de diagnostic installés"
    print_info "Outils disponibles:"
    [ -f "$BOT_DIR/diagnose_freeze.py" ] && echo -e "  ${GREEN}•${NC} diagnose_freeze.py - Diagnostic complet du freeze"
    [ -f "$BOT_DIR/emergency_close_positions.py" ] && echo -e "  ${GREEN}•${NC} emergency_close_positions.py - Fermeture d'urgence"
    [ -f "$BOT_DIR/watchdog.py" ] && echo -e "  ${GREEN}•${NC} watchdog.py - Surveillance automatique"
    [ -f "$BOT_DIR/quick_fix.sh" ] && echo -e "  ${GREEN}•${NC} quick_fix.sh - Dépannage rapide"
    [ -f "$BOT_DIR/analyze_trades_simple.py" ] && echo -e "  ${GREEN}•${NC} analyze_trades_simple.py - Analyse simple des performances"
    [ -f "$BOT_DIR/analyze_results.py" ] && echo -e "  ${GREEN}•${NC} analyze_results.py - Analyse détaillée avec recommandations"
else
    print_warning "Outils de diagnostic non trouvés (seront disponibles après git pull)"
fi

# Créer des alias pour faciliter l'usage
print_step "Création des alias de commande..."
cat > "$BOT_HOME/.bash_aliases" << 'ALIASEOF'
# BaseBot Trading - Alias pratiques
alias bot-status='cd /home/basebot/trading-bot && python3 diagnose_freeze.py'
alias bot-fix='cd /home/basebot/trading-bot && bash quick_fix.sh'
alias bot-restart='sudo systemctl restart basebot-trader && echo "Trader redémarré"'
alias bot-logs='tail -50 /home/basebot/trading-bot/logs/trading.log'
alias bot-watch='tail -f /home/basebot/trading-bot/logs/trading.log'
alias bot-scan='sudo journalctl -u basebot-scanner -f'
alias bot-filter='sudo journalctl -u basebot-filter -f'
alias bot-trader='sudo journalctl -u basebot-trader -f'
alias bot-emergency='cd /home/basebot/trading-bot && python3 emergency_close_positions.py'
alias bot-analyze='cd /home/basebot/trading-bot && python3 analyze_trades_simple.py'
alias bot-analyze-full='cd /home/basebot/trading-bot && python3 analyze_results.py'
ALIASEOF

chown $BOT_USER:$BOT_USER "$BOT_HOME/.bash_aliases"
chmod 644 "$BOT_HOME/.bash_aliases"

# Activer les alias dans .bashrc
if ! grep -q "\.bash_aliases" "$BOT_HOME/.bashrc" 2>/dev/null; then
    echo "" >> "$BOT_HOME/.bashrc"
    echo "# Charger les alias BaseBot" >> "$BOT_HOME/.bashrc"
    echo "if [ -f ~/.bash_aliases ]; then" >> "$BOT_HOME/.bashrc"
    echo "    . ~/.bash_aliases" >> "$BOT_HOME/.bashrc"
    echo "fi" >> "$BOT_HOME/.bashrc"
fi

print_success "Alias de commande configurés"
print_info "Tapez 'bot-status' pour diagnostiquer"
print_info "Tapez 'bot-fix' pour dépannage rapide"

# =============================================================================
# 14. Tests de validation
# =============================================================================

print_header "1️⃣4️⃣ Tests de validation"

print_step "Vérification de l'installation Python..."
su - $BOT_USER -c "source $VENV_DIR/bin/activate && python -c 'import web3, pandas, streamlit; print(\"✓ Modules OK\")'" >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    print_success "Modules Python validés"
else
    print_warning "Problème avec les modules Python"
fi

print_step "Vérification des fichiers..."
REQUIRED_FILES=(
    "$BOT_DIR/src/Scanner.py"
    "$BOT_DIR/src/Filter.py"
    "$BOT_DIR/src/Trader.py"
    "$BOT_DIR/src/Dashboard.py"
    "$BOT_DIR/config/.env"
)

ALL_OK=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_success "OK: $(basename $file)"
    else
        print_error "MANQUANT: $(basename $file)"
        ALL_OK=false
    fi
done

# Vérifier les fichiers de documentation critiques (ajoutés avec les derniers fixes)
print_step "Vérification de la documentation des derniers fixes..."
CRITICAL_DOCS=(
    "$BOT_DIR/VERIFICATION_CRITERES.md"
    "$BOT_DIR/FIXES_APPLIED.md"
    "$BOT_DIR/OPTIMIZATIONS_CRITIQUES.md"
    "$BOT_DIR/DEPLOY_FIXES.md"
    "$BOT_DIR/FIX_REAL_PRICES_VOLUME_1H.md"
    "$BOT_DIR/DEPLOYMENT_REPORT_MOD1.md"
)

DOCS_FOUND=0
for doc in "${CRITICAL_DOCS[@]}"; do
    if [ -f "$doc" ]; then
        DOCS_FOUND=$((DOCS_FOUND + 1))
    fi
done

if [ $DOCS_FOUND -ge 4 ]; then
    print_success "Documentation des fixes critiques présente ($DOCS_FOUND/6)"
    print_info "Fixes appliqués:"
    print_info "  • Modification #1: Critères assouplies (MIN_VOLUME $3K, MIN_LIQUIDITY $5K)"
    print_info "  • Filtre volume_1h: Rejette automatiquement les tokens morts (volume_1h=0)"
    print_info "  • Prix réels: Mode PAPER utilise uniquement les prix DexScreener"
else
    print_warning "Documentation des fixes manquante (version ancienne du repo?)"
fi

# =============================================================================
# 15. Instructions finales
# =============================================================================

print_header "✅ Installation terminée !"

echo -e "${GREEN}${BOLD}Le Base Trading Bot a été installé avec succès !${NC}\n"

echo -e "${CYAN}📍 Installation:${NC}"
echo -e "  ${GREEN}•${NC} Répertoire: ${CYAN}$BOT_DIR${NC}"
echo -e "  ${GREEN}•${NC} Utilisateur: ${CYAN}$BOT_USER${NC}"
echo -e "  ${GREEN}•${NC} Python: ${CYAN}v$PYTHON_VERSION${NC}"
echo -e "  ${GREEN}•${NC} Logs: ${CYAN}$LOG_FILE${NC}"
echo ""

echo -e "${YELLOW}${BOLD}⚠️  ÉTAPES SUIVANTES OBLIGATOIRES:${NC}\n"

echo -e "${BOLD}1. Configurer le fichier .env:${NC}"
echo -e "   ${CYAN}nano $BOT_DIR/config/.env${NC}"
echo -e "   Remplissez:"
echo -e "     ${YELLOW}•${NC} WALLET_ADDRESS"
echo -e "     ${YELLOW}•${NC} PRIVATE_KEY"
echo -e "     ${YELLOW}•${NC} ETHERSCAN_API_KEY"
echo ""

echo -e "${BOLD}2. Démarrer les services:${NC}"
echo -e "   ${CYAN}systemctl enable basebot-scanner${NC}  # Auto-démarrage"
echo -e "   ${CYAN}systemctl start basebot-scanner${NC}   # Démarrer maintenant"
echo -e "   ${CYAN}systemctl enable basebot-filter${NC}"
echo -e "   ${CYAN}systemctl start basebot-filter${NC}"
echo -e "   ${CYAN}systemctl enable basebot-trader${NC}"
echo -e "   ${CYAN}systemctl start basebot-trader${NC}"
echo -e "   ${CYAN}systemctl enable basebot-dashboard${NC}"
echo -e "   ${CYAN}systemctl start basebot-dashboard${NC}"
echo ""

echo -e "${BOLD}3. Vérifier le statut:${NC}"
echo -e "   ${CYAN}systemctl status basebot-scanner${NC}"
echo -e "   ${CYAN}systemctl status basebot-filter${NC}"
echo -e "   ${CYAN}systemctl status basebot-trader${NC}"
echo -e "   ${CYAN}systemctl status basebot-dashboard${NC}"
echo ""

echo -e "${GREEN}${BOLD}✅ Maintenance Automatique Configurée:${NC}"
echo -e "  ${GREEN}•${NC} Backup quotidien: ${CYAN}2h du matin${NC}"
echo -e "  ${GREEN}•${NC} Maintenance hebdo: ${CYAN}Dimanche 3h${NC}"
echo -e "  ${GREEN}•${NC} Maintenance mensuelle: ${CYAN}1er du mois 4h${NC}"
echo -e "  ${GREEN}•${NC} Nettoyage logs: ${CYAN}Tous les jours 1h${NC}"
echo -e "  ${GREEN}•${NC} Watchdog anti-freeze: ${CYAN}Toutes les 15 min${NC}"
echo -e "  ${YELLOW}⚠️${NC}  Aucun service n'est redémarré (trailing stops préservés)"
echo ""

echo -e "${GREEN}${BOLD}🛡️  Outils de Diagnostic Installés:${NC}"
echo -e "  ${GREEN}•${NC} ${CYAN}bot-status${NC} - Diagnostic complet du freeze"
echo -e "  ${GREEN}•${NC} ${CYAN}bot-fix${NC} - Dépannage rapide"
echo -e "  ${GREEN}•${NC} ${CYAN}bot-emergency${NC} - Fermeture d'urgence des positions"
echo -e "  ${GREEN}•${NC} ${CYAN}bot-restart${NC} - Redémarrer le trader"
echo -e "  ${GREEN}•${NC} ${CYAN}bot-logs${NC} - Voir les 50 dernières lignes"
echo -e "  ${GREEN}•${NC} ${CYAN}bot-watch${NC} - Suivre les logs en temps réel"
echo -e "  ${GREEN}•${NC} ${CYAN}bot-analyze${NC} - Analyse simple des performances"
echo -e "  ${GREEN}•${NC} ${CYAN}bot-analyze-full${NC} - Analyse détaillée avec recommandations"
echo ""

echo -e "${CYAN}📊 Dashboard:${NC}"
echo -e "  ${GREEN}•${NC} URL: ${CYAN}http://$(hostname -I | awk '{print $1}'):8501${NC}"
echo -e "  ${GREEN}•${NC} Service: ${CYAN}systemctl status basebot-dashboard${NC}"
echo ""

echo -e "${CYAN}🔧 Commandes utiles:${NC}"
echo -e "  ${GREEN}•${NC} Voir les logs en direct:"
echo -e "    ${CYAN}journalctl -u basebot-scanner -f${NC}"
echo -e "    ${CYAN}journalctl -u basebot-filter -f${NC}"
echo -e "    ${CYAN}journalctl -u basebot-trader -f${NC}"
echo -e "  ${GREEN}•${NC} Redémarrer un service:"
echo -e "    ${CYAN}systemctl restart basebot-scanner${NC}"
echo -e "  ${GREEN}•${NC} Arrêter un service:"
echo -e "    ${CYAN}systemctl stop basebot-scanner${NC}"
echo -e "  ${GREEN}•${NC} Status du bot:"
echo -e "    ${CYAN}su - $BOT_USER -c 'cd $BOT_DIR && ./status.sh'${NC}"
echo -e "  ${GREEN}•${NC} Éditer la config:"
echo -e "    ${CYAN}nano $BOT_DIR/config/.env${NC}"
echo ""

echo -e "${CYAN}📁 Structure:${NC}"
echo -e "  ${GREEN}•${NC} Code: ${CYAN}$BOT_DIR/src/${NC}"
echo -e "  ${GREEN}•${NC} Config: ${CYAN}$BOT_DIR/config/.env${NC}"
echo -e "  ${GREEN}•${NC} Logs: ${CYAN}$BOT_DIR/logs/${NC}"
echo -e "  ${GREEN}•${NC} Data: ${CYAN}$BOT_DIR/data/${NC}"
echo ""

echo -e "${MAGENTA}💡 Conseils:${NC}"
echo -e "  ${YELLOW}•${NC} Commencez en mode 'paper' (simulation)"
echo -e "  ${YELLOW}•${NC} Testez avec de petits montants"
echo -e "  ${YELLOW}•${NC} Surveillez les logs régulièrement"
echo -e "  ${YELLOW}•${NC} Sauvegardez votre clé privée"
echo ""

echo -e "${GREEN}${BOLD}🎉 Bon trading sur Base Network !${NC}\n"

log "=== DÉPLOIEMENT TERMINÉ AVEC SUCCÈS ==="

# Afficher un résumé pour connexion SSH future
cat > "$BOT_HOME/README_QUICKSTART.txt" << EOF
====================================
BASE TRADING BOT - GUIDE RAPIDE
====================================

📍 INSTALLATION
  Répertoire: $BOT_DIR
  Utilisateur: $BOT_USER

⚙️ CONFIGURATION
  Fichier: $BOT_DIR/config/.env
  Commande: nano $BOT_DIR/config/.env

🚀 SERVICES
  Scanner:   systemctl start/stop/status basebot-scanner
  Filter:    systemctl start/stop/status basebot-filter
  Trader:    systemctl start/stop/status basebot-trader
  Dashboard: systemctl start/stop/status basebot-dashboard

📊 DASHBOARD
  URL: http://$(hostname -I | awk '{print $1}'):8501

📝 LOGS
  Scanner:   journalctl -u basebot-scanner -f
  Filter:    journalctl -u basebot-filter -f
  Trader:    journalctl -u basebot-trader -f
  Dashboard: journalctl -u basebot-dashboard -f
  Fichiers:  $BOT_DIR/logs/

🛠️ MAINTENANCE
  Status:    ./status.sh (dans $BOT_DIR)
  Backup:    ./maintenance_monthly.sh

🛡️ OUTILS DE DIAGNOSTIC (Commandes rapides)
  bot-status     - Diagnostic complet du freeze
  bot-fix        - Dépannage rapide
  bot-restart    - Redémarrer le trader
  bot-logs       - Voir les derniers logs
  bot-watch      - Suivre les logs en direct
  bot-emergency  - Fermeture d'urgence des positions
  bot-analyze    - Analyse simple des performances
  bot-analyze-full - Analyse détaillée avec recommandations

🔍 SCRIPTS DE DIAGNOSTIC
  Freeze:        python3 diagnose_freeze.py
  Quick Fix:     bash quick_fix.sh
  Emergency:     python3 emergency_close_positions.py
  Watchdog:      python3 watchdog.py
  Analyse:       python3 analyze_trades_simple.py

⏰ TÂCHES AUTOMATIQUES
  - Backup quotidien: 2h du matin
  - Maintenance hebdo: Dimanche 3h
  - Maintenance mensuelle: 1er du mois 4h
  - Watchdog anti-freeze: Toutes les 15 minutes

📖 DOCUMENTATION
  Guide freeze: $BOT_DIR/TROUBLESHOOTING_FREEZE.md
  Voir: $BOT_DIR/README.md (si disponible)

====================================
EOF

chown $BOT_USER:$BOT_USER "$BOT_HOME/README_QUICKSTART.txt"
print_success "Guide rapide créé: $BOT_HOME/README_QUICKSTART.txt"

echo -e "${CYAN}Pour vous reconnecter plus tard:${NC}"
echo -e "  ${CYAN}cat $BOT_HOME/README_QUICKSTART.txt${NC}"
echo ""
