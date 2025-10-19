from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.utils import secure_filename 
import random
import os
from functools import wraps  # Para el decorador login_required

import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText    

#Funcion para generar token de recuperacion
def generar_token(email):
    token =secrets.token_urlsafe(32)
    expiry =datetime.now() + timedelta(hours=1)
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("UPDATE usuario SET reset_token= %s, token_expiry= %s WHERE correo_electronico = %s", (token, expiry,email))
    conn.commit()
    cursor.close()
    conn.close()
    return token 

#Funcion para enviar el correo con enlace de recuperacion 
def enviar_correo_reset(email,token):
    enlace = url_for('reset', token = token, _external=True)
    cuerpo = f"""Hola, Solicitaste recuperar tu contraseña. Haz click en el siguiente enlace:
    {enlace}
    Este enlace expirara en 1 hora.
    Si no lo solicitaste, ignora este mensaje. """

    remitente = 'secureloginnoresponder@gmail.com'
    clave = 'cjhc bwnp tuwu myls'
    mensaje = MIMEText(cuerpo)
    mensaje['Subject'] = 'Recuperar contraseña'
    mensaje['From']= 'secureloginnoresponder@gmail.com'
    mensaje ['To']= email

    server = smtplib.SMTP('smtp.gmail.com',587)
    server.starttls()
    server.login(remitente,clave)
    server.sendmail(remitente,email,mensaje.as_string())
    server.quit()

# =============================================
# FUNCIONES NUEVAS PARA ALERTAS Y CUPONES
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
    """Aplica descuento si hay cupón en sesión"""
    descuento = session.get('descuento_aplicado', 0)
    return total_original * (1 - descuento / 100)

app = Flask(__name__)
app.secret_key = 'clave_super_secreta'

# Configuración de la base de datos 
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'sipavagt',
    'cursorclass': pymysql.cursors.DictCursor
}

# ------------------ DECORADOR PARA PROTEGER RUTAS ------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------ RUTAS ------------------

@app.context_processor
def contar_items_carrito():
    if 'idUsuario' in session:
        idUsuario = session['idUsuario']
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(dc.cantidad), 0) AS total
                FROM detalles_carrito dc
                JOIN carrito c ON dc.idCarrito = c.idCarrito
                WHERE c.idUsuario = %s
            """, (idUsuario,))
            resultado = cur.fetchone()
            cantidad = resultado['total'] if resultado else 0
        conn.close()
        return dict(carrito_cantidad=cantidad)
    return dict(carrito_cantidad=0)


# Ruta inicial redirige al login
@app.route('/')
def home_redirect():
    return redirect(url_for('login'))

# Dashboard principal (pantalla después de login)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Debes iniciar sesión para acceder al dashboard.", "warning")
        return redirect(url_for('login'))

    # Obtener alertas de stock solo para admin
    alertas_stock = []
    if session.get('rol') == 'Admin':
        alertas_stock = check_stock_bajo()

    conn = pymysql.connect(**db_config)
    with conn:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT u.id_usuario, u.nombre, u.apellido, u.telefono, u.correo_electronico, ur.nombre_rol
                FROM usuario u
                LEFT JOIN rol_usuario ur ON u.id_rol = ur.id_rol
            """)
            usuarios = cursor.fetchall()

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
        with conn:
            with conn.cursor() as cur:
                # Verificar si el correo ya está registrado
                cur.execute("SELECT id_usuario FROM usuario WHERE correo_electronico = %s", (cte_correo,))
                existe = cur.fetchone()

                if existe:
                    flash('El correo ya está registrado. Usa otro.', 'danger')
                    return redirect(url_for('register'))

                # Insertar nuevo usuario
                cur.execute("""
                    INSERT INTO usuario (
                        nombre, apellido, telefono, correo_electronico, clave, id_rol
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (cte_nombre, cte_apellido, cte_telefono, cte_correo, password, 2))
                conn.commit()
                user_id = cur.lastrowid

        # Login automático después del registro
        session['user_id'] = user_id
        session['user_name'] = cte_nombre
        flash('Registro exitoso. ¡Bienvenido!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')

# Ruta de Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conexion = pymysql.connect(**db_config)
        cursor = conexion.cursor(pymysql.cursors.DictCursor)  # <- ¡Esto es importante!
        cursor.execute("""
            SELECT u.id_usuario, u.nombre, u.clave, r.nombre_rol
            FROM usuario u
            JOIN rol_usuario r ON u.id_rol = r.id_rol
            WHERE u.correo_electronico = %s
        """, (email,))
        user = cursor.fetchone()
        cursor.close()
        conexion.close()

        if user and check_password_hash(user['clave'], password):
            # Guardar los datos en la sesión con nombres consistentes
            session['user_id'] = user['id_usuario']
            session['rol'] = user['nombre_rol']
            session['user_name'] = user['nombre']

            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Correo o contraseña incorrectos', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


# Ruta de Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('login'))

# Ruta para recuperar la contraseña
@app.route('/forgot', methods =['GET','POST'])
def forgot():
    if request.method == 'POST':
        email = request.form['email']
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT id_usuario FROM usuario WHERE correo_electronico = %s", (email,))
        existe = cursor.fetchone()
        cursor.close()
        conn.close()

        if not existe:
            flash("Este correo no esta registrado.")
            return redirect(url_for('forgot'))
        
        token = generar_token(email)
        enviar_correo_reset(email,token)

        flash ("Te enviamos un correo con el enlace para restablecer tu contraseña")
        return redirect(url_for('login'))
    return render_template('restored.html')

# Ruta para completar la recuperacion de la contraseña
@app.route('/reset/<token>', methods =['GET','POST'])
def reset (token):
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id_usuario, token_expiry FROM usuario WHERE reset_token = %s", (token,))
    usuario = cursor.fetchone()
    conn.close()

    if not usuario or datetime.now() >usuario [1]:
        flash ("Token invalido o expirado.")
        return redirect(url_for('forgot'))
    
    if request.method == 'POST':
        nuevo_password = request.form ['password']
        hash_nueva = generate_password_hash(nuevo_password)

        conn = pymysql.connect.cursor()
        conn.execute("UPDATE usuario SET password =%s, reset_token=NULL, token_expiry=NULL WHERE id_usuario=%s", (hash_nueva, usuario[0]))
        pymysql.connect.commit()
        conn.close()

        flash ("Tu contraseña se ha actualizad0.")
        return redirect(url_for('login'))
    
    return render_template('reset.html')

# =============================================
# RUTAS NUEVAS PARA CUPONES
# =============================================

@app.route('/aplicar_cupon', methods=['POST'])
def aplicar_cupon():
    if 'user_id' not in session:
        flash("Debes iniciar sesión.", "warning")
        return redirect(url_for('login'))
    
    codigo_cupon = request.form.get('codigo_cupon', '').strip().upper()
    
    if not codigo_cupon:
        flash("Por favor ingresa un código de cupón.", "warning")
        return redirect(url_for('carrito'))
    
    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cur:
            cur.execute("SELECT descuento FROM cupones WHERE codigo = %s AND activo = TRUE", (codigo_cupon,))
            cupon = cur.fetchone()
            
            if cupon:
                session['descuento_aplicado'] = cupon[0]
                session['cupon_usado'] = codigo_cupon
                flash(f"🎉 ¡Cupón aplicado! Obtienes {cupon[0]}% de descuento", "success")
            else:
                flash("❌ Cupón no válido o expirado", "danger")
                
    except Exception as e:
        flash("Error al aplicar el cupón", "danger")
        print(f"Error applying coupon: {e}")
    finally:
        conn.close()
    
    return redirect(url_for('carrito'))

@app.route('/remover_cupon')
def remover_cupon():
    session.pop('descuento_aplicado', None)
    session.pop('cupon_usado', None)
    flash("Cupón removido", "info")
    return redirect(url_for('carrito'))

# ----------------- CRUD RUTAS (Protegidas) ------------------

@app.route("/add_clientes", methods=['POST'])
@login_required
def add_contact():
    if request.method == 'POST':
        id_cte = request.form['id_cte']
        nombre = request.form['cte_nombre']
        apellido = request.form['cte_apellido']
        correo = request.form['cte_correo']
        cedula = request.form['cte_cedula']

        conn = pymysql.connect(**db_config)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO clientes(id_cte, cte_nombre, cte_apellido, correo_electronico, cte_cedula) VALUES (%s, %s, %s, %s, %s)',
                    (id_cte, nombre, apellido, correo, cedula)
                )
                conn.commit()
                cur.execute("SELECT id_usuario FROM usuario WHERE username =%", (correo,))
                nuevo_usuario = cur.fetchone()

                cur.execute("INSERT INTO rol_usuario(id_usuario, idRol) VALUES (%, %)", (nuevo_usuario[0], 2))
            conn = pymysql.connect(**db_config)
            with conn:
                  with conn.cursor() as cur:
                   cur.execute('DELETE FROM clientes WHERE id_cte = %s', (id,))
                   conn.commit()
        flash(f"Cliente {nombre} {apellido} agregado.", 'success')
        return redirect(url_for('dashboard'))

@app.route('/edit/<string:id>')
@login_required
def get_contact(id):
    conn = pymysql.connect(**db_config)
    with conn:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM clientes WHERE id_cte = %s', (id,))
            dato = cur.fetchone()
    return render_template('Editacli.html', clients=dato)

#editar usuario
@app.route('/actualizar/<int:id>', methods=['POST'])
def actualizar(id):
    nombre =request.form['nombre']
    apellido =request.form['apellido']
    correo =request.form['correo_electronico']
    rol = request.form['rol_usuario']

    conn = pymysql.connect(**db_config)
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("""UPDATE usuario SET nombre=%s,apellido=%s, correo_electronico=%s, id_rol=%s WHERE id_usuario=%s""",(nombre,apellido,correo,rol,id))
            cursor.execute("SELECT id_rol FROM rol_usuario WHERE nombre_rol=%s",(rol,))
            existe= cursor.fetchone()

            conn.commit()
    cursor.close()
    return redirect(url_for('dashboard'))
    
        
@app.route('/inventario')
def inventario():
    #if 'rol' not in session or session['rol'] != 'Admin':
     #   flash ("Acceso restringido solo para los administradores")
      #  return redirect(url_for('login'))
    
    
    conn = pymysql.connect(**db_config)
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM producto")
            productos = cursor.fetchall()

    return render_template('inventario.html', productos=productos)

# Ruta para agregar productos (solo Admin)
@app.route('/agregar_producto', methods=['GET', 'POST'])
def agregar_producto():
    #if 'rol' not in session or session['rol'] != 'Admin':
     #   flash ("Acceso restringido solo para los administradores")
    #    return redirect(url_for('login'))
    if request.method =='POST':
        nombre =request.form['nombre']
        precio =request.form['precio']
        cantidad =request.form['cantidad']
        imagen =request.files['imagen']
        
        
        filename = secure_filename(imagen.filename)
        imagen.save(os.path.join('static/uploads', filename ))
        
        conn = pymysql.connect(**db_config)
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
             INSERT INTO producto (nombre_producto,precio,cantidad,imagen)
             VALUES (%s,%s,%s,%s)
         """,(nombre,precio,cantidad,filename))  
            conn.commit()        
        flash("Producto agregar correctamente")  
        return redirect(url_for('catalogo'))
    return render_template('agregar_producto.html')

@app.route('/editar_producto/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            # Obtener producto existente
            cur.execute("SELECT * FROM producto WHERE id_producto=%s", (id,))
            producto = cur.fetchone()

        if request.method == 'POST':
            nombre = request.form['nombre']
            precio = request.form['precio']
            cantidad = request.form['cantidad']
            imagen = request.files.get('imagen')

            # Si se sube nueva imagen
            if imagen and imagen.filename != '':
                filename = secure_filename(imagen.filename)
                imagen.save(os.path.join('static/uploads', filename))
            else:
                filename = producto['imagen']  # conserva la imagen actual

            # Actualizar producto
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE producto
                    SET nombre_producto=%s, precio=%s, cantidad=%s, imagen=%s
                    WHERE id_producto=%s
                """, (nombre, precio, cantidad, filename, id))
                conn.commit()

            flash("Producto actualizado correctamente")
            return redirect(url_for('inventario'))

        return render_template('editar_producto.html', producto=producto)

    except Exception as e:
        conn.rollback()
        flash(f"Error al editar el producto: {str(e)}")
        return redirect(url_for('inventario'))
    finally:
        conn.close()
    return render_template('editar_producto.html', producto=producto)

@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM producto WHERE id_producto=%s', (id,))
            conn.commit()
        flash('Producto eliminado correctamente')
    except Exception as e:
        conn.rollback()
        flash(f'Error al eliminar el producto: {str(e)}')
    finally:
        conn.close()
    return redirect(url_for('inventario'))
                

        

@app.route('/eliminar/<int:id>')
def eliminar(id):
    conn = pymysql.connect(**db_config)
    with conn:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM usuario WHERE id_usuario=%s',(id,))
        conn.commit()
        cursor.close()
        flash ('Usuario eliminado')
    return redirect(url_for('dashboard'))

@app.route('/agregar_usuario', methods=['POST'])
def agregar_usuario():
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    telefono = request.form['telefono']
    correo = request.form['correo_electronico']
    rol = request.form['rol_usuario']

    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usuario (nombre, apellido, telefono, correo_electronico, id_rol)
                VALUES (%s, %s, %s, %s, %s)
            """, (nombre, apellido, telefono, correo, rol))
        conn.commit()
        flash('Usuario agregado correctamente', 'success')
    except Exception as e:
        print(f"Error al agregar usuario: {e}")
        flash('Ocurrió un error al agregar el usuario', 'danger')

    return redirect(url_for('dashboard'))

@app.route('/catalogo')
def catalogo():
    conn = pymysql.connect(**db_config)
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("SELECT * FROM producto")
        productos = cur.fetchall()
    conn.close()
    return render_template('catalogo.html', productos=productos)


@app.route('/agregarCarrito/<int:id>', methods=['POST'])
def agregarCarrito(id):
    if 'idUsuario' not in session:
        flash("Debes iniciar sesión para comprar.", "warning")
        return redirect(url_for('login'))

    cantidad = int(request.form['cantidad'])
    idUsuario = session['idUsuario']

    conn = pymysql.connect(**db_config)
    with conn.cursor() as cur:
        # Obtener stock
        cur.execute("SELECT cantidad FROM producto WHERE id_producto = %s", (id,))
        stock = cur.fetchone()
        if not stock:
            flash("Producto no encontrado.", "danger")
            return redirect(url_for('catalogo'))

        stock = stock['cantidad']

        # Obtener carrito
        cur.execute("SELECT idCarrito FROM carrito WHERE idUsuario = %s", (idUsuario,))
        carrito = cur.fetchone()
        if not carrito:
            cur.execute("INSERT INTO carrito (idUsuario) VALUES (%s)", (idUsuario,))
            conn.commit()
            cur.execute("SELECT LAST_INSERT_ID() AS idCarrito")
            carrito = cur.fetchone()

        idCarrito = carrito['idCarrito']

        # Verificar si ya existe en el carrito
        cur.execute("""
            SELECT cantidad FROM detalles_carrito 
            WHERE idCarrito = %s AND idProducto = %s
        """, (idCarrito, id))
        existente = cur.fetchone()

        nueva_cantidad = cantidad
        if existente:
            nueva_cantidad += existente['cantidad']

        if nueva_cantidad > stock:
            flash("No puedes agregar más unidades de las disponibles.", "warning")
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
            flash("Producto agregado al carrito.", "success")

    conn.close()
    return redirect(url_for('catalogo'))


@app.route('/carrito')
def carrito():
    if 'idUsuario' not in session:
        flash("Debes iniciar sesión para ver tu carrito.", "warning")
        return redirect(url_for('login'))

    idUsuario = session['idUsuario']
    conn = pymysql.connect(**db_config)
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("""
            SELECT p.id_producto, p.nombre_producto, p.precio, p.imagen, dc.cantidad
            FROM detalles_carrito dc
            JOIN carrito c ON dc.idCarrito = c.idCarrito
            JOIN producto p ON dc.idProducto = p.id_producto
            WHERE c.idUsuario = %s
        """, (idUsuario,))
        productos_carrito = cur.fetchall()
    conn.close()

    total_original = sum(p['precio'] * p['cantidad'] for p in productos_carrito)
    total_con_descuento = aplicar_descuento_carrito(total_original)
    
    return render_template('carrito.html', 
                         productos=productos_carrito, 
                         total=total_con_descuento,
                         total_original=total_original)


@app.route('/actualizar_carrito/<int:id>', methods=['POST'])
def actualizar_carrito(id):
    accion = request.form.get("accion")
    idUsuario = session.get("idUsuario")

    conn = pymysql.connect(**db_config)
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
            flash("Producto no encontrado en el carrito.", "danger")
            return redirect(url_for('carrito'))

        cantidad = item['cantidad']
        stock = item['stock']

        if accion == 'sumar':
            cantidad += 1
        elif accion == 'restar':
            cantidad = max(1, cantidad - 1)

        if cantidad > stock:
            flash("Stock insuficiente.", "warning")
        else:
            cur.execute("""
                UPDATE detalles_carrito 
                SET cantidad = %s 
                WHERE idCarrito = %s AND idProducto = %s
            """, (cantidad, item['idCarrito'], id))
            conn.commit()
            flash("Cantidad actualizada.", "success")

    conn.close()
    return redirect(url_for('carrito'))


@app.route('/eliminar_del_carrito/<int:id>')
def eliminar_del_carrito(id):
    idUsuario = session.get("idUsuario")
    conn = pymysql.connect(**db_config)
    with conn.cursor() as cur:
        cur.execute("""
            DELETE dc FROM detalles_carrito dc
            JOIN carrito c ON dc.idCarrito = c.idCarrito
            WHERE c.idUsuario = %s AND dc.idProducto = %s
        """, (idUsuario, id))
        conn.commit()
    conn.close()
    flash("Producto eliminado del carrito.", "danger")
    return redirect(url_for('carrito'))


@app.route('/vaciar_carrito')
def vaciar_carrito():
    idUsuario = session.get("idUsuario")
    conn = pymysql.connect(**db_config)
    with conn.cursor() as cur:
        cur.execute("""
            DELETE dc FROM detalles_carrito dc
            JOIN carrito c ON dc.idCarrito = c.idCarrito
            WHERE c.idUsuario = %s
        """, (idUsuario,))
        conn.commit()
    conn.close()
    flash("Carrito vaciado.", "warning")
    return redirect(url_for('carrito'))

# Ruta de pago MODIFICADA
@app.route('/pago', methods=['GET', 'POST'])
def pago():
    if 'idUsuario' not in session:
        flash("Debes iniciar sesión para pagar.", "warning")
        return redirect(url_for('login'))

    # Obtener productos del carrito
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

        # Calcular total con descuento
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
                flash("Error en el pago: " + ", ".join(errores), "danger")
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
            
            flash(f" ¡Pago exitoso! Tu código de confirmación es: {codigo_pago}", "success")
            return redirect(url_for('catalogo'))

    except Exception as e:
        flash(f"Error en el proceso de pago: {str(e)}", "danger")
        return redirect(url_for('carrito'))
    finally:
        conn.close()

    return render_template('pago.html', 
                     productos=productos, 
                     total=total_final)
@app.route('/confirmar_pago')
def confirmar_pago():
    metodo = request.args.get('metodo')
    codigo_transaccion = request.args.get('codigo_transaccion')
    total = request.args.get('total')

    return render_template('confirmar_pago.html',
                           metodo=metodo,
                           codigo_transaccion=codigo_transaccion,
                           total=total)

if __name__ == "__main__":
    app.run(port=5000, debug=True)