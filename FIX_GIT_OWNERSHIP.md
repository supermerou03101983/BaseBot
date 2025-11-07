# Fix: Git Ownership Error

## Problème

```
fatal: detected dubious ownership in repository at '/home/basebot/trading-bot'
```

## Cause

Vous êtes connecté en tant que `root`, mais le répertoire `/home/basebot/trading-bot` appartient à l'utilisateur `basebot`. Git refuse de travailler pour des raisons de sécurité.

## Solution

### Option A: Se connecter en tant que basebot (RECOMMANDÉ)

```bash
# Depuis root, passer à basebot
su - basebot

# Naviguer vers le répertoire
cd /home/basebot/trading-bot

# Maintenant git pull fonctionne
git pull

# Exécuter le diagnostic
bash diagnose_scanner.sh
```

---

### Option B: Ajouter une exception Git (si vraiment nécessaire)

⚠️ **Moins sécurisé, à utiliser uniquement si Option A ne fonctionne pas**

```bash
# En tant que root
git config --global --add safe.directory /home/basebot/trading-bot

# Maintenant vous pouvez faire git pull
git pull

# Exécuter le diagnostic
bash diagnose_scanner.sh
```

---

## Commandes complètes

### Workflow complet (Option A - Recommandé):

```bash
# Connexion SSH
ssh root@your-vps

# Passer à l'utilisateur basebot
su - basebot

# Le répertoire par défaut devrait être /home/basebot
cd trading-bot

# Mettre à jour le repo
git pull

# Lancer le diagnostic
bash diagnose_scanner.sh

# Pour sortir de la session basebot
exit
```

---

### Workflow complet (Option B - Si problème avec credentials Git):

```bash
# Connexion SSH
ssh root@your-vps

# Ajouter l'exception Git
git config --global --add safe.directory /home/basebot/trading-bot

# Aller dans le répertoire
cd /home/basebot/trading-bot

# Pull en tant que root (peut échouer si clé SSH/token manquant)
git pull

# Si git pull échoue, faire en tant que basebot:
su - basebot -c "cd /home/basebot/trading-bot && git pull"

# Lancer le diagnostic (en tant que root fonctionne pour ce script)
bash diagnose_scanner.sh
```

---

## Si git pull échoue à cause des credentials

Votre repository est **privé**, donc vous avez besoin d'authentification.

### Solution 1: Utiliser HTTPS avec token

```bash
# En tant que basebot
su - basebot
cd /home/basebot/trading-bot

# Configurer Git pour utiliser HTTPS avec token
git remote set-url origin https://TOKEN@github.com/supermerou03101983/BaseBot.git

# Remplacez TOKEN par votre Personal Access Token GitHub
# Créer un token: https://github.com/settings/tokens

# Maintenant git pull fonctionne
git pull
```

### Solution 2: Utiliser SSH (si configuré)

```bash
# En tant que basebot
su - basebot
cd /home/basebot/trading-bot

# Configurer Git pour utiliser SSH
git remote set-url origin git@github.com:supermerou03101983/BaseBot.git

# Vous devez avoir ajouté votre clé SSH sur GitHub
# https://github.com/settings/keys

# Maintenant git pull fonctionne
git pull
```

---

## Vérifier l'ownership actuel

```bash
ls -la /home/basebot/trading-bot/
```

**Attendu:**
```
drwxr-xr-x  10 basebot basebot  4096 Nov  7 10:00 .
drwxr-xr-x   3 basebot basebot  4096 Nov  6 15:00 ..
drwxr-xr-x   8 basebot basebot  4096 Nov  7 10:05 .git
...
```

Tous les fichiers doivent appartenir à `basebot:basebot`.

---

## Si les fichiers appartiennent à root (après git pull en root)

```bash
# Corriger l'ownership
chown -R basebot:basebot /home/basebot/trading-bot

# Vérifier
ls -la /home/basebot/trading-bot/
```

---

## Commande finale recommandée

```bash
# 1. Se connecter en SSH
ssh root@your-vps

# 2. Passer à basebot
su - basebot

# 3. Aller dans le répertoire
cd trading-bot

# 4. Mettre à jour
git pull

# 5. Lancer le diagnostic
bash diagnose_scanner.sh

# 6. Si vous devez relancer le scanner après corrections
exit  # Sortir de basebot
systemctl restart basebot-scanner
journalctl -u basebot-scanner -f
```

---

## Résumé

| Problème | Solution |
|----------|----------|
| `dubious ownership` | `su - basebot` puis `git pull` |
| `No such file or directory` | Faire `git pull` d'abord |
| `Authentication failed` | Configurer token/SSH pour repo privé |
| Fichiers owned by root | `chown -R basebot:basebot /home/basebot/trading-bot` |

