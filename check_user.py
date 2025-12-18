#!/usr/bin/env python3
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

    with conn.cursor() as cursor:
        # Verificar el ultimo usuario
        cursor.execute("SELECT ID, user_login, user_email, display_name, user_registered FROM wp_users WHERE user_login = '69338576Q'")
        result = cursor.fetchone()

        if result:
            print(f"Usuario encontrado:")
            print(f"  ID: {result[0]}")
            print(f"  Login: {result[1]}")
            print(f"  Email: {result[2]}")
            print(f"  Display Name: {result[3]}")
            print(f"  Registrado: {result[4]}")
        else:
            print("Usuario 69338576Q NO encontrado en la base de datos")

        # Verificar total de usuarios
        cursor.execute("SELECT COUNT(*) FROM wp_users")
        total = cursor.fetchone()[0]
        print(f"\nTotal de usuarios en wp_users: {total}")

    conn.close()

except Exception as e:
    print(f"Error: {e}")