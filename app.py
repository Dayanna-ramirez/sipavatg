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




if __name__ == "__main__":
    app.run(port=5000, debug=True)
