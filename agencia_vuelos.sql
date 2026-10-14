USE agencia_vuelos;

RENAME TABLE clientes TO pasajeros;

ALTER TABLE pasajeros
RENAME COLUMN id_cliente TO id_pasajero;

ALTER TABLE reservas
RENAME COLUMN id_cliente TO id_pasajero;