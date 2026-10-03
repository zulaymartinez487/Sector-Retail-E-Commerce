from utils.envios import crear_envio, EnvioEstandar


class Carrito:
    """
    MODELO (M de MVC)

    Carrito de compras guardado en la sesión del navegador (session de
    Flask). Solo guarda {producto_id: cantidad}; el nombre, la imagen y
    el precio se leen siempre de la base de datos, para que nunca se
    cobre un precio desactualizado.

    Como es un marketplace, el resumen agrupa los productos por tienda:
    cada vendedor despacha su parte con su transportadora y cobra su
    propio envío (calculado con el patrón Bridge de utils/envios.py).
    """

    CLAVE_SESION = "carrito"
    ENVIO_GRATIS_DESDE = EnvioEstandar.ENVIO_GRATIS_DESDE

    def __init__(self, session):
        self._session = session

    @property
    def _items(self):
        # La sesión de Flask se guarda como JSON: las claves deben ser texto.
        return self._session.get(self.CLAVE_SESION, {})

    def _guardar(self, items):
        self._session[self.CLAVE_SESION] = items
        self._session.modified = True

    def cantidad_de(self, producto_id):
        return self._items.get(str(producto_id), 0)

    def agregar(self, producto_id, cantidad=1):
        items = dict(self._items)
        items[str(producto_id)] = items.get(str(producto_id), 0) + cantidad
        self._guardar(items)

    def actualizar(self, producto_id, cantidad):
        items = dict(self._items)
        if cantidad > 0:
            items[str(producto_id)] = cantidad
        else:
            items.pop(str(producto_id), None)
        self._guardar(items)

    def quitar(self, producto_id):
        self.actualizar(producto_id, 0)

    def vaciar(self):
        self._guardar({})

    def cantidad_total(self):
        return sum(self._items.values())

    def resumen(self, producto_model, modalidad="estandar"):
        """
        Devuelve el carrito agrupado por tienda, con los datos actuales de
        cada producto. Los productos que ya no están disponibles se quitan.
        modalidad: "estandar" o "express" (la abstracción del Bridge).

        {
          "grupos": [{vendedor_id, nombre_tienda, transportadora, items, subtotal, envio, ...}, ...],
          "subtotal", "envio", "total", "cantidad"
        }
        """
        ids = [int(i) for i in self._items]
        productos = {p["id"]: p for p in producto_model.buscar_por_ids(ids)}

        grupos = {}
        vigentes = {}
        for producto_id, cantidad in self._items.items():
            producto = productos.get(int(producto_id))
            if producto is None:
                continue
            vigentes[producto_id] = cantidad
            precio = float(producto["precio"])
            grupo = grupos.setdefault(producto["vendedor_id"], {
                "vendedor_id": producto["vendedor_id"],
                "nombre_tienda": producto["nombre_tienda"],
                "transportadora": producto["transportadora"],
                "items": [],
            })
            grupo["items"].append({
                "producto_id": producto["id"],
                "nombre": producto["nombre"],
                "imagen": producto["imagen"],
                "categoria": producto["categoria"],
                "stock": producto["stock"],
                "precio": precio,
                "cantidad": cantidad,
                "subtotal": precio * cantidad,
            })

        if len(vigentes) != len(self._items):
            self._guardar(vigentes)

        for grupo in grupos.values():
            grupo["subtotal"] = sum(i["subtotal"] for i in grupo["items"])
            # BRIDGE: la modalidad elegida (abstracción) + la transportadora de la tienda (implementación).
            envio = crear_envio(modalidad, grupo["transportadora"])
            grupo["modalidad"] = envio.codigo
            grupo["envio"] = envio.costo(grupo["subtotal"])
            grupo["envio_descripcion"] = envio.descripcion()
            grupo["falta_envio_gratis"] = (
                max(self.ENVIO_GRATIS_DESDE - grupo["subtotal"], 0) if envio.codigo == "estandar" else 0
            )

        lista = list(grupos.values())
        subtotal = sum(g["subtotal"] for g in lista)
        envio = sum(g["envio"] for g in lista)
        return {
            "grupos": lista,
            "subtotal": subtotal,
            "envio": envio,
            "total": subtotal + envio,
            "cantidad": sum(vigentes.values()),
            "modalidad": modalidad,
        }
