-- =========================================
-- Script de creación de base de datos: bdaverd
-- Proyecto: Marketplace multivendedor (MVC + patrones de diseño)
--
-- Se puede ejecutar varias veces: usa CREATE ... IF NOT EXISTS e
-- INSERT IGNORE con ids fijos para no duplicar los datos de ejemplo.
-- =========================================

CREATE DATABASE IF NOT EXISTS bdaverd CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE bdaverd;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    contrasena VARCHAR(255) NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para la recuperación de contraseña
CREATE TABLE IF NOT EXISTS tokens_recuperacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usado TINYINT(1) DEFAULT 0,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Un usuario se vuelve vendedor al abrir su tienda (máximo una tienda por usuario)
CREATE TABLE IF NOT EXISTS vendedores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL UNIQUE,
    nombre_tienda VARCHAR(100) NOT NULL UNIQUE,
    descripcion VARCHAR(255),
    ciudad VARCHAR(80),
    transportadora VARCHAR(40) NOT NULL DEFAULT 'Servientrega',  -- Bridge: implementación de los envíos
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Árbol de categorías (patrón Composite): padre_id NULL = categoría raíz.
-- Los productos solo se asignan a categorías hoja (las que no tienen hijas).
CREATE TABLE IF NOT EXISTS categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(60) NOT NULL UNIQUE,
    padre_id INT NULL,
    FOREIGN KEY (padre_id) REFERENCES categorias(id)
);

CREATE TABLE IF NOT EXISTS productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vendedor_id INT,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2) NOT NULL,   -- siempre en pesos colombianos (COP)
    stock INT DEFAULT 0,
    categoria_id INT NOT NULL,
    imagen VARCHAR(255),             -- ruta dentro de static/, ej: img/productos/reloj.jpg
    activo TINYINT(1) NOT NULL DEFAULT 1,  -- 0 = el vendedor lo retiró del catálogo
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendedor_id) REFERENCES vendedores(id),
    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
);

-- Pedidos (compras pagadas desde el checkout). Los montos están en COP;
-- total_moneda es lo que se cobró en la moneda elegida por el comprador.
CREATE TABLE IF NOT EXISTS pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    subtotal DECIMAL(12,2) NOT NULL DEFAULT 0,
    envio DECIMAL(12,2) NOT NULL DEFAULT 0,
    total DECIMAL(12,2) NOT NULL,
    moneda CHAR(3) NOT NULL DEFAULT 'COP',
    total_moneda DECIMAL(12,2),
    pasarela VARCHAR(30),
    referencia_pago VARCHAR(60),
    direccion VARCHAR(150),
    ciudad VARCHAR(80),
    telefono VARCHAR(20),
    cargos TEXT,                     -- Decorator: desglose del total en JSON [{concepto, valor}]
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Productos de cada pedido (con el precio que tenían al momento de comprar)
CREATE TABLE IF NOT EXISTS pedido_detalle (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id INT NOT NULL,
    producto_id INT NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- Un pedido con productos de varias tiendas genera un envío por cada vendedor
CREATE TABLE IF NOT EXISTS envios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id INT NOT NULL,
    vendedor_id INT NOT NULL,
    subtotal DECIMAL(12,2) NOT NULL,
    costo_envio DECIMAL(12,2) NOT NULL DEFAULT 0,
    modalidad ENUM('estandar', 'express') NOT NULL DEFAULT 'estandar',  -- Bridge: abstracción del envío
    estado ENUM('pendiente', 'preparando', 'enviado', 'entregado') NOT NULL DEFAULT 'pendiente',
    transportadora VARCHAR(60),
    numero_guia VARCHAR(60),
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE (pedido_id, vendedor_id),
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
    FOREIGN KEY (vendedor_id) REFERENCES vendedores(id)
);

-- ---------- Datos de demostración (contraseña de todas las cuentas: demo123) ----------

INSERT IGNORE INTO usuarios (id, nombre, correo, contrasena) VALUES
(101, 'Laura Gómez', 'tecnohub@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531'),
(102, 'Camilo Ríos', 'modaurbana@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531'),
(103, 'Sofía Herrera', 'casaverde@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531'),
(111, 'Valentina Torres', 'comprador1@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531'),
(112, 'Santiago López', 'comprador2@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531'),
(113, 'Mariana Castro', 'comprador3@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531'),
(114, 'Juan Pérez', 'comprador4@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531'),
(115, 'Daniela Ruiz', 'comprador5@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531'),
(116, 'Andrés Moreno', 'comprador6@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531'),
(117, 'Camila Vargas', 'comprador7@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531'),
(118, 'Felipe Rojas', 'comprador8@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531'),
(119, 'Isabella Díaz', 'comprador9@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531'),
(120, 'Mateo Sánchez', 'comprador10@demo.com', 'scrypt:32768:8:1$jJHKrflT8d3zyAIr$75391f91cc0f913c60ba1a9e546da60414b3179d242a898baa1c37287edc114becdd2d82e4d6d2d4fc0e0a46e4b46a3593f95eec908a4f4b1108cf82097ab531');

INSERT IGNORE INTO vendedores (id, usuario_id, nombre_tienda, descripcion, ciudad, transportadora) VALUES
(1, 101, 'TecnoHub', 'Tecnología original con garantía. Envíos a todo el país.', 'Bogotá', 'Servientrega'),
(2, 102, 'Moda Urbana', 'Ropa y accesorios con estilo urbano.', 'Medellín', 'Coordinadora'),
(3, 103, 'Casa Verde', 'Decoración, plantas y cuidado personal.', 'Cali', 'Interrapidísimo');

-- Árbol de categorías: primero las raíces y luego sus subcategorías
INSERT IGNORE INTO categorias (id, nombre, padre_id) VALUES
(1, 'Tecnología', NULL), (2, 'Moda', NULL), (3, 'Hogar', NULL), (4, 'Belleza', NULL),
(5, 'Deportes', NULL), (6, 'Juguetes', NULL), (7, 'Libros', NULL);
INSERT IGNORE INTO categorias (id, nombre, padre_id) VALUES
(11, 'Audio', 1), (12, 'Wearables', 1), (13, 'Fotografía', 1), (14, 'Computadores', 1), (15, 'Celulares', 1),
(21, 'Calzado', 2), (22, 'Ropa', 2), (23, 'Accesorios', 2),
(31, 'Decoración', 3), (32, 'Cocina', 3),
(41, 'Fragancias', 4), (42, 'Cuidado personal', 4);

-- Catálogo inicial (cada producto pertenece a una tienda)
INSERT IGNORE INTO productos (id, vendedor_id, nombre, descripcion, precio, stock, categoria_id, imagen) VALUES
(1, 1,  'Audífonos inalámbricos', 'Audífonos over-ear con cancelación de ruido, Bluetooth 5.3 y hasta 30 horas de batería.', 249900, 15, 11, 'img/productos/audifonos.jpg'),
(2, 1,  'Reloj inteligente', 'Smartwatch con monitor de ritmo cardíaco, GPS, notificaciones y resistencia al agua.', 389900, 10, 12, 'img/productos/reloj.jpg'),
(3, 1,  'Cámara instantánea', 'Imprime tus fotos al instante. Incluye flash automático y temporizador.', 459900, 6, 13, 'img/productos/camara.jpg'),
(4, 1,  'Portátil 15"', 'Pantalla Full HD de 15 pulgadas, 16 GB de RAM y 512 GB SSD. Ideal para estudiar y trabajar.', 2899900, 5, 14, 'img/productos/portatil.jpg'),
(5, 1,  'Smartphone', 'Pantalla OLED de 6.1", cámara dual de 12 MP y 128 GB de almacenamiento.', 1999900, 8, 15, 'img/productos/celular.jpg'),
(6, 2,  'Tenis deportivos', 'Tenis livianos en tejido transpirable con suela de alto rebote para correr.', 329900, 20, 21, 'img/productos/tenis.jpg'),
(7, 2,  'Gafas de sol clásicas', 'Montura negra con lentes polarizados y protección UV400.', 189900, 25, 23, 'img/productos/gafas.jpg'),
(8, 2,  'Camiseta básica', 'Camiseta 100 % algodón peinado, corte regular. Disponible en blanco.', 59900, 40, 22, 'img/productos/camiseta.jpg'),
(9, 2,  'Chaqueta de cuero', 'Chaqueta estilo motociclista en cuero sintético con cremalleras metálicas.', 349900, 7, 22, 'img/productos/chaqueta.jpg'),
(10, 2, 'Morral urbano', 'Morral resistente al agua con compartimiento acolchado para portátil de hasta 15".', 179900, 18, 23, 'img/productos/morral.jpg'),
(11, 3, 'Perfume eau de parfum', 'Fragancia floral de larga duración, presentación de 100 ml.', 529900, 12, 41, 'img/productos/perfume.jpg'),
(12, 3, 'Suculenta en matera', 'Suculenta natural en matera de cerámica color menta. Fácil de cuidar.', 39900, 30, 31, 'img/productos/planta.jpg'),
(13, 3, 'Taza de cerámica', 'Taza blanca de cerámica de 350 ml, apta para microondas y lavavajillas.', 29900, 50, 32, 'img/productos/taza.jpg'),
(14, 3, 'Lámpara de pie', 'Lámpara de pie metálica con pantalla orientable, estilo industrial.', 259900, 9, 31, 'img/productos/lampara.jpg');

-- Por si la base es de una versión anterior sin vendedores

UPDATE productos SET vendedor_id = 1 WHERE id IN (1, 2, 3, 4, 5) AND vendedor_id IS NULL;

UPDATE productos SET vendedor_id = 2 WHERE id IN (6, 7, 8, 9, 10) AND vendedor_id IS NULL;

UPDATE productos SET vendedor_id = 3 WHERE id IN (11, 12, 13, 14) AND vendedor_id IS NULL;

INSERT IGNORE INTO pedidos (id, usuario_id, subtotal, envio, total, moneda, total_moneda, pasarela, referencia_pago, direccion, ciudad, telefono, fecha_creacion) VALUES
(101, 111, 2249800, 0, 2249800, 'USD', 562.45, 'paypal', 'PPL-DEMO101', 'Calle 117 # 9-31', 'Bogotá', '3173960310', DATE_SUB(NOW(), INTERVAL 58 DAY)),
(102, 111, 389900, 0, 389900, 'COP', 389900, 'pse', 'PSE-DEMO102', 'Calle 84 # 54-19', 'Bucaramanga', '3115809806', DATE_SUB(NOW(), INTERVAL 56 DAY)),
(103, 112, 3539700, 0, 3539700, 'COP', 3539700, 'pse', 'PSE-DEMO103', 'Calle 137 # 88-69', 'Barranquilla', '3142164119', DATE_SUB(NOW(), INTERVAL 54 DAY)),
(104, 113, 3079800, 0, 3079800, 'COP', 3079800, 'tarjeta', 'TAR-DEMO104', 'Calle 141 # 54-22', 'Cali', '3120399018', DATE_SUB(NOW(), INTERVAL 52 DAY)),
(105, 113, 1999900, 0, 1999900, 'COP', 1999900, 'nequi', 'NEQ-DEMO105', 'Calle 99 # 77-64', 'Bucaramanga', '3161230843', DATE_SUB(NOW(), INTERVAL 50 DAY)),
(106, 114, 579800, 0, 579800, 'USD', 144.95, 'paypal', 'PPL-DEMO106', 'Calle 98 # 3-60', 'Cali', '3122555071', DATE_SUB(NOW(), INTERVAL 48 DAY)),
(107, 114, 389900, 0, 389900, 'COP', 389900, 'pse', 'PSE-DEMO107', 'Calle 73 # 51-51', 'Barranquilla', '3110815439', DATE_SUB(NOW(), INTERVAL 46 DAY)),
(108, 115, 519800, 0, 519800, 'COP', 519800, 'pse', 'PSE-DEMO108', 'Calle 31 # 23-20', 'Medellín', '3188384612', DATE_SUB(NOW(), INTERVAL 44 DAY)),
(109, 115, 409800, 0, 409800, 'COP', 409800, 'pse', 'PSE-DEMO109', 'Calle 141 # 80-84', 'Bogotá', '3161289682', DATE_SUB(NOW(), INTERVAL 42 DAY)),
(110, 116, 1069700, 0, 1069700, 'COP', 1069700, 'tarjeta', 'TAR-DEMO110', 'Calle 103 # 79-4', 'Bogotá', '3127910936', DATE_SUB(NOW(), INTERVAL 40 DAY)),
(111, 117, 569700, 0, 569700, 'USD', 142.43, 'paypal', 'PPL-DEMO111', 'Calle 51 # 67-3', 'Medellín', '3170901507', DATE_SUB(NOW(), INTERVAL 38 DAY)),
(112, 118, 69800, 12000, 81800, 'COP', 81800, 'tarjeta', 'TAR-DEMO112', 'Calle 76 # 67-47', 'Medellín', '3147740731', DATE_SUB(NOW(), INTERVAL 36 DAY)),
(113, 118, 259900, 0, 259900, 'COP', 259900, 'pse', 'PSE-DEMO113', 'Calle 112 # 95-30', 'Medellín', '3169476293', DATE_SUB(NOW(), INTERVAL 34 DAY)),
(114, 119, 829700, 0, 829700, 'COP', 829700, 'nequi', 'NEQ-DEMO114', 'Calle 103 # 11-29', 'Bogotá', '3130446731', DATE_SUB(NOW(), INTERVAL 32 DAY)),
(115, 120, 129700, 24000, 153700, 'COP', 153700, 'pse', 'PSE-DEMO115', 'Calle 121 # 82-43', 'Bogotá', '3196881675', DATE_SUB(NOW(), INTERVAL 30 DAY));

-- El detalle y los envíos solo se insertan si el pedido demo es nuevo (evita duplicarlos).

INSERT INTO pedido_detalle (pedido_id, producto_id, cantidad, precio_unitario)
SELECT * FROM (
  SELECT 101 AS pedido_id, 1 AS producto_id, 1 AS cantidad, 249900 AS precio_unitario
  UNION ALL SELECT 101, 5, 1, 1999900
  UNION ALL SELECT 102, 2, 1, 389900
  UNION ALL SELECT 103, 1, 1, 249900
  UNION ALL SELECT 103, 2, 1, 389900
  UNION ALL SELECT 103, 4, 1, 2899900
  UNION ALL SELECT 104, 4, 1, 2899900
  UNION ALL SELECT 104, 10, 1, 179900
  UNION ALL SELECT 105, 5, 1, 1999900
  UNION ALL SELECT 106, 1, 1, 249900
  UNION ALL SELECT 106, 6, 1, 329900
  UNION ALL SELECT 107, 2, 1, 389900
  UNION ALL SELECT 108, 6, 1, 329900
  UNION ALL SELECT 108, 7, 1, 189900
  UNION ALL SELECT 109, 8, 1, 59900
  UNION ALL SELECT 109, 9, 1, 349900
  UNION ALL SELECT 110, 7, 1, 189900
  UNION ALL SELECT 110, 9, 1, 349900
  UNION ALL SELECT 110, 11, 1, 529900
  UNION ALL SELECT 111, 8, 1, 59900
  UNION ALL SELECT 111, 6, 1, 329900
  UNION ALL SELECT 111, 10, 1, 179900
  UNION ALL SELECT 112, 12, 1, 39900
  UNION ALL SELECT 112, 13, 1, 29900
  UNION ALL SELECT 113, 14, 1, 259900
  UNION ALL SELECT 114, 12, 1, 39900
  UNION ALL SELECT 114, 14, 1, 259900
  UNION ALL SELECT 114, 11, 1, 529900
  UNION ALL SELECT 115, 13, 1, 29900
  UNION ALL SELECT 115, 12, 1, 39900
  UNION ALL SELECT 115, 8, 1, 59900
) AS d WHERE NOT EXISTS (SELECT 1 FROM pedido_detalle WHERE pedido_id BETWEEN 101 AND 199);

INSERT IGNORE INTO envios (id, pedido_id, vendedor_id, subtotal, costo_envio, estado, transportadora, numero_guia) VALUES
(101, 101, 1, 2249800, 0, 'entregado', 'Coordinadora', '1207388624'),
(102, 102, 1, 389900, 0, 'entregado', 'Servientrega', '5070378921'),
(103, 103, 1, 3539700, 0, 'enviado', 'Interrapidísimo', '3929179284'),
(104, 104, 1, 2899900, 0, 'entregado', 'Envía', '6847951704'),
(105, 104, 2, 179900, 0, 'entregado', 'Coordinadora', '2048386555'),
(106, 105, 1, 1999900, 0, 'entregado', 'Envía', '3869965264'),
(107, 106, 1, 249900, 0, 'entregado', 'Servientrega', '9352341718'),
(108, 106, 2, 329900, 0, 'entregado', 'Servientrega', '9850507787'),
(109, 107, 1, 389900, 0, 'enviado', 'Servientrega', '3120395274'),
(110, 108, 2, 519800, 0, 'entregado', 'Envía', '7658142303'),
(111, 109, 2, 409800, 0, 'entregado', 'Servientrega', '3530266207'),
(112, 110, 2, 539800, 0, 'enviado', 'Envía', '7004663331'),
(113, 110, 3, 529900, 0, 'entregado', 'Servientrega', '2719888006'),
(114, 111, 2, 569700, 0, 'enviado', 'Envía', '6859037352'),
(115, 112, 3, 69800, 12000, 'entregado', 'Coordinadora', '4926226243'),
(116, 113, 3, 259900, 0, 'entregado', 'Interrapidísimo', '3733497277'),
(117, 114, 3, 829700, 0, 'entregado', 'Interrapidísimo', '4139638261'),
(118, 115, 3, 69800, 12000, 'entregado', 'Coordinadora', '2450571437'),
(119, 115, 2, 59900, 12000, 'entregado', 'Servientrega', '8099486649');
