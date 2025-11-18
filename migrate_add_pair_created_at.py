#!/usr/bin/env python3
"""
Migration Script - Ajoute la colonne pair_created_at à la table discovered_tokens
Date: 2025-11-18
"""

import sqlite3
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / 'data' / 'trading.db'

def migrate_database():
    """Ajoute les colonnes pair_created_at et volume_24h si elles n'existent pas"""

    if not DB_PATH.exists():
        print(f"❌ Base de données non trouvée: {DB_PATH}")
        print("ℹ️  La migration n'est pas nécessaire pour une nouvelle installation.")
        return True

    print(f"📊 Migration de la base de données: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Vérifier les colonnes existantes
        cursor.execute("PRAGMA table_info(discovered_tokens)")
        columns = [row[1] for row in cursor.fetchall()]

        print(f"Colonnes actuelles: {', '.join(columns)}")

        migrations_applied = 0

        # Migration 1: Ajouter pair_created_at
        if 'pair_created_at' not in columns:
            print("➕ Ajout de la colonne 'pair_created_at'...")
            cursor.execute('''
                ALTER TABLE discovered_tokens
                ADD COLUMN pair_created_at TIMESTAMP
            ''')
            migrations_applied += 1
            print("✅ Colonne 'pair_created_at' ajoutée")
        else:
            print("✅ Colonne 'pair_created_at' déjà présente")

        # Migration 2: Ajouter volume_24h (si pas déjà présente)
        if 'volume_24h' not in columns:
            print("➕ Ajout de la colonne 'volume_24h'...")
            cursor.execute('''
                ALTER TABLE discovered_tokens
                ADD COLUMN volume_24h REAL
            ''')
            migrations_applied += 1
            print("✅ Colonne 'volume_24h' ajoutée")
        else:
            print("✅ Colonne 'volume_24h' déjà présente")

        # Migration 3: Renommer created_at en discovered_at (SQLite ne supporte pas RENAME COLUMN avant v3.25)
        # On va simplement documenter que created_at = discovered_at dans les anciennes installations
        if 'discovered_at' not in columns and 'created_at' in columns:
            print("ℹ️  Note: La colonne 'created_at' dans les anciennes installations représente 'discovered_at'")
            print("   Les nouvelles installations utiliseront 'discovered_at' explicitement")

        conn.commit()

        if migrations_applied > 0:
            print(f"\n✅ Migration terminée! {migrations_applied} colonne(s) ajoutée(s)")

            # Compter les tokens existants
            cursor.execute("SELECT COUNT(*) FROM discovered_tokens")
            token_count = cursor.fetchone()[0]

            if token_count > 0:
                print(f"\n⚠️  IMPORTANT: {token_count} token(s) existant(s) dans la base")
                print("   → pair_created_at sera NULL pour ces tokens (normal)")
                print("   → Le Scanner remplira cette colonne pour les nouveaux tokens")
                print("   → Le Filter gérera correctement les valeurs NULL (pas de bonus Age)")
        else:
            print("\n✅ Base de données déjà à jour - Aucune migration nécessaire")

        return True

    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()

def verify_migration():
    """Vérifie que la migration a réussi"""

    if not DB_PATH.exists():
        return True  # Pas de DB = nouvelle installation

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(discovered_tokens)")
        columns = [row[1] for row in cursor.fetchall()]

        required_columns = ['pair_created_at', 'volume_24h']
        missing_columns = [col for col in required_columns if col not in columns]

        if missing_columns:
            print(f"\n❌ Colonnes manquantes: {', '.join(missing_columns)}")
            return False

        print("\n✅ Vérification: Toutes les colonnes requises sont présentes")
        return True

    except Exception as e:
        print(f"\n❌ Erreur lors de la vérification: {e}")
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("  MIGRATION BASE DE DONNÉES - Token Age Fix")
    print("=" * 60)
    print()

    success = migrate_database()

    if success:
        success = verify_migration()

    if success:
        print("\n" + "=" * 60)
        print("  ✅ MIGRATION RÉUSSIE")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("  ❌ MIGRATION ÉCHOUÉE")
        print("=" * 60)
        sys.exit(1)
