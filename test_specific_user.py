#!/usr/bin/env python3
"""
Script de prueba específico para el usuario 69338576Q
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import insert_valid_users_to_db
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

# Usuario problemático
test_user = [{
    'dni': '69338576Q',
    'email': 'seidor@gmail.com',
    'telefono': '606606606'
}]

print("Probando insercion del usuario 69338576Q...")

try:
    processed_count, inserted_count, updated_count, skipped_count, errors = insert_valid_users_to_db(test_user)

    print("\nResultados:")
    print(f"  Procesados: {processed_count}")
    print(f"  Insertados: {inserted_count}")
    print(f"  Actualizados: {updated_count}")
    print(f"  Saltados: {skipped_count}")

    if errors:
        print(f"\nErrores: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\nSin errores")

except Exception as e:
    print(f"\nError general: {str(e)}")
    import traceback
    traceback.print_exc()