# 🔑 Configuration du Wallet sur le VPS

## ⚠️ Problème Actuel

Le bot ne peut pas démarrer car le fichier `.env` sur le VPS ne contient pas les vraies clés du wallet.

**Erreur détectée**: `Non-hexadecimal digit found` → La PRIVATE_KEY est invalide (valeur par défaut `YOUR_PRIVATE_KEY_HERE_WITHOUT_0x`)

---

## 🛠️ Solution: Configurer le Wallet

### Étape 1: Préparer vos clés

Vous avez besoin de :
1. **Adresse du wallet** (ex: `0x1234...5678`)
2. **Clé privée** (ex: `abcdef1234567890...` **SANS le préfixe 0x**)

⚠️ **IMPORTANT**: La clé privée doit être:
- En hexadécimal (64 caractères)
- SANS le préfixe `0x`
- Exemple valide: `1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef`

### Étape 2: Éditer le .env sur le VPS

#### Option A: Via SSH interactif (recommandé)

```bash
ssh root@46.62.194.176
cd /home/basebot/trading-bot
nano config/.env

# Cherchez ces lignes:
WALLET_ADDRESS=YOUR_WALLET_ADDRESS_HERE
PRIVATE_KEY=YOUR_PRIVATE_KEY_HERE_WITHOUT_0x

# Remplacez par vos vraies valeurs:
WALLET_ADDRESS=0xVOTRE_ADRESSE_ICI
PRIVATE_KEY=VOTRE_CLE_PRIVEE_SANS_0x

# Sauvegardez: Ctrl+O, Enter, Ctrl+X
```

#### Option B: Via script automatisé

```bash
# Remplacez les valeurs ci-dessous par les vraies
WALLET_ADDRESS="0xVOTRE_ADRESSE"
PRIVATE_KEY="VOTRE_CLE_SANS_0x"

sshpass -p "000Rnella" ssh root@46.62.194.176 << EOF
cd /home/basebot/trading-bot
sed -i "s/WALLET_ADDRESS=.*/WALLET_ADDRESS=$WALLET_ADDRESS/" config/.env
sed -i "s/PRIVATE_KEY=.*/PRIVATE_KEY=$PRIVATE_KEY/" config/.env
echo "✓ Wallet configuré"
EOF
```

### Étape 3: Redémarrer le bot

```bash
sshpass -p "000Rnella" ssh root@46.62.194.176 << 'EOF'
cd /home/basebot/trading-bot
sudo systemctl restart basebot-trader
sleep 3
systemctl status basebot-trader
EOF
```

### Étape 4: Vérifier que ça fonctionne

```bash
sshpass -p "000Rnella" ssh root@46.62.194.176 "journalctl -u basebot-trader -n 20"
```

Vous devriez voir:
- ✅ `RealTrader initialisé` ou `Trader démarré`
- ✅ Pas d'erreur `Non-hexadecimal digit found`

---

## 🔐 Sécurité

### Important

1. **NE JAMAIS** committer la vraie clé privée sur GitHub
2. Le fichier `.env` sur le VPS reste sur le VPS uniquement
3. Votre `.env` local doit aussi avoir la vraie clé privée pour tester localement

### Vérifier que .env est ignoré par git

```bash
# Sur votre Mac
cd /Users/vincentdoms/Documents/BaseBot
grep -E '\.env|config/\.env' .gitignore
```

Devrait afficher:
```
.env
config/.env
```

✅ C'est bien le cas - vos clés ne seront jamais commitées

---

## 💰 Fonds sur le Wallet

Le bot a besoin de ETH sur Base Network pour trader:

### Vérifier le solde

```bash
# Via le dashboard
# Ouvrez http://46.62.194.176:8501
# Le dashboard affiche le solde du wallet

# Ou via SSH
sshpass -p "000Rnella" ssh root@46.62.194.176 << 'EOF'
cd /home/basebot/trading-bot
python3 << 'PYTHON'
from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv('config/.env')
w3 = Web3(Web3.HTTPProvider('https://base.drpc.org'))
address = os.getenv('WALLET_ADDRESS')
balance = w3.eth.get_balance(address)
print(f"Solde: {w3.from_wei(balance, 'ether')} ETH")
PYTHON
EOF
```

### Montant recommandé

- **Minimum**: 0.05 ETH (pour ~3 positions de 0.015 ETH chacune)
- **Recommandé**: 0.1 ETH (plus confortable)
- **Optimal**: 0.2+ ETH (permet de trader sans interruption)

Le bot utilise **15% du capital par trade** avec **maximum 3 positions simultanées**.

---

## 🧪 Mode Paper Trading (Test sans risque)

Si vous voulez tester le bot sans risquer de l'argent réel:

```bash
sshpass -p "000Rnella" ssh root@46.62.194.176 << 'EOF'
cd /home/basebot/trading-bot
echo '{"mode": "paper"}' > config/trading_mode.json
sudo systemctl restart basebot-trader
echo "✓ Mode paper trading activé"
EOF
```

En mode paper:
- Le bot simule les trades
- Pas de transactions réelles sur la blockchain
- Pas besoin de ETH
- Utile pour tester la stratégie

Pour revenir en mode réel:
```bash
sshpass -p "000Rnella" ssh root@46.62.194.176 << 'EOF'
cd /home/basebot/trading-bot
echo '{"mode": "real"}' > config/trading_mode.json
sudo systemctl restart basebot-trader
echo "✓ Mode real trading activé"
EOF
```

---

## 📋 Checklist de Configuration

- [ ] Wallet créé avec ETH sur Base Network
- [ ] Adresse du wallet notée
- [ ] Clé privée notée (SANS 0x)
- [ ] `.env` sur VPS édité avec les vraies valeurs
- [ ] Services redémarrés
- [ ] Pas d'erreur dans les logs
- [ ] Solde suffisant (≥0.05 ETH)
- [ ] Mode trading choisi (paper/real)

---

## 🚀 Une fois configuré

Le bot va:
1. Scanner les nouveaux tokens sur Base (toutes les 30 secondes)
2. Filtrer les tokens selon les critères (toutes les 60 secondes)
3. Entrer en position sur les tokens approuvés
4. Gérer les positions avec trailing stops
5. Fermer les positions selon les règles de sortie

Vous pouvez suivre l'activité:
- **Dashboard**: http://46.62.194.176:8501
- **Logs**: `tail -f /home/basebot/trading-bot/logs/trader.log`

---

## ❓ Besoin d'aide?

Si le bot ne démarre toujours pas après configuration:

```bash
# Voir les logs détaillés
sshpass -p "000Rnella" ssh root@46.62.194.176 "journalctl -u basebot-trader -n 50"

# Vérifier la configuration
sshpass -p "000Rnella" ssh root@46.62.194.176 "head -n 50 /home/basebot/trading-bot/config/.env | grep -v PRIVATE_KEY"
```

Erreurs communes:
- `Non-hexadecimal digit found` → Clé privée invalide (vérifiez le format)
- `Insufficient funds` → Pas assez de ETH sur le wallet
- `Connection refused` → RPC down (le bot va fallback automatiquement)

---

**Prochaine étape**: Configurez votre wallet, redémarrez le bot, et attendez les premiers trades !
