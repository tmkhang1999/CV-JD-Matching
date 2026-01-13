#!/usr/bin/env python3
"""
Database migration script to fix null document_id constraint violations.
This script should be run to clean up existing data before applying the schema changes.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.db.session import SessionLocal


def clean_null_document_ids():
    """Remove any document_embeddings records with null document_id"""
    db = SessionLocal()
    try:
        # Find and remove any embeddings with null document_id
        result = db.execute(text("SELECT COUNT(*) FROM document_embeddings WHERE document_id IS NULL"))
        null_count = result.scalar()

        if null_count > 0:
            print(f"Found {null_count} embedding records with null document_id. Removing them...")
            db.execute(text("DELETE FROM document_embeddings WHERE document_id IS NULL"))
            db.commit()
            print("Removed null document_id records.")
        else:
            print("No null document_id records found.")

        # Add NOT NULL constraint if it doesn't exist
        try:
            db.execute(text("ALTER TABLE document_embeddings ALTER COLUMN document_id SET NOT NULL"))
            db.commit()
            print("Added NOT NULL constraint to document_id column.")
        except Exception as e:
            if "already exists" in str(e) or "not null" in str(e).lower():
                print("NOT NULL constraint already exists on document_id column.")
            else:
                print(f"Warning: Could not add NOT NULL constraint: {e}")

    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("Running database migration to fix null document_id constraint violations...")
    clean_null_document_ids()
    print("Migration completed.")
