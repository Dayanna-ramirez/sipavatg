from flask import Flask ,render_template,request,redirect,url_for,flash
#Importamos el modulo de flask

from flask_mysqldb import MySQL #importamos modulo de mysql

app=Flask(__name__) #Parametro

#CREAMOS VARIABLES DE CONEXION AL SERVIDOR DE MYSQL

app.config['MYSQL_HOST']='Localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='mbdpy'
mysql=MySQL(app)
#Creamos Ruta Principal
@app.route("/")
def Index():
    cu=mysql.connection.cursor()
    cu.execute('select * from clientes') #construimos la consulta
    datos=cu.fetchall() #ejecutamos para obtener todos los datos
    #print(datos) #imprime los datos de la consulta
    return render_template('index.html',clients=datos)
#Crear Ruta Agregar Clientes
@app.route("/add_clientes", methods=['POST'])#Ruta de Acceso al archivo adicionar contacto
def add_contact():
    if request.method == 'POST':
        cc=request.form['Cedula']
        n=request.form['Nombres']
        tel=request.form['Telefono']
        em=request.form['Email']

        #mbdpyBASE DE DATOSS
        cur=mysql.connection.cursor()#EL CURSOR ME PERMITE EJECUTAR LAS CONSULTAS DE MYSQL
        cur.execute('insert into clientes(id_cte,Nom_cte,Tel_cte,em_cte) values(%s,%s,%s,%s)',
                  (cc,n,tel,em))
        mysql.connection.commit()
        #Confirmamos que se Reciben los datos
        print(f"c.c {cc} Nombres {n} Tel {tel} email {em}")
        #return "Agregar Datos Recibidos" #RETORNA UN MENSAJE
        return redirect(url_for('Index')) #me redirecciona a la funcion de la ruta "/"
    #Crear Ruta Consulta Dato Actualizar
@app.route('/edit/<string:id>')#Ruta de Acceso al archivo editar clientes
def get_contact(id):
    cur=mysql.connection.cursor()
    cur.execute('SELECT * from clientes WHERE id_cte={0}'.format(id))
    dato=cur.fetchall()#devuelve la consulta en un arreglo
    return render_template('Editacli.html',clients=dato[0])
@app.route('/actualiza/<string:id>',methods=['POST'])#Ruta de Acceso al archivo editar clientes
def set_contact(id):
    if request.method=='POST':
        cc=request.form['Cedula']
        n=request.form['Nombres']
        tel=request.form['Telefono']
        em=request.form['Email']
        cur=mysql.connection.cursor()
        cur.execute("""UPDATE clientes
                    SET id_cte=%s,
                        Nom_cte=%s,
                        Tel_cte=%s,
                        em_cte=%s
                    WHERE id_cte=%s""", (cc,n,tel,em,id))
        mysql.connection.commit()
        return redirect(url_for('Index'))
    #Crear Ruta Eliminar Clientes
@app.route("/delete/<string:id>")#Ruta de Acceso al archivo editar clientes
def delete_contact(id):
    cur=mysql.connection.cursor()
    cur.execute('DELETE from clientes WHERE id_cte={0}'.format(id))
    mysql.connection.commit()
    return redirect(url_for('Index'))
if __name__ == "__main__":
    app.run(port =5000,debug=True)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    