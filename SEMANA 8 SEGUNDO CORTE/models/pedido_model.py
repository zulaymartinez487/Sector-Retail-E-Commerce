import json
from config.database import Database


class StockInsuficienteError(Exception):
    """Se lanza cuando un producto del carrito ya no tiene unidades suficientes."""

    def __init__(self, nombre_producto):
        super().__init__(nombre_producto)
        self.nombre_producto = nombre_producto


class PagoRechazadoError(Exception):
    """Se lanza cuando la pasarela no aprueba el cobro."""


ESTADOS_ENVIO = ("pendiente", "preparando", "enviado", "entregado")


class PedidoModel:
    """
    MODELO (M de MVC)

    Pedidos del marketplace. Un pedido puede tener productos de varias
    tiendas: se guarda un envío por cada vendedor, y cada vendedor
    gestiona el estado de su envío.
    """

    def __init__(self):
        # Database() siempre regresa la misma instancia gracias al Singleton
        self.db = Database()

    def crear_pedido(self, usuario_id, resumen, costo, entrega, cobrar):
        """
        Crea el pedido en UNA sola transacción:
          1. descuenta el stock (si algo se agotó -> StockInsuficienteError),
          2. cobra con la pasarela (si la rechaza -> PagoRechazadoError),
          3. guarda el pedido, su detalle y un envío por vendedor.
        Si cualquier paso falla se deshace todo: no hay cobros sin pedido
        ni stock descontado de más.

        resumen: lo que devuelve Carrito.resumen() (grupos por vendedor, envíos por tienda).
        costo:   el CostoPedido ya decorado (Decorator) con los extras elegidos.
        entrega: dict con direccion, ciudad, telefono, moneda, total_moneda y pasarela.
        cobrar:  función que recibe el total en COP y devuelve un ResultadoPago.
        """
        conexion = self.db.obtener_conexion()
        conexion.begin()
        try:
            with conexion.cursor() as cursor:
                for grupo in resumen["grupos"]:
                    for item in grupo["items"]:
                        # El "stock >= cantidad" evita vender más de lo que hay,
                        # incluso si dos personas compran al mismo tiempo.
                        cursor.execute(
                            "UPDATE productos SET stock = stock - %s WHERE id = %s AND activo = 1 AND stock >= %s",
                            (item["cantidad"], item["producto_id"], item["cantidad"]),
                        )
                        if cursor.rowcount == 0:
                            raise StockInsuficienteError(item["nombre"])

                pago = cobrar(costo.total())
                if not pago.aprobado:
                    raise PagoRechazadoError(pago.mensaje)

                cursor.execute(
                    """
                    INSERT INTO pedidos (usuario_id, subtotal, envio, total, moneda, total_moneda,
                                         pasarela, referencia_pago, direccion, ciudad, telefono, cargos)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (usuario_id, resumen["subtotal"], resumen["envio"], costo.total(),
                     entrega["moneda"], entrega["total_moneda"], entrega["pasarela"], pago.referencia,
                     entrega["direccion"], entrega["ciudad"], entrega["telefono"],
                     json.dumps(costo.desglose(), ensure_ascii=False)),
                )
                pedido_id = cursor.lastrowid

                for grupo in resumen["grupos"]:
                    cursor.execute(
                        """
                        INSERT INTO envios (pedido_id, vendedor_id, subtotal, costo_envio, modalidad, transportadora)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (pedido_id, grupo["vendedor_id"], grupo["subtotal"], grupo["envio"],
                         grupo["modalidad"], grupo["transportadora"]),
                    )
                    cursor.executemany(
                        """
                        INSERT INTO pedido_detalle (pedido_id, producto_id, cantidad, precio_unitario)
                        VALUES (%s, %s, %s, %s)
                        """,
                        [(pedido_id, i["producto_id"], i["cantidad"], i["precio"]) for i in grupo["items"]],
                    )
            conexion.commit()
            return pedido_id, pago.referencia
        except Exception:
            conexion.rollback()
            raise

    def _detalles(self, pedido_ids, vendedor_id=None):
        if not pedido_ids:
            return []
        marcadores = ", ".join(["%s"] * len(pedido_ids))
        query = f"""
            SELECT d.pedido_id, d.cantidad, d.precio_unitario,
                   d.cantidad * d.precio_unitario AS subtotal,
                   p.id AS producto_id, p.nombre, p.imagen, p.vendedor_id
            FROM pedido_detalle d
            JOIN productos p ON p.id = d.producto_id
            WHERE d.pedido_id IN ({marcadores})
        """
        parametros = list(pedido_ids)
        if vendedor_id:
            query += " AND p.vendedor_id = %s"
            parametros.append(vendedor_id)
        return self.db.ejecutar_consulta(query + " ORDER BY d.id", tuple(parametros)) or []

    def listar_por_usuario(self, usuario_id):
        """Pedidos del comprador (más recientes primero), con sus envíos y productos."""
        pedidos = self.db.ejecutar_consulta(
            "SELECT * FROM pedidos WHERE usuario_id = %s ORDER BY fecha_creacion DESC, id DESC",
            (usuario_id,),
        ) or []
        if not pedidos:
            return []

        ids = [p["id"] for p in pedidos]
        marcadores = ", ".join(["%s"] * len(ids))
        envios = self.db.ejecutar_consulta(
            f"""
            SELECT e.*, v.nombre_tienda FROM envios e JOIN vendedores v ON v.id = e.vendedor_id
            WHERE e.pedido_id IN ({marcadores}) ORDER BY e.id
            """,
            tuple(ids),
        ) or []
        detalles = self._detalles(ids)

        for envio in envios:
            envio["productos"] = [d for d in detalles
                                  if d["pedido_id"] == envio["pedido_id"] and d["vendedor_id"] == envio["vendedor_id"]]
            envio["paso"] = ESTADOS_ENVIO.index(envio["estado"])
        for pedido in pedidos:
            pedido["envios"] = [e for e in envios if e["pedido_id"] == pedido["id"]]
            # Desglose de cargos guardado por el Decorator (los pedidos antiguos no lo tienen).
            pedido["desglose"] = json.loads(pedido["cargos"]) if pedido.get("cargos") else [
                ("Productos", float(pedido["subtotal"])), ("Envíos", float(pedido["envio"]))
            ]
        return pedidos

    # ---------- Envíos (vendedores) ----------

    def listar_envios_vendedor(self, vendedor_id, estado=None):
        query = """
            SELECT e.*, p.fecha_creacion, p.direccion, p.ciudad, p.telefono,
                   u.nombre AS comprador, u.correo AS correo_comprador
            FROM envios e
            JOIN pedidos p ON p.id = e.pedido_id
            JOIN usuarios u ON u.id = p.usuario_id
            WHERE e.vendedor_id = %s
        """
        parametros = [vendedor_id]
        if estado:
            query += " AND e.estado = %s"
            parametros.append(estado)
        envios = self.db.ejecutar_consulta(query + " ORDER BY p.fecha_creacion DESC, e.id DESC", tuple(parametros)) or []
        detalles = self._detalles([e["pedido_id"] for e in envios], vendedor_id)
        for envio in envios:
            envio["productos"] = [d for d in detalles if d["pedido_id"] == envio["pedido_id"]]
            envio["paso"] = ESTADOS_ENVIO.index(envio["estado"])
        return envios

    def buscar_envio(self, envio_id, vendedor_id):
        resultado = self.db.ejecutar_consulta(
            """
            SELECT e.*, u.nombre AS comprador, u.correo AS correo_comprador, v.nombre_tienda
            FROM envios e
            JOIN pedidos p ON p.id = e.pedido_id
            JOIN usuarios u ON u.id = p.usuario_id
            JOIN vendedores v ON v.id = e.vendedor_id
            WHERE e.id = %s AND e.vendedor_id = %s
            """,
            (envio_id, vendedor_id),
        )
        return resultado[0] if resultado else None

    def actualizar_envio(self, envio_id, vendedor_id, estado, transportadora, numero_guia):
        query = """
            UPDATE envios SET estado = %s, transportadora = %s, numero_guia = %s
            WHERE id = %s AND vendedor_id = %s
        """
        return self.db.ejecutar_consulta(
            query, (estado, transportadora, numero_guia, envio_id, vendedor_id), fetch=False
        )
