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
@app.route('/dashboard')
#@login_required
def dashboard():
    conn = pymysql.connect(**db_config)
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nombre, apellido FROM usuario")
            usuarios = cur.fetchall()
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
        cte_cedula = request.form['cte_cedula']
        password = generate_password_hash(request.form['password'])

        # Guardar en base de datos
        conn = pymysql.connect(**db_config)
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO usuario (
                        nombre, apellido, telefono, correo_electronico,
                        cedula, clave
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (cte_nombre, cte_apellido, cte_telefono, cte_correo,
                      cte_cedula, password))
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
                cur.execute('SELECT * FROM usuario WHERE correo_electronico = %s', (email,))
                user = cur.fetchone()

        if user and check_password_hash(user['clave'], password):
            session['user_id'] = user['id_usuario']
            session['correo_electronico'] = user['correo_electronico']
            session['rol'] = user ['id_rol']
            
            
            flash(f'Bienvenido {user["correo_electronico"]}', 'success')
            return redirect(url_for('dashboard'))
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

@app.route('/actualiza/<string:id>', methods=['POST'])
@login_required
def set_contact(id):
    if request.method == 'POST':
        nombre = request.form['cte_nombre']
        apellido = request.form['cte_apellido']
        correo = request.form['cte_correo']
        cedula = request.form['cte_cedula']

        conn = pymysql.connect(**db_config)
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE clientes
                    SET cte_nombre = %s,
                        cte_apellido = %s,
                        cte_correo = %s,
                        cte_cedula = %s
                    WHERE id_cte = %s
                """, (nombre, apellido, correo, cedula, id))
                conn.commit()

        flash('Cliente actualizado correctamente.', 'success')
        return redirect(url_for('dashboard'))
    
@app.route('/catalogo')
def catalogo():
    #if 'rol' not in session or session['rol'] != 'Admin':
     #   flash ("Acceso restringido solo para los administradores")
      #  return redirect(url_for('login'))
    
    
    conn = pymysql.connect(**db_config)
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM catalogo")
            productos = cursor.fetchall()

    return render_template('catalogo.html', productos=productos)

@app.route('/agregar_producto', methods=['GET', 'POST'])
def agregar_producto():
    if 'rol' not in session or session['rol'] != 'Admin':
        flash ("Acceso restringido solo para los administradores")
        return redirect(url_for('login'))
    if request.method =='POST':
        nombre =request.form['nombre']
        descripcion =request.form['descripcion']
        precio =request.form['precio']
        cantidad =request.form['cantidad']
        imagen =request.files['imagen']
        
        
        filename = secure_filename(imagen.filename)
        imagen.save(os.path.joim('satic/uploads', filename ))
        
        conn = pymysql.connect(**db_config)
        with conn:
            with conn.cursor() as cur:
                conn.execute("""
             INSERT INTO productos (nombre_producto,descripcion,precio,cantidad,imagen)
             VALUES (%s,%s,%s,%s,%s)
         """,(nombre,descripcion,precio,cantidad,filename))  
        conn.commit()
        conn.close()     
        
        flash("Producto agregar correctamente")  
        return redirect(url_for('inventario'))
    return render_template('agregar_producto.html')
                
        

@app.route("/delete/<string:id>")
@login_required
def delete_contact(id):
    conn = pymysql.connect(**db_config)
    with conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM clientes WHERE id_cte = %s', (id,))
            conn.commit()
    return redirect(url_for('dashboard'))

if __name__ == "__main__":
    app.run(port=5000, debug=True)
