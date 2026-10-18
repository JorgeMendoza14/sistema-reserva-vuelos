import getpass
import os

import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash


def obtener_conexion():
    load_dotenv()
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


def main():
    nombre = input("Nombre del administrador: ").strip()
    correo = input("Correo del administrador: ").strip()
    contrasena = getpass.getpass("Contraseña: ")
    confirmacion = getpass.getpass("Confirma la contraseña: ")

    if not nombre or not correo or not contrasena:
        print("Todos los campos son obligatorios.")
        return
    if contrasena != confirmacion:
        print("Las contraseñas no coinciden.")
        return

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO usuarios (nombre, correo, contrasena, rol, estado)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                nombre,
                correo,
                generate_password_hash(contrasena),
                "administrador",
                True,
            ),
        )
        conexion.commit()
        print("Administrador creado correctamente.")
    except mysql.connector.Error as error:
        conexion.rollback()
        print(f"No se pudo crear el administrador: {error}")
    finally:
        cursor.close()
        conexion.close()


if __name__ == "__main__":
    main()