#!/usr/bin/env python3
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

# Datos del usuario problemático
dni = '69338576Q'
email = 'seidor@gmail.com'

print(f"Verificando usuario {dni}...")

try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

    with conn.cursor() as cursor:
        # Buscar por login
        cursor.execute("SELECT ID, user_login, user_email FROM wp_users WHERE user_login = %s", (dni,))
        result_login = cursor.fetchone()

        # Buscar por email
        cursor.execute("SELECT ID, user_login, user_email FROM wp_users WHERE user_email = %s", (email,))
        result_email = cursor.fetchone()

        print(f"Por login '{dni}': {result_login}")
        print(f"Por email '{email}': {result_email}")

        # Verificar si existe alguna tabla wp_users
        cursor.execute("SHOW TABLES LIKE 'wp_users'")
        table_exists = cursor.fetchone()
        print(f"Tabla wp_users existe: {table_exists is not None}")

        if table_exists:
            # Verificar estructura de la tabla
            cursor.execute("DESCRIBE wp_users")
            columns = cursor.fetchall()
            print("Columnas de wp_users:")
            for col in columns:
                print(f"  {col[0]}: {col[1]}")

    conn.close()

except Exception as e:
    print(f"Error: {e}")