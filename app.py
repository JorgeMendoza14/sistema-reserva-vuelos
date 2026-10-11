import os
import mysql.connector

from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


def obtener_conexion():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


@app.route("/")
def inicio():
    conexion = obtener_conexion()

    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            v.numero_vuelo,
            a.nombre AS aerolinea,
            origen.ciudad AS origen,
            destino.ciudad AS destino,
            v.fecha_salida,
            v.hora_salida,
            v.precio,
            v.asientos_disponibles
        FROM vuelos v
        INNER JOIN aerolineas a
            ON v.id_aerolinea = a.id_aerolinea
        INNER JOIN aeropuertos origen
            ON v.id_origen = origen.id_aeropuerto
        INNER JOIN aeropuertos destino
            ON v.id_destino = destino.id_aeropuerto
    """)

    vuelos = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("index.html", vuelos=vuelos)


if __name__ == "__main__":
    app.run(debug=True)