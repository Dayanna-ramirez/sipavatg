-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 07-10-2025 a las 02:38:05
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `sipavagt`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `catalogo`
--

CREATE TABLE `catalogo` (
  `id_catalogo` int(11) NOT NULL,
  `imagen` varchar(255) DEFAULT NULL,
  `descripcion` text DEFAULT NULL,
  `ultima_actualizacion` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `envio`
--

CREATE TABLE `envio` (
  `id_envio` int(11) NOT NULL,
  `direccion` varchar(150) DEFAULT NULL,
  `datos_contacto` varchar(100) DEFAULT NULL,
  `precio_envio` decimal(8,2) DEFAULT NULL,
  `fecha_estimada_entrega` date DEFAULT NULL,
  `estado_pedido` enum('pendiente','preparando','enviado','entregado','cancelado') DEFAULT NULL,
  `id_venta` int(11) DEFAULT NULL,
  `id_metodo` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `factura`
--

CREATE TABLE `factura` (
  `id_factura` int(11) NOT NULL,
  `fecha` date DEFAULT NULL,
  `total` decimal(10,2) DEFAULT NULL,
  `cantidad_productos` int(11) DEFAULT NULL,
  `detalle` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `metodo_pago`
--

CREATE TABLE `metodo_pago` (
  `id_metodo` int(11) NOT NULL,
  `tipo` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `producto`
--

CREATE TABLE `producto` (
  `id_producto` int(11) NOT NULL,
  `nombre_producto` varchar(80) DEFAULT NULL,
  `precio` decimal(10,2) DEFAULT NULL,
  `cantidad` int(11) NOT NULL,
  `imagen` varchar(255) NOT NULL,
  `fecha_elaboracion` date DEFAULT NULL,
  `id_catalogo` int(11) DEFAULT NULL,
  `id_inventario` int(11) DEFAULT NULL,
  `id_categoria` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `producto`
--

INSERT INTO `producto` (`id_producto`, `nombre_producto`, `precio`, `cantidad`, `imagen`, `fecha_elaboracion`, `id_catalogo`, `id_inventario`, `id_categoria`) VALUES
(1, 'ad', 12.00, 12, 's-l1600.webp', NULL, NULL, NULL, NULL),
(2, 'zxczx', 123.00, 4, 'collar-para-dama-collares-mayoreo-bisuteria-fina-D_NQ_NP_139425-MLM25445564656_032017-F.jpg', NULL, NULL, NULL, NULL);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `proveedor`
--

CREATE TABLE `proveedor` (
  `id_proveedor` int(11) NOT NULL,
  `nombre` varchar(100) DEFAULT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  `correo` varchar(100) DEFAULT NULL,
  `direccion` varchar(150) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `rol_usuario`
--

CREATE TABLE `rol_usuario` (
  `id_rol` int(11) NOT NULL,
  `nombre_rol` varchar(50) NOT NULL,
  `nivel_acceso` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `rol_usuario`
--

INSERT INTO `rol_usuario` (`id_rol`, `nombre_rol`, `nivel_acceso`) VALUES
(1, 'Admin', 1),
(2, 'Usuario', 2);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuario`
--

CREATE TABLE `usuario` (
  `id_usuario` int(11) NOT NULL,
  `nombre` varchar(50) NOT NULL,
  `apellido` varchar(50) NOT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  `correo_electronico` varchar(100) DEFAULT NULL,
  `cedula` int(11) DEFAULT NULL,
  `fecha_registro` date DEFAULT NULL,
  `clave` varchar(255) DEFAULT NULL,
  `id_rol` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `usuario`
--

INSERT INTO `usuario` (`id_usuario`, `nombre`, `apellido`, `telefono`, `correo_electronico`, `cedula`, `fecha_registro`, `clave`, `id_rol`) VALUES
(3, 'david', 'perezfg', '3227122202', 'usechedavid525@gmail.com', 1023901661, NULL, 'scrypt:32768:8:1$QHThX4PfuL7LIJX1$f8e29df003c8e16e9555604c44693a3d2ab8f0145452fa76821a63cc28e3b3e5db9410933f281888643fa383f1469885421069a3658930a0bc643f41a8053ea9', 1),
(4, 'helen', 'silva', '3227122202', 'helensilvabravo@gmial.com', 1023901661, NULL, 'scrypt:32768:8:1$pdJdYzMFUFmW5Zd2$90d0f975fcc3de0397d33de03888da802f532f077fa67d9ef12a3692f4c37680cf3314ee653bbd230e0d0bee6556b36dc532c250da69c46671918d2052ddee39', NULL),
(5, 'dayanna', 'ramirez', '3222352746', 'dvrg2612ramirez@gmail.com', 1021679171, NULL, 'scrypt:32768:8:1$1uT4FzfhE73RuFqZ$011407640b132bd5fe84210055dbd842caa57682c57215a1f7ef588c660e3e2fe4b18e6eedfc3e98a27183323b8d06eab2132779fea8b281e7c6329354b6eaba', 2),
(6, 'angela', 'fonseca', '1234', 'a@gmail.com', 123456, NULL, 'scrypt:32768:8:1$ERpyi21nAXtMWfoL$0296e1d3aa5014d304fcb46f19016779cbc58d58979ad9b03f5aae8851490b73037185dccb1584c1e9824a47c3ea59c6533d37017920d0929fcd70035b1c68ff', 1),
(7, 'aaaaaaa', 'sss', '211223', 'dsassx@ghg', 22226661, NULL, 'scrypt:32768:8:1$1maJQNsLrz3X5VJe$cc316826e0d6c9c5ae611f0e36c2d7f9c7375b602a7febe8c5816a7d672ead02e56ddcaee389b508a1efaaa832664ab5ce63cd74ecdc68bfbc6f27ee1c60074a', 2),
(11, 'vvvvv', 'vvvvv', '211223', 'fdsfsd@dfdsfgsd', 22226661, NULL, 'scrypt:32768:8:1$cTh5zLQ6fLZpZ551$e7435e1ff07104fcb13f060b271a0035e1430f30f6c5dd675d67df816fd92a3923cc2dded0a1bedfca66ed542518838d6e3a9a12573cfb4c36d80988e3f2634c', 2),
(13, 'bbbb', 'bbbb', 'bbbbb', 'bbbbbb@vvvvv', 223334444, NULL, 'scrypt:32768:8:1$7kki1bsWf0KrogwU$4ad959f1c6efb273b3ddc93fbfaf17e5c4f55da216ad97ad0b75ac93c47471de813025a54fcb6ac25c0364d83545830e62397b90949bc37d08d7cf54706dc4eb', NULL),
(14, 'a', 'a', '123', 'a@a', NULL, NULL, 'scrypt:32768:8:1$y6FEar36eRYLgFcY$083d1994990815147d27e8d20d2853426afcb98935ef92fd2059d3fa9dc009bc38ebf041268ff3245503c4b6cbd1d7bda6b7e0afa11db06185a68e475a9a32db', 2),
(15, 'asd', 'asd', '123', 'asd@asd', NULL, NULL, NULL, 1);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `venta`
--

CREATE TABLE `venta` (
  `id_venta` int(11) NOT NULL,
  `id_usuario` int(11) DEFAULT NULL,
  `id_producto` int(11) DEFAULT NULL,
  `cantidad` int(11) DEFAULT NULL,
  `id_factura` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `catalogo`
--
ALTER TABLE `catalogo`
  ADD PRIMARY KEY (`id_catalogo`);

--
-- Indices de la tabla `envio`
--
ALTER TABLE `envio`
  ADD PRIMARY KEY (`id_envio`),
  ADD KEY `id_venta` (`id_venta`),
  ADD KEY `id_metodo` (`id_metodo`);

--
-- Indices de la tabla `factura`
--
ALTER TABLE `factura`
  ADD PRIMARY KEY (`id_factura`);

--
-- Indices de la tabla `metodo_pago`
--
ALTER TABLE `metodo_pago`
  ADD PRIMARY KEY (`id_metodo`);

--
-- Indices de la tabla `producto`
--
ALTER TABLE `producto`
  ADD PRIMARY KEY (`id_producto`),
  ADD KEY `id_catalogo` (`id_catalogo`),
  ADD KEY `id_inventario` (`id_inventario`);

--
-- Indices de la tabla `proveedor`
--
ALTER TABLE `proveedor`
  ADD PRIMARY KEY (`id_proveedor`);

--
-- Indices de la tabla `rol_usuario`
--
ALTER TABLE `rol_usuario`
  ADD PRIMARY KEY (`id_rol`);

--
-- Indices de la tabla `usuario`
--
ALTER TABLE `usuario`
  ADD PRIMARY KEY (`id_usuario`),
  ADD UNIQUE KEY `correo_electronico` (`correo_electronico`),
  ADD KEY `id_rol` (`id_rol`);

--
-- Indices de la tabla `venta`
--
ALTER TABLE `venta`
  ADD PRIMARY KEY (`id_venta`),
  ADD KEY `id_usuario` (`id_usuario`),
  ADD KEY `id_producto` (`id_producto`),
  ADD KEY `id_factura` (`id_factura`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `catalogo`
--
ALTER TABLE `catalogo`
  MODIFY `id_catalogo` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT de la tabla `envio`
--
ALTER TABLE `envio`
  MODIFY `id_envio` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `factura`
--
ALTER TABLE `factura`
  MODIFY `id_factura` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `metodo_pago`
--
ALTER TABLE `metodo_pago`
  MODIFY `id_metodo` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `producto`
--
ALTER TABLE `producto`
  MODIFY `id_producto` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `proveedor`
--
ALTER TABLE `proveedor`
  MODIFY `id_proveedor` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `rol_usuario`
--
ALTER TABLE `rol_usuario`
  MODIFY `id_rol` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `usuario`
--
ALTER TABLE `usuario`
  MODIFY `id_usuario` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=16;

--
-- AUTO_INCREMENT de la tabla `venta`
--
ALTER TABLE `venta`
  MODIFY `id_venta` int(11) NOT NULL AUTO_INCREMENT;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `envio`
--
ALTER TABLE `envio`
  ADD CONSTRAINT `envio_ibfk_1` FOREIGN KEY (`id_venta`) REFERENCES `venta` (`id_venta`),
  ADD CONSTRAINT `envio_ibfk_2` FOREIGN KEY (`id_metodo`) REFERENCES `metodo_pago` (`id_metodo`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
