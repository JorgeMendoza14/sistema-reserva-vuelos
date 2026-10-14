import os
import mysql.connector

from flask import Flask, abort, redirect, render_template, request, url_for
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


@app.route("/pasajeros", methods=["GET", "POST"])
def pasajeros():
    if request.method == "POST":
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO pasajeros
                (cedula, nombres, apellidos, telefono, correo, fecha_nacimiento)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                request.form["cedula"],
                request.form["nombres"],
                request.form["apellidos"],
                request.form["telefono"],
                request.form["correo"],
                request.form["fecha_nacimiento"],
            ),
        )
        conexion.commit()
        cursor.close()
        conexion.close()
        return redirect(url_for("pasajeros"))

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id_pasajero, cedula, nombres, apellidos, telefono, correo,
               fecha_nacimiento
        FROM pasajeros
        ORDER BY id_pasajero
        """
    )
    lista_pasajeros = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template("pasajeros.html", pasajeros=lista_pasajeros)


@app.route("/pasajeros/editar/<int:id_pasajero>", methods=["GET", "POST"])
def editar_pasajero(id_pasajero):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
            UPDATE pasajeros
            SET cedula = %s, nombres = %s, apellidos = %s, telefono = %s,
                correo = %s, fecha_nacimiento = %s
            WHERE id_pasajero = %s
            """,
            (
                request.form["cedula"],
                request.form["nombres"],
                request.form["apellidos"],
                request.form["telefono"],
                request.form["correo"],
                request.form["fecha_nacimiento"],
                id_pasajero,
            ),
        )
        conexion.commit()
        cursor.close()
        conexion.close()
        return redirect(url_for("pasajeros"))

    cursor.execute(
        """
        SELECT id_pasajero, cedula, nombres, apellidos, telefono, correo,
               fecha_nacimiento
        FROM pasajeros
        WHERE id_pasajero = %s
        """,
        (id_pasajero,),
    )
    pasajero_editar = cursor.fetchone()
    if pasajero_editar is None:
        cursor.close()
        conexion.close()
        abort(404)

    cursor.execute(
        """
        SELECT id_pasajero, cedula, nombres, apellidos, telefono, correo,
               fecha_nacimiento
        FROM pasajeros
        ORDER BY id_pasajero
        """
    )
    lista_pasajeros = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template(
        "pasajeros.html",
        pasajeros=lista_pasajeros,
        pasajero_editar=pasajero_editar,
    )


@app.route("/pasajeros/eliminar/<int:id_pasajero>", methods=["POST"])
def eliminar_pasajero(id_pasajero):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "DELETE FROM pasajeros WHERE id_pasajero = %s",
        (id_pasajero,),
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    return redirect(url_for("pasajeros"))


@app.route("/aerolineas", methods=["GET", "POST"])
def aerolineas():
    if request.method == "POST":
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO aerolineas (nombre, codigo, pais)
            VALUES (%s, %s, %s)
            """,
            (
                request.form["nombre"],
                request.form["codigo"],
                request.form["pais"],
            ),
        )
        conexion.commit()
        cursor.close()
        conexion.close()
        return redirect(url_for("aerolineas"))

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id_aerolinea, nombre, codigo, pais
        FROM aerolineas
        ORDER BY id_aerolinea
        """
    )
    lista_aerolineas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template("aerolineas.html", aerolineas=lista_aerolineas)


@app.route("/aerolineas/editar/<int:id_aerolinea>", methods=["GET", "POST"])
def editar_aerolinea(id_aerolinea):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
            UPDATE aerolineas
            SET nombre = %s, codigo = %s, pais = %s
            WHERE id_aerolinea = %s
            """,
            (
                request.form["nombre"],
                request.form["codigo"],
                request.form["pais"],
                id_aerolinea,
            ),
        )
        conexion.commit()
        cursor.close()
        conexion.close()
        return redirect(url_for("aerolineas"))

    cursor.execute(
        """
        SELECT id_aerolinea, nombre, codigo, pais
        FROM aerolineas
        WHERE id_aerolinea = %s
        """,
        (id_aerolinea,),
    )
    aerolinea_editar = cursor.fetchone()
    if aerolinea_editar is None:
        cursor.close()
        conexion.close()
        abort(404)

    cursor.execute(
        """
        SELECT id_aerolinea, nombre, codigo, pais
        FROM aerolineas
        ORDER BY id_aerolinea
        """
    )
    lista_aerolineas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template(
        "aerolineas.html",
        aerolineas=lista_aerolineas,
        aerolinea_editar=aerolinea_editar,
    )


@app.route("/aerolineas/eliminar/<int:id_aerolinea>", methods=["POST"])
def eliminar_aerolinea(id_aerolinea):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "DELETE FROM aerolineas WHERE id_aerolinea = %s",
        (id_aerolinea,),
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    return redirect(url_for("aerolineas"))


if __name__ == "__main__":
    app.run(debug=True)