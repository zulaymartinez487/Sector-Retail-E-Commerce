from config.database import Database

# Cada producto se consulta junto con su categoría y los datos de la tienda que lo vende
# (incluida su transportadora, que se usa para calcular el envío).
_SELECT_PRODUCTO = """
    SELECT p.*, c.nombre AS categoria, v.nombre_tienda, v.ciudad AS ciudad_tienda, v.transportadora
    FROM productos p
    JOIN vendedores v ON v.id = p.vendedor_id
    JOIN categorias c ON c.id = p.categoria_id
"""


class ProductoModel:
    """
    MODELO (M de MVC)

    Catálogo e inventario de productos. Cada producto pertenece a la
    tienda de un vendedor.
    """

    def __init__(self):
        # Database() siempre regresa la misma instancia gracias al Singleton
        self.db = Database()

    # ---------- Catálogo (compradores) ----------

    def listar(self, categoria_ids=None, busqueda=None, vendedor_id=None, orden="relevancia", incluir_inactivos=False):
        """categoria_ids: ids de una rama del árbol de categorías (Composite.ids_categorias())."""
        query = _SELECT_PRODUCTO + (" WHERE 1 = 1" if incluir_inactivos else " WHERE p.activo = 1")
        parametros = []
        if categoria_ids:
            query += f" AND p.categoria_id IN ({', '.join(['%s'] * len(categoria_ids))})"
            parametros += list(categoria_ids)
        if busqueda:
            query += " AND (p.nombre LIKE %s OR p.descripcion LIKE %s OR v.nombre_tienda LIKE %s)"
            parametros += [f"%{busqueda}%"] * 3
        if vendedor_id:
            query += " AND p.vendedor_id = %s"
            parametros.append(vendedor_id)
        query += {
            "precio_asc": " ORDER BY p.precio ASC",
            "precio_desc": " ORDER BY p.precio DESC",
        }.get(orden, " ORDER BY p.id")
        return self.db.ejecutar_consulta(query, tuple(parametros)) or []

    def buscar_por_id(self, producto_id, incluir_inactivos=False):
        query = _SELECT_PRODUCTO + " WHERE p.id = %s"
        if not incluir_inactivos:
            query += " AND p.activo = 1"
        resultado = self.db.ejecutar_consulta(query, (producto_id,))
        return resultado[0] if resultado else None

    def buscar_por_ids(self, ids):
        """Devuelve los productos activos en el mismo orden de la lista de ids."""
        if not ids:
            return []
        marcadores = ", ".join(["%s"] * len(ids))
        filas = self.db.ejecutar_consulta(
            _SELECT_PRODUCTO + f" WHERE p.activo = 1 AND p.id IN ({marcadores})", tuple(ids)
        ) or []
        por_id = {f["id"]: f for f in filas}
        return [por_id[i] for i in ids if i in por_id]

    def listar_relacionados(self, producto, limite=4):
        """Otros productos activos de la misma subcategoría."""
        query = _SELECT_PRODUCTO + """
            WHERE p.activo = 1 AND p.categoria_id = %s AND p.id <> %s
            ORDER BY RAND() LIMIT %s
        """
        return self.db.ejecutar_consulta(query, (producto["categoria_id"], producto["id"], limite)) or []

    # ---------- Inventario (vendedores) ----------

    def listar_por_vendedor(self, vendedor_id):
        return self.db.ejecutar_consulta(
            _SELECT_PRODUCTO + " WHERE p.vendedor_id = %s ORDER BY p.activo DESC, p.id DESC",
            (vendedor_id,),
        ) or []

    def crear(self, vendedor_id, nombre, descripcion, precio, stock, categoria_id, imagen):
        query = """
            INSERT INTO productos (vendedor_id, nombre, descripcion, precio, stock, categoria_id, imagen)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        return self.db.ejecutar_consulta(
            query, (vendedor_id, nombre, descripcion, precio, stock, categoria_id, imagen), fetch=False
        )

    def actualizar(self, producto_id, vendedor_id, nombre, descripcion, precio, stock, categoria_id, imagen):
        # El "AND vendedor_id" impide que un vendedor edite productos de otra tienda.
        query = """
            UPDATE productos
            SET nombre = %s, descripcion = %s, precio = %s, stock = %s, categoria_id = %s, imagen = %s
            WHERE id = %s AND vendedor_id = %s
        """
        return self.db.ejecutar_consulta(
            query, (nombre, descripcion, precio, stock, categoria_id, imagen, producto_id, vendedor_id), fetch=False
        )

    def cambiar_activo(self, producto_id, vendedor_id, activo):
        # No se borra: los pedidos antiguos siguen apuntando al producto.
        query = "UPDATE productos SET activo = %s WHERE id = %s AND vendedor_id = %s"
        return self.db.ejecutar_consulta(query, (1 if activo else 0, producto_id, vendedor_id), fetch=False)
