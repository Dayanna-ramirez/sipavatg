from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.utils import secure_filename 
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
        idUsuario = session ['idUsuario']
        conn = pymysql.connect.cursor()
        conn.execute("""
                    SELECT SUM(dc.cantidad)
                    FROM detalle_carrito dc
                    JOIN carrito c ON dc.idCarrito = c.idCarrito
                    WHERE c.idUsuario = %s
                    """, (idUsuario,))
        cantidad = conn.fetchall()[0]
        conn.close()
        return dict(carrito_cantidad=cantidad if cantidad else 0)
    return dict(carrito_cantidad=0)

# Ruta inicial redirige al login
@app.route('/')
def home_redirect():
    return redirect(url_for('login'))

# Dashboard principal (pantalla después de login)
@app.route ('/dashboard')
def dashboard():
   # if 'usuario' not in session:
    #    flash("debes iniciar sesion para acceder al dashboard.")
     #   return redirect(url_for('login'))

    conn = pymysql.connect(**db_config)
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT u.id_usuario, u.nombre, u.apellido, u.telefono, u.correo_electronico, ur.nombre_rol
            FROM usuario u
            LEFT JOIN rol_usuario ur ON u.id_rol = ur.id_rol
            """)
            usuario = cursor.fetchall()

    cursor.close()
    return render_template('home.html' , usuarios=usuario)
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

        # Guardar en base de datos
        conn = pymysql.connect(**db_config)
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                            INSERT INTO usuario (
                        nombre, apellido, telefono, correo_electronico, clave, id_rol
                    ) VALUES (%s, %s, %s, %s, %s,%s)
                """, (cte_nombre, cte_apellido, cte_telefono, cte_correo, password,2))
                conn.commit()
                user_id = cur.lastrowid  # Obtener el ID insertado

        # Login automático después de registro
        session['user_id'] = user_id
        session['user_name'] = cte_nombre
        flash('Registro exitoso. Bienvenido!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')

# Ruta de Login

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = pymysql.connect(**db_config)
        with conn:
            with conn.cursor() as cur:
                # Consulta corregida con JOIN bien formado
                cur.execute("""
                    SELECT u.id_usuario, u.nombre, u.clave, r.nombre_rol
                    FROM usuario u
                    JOIN rol_usuario r ON u.id_rol = r.id_rol
                    WHERE u.correo_electronico = %s
                """, (email,))
                user = cur.fetchone()

                if user and check_password_hash(user['clave'], password):
                    # Guardar datos en la sesión
                    session['idUsario']= user[0]
                    session['user_id'] = user['id_usuario']
                    session['rol'] = user['nombre_rol']
                    session['user_name'] = user['nombre']
                    flash(f'Bienvenido {user["nombre"]}', 'success')

                    # Redirigir según el rol
                    if user['nombre_rol'] == 'Admin':
                        return redirect(url_for('dashboard'))
                    elif user['nombre_rol'] == 'Usuario':
                        return redirect(url_for('dashboard'))#cambiar a la rutaque debe ver el usuario
                    else:
                        flash("Rol no reconocido", "danger")
                        return redirect(url_for('login'))
                else:
                    flash('Correo o contraseña incorrectos.', 'danger')
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

@app.route ('/catalogo')
def catalogo():
    conn = pymysql.connect(**db_config.cursors.DictCursor)
    conn.execute("SELECT * productos")
    productos = conn.fetchall()
    conn.close()
    return render_template('catalogo.html', productos=productos)

@app.route('/agregarCarrito/<int:id>', methods=['POST'])
def agregarCarrito(id):
    if 'usuario' not in session:
        flash("Debes iniciar sesion para comprar.")
        return redirect(url_for('login'))
    
    cantidad = int (request.form['cantidad'])
    idUsuario = session.get('idUsuario')

    conn = pymysql.connect.cursor()
    conn.execute("SELECT cantidad FROM productos WHERE idProducto =%s", (id,))
    stock = conn.fetchall()[0]
    conn.execute("SELECT idCarrito FROM carrito WHERE idUsuario =%s", (idUsuario,))
    carrito = conn.fetchall()

    if not carrito:
        conn.execute("INSERT INTO carrito(idUsuario) VALUES (%s)", (idUsuario,))
        pymysql.connect.commit()
        conn.execute("SELECT LAST_INSERT_ID()")
        carrito = conn.fetchall()

    idCarrito = carrito[0]

    conn.execute("""SELECT cantidad FROM detalle_carrito
                     WHERE idCarrito = %s AND idProducto =%s
                     """,(idCarrito,id))
    existente = conn.fetchall()
    cantidad_total = cantidad

    if existente:
        cantidad_total += existente[0]

    if cantidad_total > stock:
        flash("No puedes agregar mas unidades de las disponibles en el inventario", "warning")
        conn.close()
        return redirect(url_for("catalogo"))
        

    if existente:
            nueva_cantidad = existente[0] + cantidad
            conn.execute("""
                         UPDATE detalle_carrito
                         SET cantidad = %s
                         WHERE idCarrito = %s AND idProducto = %s
                         """,(nueva_cantidad, idCarrito,id))
    else: 
            conn.execute("""
               INSERT INTO detalle_carrito(idCarrito, idProducto,cantidad)
               VALUES (%s,%s,%s)
               """,(idCarrito,id,cantidad))

    pymysql.connect.commit()
    conn.close()

    flash("Producto agregado al carrito")
    return redirect(url_for('catalogo'))

@app.route('/carrito')
def carrito():
    if 'usuario' not in session:
        flash("Debes iniciar sesion para comprar.")
        return redirect(url_for('login'))
    
    idUsuario = session.get('idUsuario')

    conn = pymysql.connect.cursor(**db_config.cursors.DictCursor)
    conn.execute("""
            SELECT  p.idProducto, p.nombre_producto, p.precio, p.imagen, dc.cantidad, p.cantidad AS stock
            FROM detalle_carrito dc
            JOIN carrito c ON dc.idCarrito = c.idCarrito
            JOIN productos p ON de.idProducto = p.idProducto
            WHERE c.idProducto = %s
    """, (idUsuario,))
    productos_carrito = conn.fetchall()
    conn.close()

    total = sum(item['precio'] * item ['cantidad'] for item in productos_carrito)

    return render_template('carrito.html', productos=productos_carrito, total = total)

@app.route('/actualizar_carrito/<int:id>', methods=["POST"])
def actualizar_carrito(id):
    accion = request.form.get("accion")
    cantidad_actual = int(request.form.get("cantidad_actual",1))
    idUsuario = session.get("idUsuario")

    if accion == "sumar":
        nueva_cantidad = cantidad_actual +1
    elif accion == "restar":
        nueva_cantidad = max(1,cantidad_actual -1)
    else:
        nueva_cantidad = int(request.form.get("cantidad_manual", cantidad_actual))


    conn = pymysql.connect.cursor()

    conn.execute("SELECT cantidad  FROM productos WHERE idProducto = %s", (id,))
    stock = conn.fetchall()[0]

    if nueva_cantidad > stock:
        flash("No puedes exceder el niventario disponible", "warning")
        conn.close()
        return redirect(url_for("carrito"))
    if nueva_cantidad > 0:
        conn.execute("""
                UPDATE detalle_carrito dc
                JOIN carrito c ON dc.idCarrito= c.idCarrito
                SET dc.cantidad = %s
                WHERE c.idUsuario = %s AND dc,idProducto = %s
                     """, (nueva_cantidad, idUsuario,id))
    else:
        conn.execute("""
                DELETE dc FROM detalle_carrito dc
                JOIN carrito c ON dc.idCarrito = c.idCarrito
                WHERE c.idUsuario = %s AND dc.idProducto = %s
                     """, (idUsuario,id))
    pymysql.connect.commit()
    conn.close()

    flash("carrito actualizado", "info")
    return redirect(url_for("carrito"))

@app.route("/eliminar_del_carrito/", "info")
def eliminar_del_carrito(id):
    idUsuario = session.get("idUsuario")
    conn = pymysql.connect.cursor()
    conn.execute("""
                DELETE dc FROM detalle_carrito dc
                JOIN carrito c ON dc.idCarrito = c.idCarrito
                WHERE c.idUsuario = %s AND dc.idProducto = %s
                     """, (idUsuario,id))
    pymysql.connect.commit()
    conn.close()
    flash("Producto actualizado", "danger")
    return redirect(url_for("carrito"))

@app.route("/vaciar_carrito")
def vaciar_carrito():
    idUsuario = session.get("idUsuario")
    conn = pymysql.connect.cursor()
    conn.execute("""
                DELETE dc FROM detalle_carrito dc
                JOIN carrito c ON dc.idCarrito = c.idCarrito
                WHERE c.idUsuario = %s 
                     """, (idUsuario,))
    pymysql.connect.commit()
    conn.close()
    flash("Carrito vaciado", "warning")
    return redirect(url_for("carrito"))



if __name__ == "__main__":
    app.run(port=5000, debug=True)
