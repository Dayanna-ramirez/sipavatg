from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.utils import secure_filename 
import random
import os
from functools import wraps  # Para el decorador login_required

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

    conn = pymysql.connect(**db_config)
    with conn:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT u.id_usuario, u.nombre, u.apellido, u.telefono, u.correo_electronico, ur.nombre_rol
                FROM usuario u
                LEFT JOIN rol_usuario ur ON u.id_rol = ur.id_rol
            """)
            usuarios = cursor.fetchall()

    return render_template('home.html', usuarios=usuarios)
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

    return render_template('register.html')# Ruta de Login

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

# Ruta para Olvidar Contraseña
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        flash(f'Se ha enviado un correo a {email} para recuperar la contraseña (simulado).', 'info')
        return redirect(url_for('login'))

    return render_template('restored.html')

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

    total = sum(p['precio'] * p['cantidad'] for p in productos_carrito)
    return render_template('carrito.html', productos=productos_carrito, total=total)


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

@app.route('/pago', methods=['GET', 'POST'])
def pago():
    if 'idUsuario' not in session:
        flash("Debes iniciar sesión para ver tu carrito.", "warning")
        return redirect(url_for('login'))

    idUsuario = session['idUsuario']

    conn = pymysql.connect(**db_config)
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("""
            SELECT p.id_producto, p.nombre_producto, p.precio, dc.cantidad, p.cantidad AS stock
            FROM detalles_carrito dc
            JOIN carrito c ON dc.idCarrito = c.idCarrito
            JOIN producto p ON dc.idProducto = p.id_producto
            WHERE c.idUsuario = %s
        """, (idUsuario,))
        productos = cur.fetchall()

    total = sum(p['precio'] * p['cantidad'] for p in productos)

    if request.method == 'POST':
        metodo = request.form.get('metodo_pago')
        errores = []
        for p in productos:
            if p['cantidad'] > p['stock']:
                errores.append(f"{p['nombre_producto']} excede el stock disponible")

        if errores:
            flash("Error en el pago: " + ", ".join(errores), "danger")
            return redirect(url_for('carrito'))

        codigo_transaccion = f"TXN{random.randint(100000, 999999)}"

        # --- Descontar del inventario ---
        with conn.cursor() as cur:
            for p in productos:
                nueva_cantidad = p['stock'] - p['cantidad']
                cur.execute("""
                    UPDATE producto
                    SET cantidad = %s
                    WHERE id_producto = %s
                """, (nueva_cantidad, p['id_producto']))

            # --- Vaciar el carrito ---
            cur.execute("""
                DELETE dc FROM detalles_carrito dc 
                JOIN carrito c ON dc.idCarrito = c.idCarrito
                WHERE c.idUsuario = %s
            """, (idUsuario,))

            conn.commit()  # ✅ AQUÍ GUARDAS TODO

        conn.close()

        flash(f"Pago realizado con {metodo}. Código de transacción: {codigo_transaccion}", "success")
        return redirect(url_for('confirmar_pago', metodo=metodo, codigo_transaccion=codigo_transaccion, total=total))


    return render_template('pago.html', productos=productos, total=total)

@app.route('/confirmar_pago')
def confirmar_pago():
    metodo = request.args.get('metodo')
    codigo_transaccion = request.args.get('codigo_transaccion')  # ← así debe ser
    total = request.args.get('total')

    return render_template('confirmar_pago.html',
                           metodo=metodo,
                           codigo_transaccion=codigo_transaccion,
                           total=total)

                    

if __name__ == "__main__":
    app.run(port=5000, debug=True)
