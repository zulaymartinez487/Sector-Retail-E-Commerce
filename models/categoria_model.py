from abc import ABC, abstractmethod
from config.database import Database


# =====================================================================
# PATRÓN COMPOSITE (árbol)
#
# El catálogo es un árbol: las categorías contienen subcategorías, y las
# subcategorías contienen productos. Ejemplo:
#
#   Catálogo
#   ├── Tecnología
#   │   ├── Audio ──────── Audífonos inalámbricos
#   │   └── Celulares ──── Smartphone
#   └── Moda
#       └── Ropa ───────── Camiseta básica, Chaqueta de cuero
#
# Categoria (nodo compuesto) y ProductoHoja (hoja) comparten la misma
# interfaz ComponenteCatalogo. Por eso quien usa el árbol no necesita
# saber si tiene en la mano una categoría o un producto: le pregunta
# "¿cuántos productos tienes?", "¿cuántas unidades en stock?" o "¿cuánto
# vale tu inventario?", y cada categoría resuelve la pregunta sumando
# recursivamente las respuestas de sus hijos.
# =====================================================================

class ComponenteCatalogo(ABC):
    """Interfaz común de categorías y productos dentro del árbol."""

    def __init__(self, nombre):
        self.nombre = nombre
        self.padre = None

    @abstractmethod
    def contar_productos(self):
        raise NotImplementedError

    @abstractmethod
    def unidades_en_stock(self):
        raise NotImplementedError

    @abstractmethod
    def valor_inventario(self):
        """Valor del inventario en COP: precio x unidades en stock."""
        raise NotImplementedError

    @abstractmethod
    def productos(self):
        """Todos los productos (hojas) que hay debajo de este componente."""
        raise NotImplementedError

    def es_hoja(self):
        return True

    def ruta(self):
        """Lista de categorías desde la raíz hasta este componente (para las migas de pan)."""
        camino, nodo = [], self.padre
        while nodo is not None and nodo.padre is not None:   # la raíz "Catálogo" no se muestra
            camino.insert(0, nodo)
            nodo = nodo.padre
        return camino


class ProductoHoja(ComponenteCatalogo):
    """Hoja del árbol: un producto concreto."""

    def __init__(self, producto):
        super().__init__(producto["nombre"])
        self.datos = producto

    def contar_productos(self):
        return 1

    def unidades_en_stock(self):
        return int(self.datos["stock"])

    def valor_inventario(self):
        return float(self.datos["precio"]) * int(self.datos["stock"])

    def productos(self):
        return [self.datos]


class Categoria(ComponenteCatalogo):
    """Nodo compuesto: una categoría con subcategorías y/o productos."""

    def __init__(self, nombre, categoria_id=None):
        super().__init__(nombre)
        self.id = categoria_id
        self.hijos = []

    def agregar(self, componente):
        componente.padre = self
        self.hijos.append(componente)
        return componente

    def es_hoja(self):
        return False

    # Las operaciones de una categoría son la suma de las de sus hijos (recursión).
    def contar_productos(self):
        return sum(h.contar_productos() for h in self.hijos)

    def unidades_en_stock(self):
        return sum(h.unidades_en_stock() for h in self.hijos)

    def valor_inventario(self):
        return sum(h.valor_inventario() for h in self.hijos)

    def productos(self):
        return [p for h in self.hijos for p in h.productos()]

    # ---------- Navegación del árbol ----------

    def subcategorias(self):
        return [h for h in self.hijos if not h.es_hoja()]

    def buscar(self, nombre):
        """Busca una categoría por nombre en todo el subárbol."""
        if self.nombre == nombre:
            return self
        for hijo in self.subcategorias():
            encontrada = hijo.buscar(nombre)
            if encontrada:
                return encontrada
        return None

    def ids_categorias(self):
        """Id de esta categoría y de todas las que tiene debajo (para filtrar el catálogo)."""
        ids = [self.id] if self.id is not None else []
        for hijo in self.subcategorias():
            ids += hijo.ids_categorias()
        return ids

    def categorias_hoja(self):
        """Categorías sin subcategorías: son las únicas en las que se publican productos."""
        if self.id is not None and not self.subcategorias():
            return [self]
        return [h for hijo in self.subcategorias() for h in hijo.categorias_hoja()]


class CategoriaModel:
    """
    MODELO (M de MVC)

    Lee la tabla categorias y arma el árbol Composite del catálogo.
    """

    def __init__(self):
        # Database() siempre regresa la misma instancia gracias al Singleton
        self.db = Database()

    def construir_arbol(self, productos=()):
        """
        Devuelve la raíz del árbol con todas las categorías. Si se pasan
        productos, cada uno se cuelga como hoja de su categoría.
        """
        filas = self.db.ejecutar_consulta("SELECT * FROM categorias ORDER BY padre_id IS NOT NULL, nombre") or []
        raiz = Categoria("Catálogo")
        nodos = {f["id"]: Categoria(f["nombre"], f["id"]) for f in filas}
        for f in filas:
            padre = nodos.get(f["padre_id"], raiz)
            padre.agregar(nodos[f["id"]])
        for producto in productos:
            if producto["categoria_id"] in nodos:
                nodos[producto["categoria_id"]].agregar(ProductoHoja(producto))
        return raiz

    def es_hoja(self, categoria_id):
        """True si la categoría existe y no tiene subcategorías."""
        resultado = self.db.ejecutar_consulta(
            """
            SELECT c.id FROM categorias c
            WHERE c.id = %s AND NOT EXISTS (SELECT 1 FROM categorias h WHERE h.padre_id = c.id)
            """,
            (categoria_id,),
        )
        return bool(resultado)
