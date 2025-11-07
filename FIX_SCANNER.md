# Fix de l'erreur Scanner

## Problème rencontré

```
ERROR - Erreur lors de la récupération des nouveaux tokens: 'DexScreenerAPI' object has no attribute 'get_recent_pairs_on_chain'
```

## Solution appliquée

### 1. Ajout de la méthode manquante dans `DexScreenerAPI`

**Fichier**: [src/web3_utils.py](src/web3_utils.py)

Ajout de la méthode `get_recent_pairs_on_chain()` à la classe `DexScreenerAPI` :

```python
def get_recent_pairs_on_chain(self, chain_id: str = 'base', limit: int = 50) -> list:
    """
    Recupere les paires recentes sur une blockchain donnee

    Args:
        chain_id: ID de la blockchain (ex: 'base', 'ethereum')
        limit: Nombre maximum de paires a retourner

    Returns:
        Liste de paires avec leurs donnees
    """
```

Cette méthode :
- Récupère les paires récentes depuis l'API DexScreener
- Filtre par blockchain (Base dans notre cas)
- Trie par volume 24h (proxy pour activité récente)
- Retourne les paires formatées avec toutes les données nécessaires

### 2. Amélioration du Scanner

**Fichier**: [src/Scanner.py](src/Scanner.py)

Modifications apportées :

1. **Utilisation de l'API DexScreener en priorité** :
   - Le Scanner utilise maintenant `get_recent_pairs_on_chain()` pour découvrir de nouveaux tokens
   - Récupère les 20 paires les plus actives sur Base Network

2. **Système de fallback** :
   - Si l'API DexScreener échoue, le Scanner bascule sur la base de données locale
   - Méthode `_fetch_tokens_from_db()` pour réanalyser les tokens existants

3. **Délai de scan configurable** :
   - Utilise la variable d'environnement `SCAN_INTERVAL_SECONDS` (défaut: 30 secondes)
   - Évite de surcharger l'API DexScreener

## Tests

Un script de test a été créé : [test_scanner.py](test_scanner.py)

Pour tester le fix :

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Lancer les tests
python test_scanner.py
```

Le script de test vérifie :
- ✅ La méthode `get_recent_pairs_on_chain` existe et fonctionne
- ✅ La méthode `get_token_info` fonctionne
- ✅ Le Scanner s'initialise correctement
- ✅ Toutes les méthodes nécessaires sont présentes

## Déploiement du fix

### Sur un VPS existant

```bash
# Se connecter au VPS
ssh root@votre-vps

# Arrêter le service Scanner
systemctl stop basebot-scanner

# Mettre à jour le code
su - basebot -c "cd /home/basebot/trading-bot && git pull"

# Redémarrer le service
systemctl start basebot-scanner

# Vérifier les logs
journalctl -u basebot-scanner -f
```

### Nouveau déploiement

Le fix est déjà inclus dans le script `deploy.sh`. Une simple installation suffit :

```bash
curl -s https://raw.githubusercontent.com/supermerou03101983/BaseBot/main/deploy.sh | sudo bash
```

## Vérification

Pour vérifier que le Scanner fonctionne correctement :

```bash
# Voir les logs en temps réel
journalctl -u basebot-scanner -f

# Voir les derniers logs
journalctl -u basebot-scanner -n 100

# Vérifier le statut
systemctl status basebot-scanner
```

Vous devriez voir dans les logs :

```
INFO - Scanner démarré...
INFO - Récupération des nouveaux tokens depuis DexScreener...
INFO - X paires trouvées sur DexScreener
INFO - Token découvert: SYMBOL (0x...) - MC: $XXX
```

## Configuration

Variables d'environnement dans `config/.env` :

```env
# Intervalle de scan en secondes (défaut: 30)
SCAN_INTERVAL_SECONDS=30

# URL RPC pour Base Network
RPC_URL=https://base.drpc.org

# Clés API (optionnel mais recommandé)
ETHERSCAN_API_KEY=VotreCléEtherscan
```

## Dépendances

Aucune nouvelle dépendance n'a été ajoutée. Le fix utilise uniquement :
- `requests` (déjà dans requirements.txt)
- API DexScreener publique (sans clé requise)

## Notes techniques

### Limitations de l'API DexScreener

L'API publique de DexScreener a quelques limitations :
- Pas de rate limit officiel, mais recommandation d'espacer les requêtes
- L'endpoint `/search` ne retourne pas toutes les nouvelles paires
- Solution : scanner toutes les 30 secondes minimum

### Alternative : Scan on-chain

Pour une solution plus robuste à l'avenir, considérer :
- Scanner les événements `PairCreated` des factories Uniswap/Aerodrome
- Utiliser un service d'indexation (The Graph, Goldsky)
- Implémenter un WebSocket pour les événements en temps réel

## Support

Si le problème persiste :

1. Vérifier les logs : `journalctl -u basebot-scanner -f`
2. Tester manuellement : `python test_scanner.py`
3. Vérifier la connexion RPC : `curl -X POST https://mainnet.base.org`
4. Ouvrir une issue sur GitHub avec les logs complets

---

**Date du fix** : 2025-11-06
**Version** : 1.0.1
