from config.database import Database


class VendedorModel:
    """
    MODELO (M de MVC)

    Tiendas del marketplace: registro, datos públicos y estadísticas del
    panel del vendedor.
    """

    def __init__(self):
        # Database() siempre regresa la misma instancia gracias al Singleton
        self.db = Database()

    def crear(self, usuario_id, nombre_tienda, descripcion, ciudad, transportadora):
        query = """
            INSERT INTO vendedores (usuario_id, nombre_tienda, descripcion, ciudad, transportadora)
            VALUES (%s, %s, %s, %s, %s)
        """
        return self.db.ejecutar_consulta(
            query, (usuario_id, nombre_tienda, descripcion, ciudad, transportadora), fetch=False
        )

    def cambiar_transportadora(self, vendedor_id, transportadora):
        query = "UPDATE vendedores SET transportadora = %s WHERE id = %s"
        return self.db.ejecutar_consulta(query, (transportadora, vendedor_id), fetch=False)

    def buscar_por_id(self, vendedor_id):
        resultado = self.db.ejecutar_consulta("SELECT * FROM vendedores WHERE id = %s", (vendedor_id,))
        return resultado[0] if resultado else None

    def buscar_por_usuario(self, usuario_id):
        resultado = self.db.ejecutar_consulta("SELECT * FROM vendedores WHERE usuario_id = %s", (usuario_id,))
        return resultado[0] if resultado else None

    def nombre_en_uso(self, nombre_tienda):
        return bool(self.db.ejecutar_consulta(
            "SELECT id FROM vendedores WHERE nombre_tienda = %s", (nombre_tienda,)
        ))

    def estadisticas(self, vendedor_id):
        """Números del panel del vendedor."""
        ventas = self.db.ejecutar_consulta(
            """
            SELECT COALESCE(SUM(subtotal), 0) AS total_vendido,
                   COUNT(*) AS pedidos,
                   COALESCE(SUM(estado IN ('pendiente', 'preparando')), 0) AS por_despachar
            FROM envios WHERE vendedor_id = %s
            """,
            (vendedor_id,),
        )[0]
        productos = self.db.ejecutar_consulta(
            """
            SELECT COALESCE(SUM(activo = 1), 0) AS activos,
                   COALESCE(SUM(activo = 1 AND stock <= 5), 0) AS stock_bajo
            FROM productos WHERE vendedor_id = %s
            """,
            (vendedor_id,),
        )[0]
        return {**ventas, **productos}
