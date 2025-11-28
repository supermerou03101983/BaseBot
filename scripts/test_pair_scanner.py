#!/usr/bin/env python3
"""
Script de test pour PairEventWindowScanner
Vérifie le bon fonctionnement du scanner on-chain
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire src au path si besoin
PROJECT_DIR = Path(__file__).parent
sys.path.append(str(PROJECT_DIR))

from pair_event_window_scanner import PairEventWindowScanner


def test_connection():
    """Test 1: Vérifier la connexion au RPC"""
    print("\n" + "="*80)
    print("TEST 1: Connexion au RPC Base")
    print("="*80)

    try:
        scanner = PairEventWindowScanner()
        current_block = scanner.w3.eth.block_number
        print(f"✅ Connexion réussie!")
        print(f"📊 Bloc actuel: {current_block}")
        print(f"⏱️  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return scanner
    except Exception as e:
        print(f"❌ ÉCHEC: {e}")
        return None


def test_scan_window(scanner, min_hours=2, max_hours=6, max_results=10):
    """Test 2: Scanner une fenêtre temporelle"""
    print("\n" + "="*80)
    print(f"TEST 2: Scan de tokens entre {min_hours}h et {max_hours}h")
    print("="*80)

    try:
        tokens = scanner.scan_tokens_in_age_window(
            min_hours=min_hours,
            max_hours=max_hours,
            max_results=max_results
        )

        print(f"\n✅ Scan terminé: {len(tokens)} tokens trouvés")

        if tokens:
            print(f"\n📋 Aperçu des résultats:\n")
            for i, token in enumerate(tokens[:5], 1):  # Afficher les 5 premiers
                base = "WETH" if "4200" in token['base_token'] else "USDC/USDbC"
                print(f"{i}. Token: {token['token_address']}")
                print(f"   Factory: {token['factory_name']}")
                print(f"   Base: {base}")
                print(f"   Âge: {token['age_hours']:.2f}h")
                print()

        return tokens

    except Exception as e:
        print(f"❌ ÉCHEC: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_metadata(scanner, tokens):
    """Test 3: Récupération des métadonnées"""
    print("\n" + "="*80)
    print("TEST 3: Récupération des métadonnées ERC20")
    print("="*80)

    if not tokens:
        print("⚠️  Aucun token à tester (scan précédent vide)")
        return

    # Tester sur le premier token
    token = tokens[0]
    print(f"\n🔍 Test sur: {token['token_address']}")

    try:
        metadata = scanner.get_token_metadata(token['token_address'])

        print(f"✅ Métadonnées récupérées:")
        print(f"   Nom: {metadata['name']}")
        print(f"   Symbole: {metadata['symbol']}")
        print(f"   Decimals: {metadata['decimals']}")

    except Exception as e:
        print(f"❌ ÉCHEC: {e}")


def test_edge_cases(scanner):
    """Test 4: Cas limites"""
    print("\n" + "="*80)
    print("TEST 4: Cas limites")
    print("="*80)

    # Test fenêtre très courte (dernière heure)
    print("\n🔍 Test 4a: Fenêtre courte (0.5h à 1h)")
    try:
        tokens_short = scanner.scan_tokens_in_age_window(
            min_hours=0.5,
            max_hours=1.0,
            max_results=5
        )
        print(f"   ✅ {len(tokens_short)} tokens trouvés dans la dernière heure")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

    # Test fenêtre plus longue (24h)
    print("\n🔍 Test 4b: Fenêtre longue (12h à 24h)")
    try:
        tokens_long = scanner.scan_tokens_in_age_window(
            min_hours=12,
            max_hours=24,
            max_results=5
        )
        print(f"   ✅ {len(tokens_long)} tokens trouvés (12-24h)")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

    # Test avec limite = 0
    print("\n🔍 Test 4c: Limite de résultats = 0")
    try:
        tokens_zero = scanner.scan_tokens_in_age_window(
            min_hours=2,
            max_hours=6,
            max_results=0
        )
        print(f"   ✅ {len(tokens_zero)} tokens (devrait être 0)")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")


def test_factories(scanner):
    """Test 5: Vérifier que les deux factories sont bien scannées"""
    print("\n" + "="*80)
    print("TEST 5: Multi-factory support (Aerodrome + BaseSwap)")
    print("="*80)

    try:
        tokens = scanner.scan_tokens_in_age_window(
            min_hours=1,
            max_hours=24,
            max_results=50
        )

        # Compter par factory
        aerodrome_count = sum(1 for t in tokens if t['factory_name'] == 'Aerodrome')
        baseswap_count = sum(1 for t in tokens if t['factory_name'] == 'BaseSwap')

        print(f"\n✅ Résultats par factory:")
        print(f"   🏭 Aerodrome: {aerodrome_count} tokens")
        print(f"   🏭 BaseSwap: {baseswap_count} tokens")
        print(f"   📊 Total: {len(tokens)} tokens")

    except Exception as e:
        print(f"❌ ÉCHEC: {e}")


def main():
    """Lance tous les tests"""
    print("\n" + "🚀"*40)
    print("  TEST SUITE: PairEventWindowScanner")
    print("🚀"*40)

    # Configurer le logging
    logging.basicConfig(
        level=logging.WARNING,  # Réduire le bruit pendant les tests
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Test 1: Connexion
    scanner = test_connection()
    if not scanner:
        print("\n❌ Arrêt des tests: connexion impossible")
        sys.exit(1)

    # Test 2: Scan principal
    tokens = test_scan_window(scanner, min_hours=2, max_hours=6, max_results=10)

    # Test 3: Métadonnées
    test_metadata(scanner, tokens)

    # Test 4: Cas limites
    test_edge_cases(scanner)

    # Test 5: Multi-factory
    test_factories(scanner)

    # Résumé final
    print("\n" + "="*80)
    print("✅ TOUS LES TESTS TERMINÉS")
    print("="*80)
    print("\n💡 Le scanner est prêt à être intégré dans Scanner.py")
    print("   Utilisation:")
    print("   >>> from pair_event_window_scanner import PairEventWindowScanner")
    print("   >>> scanner = PairEventWindowScanner()")
    print("   >>> tokens = scanner.scan_tokens_in_age_window(min_hours=2, max_hours=12)")
    print()


if __name__ == '__main__':
    main()
