import os
from decimal import Decimal, InvalidOperation
import mysql.connector

from flask import Flask, abort, redirect, render_template, request, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ESTADOS_VUELO = ("Disponible", "Completo", "Cancelado", "Finalizado")
ESTADOS_RESERVA = ("Pendiente", "Confirmada", "Cancelada")
METODOS_PAGO = ("Efectivo", "Tarjeta", "Transferencia")
ESTADOS_PAGO = ("Pendiente", "Pagado", "Reembolsado")


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


def validar_datos_reserva(formulario):
    try:
        datos = {
            "id_pasajero": int(formulario.get("id_pasajero", "")),
            "id_vuelo": int(formulario.get("id_vuelo", "")),
            "fecha_reserva": formulario.get("fecha_reserva", ""),
            "cantidad_pasajeros": int(formulario.get("cantidad_pasajeros", "")),
            "estado": formulario.get("estado", ""),
        }
    except (TypeError, ValueError):
        return None, "Selecciona un pasajero y un vuelo, e indica la cantidad."

    if not datos["fecha_reserva"]:
        return None, "Indica la fecha de la reserva."
    if datos["cantidad_pasajeros"] <= 0:
        return None, "La cantidad de pasajeros debe ser mayor que 0."
    if datos["estado"] not in ESTADOS_RESERVA:
        return None, "Selecciona un estado válido."
    return datos, None


def cargar_datos_reservas(cursor, formulario=None, reserva_editar=None, error=None):
    cursor.execute(
        """
        SELECT id_pasajero, nombres, apellidos
        FROM pasajeros
        ORDER BY apellidos, nombres
        """
    )
    lista_pasajeros = cursor.fetchall()

    cursor.execute(
        """
        SELECT v.id_vuelo, v.numero_vuelo, v.precio, v.asientos_disponibles,
               origen.ciudad AS ciudad_origen, origen.codigo AS codigo_origen,
               destino.ciudad AS ciudad_destino, destino.codigo AS codigo_destino
        FROM vuelos v
        INNER JOIN aeropuertos origen
            ON v.id_origen = origen.id_aeropuerto
        INNER JOIN aeropuertos destino
            ON v.id_destino = destino.id_aeropuerto
        ORDER BY v.fecha_salida, v.hora_salida
        """
    )
    lista_vuelos_reserva = cursor.fetchall()

    cursor.execute(
        """
        SELECT r.id_reserva, r.id_pasajero, r.id_vuelo, r.fecha_reserva,
               r.cantidad_pasajeros, r.total, r.estado,
               CONCAT(p.nombres, ' ', p.apellidos) AS nombre_pasajero,
               v.numero_vuelo,
               origen.ciudad AS ciudad_origen, origen.codigo AS codigo_origen,
               destino.ciudad AS ciudad_destino, destino.codigo AS codigo_destino
        FROM reservas r
        INNER JOIN pasajeros p
            ON r.id_pasajero = p.id_pasajero
        INNER JOIN vuelos v
            ON r.id_vuelo = v.id_vuelo
        INNER JOIN aeropuertos origen
            ON v.id_origen = origen.id_aeropuerto
        INNER JOIN aeropuertos destino
            ON v.id_destino = destino.id_aeropuerto
        ORDER BY r.id_reserva
        """
    )
    lista_reservas = cursor.fetchall()

    return render_template(
        "reservas.html",
        reservas=lista_reservas,
        pasajeros=lista_pasajeros,
        vuelos=lista_vuelos_reserva,
        estados=ESTADOS_RESERVA,
        formulario=formulario or reserva_editar or {},
        reserva_editar=reserva_editar,
        error=error,
    )


def obtener_vuelo_bloqueado(cursor, id_vuelo):
    cursor.execute(
        """
        SELECT id_vuelo, precio, asientos_disponibles
        FROM vuelos
        WHERE id_vuelo = %s
        FOR UPDATE
        """,
        (id_vuelo,),
    )
    return cursor.fetchone()


def validar_datos_pago(formulario):
    try:
        datos = {
            "id_reserva": int(formulario.get("id_reserva", "")),
            "metodo_pago": formulario.get("metodo_pago", ""),
            "fecha_pago": formulario.get("fecha_pago", ""),
            "estado": formulario.get("estado", ""),
        }
    except (TypeError, ValueError):
        return None, "Selecciona una reserva válida."

    if not datos["fecha_pago"]:
        return None, "Indica la fecha del pago."
    if datos["metodo_pago"] not in METODOS_PAGO:
        return None, "Selecciona un método de pago válido."
    if datos["estado"] not in ESTADOS_PAGO:
        return None, "Selecciona un estado válido."
    return datos, None


def cargar_datos_pagos(cursor, formulario=None, pago_editar=None, error=None):
    cursor.execute(
        """
        SELECT r.id_reserva, r.total, r.estado,
               CONCAT(p.nombres, ' ', p.apellidos) AS nombre_pasajero,
               v.numero_vuelo
        FROM reservas r
        INNER JOIN pasajeros p
            ON r.id_pasajero = p.id_pasajero
        INNER JOIN vuelos v
            ON r.id_vuelo = v.id_vuelo
        ORDER BY r.id_reserva
        """
    )
    lista_reservas_pago = cursor.fetchall()

    cursor.execute(
        """
        SELECT pg.id_pago, pg.id_reserva, pg.monto, pg.metodo_pago,
               pg.fecha_pago, pg.estado,
               CONCAT(p.nombres, ' ', p.apellidos) AS nombre_pasajero,
               v.numero_vuelo, r.total AS total_reserva
        FROM pagos pg
        INNER JOIN reservas r
            ON pg.id_reserva = r.id_reserva
        INNER JOIN pasajeros p
            ON r.id_pasajero = p.id_pasajero
        INNER JOIN vuelos v
            ON r.id_vuelo = v.id_vuelo
        ORDER BY pg.id_pago
        """
    )
    lista_pagos = cursor.fetchall()

    return render_template(
        "pagos.html",
        pagos=lista_pagos,
        reservas=lista_reservas_pago,
        metodos_pago=METODOS_PAGO,
        estados=ESTADOS_PAGO,
        formulario=formulario or pago_editar or {},
        pago_editar=pago_editar,
        error=error,
    )


def obtener_reserva_pago_bloqueada(cursor, id_reserva):
    cursor.execute(
        """
        SELECT id_reserva, total, estado, id_vuelo, cantidad_pasajeros
        FROM reservas
        WHERE id_reserva = %s
        FOR UPDATE
        """,
        (id_reserva,),
    )
    return cursor.fetchone()


def hay_otro_pago_pagado(cursor, id_reserva, id_pago=None):
    cursor.execute(
        """
        SELECT id_pago
        FROM pagos
        WHERE id_reserva = %s AND estado = %s
        """,
        (id_reserva, "Pagado"),
    )
    return any(pago["id_pago"] != id_pago for pago in cursor.fetchall())


def cambiar_reserva_por_pago(cursor, reserva, estado_pago, estado_anterior, otro_pago_pagado):
    if estado_pago == "Pagado":
        if reserva["estado"] == "Cancelada":
            vuelo = obtener_vuelo_bloqueado(cursor, reserva["id_vuelo"])
            if vuelo is None:
                return "El vuelo de la reserva ya no existe."
            if vuelo["asientos_disponibles"] < reserva["cantidad_pasajeros"]:
                return "El vuelo no tiene suficientes asientos para reactivar la reserva."
            cursor.execute(
                """
                UPDATE vuelos
                SET asientos_disponibles = asientos_disponibles - %s
                WHERE id_vuelo = %s AND asientos_disponibles >= %s
                """,
                (
                    reserva["cantidad_pasajeros"],
                    reserva["id_vuelo"],
                    reserva["cantidad_pasajeros"],
                ),
            )
            if cursor.rowcount != 1:
                return "No se pudieron reservar los asientos del vuelo."
        cursor.execute(
            "UPDATE reservas SET estado = %s WHERE id_reserva = %s",
            ("Confirmada", reserva["id_reserva"]),
        )
    elif estado_pago == "Reembolsado" and not otro_pago_pagado:
        if reserva["estado"] != "Cancelada":
            vuelo = obtener_vuelo_bloqueado(cursor, reserva["id_vuelo"])
            if vuelo is None:
                return "El vuelo de la reserva ya no existe."
            cursor.execute(
                """
                UPDATE vuelos
                SET asientos_disponibles = asientos_disponibles + %s
                WHERE id_vuelo = %s
                """,
                (reserva["cantidad_pasajeros"], reserva["id_vuelo"]),
            )
            cursor.execute(
                "UPDATE reservas SET estado = %s WHERE id_reserva = %s",
                ("Cancelada", reserva["id_reserva"]),
            )
    elif (
        estado_pago == "Pendiente"
        and estado_anterior == "Pagado"
        and not otro_pago_pagado
        and reserva["estado"] == "Confirmada"
    ):
        cursor.execute(
            "UPDATE reservas SET estado = %s WHERE id_reserva = %s",
            ("Pendiente", reserva["id_reserva"]),
        )
    return None


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


@app.route("/reservas", methods=["GET", "POST"])
def reservas():
    if request.method == "GET":
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        respuesta = cargar_datos_reservas(cursor)
        cursor.close()
        conexion.close()
        return respuesta

    datos, error = validar_datos_reserva(request.form)
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    if error:
        respuesta = cargar_datos_reservas(cursor, formulario=request.form, error=error)
        cursor.close()
        conexion.close()
        return respuesta, 400

    try:
        conexion.start_transaction()
        vuelo = obtener_vuelo_bloqueado(cursor, datos["id_vuelo"])
        if vuelo is None:
            error = "El vuelo seleccionado no existe."
        elif (
            datos["estado"] != "Cancelada"
            and vuelo["asientos_disponibles"] < datos["cantidad_pasajeros"]
        ):
            error = "El vuelo no tiene suficientes asientos disponibles."

        if error:
            conexion.rollback()
            respuesta = cargar_datos_reservas(cursor, formulario=request.form, error=error)
        else:
            if datos["estado"] != "Cancelada":
                cursor.execute(
                    """
                    UPDATE vuelos
                    SET asientos_disponibles = asientos_disponibles - %s
                    WHERE id_vuelo = %s AND asientos_disponibles >= %s
                    """,
                    (
                        datos["cantidad_pasajeros"],
                        datos["id_vuelo"],
                        datos["cantidad_pasajeros"],
                    ),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("No se pudieron descontar los asientos.")

            total = Decimal(str(vuelo["precio"])) * datos["cantidad_pasajeros"]
            cursor.execute(
                """
                INSERT INTO reservas
                    (id_pasajero, id_vuelo, fecha_reserva,
                     cantidad_pasajeros, total, estado)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    datos["id_pasajero"],
                    datos["id_vuelo"],
                    datos["fecha_reserva"],
                    datos["cantidad_pasajeros"],
                    total,
                    datos["estado"],
                ),
            )
            conexion.commit()
            respuesta = redirect(url_for("reservas"))
    except Exception:
        conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()

    if error:
        return respuesta, 400
    return respuesta


@app.route("/reservas/editar/<int:id_reserva>", methods=["GET", "POST"])
def editar_reserva(id_reserva):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    if request.method == "GET":
        cursor.execute(
            "SELECT * FROM reservas WHERE id_reserva = %s",
            (id_reserva,),
        )
        reserva_editar = cursor.fetchone()
        if reserva_editar is None:
            cursor.close()
            conexion.close()
            abort(404)

        respuesta = cargar_datos_reservas(cursor, reserva_editar=reserva_editar)
        cursor.close()
        conexion.close()
        return respuesta

    datos, error = validar_datos_reserva(request.form)
    if error:
        cursor.execute(
            "SELECT id_reserva FROM reservas WHERE id_reserva = %s",
            (id_reserva,),
        )
        if cursor.fetchone() is None:
            cursor.close()
            conexion.close()
            abort(404)
        respuesta = cargar_datos_reservas(
            cursor,
            formulario=request.form,
            reserva_editar={"id_reserva": id_reserva},
            error=error,
        )
        cursor.close()
        conexion.close()
        return respuesta, 400

    no_encontrada = False
    try:
        conexion.start_transaction()
        cursor.execute(
            """
            SELECT id_vuelo, cantidad_pasajeros, estado
            FROM reservas
            WHERE id_reserva = %s
            FOR UPDATE
            """,
            (id_reserva,),
        )
        reserva_actual = cursor.fetchone()
        if reserva_actual is None:
            conexion.rollback()
            no_encontrada = True
        else:
            id_vuelos = sorted({reserva_actual["id_vuelo"], datos["id_vuelo"]})
            vuelos_bloqueados = {}
            for id_vuelo in id_vuelos:
                vuelos_bloqueados[id_vuelo] = obtener_vuelo_bloqueado(cursor, id_vuelo)

            vuelo_nuevo = vuelos_bloqueados[datos["id_vuelo"]]
            if vuelo_nuevo is None:
                error = "El vuelo seleccionado no existe."
            else:
                cambios_asientos = {}
                if reserva_actual["estado"] != "Cancelada":
                    cambios_asientos[reserva_actual["id_vuelo"]] = (
                        reserva_actual["cantidad_pasajeros"]
                    )
                if datos["estado"] != "Cancelada":
                    id_vuelo_nuevo = datos["id_vuelo"]
                    cambios_asientos[id_vuelo_nuevo] = (
                        cambios_asientos.get(id_vuelo_nuevo, 0)
                        - datos["cantidad_pasajeros"]
                    )

                for id_vuelo, cambio in cambios_asientos.items():
                    vuelo_bloqueado = vuelos_bloqueados[id_vuelo]
                    asientos_finales = vuelo_bloqueado["asientos_disponibles"] + cambio
                    if asientos_finales < 0:
                        error = "El vuelo no tiene suficientes asientos disponibles."
                        break

            if error:
                conexion.rollback()
                respuesta = cargar_datos_reservas(
                    cursor,
                    formulario=request.form,
                    reserva_editar={"id_reserva": id_reserva},
                    error=error,
                )
            else:
                for id_vuelo, cambio in cambios_asientos.items():
                    if cambio:
                        asientos_finales = (
                            vuelos_bloqueados[id_vuelo]["asientos_disponibles"] + cambio
                        )
                        cursor.execute(
                            """
                            UPDATE vuelos
                            SET asientos_disponibles = %s
                            WHERE id_vuelo = %s AND %s >= 0
                            """,
                            (asientos_finales, id_vuelo, asientos_finales),
                        )
                        if cursor.rowcount != 1:
                            raise RuntimeError("No se pudieron actualizar los asientos.")

                total = Decimal(str(vuelo_nuevo["precio"])) * datos["cantidad_pasajeros"]
                cursor.execute(
                    """
                    UPDATE reservas
                    SET id_pasajero = %s, id_vuelo = %s, fecha_reserva = %s,
                        cantidad_pasajeros = %s, total = %s, estado = %s
                    WHERE id_reserva = %s
                    """,
                    (
                        datos["id_pasajero"],
                        datos["id_vuelo"],
                        datos["fecha_reserva"],
                        datos["cantidad_pasajeros"],
                        total,
                        datos["estado"],
                        id_reserva,
                    ),
                )
                conexion.commit()
                respuesta = redirect(url_for("reservas"))
    except Exception:
        conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()

    if no_encontrada:
        abort(404)
    if error:
        return respuesta, 400
    return respuesta


@app.route("/reservas/eliminar/<int:id_reserva>", methods=["POST"])
def eliminar_reserva(id_reserva):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        conexion.start_transaction()
        cursor.execute(
            """
            SELECT id_vuelo, cantidad_pasajeros, estado
            FROM reservas
            WHERE id_reserva = %s
            FOR UPDATE
            """,
            (id_reserva,),
        )
        reserva = cursor.fetchone()
        if reserva is not None:
            if reserva["estado"] != "Cancelada":
                vuelo = obtener_vuelo_bloqueado(cursor, reserva["id_vuelo"])
                if vuelo is not None:
                    cursor.execute(
                        """
                        UPDATE vuelos
                        SET asientos_disponibles = asientos_disponibles + %s
                        WHERE id_vuelo = %s
                        """,
                        (reserva["cantidad_pasajeros"], reserva["id_vuelo"]),
                    )
            cursor.execute(
                "DELETE FROM reservas WHERE id_reserva = %s",
                (id_reserva,),
            )
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()
    return redirect(url_for("reservas"))


@app.route("/pagos", methods=["GET", "POST"])
def pagos():
    if request.method == "GET":
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        respuesta = cargar_datos_pagos(cursor)
        cursor.close()
        conexion.close()
        return respuesta

    datos, error = validar_datos_pago(request.form)
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    if error:
        respuesta = cargar_datos_pagos(cursor, formulario=request.form, error=error)
        cursor.close()
        conexion.close()
        return respuesta, 400

    try:
        conexion.start_transaction()
        reserva = obtener_reserva_pago_bloqueada(cursor, datos["id_reserva"])
        if reserva is None:
            error = "La reserva seleccionada no existe."
        else:
            otro_pago_pagado = hay_otro_pago_pagado(cursor, datos["id_reserva"])
            if datos["estado"] == "Pagado" and otro_pago_pagado:
                error = "Esta reserva ya tiene un pago en estado Pagado."

        if not error:
            monto = Decimal(str(reserva["total"]))
            error = cambiar_reserva_por_pago(
                cursor,
                reserva,
                datos["estado"],
                None,
                otro_pago_pagado,
            )

        if error:
            conexion.rollback()
            respuesta = cargar_datos_pagos(cursor, formulario=request.form, error=error)
        else:
            cursor.execute(
                """
                INSERT INTO pagos
                    (id_reserva, monto, metodo_pago, fecha_pago, estado)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    datos["id_reserva"],
                    monto,
                    datos["metodo_pago"],
                    datos["fecha_pago"],
                    datos["estado"],
                ),
            )
            conexion.commit()
            respuesta = redirect(url_for("pagos"))
    except Exception:
        conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()

    if error:
        return respuesta, 400
    return respuesta


@app.route("/pagos/editar/<int:id_pago>", methods=["GET", "POST"])
def editar_pago(id_pago):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    if request.method == "GET":
        cursor.execute(
            "SELECT * FROM pagos WHERE id_pago = %s",
            (id_pago,),
        )
        pago_editar = cursor.fetchone()
        if pago_editar is None:
            cursor.close()
            conexion.close()
            abort(404)
        respuesta = cargar_datos_pagos(cursor, pago_editar=pago_editar)
        cursor.close()
        conexion.close()
        return respuesta

    datos, error = validar_datos_pago(request.form)
    if error:
        cursor.execute(
            "SELECT id_pago FROM pagos WHERE id_pago = %s",
            (id_pago,),
        )
        if cursor.fetchone() is None:
            cursor.close()
            conexion.close()
            abort(404)
        respuesta = cargar_datos_pagos(
            cursor,
            formulario=request.form,
            pago_editar={"id_pago": id_pago},
            error=error,
        )
        cursor.close()
        conexion.close()
        return respuesta, 400

    no_encontrado = False
    try:
        conexion.start_transaction()
        cursor.execute(
            "SELECT * FROM pagos WHERE id_pago = %s FOR UPDATE",
            (id_pago,),
        )
        pago_actual = cursor.fetchone()
        if pago_actual is None:
            conexion.rollback()
            no_encontrado = True
        else:
            ids_reserva = sorted({pago_actual["id_reserva"], datos["id_reserva"]})
            reservas_bloqueadas = {}
            for id_reserva in ids_reserva:
                reservas_bloqueadas[id_reserva] = obtener_reserva_pago_bloqueada(
                    cursor, id_reserva
                )

            reserva_nueva = reservas_bloqueadas[datos["id_reserva"]]
            reserva_anterior = reservas_bloqueadas[pago_actual["id_reserva"]]
            if reserva_nueva is None or reserva_anterior is None:
                error = "La reserva seleccionada ya no existe."

            otro_pago_pagado = False
            if not error:
                otro_pago_pagado = hay_otro_pago_pagado(
                    cursor, datos["id_reserva"], id_pago
                )
                if datos["estado"] == "Pagado" and otro_pago_pagado:
                    error = "Esta reserva ya tiene otro pago en estado Pagado."

            if not error:
                monto = Decimal(str(reserva_nueva["total"]))
                estado_anterior = (
                    pago_actual["estado"]
                    if pago_actual["id_reserva"] == datos["id_reserva"]
                    else None
                )
                error = cambiar_reserva_por_pago(
                    cursor,
                    reserva_nueva,
                    datos["estado"],
                    estado_anterior,
                    otro_pago_pagado,
                )

            if not error:
                if (
                    pago_actual["id_reserva"] != datos["id_reserva"]
                    and pago_actual["estado"] == "Pagado"
                    and not hay_otro_pago_pagado(
                        cursor, pago_actual["id_reserva"], id_pago
                    )
                    and reserva_anterior["estado"] == "Confirmada"
                ):
                    cursor.execute(
                        "UPDATE reservas SET estado = %s WHERE id_reserva = %s",
                        ("Pendiente", pago_actual["id_reserva"]),
                    )

                cursor.execute(
                    """
                    UPDATE pagos
                    SET id_reserva = %s, monto = %s, metodo_pago = %s,
                        fecha_pago = %s, estado = %s
                    WHERE id_pago = %s
                    """,
                    (
                        datos["id_reserva"],
                        monto,
                        datos["metodo_pago"],
                        datos["fecha_pago"],
                        datos["estado"],
                        id_pago,
                    ),
                )
                conexion.commit()
                respuesta = redirect(url_for("pagos"))
            else:
                conexion.rollback()
                respuesta = cargar_datos_pagos(
                    cursor,
                    formulario=request.form,
                    pago_editar={"id_pago": id_pago},
                    error=error,
                )
    except Exception:
        conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()

    if no_encontrado:
        abort(404)
    if error:
        return respuesta, 400
    return respuesta


@app.route("/pagos/eliminar/<int:id_pago>", methods=["POST"])
def eliminar_pago(id_pago):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        conexion.start_transaction()
        cursor.execute(
            "SELECT * FROM pagos WHERE id_pago = %s FOR UPDATE",
            (id_pago,),
        )
        pago = cursor.fetchone()
        if pago is not None:
            reserva = obtener_reserva_pago_bloqueada(cursor, pago["id_reserva"])
            if (
                reserva is not None
                and pago["estado"] == "Pagado"
                and not hay_otro_pago_pagado(cursor, pago["id_reserva"], id_pago)
                and reserva["estado"] == "Confirmada"
            ):
                cursor.execute(
                    "UPDATE reservas SET estado = %s WHERE id_reserva = %s",
                    ("Pendiente", pago["id_reserva"]),
                )
            cursor.execute("DELETE FROM pagos WHERE id_pago = %s", (id_pago,))
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()
    return redirect(url_for("pagos"))


if __name__ == "__main__":
    app.run(debug=True)