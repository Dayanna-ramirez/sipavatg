from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps  # Para el decorador login_required
from flask_mysqldb import MySQL


app = Flask(__name__)
app.secret_key = 'clave_super_secreta'
app.config['MYSQL_HOST']= 'localhost' # El servidor de base de datos (localhost si usas XAMPP)
app.config['MYSQL_USER']= 'root'  # Usuario por defecto de PhpMyAdmin
app.config['MYSQL_PASSWORD']= ''   #Se deja vacio si no se tiene contraseña
app.config['MYSQL_EMPRESA']= 'bdpython'   #Nombre de tu base de datos con login y roles

#Incializamos la conexion con MySQL

mysql =MySQL(app)

# Configuración de la base de datos
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'mbdpy',
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
@login_required
def dashboard():
    conn = pymysql.connect(**db_config)
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT cte_nombre, cte_apellido, cte_curso FROM clientes")
            usuarios = cur.fetchall()
    return render_template('home.html', usuarios=usuarios)

# Ruta de Registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Recoger datos del formulario
        cte_nombre = request.form['cte_nombre']  cte_password = request.form['cte_password']
        cte_apellido = request.form['cte_apellido']
        cte_fecha_nac = request.form['cte_fecha_nac']
        cte_correo = request.form['cte_correo']
        cte_cedula = request.form['cte_cedula']
        cte_password = request.form['cte_password']
        password = generate_password_hash(request.form['password'])

        # Guardar en base de datos
        conn = pymysql.connect(**db_config)
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO clientes (
                        cte_nombre, cte_apellido,
                        cte_fecha_nac, cte_correo, 
                        cte_cedula, password
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (cte_nombre, cte_apellido,
                      cte_fecha_nac, cte_correo,
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
                cur.execute('SELECT * FROM clientes WHERE cte_correo = %s', (email,))
                user = cur.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id_cte']
            session['user_name'] = user['cte_nombre']
            flash(f'Bienvenido {user["cte_nombre"]}', 'success')
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
                    'INSERT INTO clientes(id_cte, cte_nombre, cte_apellido, cte_correo, cte_cedula) VALUES (%s, %s, %s, %s, %s)',
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
