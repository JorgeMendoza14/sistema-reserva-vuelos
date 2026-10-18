import os
from decimal import Decimal, InvalidOperation
import mysql.connector

from flask import Flask, abort, redirect, render_template, request, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ESTADOS_VUELO = ("Disponible", "Completo", "Cancelado", "Finalizado")


def obtener_conexion():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


def cargar_opciones_vuelo(cursor):
    cursor.execute(
        "SELECT id_aerolinea, nombre FROM aerolineas ORDER BY nombre"
    )
    lista_aerolineas = cursor.fetchall()

    cursor.execute(
        """
        SELECT id_aeropuerto, nombre, codigo, ciudad
        FROM aeropuertos
        ORDER BY ciudad, nombre
        """
    )
    lista_aeropuertos = cursor.fetchall()
    return lista_aerolineas, lista_aeropuertos


def validar_datos_vuelo(formulario):
    try:
        datos = {
            "numero_vuelo": formulario.get("numero_vuelo", "").strip(),
            "id_aerolinea": int(formulario.get("id_aerolinea", "")),
            "id_origen": int(formulario.get("id_origen", "")),
            "id_destino": int(formulario.get("id_destino", "")),
            "fecha_salida": formulario.get("fecha_salida", ""),
            "hora_salida": formulario.get("hora_salida", ""),
            "fecha_llegada": formulario.get("fecha_llegada", ""),
            "hora_llegada": formulario.get("hora_llegada", ""),
            "precio": Decimal(formulario.get("precio", "")),
            "asientos_disponibles": int(formulario.get("asientos_disponibles", "")),
            "estado": formulario.get("estado", ""),
        }
    except (InvalidOperation, TypeError, ValueError):
        return None, "Revisa los valores numéricos del vuelo."

    if not all((
        datos["numero_vuelo"],
        datos["fecha_salida"],
        datos["hora_salida"],
        datos["fecha_llegada"],
        datos["hora_llegada"],
    )):
        return None, "Completa todos los campos del vuelo."
    if datos["id_origen"] == datos["id_destino"]:
        return None, "El origen y el destino deben ser aeropuertos distintos."
    if not datos["precio"].is_finite() or datos["precio"] <= 0:
        return None, "El precio debe ser mayor que 0."
    if datos["asientos_disponibles"] < 0:
        return None, "Los asientos disponibles no pueden ser negativos."
    if datos["estado"] not in ESTADOS_VUELO:
        return None, "Selecciona un estado válido."
    return datos, None


def obtener_lista_vuelos(cursor):
    cursor.execute(
        """
        SELECT v.id_vuelo, v.numero_vuelo, v.id_aerolinea,
               v.id_origen, v.id_destino, v.fecha_salida, v.hora_salida,
               v.fecha_llegada, v.hora_llegada, v.precio,
               v.asientos_disponibles, v.estado,
               a.nombre AS aerolinea,
               origen.ciudad AS ciudad_origen,
               origen.codigo AS codigo_origen,
               destino.ciudad AS ciudad_destino,
               destino.codigo AS codigo_destino
        FROM vuelos v
        INNER JOIN aerolineas a
            ON v.id_aerolinea = a.id_aerolinea
        INNER JOIN aeropuertos origen
            ON v.id_origen = origen.id_aeropuerto
        INNER JOIN aeropuertos destino
            ON v.id_destino = destino.id_aeropuerto
        ORDER BY v.id_vuelo
        """
    )
    return cursor.fetchall()


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


@app.route("/aeropuertos", methods=["GET", "POST"])
def aeropuertos():
    if request.method == "POST":
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO aeropuertos (nombre, codigo, ciudad, pais)
            VALUES (%s, %s, %s, %s)
            """,
            (
                request.form["nombre"],
                request.form["codigo"],
                request.form["ciudad"],
                request.form["pais"],
            ),
        )
        conexion.commit()
        cursor.close()
        conexion.close()
        return redirect(url_for("aeropuertos"))

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id_aeropuerto, nombre, codigo, ciudad, pais
        FROM aeropuertos
        ORDER BY id_aeropuerto
        """
    )
    lista_aeropuertos = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template("aeropuertos.html", aeropuertos=lista_aeropuertos)


@app.route("/aeropuertos/editar/<int:id_aeropuerto>", methods=["GET", "POST"])
def editar_aeropuerto(id_aeropuerto):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
            UPDATE aeropuertos
            SET nombre = %s, codigo = %s, ciudad = %s, pais = %s
            WHERE id_aeropuerto = %s
            """,
            (
                request.form["nombre"],
                request.form["codigo"],
                request.form["ciudad"],
                request.form["pais"],
                id_aeropuerto,
            ),
        )
        conexion.commit()
        cursor.close()
        conexion.close()
        return redirect(url_for("aeropuertos"))

    cursor.execute(
        """
        SELECT id_aeropuerto, nombre, codigo, ciudad, pais
        FROM aeropuertos
        WHERE id_aeropuerto = %s
        """,
        (id_aeropuerto,),
    )
    aeropuerto_editar = cursor.fetchone()
    if aeropuerto_editar is None:
        cursor.close()
        conexion.close()
        abort(404)

    cursor.execute(
        """
        SELECT id_aeropuerto, nombre, codigo, ciudad, pais
        FROM aeropuertos
        ORDER BY id_aeropuerto
        """
    )
    lista_aeropuertos = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template(
        "aeropuertos.html",
        aeropuertos=lista_aeropuertos,
        aeropuerto_editar=aeropuerto_editar,
    )


@app.route("/aeropuertos/eliminar/<int:id_aeropuerto>", methods=["POST"])
def eliminar_aeropuerto(id_aeropuerto):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "DELETE FROM aeropuertos WHERE id_aeropuerto = %s",
        (id_aeropuerto,),
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    return redirect(url_for("aeropuertos"))


@app.route("/vuelos", methods=["GET", "POST"])
def vuelos():
    if request.method == "POST":
        datos, error = validar_datos_vuelo(request.form)
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        if error:
            lista_aerolineas, lista_aeropuertos = cargar_opciones_vuelo(cursor)
            lista_vuelos = obtener_lista_vuelos(cursor)
            cursor.close()
            conexion.close()
            return render_template(
                "vuelos.html",
                vuelos=lista_vuelos,
                aerolineas=lista_aerolineas,
                aeropuertos=lista_aeropuertos,
                estados=ESTADOS_VUELO,
                datos_formulario=request.form,
                error=error,
            ), 400

        cursor.execute(
            """
            INSERT INTO vuelos
                (numero_vuelo, id_aerolinea, id_origen, id_destino,
                 fecha_salida, hora_salida, fecha_llegada, hora_llegada,
                 precio, asientos_disponibles, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                datos["numero_vuelo"],
                datos["id_aerolinea"],
                datos["id_origen"],
                datos["id_destino"],
                datos["fecha_salida"],
                datos["hora_salida"],
                datos["fecha_llegada"],
                datos["hora_llegada"],
                datos["precio"],
                datos["asientos_disponibles"],
                datos["estado"],
            ),
        )
        conexion.commit()
        cursor.close()
        conexion.close()
        return redirect(url_for("vuelos"))

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    lista_aerolineas, lista_aeropuertos = cargar_opciones_vuelo(cursor)
    lista_vuelos = obtener_lista_vuelos(cursor)
    cursor.close()
    conexion.close()
    return render_template(
        "vuelos.html",
        vuelos=lista_vuelos,
        aerolineas=lista_aerolineas,
        aeropuertos=lista_aeropuertos,
        estados=ESTADOS_VUELO,
    )


@app.route("/vuelos/editar/<int:id_vuelo>", methods=["GET", "POST"])
def editar_vuelo(id_vuelo):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    if request.method == "POST":
        datos, error = validar_datos_vuelo(request.form)
        if error:
            cursor.execute(
                "SELECT id_vuelo FROM vuelos WHERE id_vuelo = %s",
                (id_vuelo,),
            )
            if cursor.fetchone() is None:
                cursor.close()
                conexion.close()
                abort(404)
            lista_aerolineas, lista_aeropuertos = cargar_opciones_vuelo(cursor)
            lista_vuelos = obtener_lista_vuelos(cursor)
            cursor.close()
            conexion.close()
            return render_template(
                "vuelos.html",
                vuelos=lista_vuelos,
                aerolineas=lista_aerolineas,
                aeropuertos=lista_aeropuertos,
                estados=ESTADOS_VUELO,
                vuelo_editar={"id_vuelo": id_vuelo},
                datos_formulario=request.form,
                error=error,
            ), 400

        cursor.execute(
            """
            UPDATE vuelos
            SET numero_vuelo = %s, id_aerolinea = %s, id_origen = %s,
                id_destino = %s, fecha_salida = %s, hora_salida = %s,
                fecha_llegada = %s, hora_llegada = %s, precio = %s,
                asientos_disponibles = %s, estado = %s
            WHERE id_vuelo = %s
            """,
            (
                datos["numero_vuelo"],
                datos["id_aerolinea"],
                datos["id_origen"],
                datos["id_destino"],
                datos["fecha_salida"],
                datos["hora_salida"],
                datos["fecha_llegada"],
                datos["hora_llegada"],
                datos["precio"],
                datos["asientos_disponibles"],
                datos["estado"],
                id_vuelo,
            ),
        )
        conexion.commit()
        cursor.close()
        conexion.close()
        return redirect(url_for("vuelos"))

    cursor.execute(
        "SELECT * FROM vuelos WHERE id_vuelo = %s",
        (id_vuelo,),
    )
    vuelo_editar = cursor.fetchone()
    if vuelo_editar is None:
        cursor.close()
        conexion.close()
        abort(404)

    lista_aerolineas, lista_aeropuertos = cargar_opciones_vuelo(cursor)
    lista_vuelos = obtener_lista_vuelos(cursor)
    cursor.close()
    conexion.close()
    return render_template(
        "vuelos.html",
        vuelos=lista_vuelos,
        aerolineas=lista_aerolineas,
        aeropuertos=lista_aeropuertos,
        estados=ESTADOS_VUELO,
        vuelo_editar=vuelo_editar,
        datos_formulario=vuelo_editar,
    )


@app.route("/vuelos/eliminar/<int:id_vuelo>", methods=["POST"])
def eliminar_vuelo(id_vuelo):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "DELETE FROM vuelos WHERE id_vuelo = %s",
        (id_vuelo,),
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    return redirect(url_for("vuelos"))


if __name__ == "__main__":
    app.run(debug=True)