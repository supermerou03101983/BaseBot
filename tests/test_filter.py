#!/usr/bin/env python3
"""
Test Filter.py avec données mockées
Valide la logique Momentum Safe (Modification #6)
"""

from datetime import datetime, timezone, timedelta

# Mock data - Tokens simulés avec différents profils
mock_tokens = [
    {
        "name": "WINNER Token",
        "symbol": "WIN",
        "token_address": "0x1111111111111111111111111111111111111111",
        "pair_created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
        "liquidity": 50000,
        "market_cap": 150000,
        "volume_1h": 8000,
        "volume_5min": 2500,  # Ratio = 0.31 (bon)
        "price_change_5m": 6.5,
        "price_change_1h": 12.0,
        "holder_count": 180,
        "owner_percentage": 3.5,
        "buy_tax": 1.0,
        "sell_tax": 1.5
    },
    {
        "name": "TOO YOUNG",
        "symbol": "YOUNG",
        "token_address": "0x2222222222222222222222222222222222222222",
        "pair_created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),  # 2h = trop jeune
        "liquidity": 50000,
        "market_cap": 150000,
        "volume_1h": 8000,
        "volume_5min": 2500,
        "price_change_5m": 6.5,
        "price_change_1h": 12.0,
        "holder_count": 180,
        "owner_percentage": 3.5,
        "buy_tax": 1.0,
        "sell_tax": 1.5
    },
    {
        "name": "TOO OLD",
        "symbol": "OLD",
        "token_address": "0x3333333333333333333333333333333333333333",
        "pair_created_at": (datetime.now(timezone.utc) - timedelta(hours=10)).strftime('%Y-%m-%d %H:%M:%S'),  # 10h = trop vieux
        "liquidity": 50000,
        "market_cap": 150000,
        "volume_1h": 8000,
        "volume_5min": 2500,
        "price_change_5m": 6.5,
        "price_change_1h": 12.0,
        "holder_count": 180,
        "owner_percentage": 3.5,
        "buy_tax": 1.0,
        "sell_tax": 1.5
    },
    {
        "name": "LOW LIQUIDITY",
        "symbol": "LOWLIQ",
        "token_address": "0x4444444444444444444444444444444444444444",
        "pair_created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
        "liquidity": 8000,  # < $12k
        "market_cap": 150000,
        "volume_1h": 8000,
        "volume_5min": 2500,
        "price_change_5m": 6.5,
        "price_change_1h": 12.0,
        "holder_count": 180,
        "owner_percentage": 3.5,
        "buy_tax": 1.0,
        "sell_tax": 1.5
    },
    {
        "name": "LOW VOLUME 1H",
        "symbol": "LOWVOL",
        "token_address": "0x5555555555555555555555555555555555555555",
        "pair_created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
        "liquidity": 50000,
        "market_cap": 150000,
        "volume_1h": 2000,  # < $4k
        "volume_5min": 600,
        "price_change_5m": 6.5,
        "price_change_1h": 12.0,
        "holder_count": 180,
        "owner_percentage": 3.5,
        "buy_tax": 1.0,
        "sell_tax": 1.5
    },
    {
        "name": "BAD MOMENTUM 5MIN",
        "symbol": "BADM5",
        "token_address": "0x6666666666666666666666666666666666666666",
        "pair_created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
        "liquidity": 50000,
        "market_cap": 150000,
        "volume_1h": 8000,
        "volume_5min": 2500,
        "price_change_5m": 2.0,  # < +4%
        "price_change_1h": 12.0,
        "holder_count": 180,
        "owner_percentage": 3.5,
        "buy_tax": 1.0,
        "sell_tax": 1.5
    },
    {
        "name": "BAD MOMENTUM 1H",
        "symbol": "BADM1",
        "token_address": "0x7777777777777777777777777777777777777777",
        "pair_created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
        "liquidity": 50000,
        "market_cap": 150000,
        "volume_1h": 8000,
        "volume_5min": 2500,
        "price_change_5m": 6.5,
        "price_change_1h": 5.0,  # < +7%
        "holder_count": 180,
        "owner_percentage": 3.5,
        "buy_tax": 1.0,
        "sell_tax": 1.5
    },
    {
        "name": "LOW HOLDERS",
        "symbol": "LOWH",
        "token_address": "0x8888888888888888888888888888888888888888",
        "pair_created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
        "liquidity": 50000,
        "market_cap": 150000,
        "volume_1h": 8000,
        "volume_5min": 2500,
        "price_change_5m": 6.5,
        "price_change_1h": 12.0,
        "holder_count": 80,  # < 120
        "owner_percentage": 3.5,
        "buy_tax": 1.0,
        "sell_tax": 1.5
    },
    {
        "name": "HIGH TAXES",
        "symbol": "TAX",
        "token_address": "0x9999999999999999999999999999999999999999",
        "pair_created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
        "liquidity": 50000,
        "market_cap": 150000,
        "volume_1h": 8000,
        "volume_5min": 2500,
        "price_change_5m": 6.5,
        "price_change_1h": 12.0,
        "holder_count": 180,
        "owner_percentage": 3.5,
        "buy_tax": 5.0,  # > 3%
        "sell_tax": 1.5
    },
    {
        "name": "LOW RATIO 5M/1H",
        "symbol": "RATIO",
        "token_address": "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "pair_created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S'),
        "liquidity": 50000,
        "market_cap": 150000,
        "volume_1h": 8000,
        "volume_5min": 1000,  # Ratio = 0.125 < 0.3
        "price_change_5m": 6.5,
        "price_change_1h": 12.0,
        "holder_count": 180,
        "owner_percentage": 3.5,
        "buy_tax": 1.0,
        "sell_tax": 1.5
    }
]


def test_filter():
    """Test la fonction calculate_score avec les mocks"""
    import sys
    import os
    from pathlib import Path

    # Ajouter src/ au path
    PROJECT_DIR = Path(__file__).parent
    sys.path.insert(0, str(PROJECT_DIR / 'src'))

    # Charger .env pour les seuils
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / 'config' / '.env')

    # Importer Filter
    from Filter import TokenFilter

    print("=" * 80)
    print("🧪 TEST FILTER - Stratégie Momentum Safe (Modification #6)")
    print("=" * 80)
    print()

    # Initialiser le filter
    try:
        token_filter = TokenFilter()
        print("✅ TokenFilter initialisé avec succès")
        print()
    except Exception as e:
        print(f"❌ ERREUR initialisation TokenFilter: {e}")
        return

    # Tester chaque mock
    results = []

    for token in mock_tokens:
        symbol = token['symbol']
        print(f"📊 Test: {symbol} ({token['name']})")
        print("-" * 80)

        try:
            score, reasons = token_filter.calculate_score(token)

            if score > 0:
                status = "✅ APPROUVÉ"
                results.append(("✅", symbol, score, reasons[0] if reasons else ""))
            else:
                status = "❌ REJETÉ"
                reject_reason = reasons[0] if reasons else "Raison inconnue"
                results.append(("❌", symbol, score, reject_reason))

            print(f"{status} | Score: {score:.1f}")
            print(f"Raisons:")
            for reason in reasons[:3]:  # Afficher les 3 premières raisons
                print(f"  - {reason}")

        except Exception as e:
            print(f"❌ ERREUR: {e}")
            results.append(("💥", symbol, 0, str(e)))

        print()

    # Résumé
    print("=" * 80)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 80)
    print()

    approved = [r for r in results if r[0] == "✅"]
    rejected = [r for r in results if r[0] == "❌"]
    errors = [r for r in results if r[0] == "💥"]

    print(f"✅ Approuvés: {len(approved)}/{len(results)}")
    for status, symbol, score, reason in approved:
        print(f"   - {symbol}: {score:.1f} pts")

    print()
    print(f"❌ Rejetés: {len(rejected)}/{len(results)}")
    for status, symbol, score, reason in rejected:
        print(f"   - {symbol}: {reason}")

    if errors:
        print()
        print(f"💥 Erreurs: {len(errors)}/{len(results)}")
        for status, symbol, score, reason in errors:
            print(f"   - {symbol}: {reason}")

    print()
    print("=" * 80)

    # Résultat attendu
    print("✅ RÉSULTAT ATTENDU:")
    print("   - WIN: APPROUVÉ (seul token parfait)")
    print("   - Tous les autres: REJETÉS (chacun a un défaut)")
    print()

    if len(approved) == 1 and approved[0][1] == "WIN" and len(rejected) == 9:
        print("🎉 TEST RÉUSSI - Filtre fonctionne correctement!")
        return True
    else:
        print("⚠️ TEST ÉCHOUÉ - Vérifier la logique du filtre")
        return False


if __name__ == '__main__':
    success = test_filter()
    exit(0 if success else 1)
