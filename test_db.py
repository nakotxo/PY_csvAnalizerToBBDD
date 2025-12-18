#!/usr/bin/env python3
"""
Script de prueba para verificar la inserción en base de datos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import insert_valid_users_to_db

# Datos de prueba
test_users = [
    {
        'dni': '12345678A',
        'email': 'test1@example.com',
        'telefono': '600123456'
    },
    {
        'dni': '87654321B',
        'email': 'test2@example.com',
        'telefono': '600654321'
    }
]

print("Probando insercion en base de datos...")
print(f"Datos de prueba: {len(test_users)} usuarios")

try:
    processed_count, inserted_count, updated_count, skipped_count, errors = insert_valid_users_to_db(test_users)

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

    print("\nVerifica en DBeaver si los usuarios se insertaron correctamente en wp_users")

except Exception as e:
    print(f"\nError ejecutando la prueba: {str(e)}")