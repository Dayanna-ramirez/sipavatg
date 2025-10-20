from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import random
import os
from functools import wraps
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText    
from decimal import Decimal

app = Flask(__name__)
app.secret_key = 'clave_super_secreta'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'sipavatg@gmail.com'
app.config['MAIL_PASSWORD'] = '123456789'
app.config['MAIL_DEFAULT_SENDER'] = 'sipavatg@gmail.com'

mail = Mail(app)

# Serializer para tokens de recuperación de contraseña
s = URLSafeTimedSerializer(app.secret_key)

# ------------------- CONFIGURACIÓN DE BASE DE DATOS -------------------
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'sipavagt',
    'cursorclass': pymysql.cursors.DictCursor
}

# =============================================
# FUNCIONES AUXILIARES
# =============================================

def check_stock_bajo():
    """Verifica productos con stock bajo"""
    try:
        conn = pymysql.connect(**db_config)
        cur = conn.cursor()
        cur.execute("SELECT nombre_producto, cantidad FROM producto WHERE cantidad <= 5")
        productos_bajos = cur.fetchall()
        return productos_bajos
    except Exception as e:
        print(f"Error checking stock: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def aplicar_descuento_carrito(total_original):
    """Aplica descuento al carrito"""
    descuento = Decimal(session.get('descuento_aplicado', 0))
    return total_original * (Decimal(1) - descuento / Decimal(100))

def enviar_alerta(destinatario, asunto, mensaje):
    """Envía un correo de alerta a un destinatario específico."""
    try:
        msg = Message(asunto, recipients=[destinatario])
        msg.body = mensaje
        mail.send(msg)
        print(f"✅ Correo enviado a {destinatario}")
    except Exception as e:
        print(f"❌ Error al enviar correo: {e}")

# ------------------ DECORADORES ------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session and 'idUsuario' not in session:
            flash('❌ Debes iniciar sesión primero.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'rol' not in session or session['rol'] != 'Admin':
            flash('❌ Acceso denegado. Esta función es solo para administradores.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------ CONTEXTPROCESSOR ------------------
@app.context_processor
def contar_items_carrito():
    if 'idUsuario' in session:
        idUsuario = session['idUsuario']
        conn = pymysql.connect(**db_config)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(SUM(dc.cantidad), 0) AS total
                    FROM detalles_carrito dc
                    JOIN carrito c ON dc.idCarrito = c.idCarrito
                    WHERE c.idUsuario = %s
                """, (idUsuario,))
                resultado = cur.fetchone()
                cantidad = resultado['total'] if resultado else 0
        finally:
            conn.close()
        return dict(carrito_cantidad=cantidad)
    return dict(carrito_cantidad=0)

# =============================================
# RUTAS PRINCIPALES
# =============================================

# Ruta inicial redirige al login
@app.route('/')
def home_redirect():
    return redirect(url_for('login'))

# Dashboard principal (pantalla después de login)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session and 'idUsuario' not in session:
        flash("❌ Debes iniciar sesión para acceder al dashboard.", "warning")
        return redirect(url_for('login'))

    # Obtener alertas de stock solo para admin
    alertas_stock = []
    if session.get('rol') == 'Admin':
        alertas_stock = check_stock_bajo()

    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT u.id_usuario, u.nombre, u.apellido, u.telefono, u.correo_electronico, ur.nombre_rol
                FROM usuario u
                LEFT JOIN rol_usuario ur ON u.id_rol = ur.id_rol
            """)
            usuarios = cursor.fetchall()
    finally:
        conn.close()

    return render_template('home.html', usuarios=usuarios, alertas_stock=alertas_stock)

# Ruta de Registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Recoger datos del formulario
        cte_nombre = request.form['cte_nombre']
        cte_apellido = request.form['cte_apellido']
        cte_telefono = request.form['cte_telefono']
        cte_correo = request.form['correo_electronico']
        password = generate_password_hash(request.form['password'])

        # Conectar a la base de datos
        conn = pymysql.connect(**db_config)
        try:
            with conn.cursor() as cur:
                # Verificar si el correo ya está registrado
                cur.execute("SELECT id_usuario FROM usuario WHERE correo_electronico = %s", (cte_correo,))
                existe = cur.fetchone()

                if existe:
                    flash('❌ El correo ya está registrado. Usa otro.', 'danger')
                    return redirect(url_for('register'))

                # Insertar nuevo usuario
                cur.execute("""
                    INSERT INTO usuario (
                        nombre, apellido, telefono, correo_electronico, clave, id_rol
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (cte_nombre, cte_apellido, cte_telefono, cte_correo, password, 2))
                conn.commit()
                user_id = cur.lastrowid
        finally:
            conn.close()

        # Login automático después del registro
        session['user_id'] = user_id
        session['idUsuario'] = user_id
        session['user_name'] = cte_nombre
        session['rol'] = 'Usuario'  # Rol por defecto para nuevos registros
        flash('✅ Registro exitoso. ¡Bienvenido!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')

# Ruta de Login - VERSIÓN CORREGIDA
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        print(f"🔐 Intento de login para: {email}")  # Debug

        conn = pymysql.connect(**db_config)
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT u.id_usuario, u.nombre, u.clave, r.nombre_rol
                    FROM usuario u
                    LEFT JOIN rol_usuario r ON u.id_rol = r.id_rol
                    WHERE u.correo_electronico = %s
                """, (email,))
                user = cursor.fetchone()
                
                print(f"📊 Usuario encontrado: {user}")  # Debug
                
                if user:
                    print(f"🔑 Hash en BD: {user['clave'][:50]}...")  # Debug
                    print(f"🔐 Contraseña proporcionada: {password}")  # Debug
                    
                    # Verificar contraseña
                    if check_password_hash(user['clave'], password):
                        # Guardar los datos en la sesión
                        session['user_id'] = user['id_usuario']
                        session['idUsuario'] = user['id_usuario']
                        session['rol'] = user.get('nombre_rol', 'Usuario')
                        session['user_name'] = user.get('nombre')
                        
                        print(f"✅ Login exitoso. Rol: {session['rol']}")  # Debug
                        flash('✅ Inicio de sesión exitoso', 'success')
                        return redirect(url_for('dashboard'))
                    else:
                        print("❌ Contraseña incorrecta")  # Debug
                        flash('❌ Correo o contraseña incorrectos', 'danger')
                else:
                    print("❌ Usuario no encontrado")  # Debug
                    flash('❌ Correo o contraseña incorrectos', 'danger')
                    
        except Exception as e:
            print(f"💥 Error en login: {e}")  # Debug
            flash('❌ Error en el servidor. Intenta nuevamente.', 'danger')
        finally:
            conn.close()

        return redirect(url_for('login'))

    return render_template('login.html')

# Ruta de Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('🔒 Sesión cerrada.', 'info')
    return redirect(url_for('login'))

# =============================================
# RUTAS DE RECUPERACIÓN DE CONTRASEÑA
# =============================================

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        conn = pymysql.connect(**db_config)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id_usuario, nombre FROM usuario WHERE correo_electronico = %s", (email,))
                user = cur.fetchone()
        finally:
            conn.close()

        if user:
            token = s.dumps(email, salt='recuperar-clave')
            link = url_for('reset_password', token=token, _external=True)

            try:
                msg = Message('Recuperar contraseña - SIPAVATG', recipients=[email])
                msg.body = f"Hola {user['nombre']},\n\nPara restablecer tu contraseña haz clic en el siguiente enlace:\n{link}\n\nSi no solicitaste este cambio, ignora este mensaje."
                mail.send(msg)
                flash('✅ Se ha enviado un enlace de recuperación a tu correo.', 'success')
            except Exception as e:
                flash(f'❌ Error al enviar el correo: {e}', 'danger')
        else:
            flash('❌ El correo no está registrado en el sistema.', 'warning')

        return redirect(url_for('login'))

    return render_template('restored.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Decodifica el token (válido por 1 hora)
        email = s.loads(token, salt='recuperar-clave', max_age=3600)
    except Exception:
        flash('❌ El enlace ha expirado o no es válido.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        nueva_contrasena = request.form.get('password')
        hash_nueva = generate_password_hash(nueva_contrasena)

        conn = pymysql.connect(**db_config)
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE usuario SET clave = %s WHERE correo_electronico = %s",
                            (hash_nueva, email))
                conn.commit()
        finally:
            conn.close()

        flash('✅ Tu contraseña ha sido actualizada correctamente.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

# =============================================
# RUTAS PARA CUPONES
# =============================================

@app.route('/aplicar_cupon', methods=['POST'])
@login_required
def aplicar_cupon():
    codigo_cupon = request.form.get('codigo_cupon', '').strip().upper()
    
    if not codigo_cupon:
        flash("⚠️ Por favor ingresa un código de cupón.", "warning")
        return redirect(url_for('carrito'))
    
    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cur:
            cur.execute("SELECT descuento FROM cupones WHERE codigo = %s AND activo = TRUE", (codigo_cupon,))
            cupon = cur.fetchone()
            
            if cupon:
                session['descuento_aplicado'] = cupon['descuento']
                session['cupon_usado'] = codigo_cupon
                flash(f"🎉 ¡Cupón aplicado! Obtienes {cupon['descuento']}% de descuento", "success")
            else:
                flash("❌ Cupón no válido o expirado", "danger")
                
    except Exception as e:
        flash("❌ Error al aplicar el cupón", "danger")
        print(f"Error applying coupon: {e}")
    finally:
        conn.close()
    
    return redirect(url_for('carrito'))

@app.route('/remover_cupon')
@login_required
def remover_cupon():
    session.pop('descuento_aplicado', None)
    session.pop('cupon_usado', None)
    flash("ℹ️ Cupón removido", "info")
    return redirect(url_for('carrito'))

# =============================================
# RUTAS DE ADMINISTRACIÓN (PROTEGIDAS)
# =============================================

@app.route('/inventario')
@login_required
@admin_required
def inventario():
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM producto")
            productos = cursor.fetchall()
    finally:
        conn.close()

    return render_template('inventario.html', productos=productos)

@app.route('/agregar_producto', methods=['GET', 'POST'])
@login_required
@admin_required
def agregar_producto():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio = request.form.get('precio')
        cantidad = request.form.get('cantidad')
        imagen = request.files.get('imagen')

        filename = None
        if imagen and imagen.filename != '':
            filename = secure_filename(imagen.filename)
            os.makedirs('static/uploads', exist_ok=True)
            imagen.save(os.path.join('static/uploads', filename))

        conn = pymysql.connect(**db_config)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO producto (nombre_producto, precio, cantidad, imagen)
                    VALUES (%s, %s, %s, %s)
                """, (nombre, precio, cantidad, filename))
                conn.commit()
        finally:
            conn.close()

        flash("✅ Producto agregado correctamente", "success")
        return redirect(url_for('inventario'))
    return render_template('agregar_producto.html')

@app.route('/editar_producto/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_producto(id):
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM producto WHERE id_producto=%s", (id,))
            producto = cur.fetchone()

        if request.method == 'POST':
            nombre = request.form.get('nombre')
            precio = request.form.get('precio')
            cantidad = request.form.get('cantidad')
            imagen = request.files.get('imagen')

            if imagen and imagen.filename != '':
                filename = secure_filename(imagen.filename)
                os.makedirs('static/uploads', exist_ok=True)
                imagen.save(os.path.join('static/uploads', filename))
            else:
                filename = producto.get('imagen') if producto else None

            conn2 = pymysql.connect(**db_config)
            try:
                with conn2.cursor() as cur2:
                    cur2.execute("""
                        UPDATE producto
                        SET nombre_producto=%s, precio=%s, cantidad=%s, imagen=%s
                        WHERE id_producto=%s
                    """, (nombre, precio, cantidad, filename, id))
                    conn2.commit()
            finally:
                conn2.close()

            flash("✅ Producto actualizado correctamente", "success")
            return redirect(url_for('inventario'))

        return render_template('editar_producto.html', producto=producto)

    except Exception as e:
        flash(f"❌ Error al editar el producto: {str(e)}", "danger")
        return redirect(url_for('inventario'))
    finally:
        conn.close()

@app.route('/eliminar_producto/<int:id>')
@login_required
@admin_required
def eliminar_producto(id):
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM producto WHERE id_producto=%s', (id,))
            conn.commit()
        flash('✅ Producto eliminado correctamente', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error al eliminar el producto: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('inventario'))

@app.route('/actualizar_usuario/<int:id>', methods=['POST'])
@login_required
@admin_required
def actualizar_usuario(id):
    """Actualizar usuario (para formularios modales)"""
    nombre = request.form.get('nombre')
    apellido = request.form.get('apellido')
    telefono = request.form.get('telefono')
    correo = request.form.get('correo_electronico')
    rol = request.form.get('rol_usuario')

    if not all([nombre, apellido, correo, rol]):
        flash('❌ Todos los campos son obligatorios', 'danger')
        return redirect(url_for('dashboard'))

    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cursor:
            # Verificar si el correo ya existe en otro usuario
            cursor.execute("SELECT id_usuario FROM usuario WHERE correo_electronico = %s AND id_usuario != %s", 
                          (correo, id))
            usuario_existente = cursor.fetchone()
            
            if usuario_existente:
                flash('❌ El correo electrónico ya está en uso por otro usuario', 'danger')
                return redirect(url_for('dashboard'))

            # Actualizar usuario
            cursor.execute("""
                UPDATE usuario 
                SET nombre=%s, apellido=%s, telefono=%s, correo_electronico=%s, id_rol=%s 
                WHERE id_usuario=%s
            """, (nombre, apellido, telefono, correo, rol, id))
            conn.commit()
            
        flash('✅ Usuario actualizado correctamente', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error al actualizar usuario: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('dashboard'))

@app.route('/eliminar_usuario/<int:id>')
@login_required
@admin_required
def eliminar_usuario(id):
    """Eliminar usuario"""
    # No permitir eliminarse a sí mismo
    if id == session.get('idUsuario'):
        flash('❌ No puedes eliminar tu propio usuario', 'danger')
        return redirect(url_for('dashboard'))

    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM usuario WHERE id_usuario = %s', (id,))
            conn.commit()
        flash('✅ Usuario eliminado correctamente', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error al eliminar usuario: {e}', 'danger')
    finally:
        conn.close()
        
    return redirect(url_for('dashboard'))

@app.route('/agregar_usuario', methods=['POST'])
@login_required
@admin_required
def agregar_usuario():
    """Agregar nuevo usuario"""
    nombre = request.form.get('nombre')
    apellido = request.form.get('apellido')
    telefono = request.form.get('telefono')
    correo = request.form.get('correo_electronico')
    password = request.form.get('password')
    rol = request.form.get('rol_usuario')

    # Validar campos obligatorios
    if not all([nombre, apellido, correo, password, rol]):
        flash('❌ Todos los campos son obligatorios', 'danger')
        return redirect(url_for('dashboard'))

    # Hashear contraseña
    password_hash = generate_password_hash(password)

    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cur:
            # Verificar si el correo ya existe
            cur.execute("SELECT id_usuario FROM usuario WHERE correo_electronico = %s", (correo,))
            if cur.fetchone():
                flash('❌ El correo electrónico ya está registrado', 'danger')
                return redirect(url_for('dashboard'))

            # Insertar nuevo usuario
            cur.execute("""
                INSERT INTO usuario (nombre, apellido, telefono, correo_electronico, clave, id_rol)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nombre, apellido, telefono, correo, password_hash, rol))
            conn.commit()
            
        flash('✅ Usuario agregado correctamente', 'success')
    except Exception as e:
        print(f"Error al agregar usuario: {e}")
        flash('❌ Ocurrió un error al agregar el usuario', 'danger')
    finally:
        conn.close()

    return redirect(url_for('dashboard'))

# =============================================
# RUTAS DE CATÁLOGO Y CARRITO
# =============================================

@app.route('/catalogo')
def catalogo():
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM producto")
            productos = cur.fetchall()
    finally:
        conn.close()
    return render_template('catalogo.html', productos=productos)

@app.route('/agregarCarrito/<int:id>', methods=['POST'])
@login_required
def agregarCarrito(id):
    try:
        cantidad = int(request.form.get('cantidad', 1))
    except ValueError:
        cantidad = 1

    idUsuario = session['idUsuario']

    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT cantidad FROM producto WHERE id_producto = %s", (id,))
            stock = cur.fetchone()
            if not stock:
                flash("❌ Producto no encontrado.", "danger")
                return redirect(url_for('catalogo'))

            stock_val = stock['cantidad']

            cur.execute("SELECT idCarrito FROM carrito WHERE idUsuario = %s", (idUsuario,))
            carrito = cur.fetchone()
            if not carrito:
                cur.execute("INSERT INTO carrito (idUsuario) VALUES (%s)", (idUsuario,))
                conn.commit()
                cur.execute("SELECT LAST_INSERT_ID() AS idCarrito")
                carrito = cur.fetchone()

            idCarrito = carrito['idCarrito']

            cur.execute("""
                SELECT cantidad FROM detalles_carrito 
                WHERE idCarrito = %s AND idProducto = %s
            """, (idCarrito, id))
            existente = cur.fetchone()

            nueva_cantidad = cantidad
            if existente:
                nueva_cantidad += existente['cantidad']

            if nueva_cantidad > stock_val:
                flash("⚠️ No puedes agregar más unidades de las disponibles.", "warning")
            else:
                if existente:
                    cur.execute("""
                        UPDATE detalles_carrito
                        SET cantidad = %s
                        WHERE idCarrito = %s AND idProducto = %s
                    """, (nueva_cantidad, idCarrito, id))
                else:
                    cur.execute("""
                        INSERT INTO detalles_carrito (idCarrito, idProducto, cantidad)
                        VALUES (%s, %s, %s)
                    """, (idCarrito, id, cantidad))

                conn.commit()
                flash("✅ Producto agregado al carrito.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Ocurrió un error al agregar al carrito: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for('catalogo'))

@app.route('/carrito')
@login_required
def carrito():
    idUsuario = session['idUsuario']
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.id_producto, p.nombre_producto, p.precio, p.imagen, dc.cantidad
                FROM detalles_carrito dc
                JOIN carrito c ON dc.idCarrito = c.idCarrito
                JOIN producto p ON dc.idProducto = p.id_producto
                WHERE c.idUsuario = %s
            """, (idUsuario,))
            productos_carrito = cur.fetchall()
    finally:
        conn.close()

    total_original = sum(p['precio'] * p['cantidad'] for p in productos_carrito)
    total_con_descuento = aplicar_descuento_carrito(total_original)

    return render_template('carrito.html',
                        productos=productos_carrito,
                        total=total_con_descuento,
                        total_original=total_original,
                        Decimal=Decimal)

@app.route('/actualizar_carrito/<int:id>', methods=['POST'])
@login_required
def actualizar_carrito(id):
    accion = request.form.get("accion")
    idUsuario = session.get("idUsuario")

    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT dc.cantidad, p.cantidad AS stock, dc.idCarrito
                FROM detalles_carrito dc
                JOIN carrito c ON dc.idCarrito = c.idCarrito
                JOIN producto p ON dc.idProducto = p.id_producto
                WHERE c.idUsuario = %s AND dc.idProducto = %s
            """, (idUsuario, id))
            item = cur.fetchone()

            if not item:
                flash("❌ Producto no encontrado en el carrito.", "danger")
                return redirect(url_for('carrito'))

            cantidad = item['cantidad']
            stock = item['stock']

            if accion == 'sumar':
                cantidad += 1
            elif accion == 'restar':
                cantidad = max(1, cantidad - 1)

            if cantidad > stock:
                flash("⚠️ Stock insuficiente.", "warning")
            else:
                cur.execute("""
                    UPDATE detalles_carrito 
                    SET cantidad = %s 
                    WHERE idCarrito = %s AND idProducto = %s
                """, (cantidad, item['idCarrito'], id))
                conn.commit()
                flash("✅ Cantidad actualizada.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Ocurrió un error al actualizar el carrito: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('carrito'))

@app.route('/eliminar_del_carrito/<int:id>')
@login_required
def eliminar_del_carrito(id):
    idUsuario = session.get("idUsuario")
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE dc FROM detalles_carrito dc
                JOIN carrito c ON dc.idCarrito = c.idCarrito
                WHERE c.idUsuario = %s AND dc.idProducto = %s
            """, (idUsuario, id))
            conn.commit()
        flash("🗑️ Producto eliminado del carrito.", "info")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Ocurrió un error al eliminar del carrito: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('carrito'))

@app.route('/vaciar_carrito')
@login_required
def vaciar_carrito():
    idUsuario = session.get("idUsuario")
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE dc FROM detalles_carrito dc
                JOIN carrito c ON dc.idCarrito = c.idCarrito
                WHERE c.idUsuario = %s
            """, (idUsuario,))
            conn.commit()
        flash("🗑️ Carrito vaciado.", "warning")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Ocurrió un error al vaciar el carrito: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for('carrito'))

# =============================================
# RUTAS DE PAGO
# =============================================

@app.route('/pago', methods=['GET', 'POST'])
@login_required
def pago():
    id_usuario = session['idUsuario']
    conn = pymysql.connect(**db_config)
    
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("""
                SELECT p.id_producto, p.nombre_producto, p.precio, dc.cantidad, p.cantidad AS stock
                FROM detalles_carrito dc
                JOIN carrito c ON dc.idCarrito = c.idCarrito
                JOIN producto p ON dc.idProducto = p.id_producto
                WHERE c.idUsuario = %s
            """, (id_usuario,))
            productos = cur.fetchall()

        total_original = sum(p['precio'] * p['cantidad'] for p in productos)
        total_final = aplicar_descuento_carrito(total_original)

        if request.method == 'POST':
            metodo_pago = request.form.get('metodo_pago', 'tarjeta')
            
            # Verificar stock antes del pago
            errores = []
            for p in productos:
                if p['cantidad'] > p['stock']:
                    errores.append(f"{p['nombre_producto']} excede el stock disponible")

            if errores:
                flash("❌ Error en el pago: " + ", ".join(errores), "danger")
                return redirect(url_for('carrito'))
            
            # Simular pago exitoso
            codigo_pago = f"PAGO-{random.randint(1000, 9999)}"
            
            # Actualizar stock y limpiar carrito
            with conn.cursor() as cur:
                for producto in productos:
                    cur.execute("""
                        UPDATE producto 
                        SET cantidad = cantidad - %s 
                        WHERE id_producto = %s
                    """, (producto['cantidad'], producto['id_producto']))
                
                # Vaciar carrito
                cur.execute("""
                    DELETE dc FROM detalles_carrito dc 
                    JOIN carrito c ON dc.idCarrito = c.idCarrito 
                    WHERE c.idUsuario = %s
                """, (id_usuario,))
                
                conn.commit()
            
            # Limpiar cupón después del pago
            session.pop('descuento_aplicado', None)
            session.pop('cupon_usado', None)
            
            flash(f"✅ ¡Pago exitoso! Tu código de confirmación es: {codigo_pago}", "success")
            return redirect(url_for('catalogo'))

    except Exception as e:
        flash(f"❌ Error en el proceso de pago: {str(e)}", "danger")
        return redirect(url_for('carrito'))
    finally:
        conn.close()

    return render_template('pago.html', 
                     productos=productos, 
                     total=total_final)

@app.route('/confirmar_pago')
@login_required
def confirmar_pago():
    metodo = request.args.get('metodo')
    codigo = request.args.get('codigo') or request.args.get('codigo_transaccion')
    total = request.args.get('total')
    return render_template('confirmar_pago.html', metodo=metodo, codigo=codigo, total=total)

# =============================================
# RUTAS ADICIONALES
# =============================================

@app.route('/enviar_prueba')
def enviar_prueba():
    enviar_alerta('sipavatg@gmail.com', 'Prueba de alerta', '¡Hola Helen! Este es un correo de prueba desde Flask.')
    return '📧 Correo de prueba enviado. Revisa la consola y tu bandeja.'

if __name__ == "__main__":
    app.run(port=5000, debug=True)