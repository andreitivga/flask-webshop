from flask import Flask, render_template, request, redirect, session, flash
from flask_mysqldb import MySQL
import yaml
import datetime
import random, string
import re

app = Flask(__name__) #obiectul flask in care se tine site-ul

app.secret_key = 'hello' #cheia secreta
#configuram db
#informatii despre conectarea la db dintr-un fisier de configurare
db = yaml.load(open('db.yaml'))
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(app) #obiect prin care ne conectam la bd mysql

#fiecare app.route si functie reprezinta o pagina separata pentru site ul nostru
#fiecare functie returneaza fie un render de html fie redirecteaza catre alta pagina
@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST']) #pagina pe care se deschide siteul. contine produse si mai multe functionalitati
def index():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    #selectam toate produsele si apoi prelucram ca pagina sa ne ofere 6 produse la intamplare
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM produse')
    prod = cur.fetchall()

    prod_random = random.sample(prod, len(prod))
    prod_random_list = []
    prod_random_list_top6 = []

    for i in prod_random:
        prod_random_list.append(list(i))

    for i in range(len(prod_random)):
        id_c = prod_random[i][1]
        id_b = prod_random[i][2]

        cur.execute(
            "SELECT c.Nume_Categorie, b.Nume_brand FROM categorie_hrana c join produse p on p.ID_Categorie = c.ID_Categorie "
            "JOIN brand b on p.ID_Brand = b.ID_Brand "
            "WHERE c.ID_Categorie = {} and b.ID_Brand = {}".format(id_c, id_b))

        rez = cur.fetchone()

        prod_random_list[i][1] = rez[0]
        prod_random_list[i][2] = rez[1]
        prod_random_list_top6 = prod_random_list[0:6]


    #selectam randurile necesare din baza de date pentru formul de filtrare
    cur.execute('select distinct nume_categorie from categorie_hrana')
    c = cur.fetchall()

    cur.execute('select distinct nume_brand from brand')
    b = cur.fetchall()

    cur.execute('select distinct tip from produse')
    t = cur.fetchall()

    cur.execute('select distinct varsta from produse')
    v = cur.fetchall()

    cur.execute('select distinct gramaj from produse')
    g = cur.fetchall()


    if request.method == 'POST':
        if 'buton_filtre' in request.form: #daca apasam pe butonu de filtre ne duce catre pagina cu produse filtrate
            data = request.form

            interval_pret = data['pret'] #salvam date din form si dupa le salvam in sesiune sa le pasam la functia corespunzatoare
            categorie = data['categorie']
            brand = data['brand']
            tip_hrana = data['tip']
            varsta = data['varsta']
            gramaj = str(data['gramaj'])

            session['filtre_interval_pret'] = interval_pret
            session['filtre_categorie'] = categorie
            session['filtre_brand'] = brand
            session['filtre_tip_hrana'] = tip_hrana
            session['filtre_varsta'] = varsta
            session['filtre_gramaj'] = gramaj

            return redirect('/produse_filtrate')

       ########### daca se apasa butonul add to cart la un produs ma redirecteaza catre pagina cart
        #iar daca nu sunt logat ma redirecteaza pe pagina login
        if ss_aux:
            nume_produs = list(request.form.keys())[0]
            cantitate_produs = list(request.form.values())[0]

            cart_list = session['cart']

            for i in cart_list:
                if i[0] == nume_produs:
                    return redirect('/eroare_add_to_cart')

            cart_list.append((nume_produs, cantitate_produs))
            session['cart'] = cart_list #salvam in sesiune toate produsele adaugate in cart

            return redirect('/cart')
        else:
            return redirect('/login')


    return render_template('index.html', ss=ss_aux, admin_var=admin_var, prod_random=prod_random_list_top6,
                           c=c, b=b, t=t, v=v, g=g)

@app.route('/login', methods=['GET', 'POST']) #pagina de login
def login():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if request.method == 'POST':
        userDetails = request.form

        email = userDetails['email'] #salvam inputul de la utilizator
        password = userDetails['pass']

        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM utilizatori WHERE Email = %s AND Parola = %s', (email, password)) #luam din bd aceste date
        account = cur.fetchone()

        if account: #creem sesiune pentru utilizator
            session['loggedin'] = True
            session['id'] = account[0]
            session['username'] = account[1]
            session['cart'] = []

            mysql.connection.commit()
            cur.close()

            if session['id'] != 1: #daca suntem admin ne redirecteaza pe pagina de admin
                return redirect('/my')
            else:
                return redirect('/admin')

        else:
            return "<h1> Nume sau parola incorecta. </h1> <h2><a href='/login'>Apasa aici pentru a incerca din nou.</a> </h2>"

    return render_template('/login.html', ss=ss_aux, admin_var=admin_var)


@app.route('/signup', methods=['GET', 'POST']) #pagina in care iti creezi cont
def signup():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if ss_aux:
        return "Eroare! Cat timp esti logat, nu mai poti sa-ti faci alt cont. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if request.method == 'POST': #luam inputul de la utilizator
        #fetch form data
        userDetails = request.form

        email = userDetails['email']
        password = userDetails['pass']
        nume = userDetails['nume']
        prenume = userDetails['prenume']
        varsta = userDetails['varsta']
        nr_telefon = userDetails['nr_telefon']
        strada = userDetails['strada']
        nr_strada = userDetails['nr_strada']
        cod_postal = userDetails['cod_postal']
        oras = userDetails['oras']
        judet = userDetails['judet']

        try: #ii dam insert in bd
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO utilizatori(Email, Parola, Nume, Prenume, Varsta, Nr_Telefon, Strada, Numar_Strada, "
                        "Cod_Postal, Oras, Judet) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (email, password,
                         nume, prenume, varsta, nr_telefon, strada, nr_strada, cod_postal, oras, judet))
        except:
            return "Eroare! Emailul a mai fost folosit pentru alt cont. Incearca cu alt email. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"
        mysql.connection.commit()
        cur.close()

        return render_template('succes.html')


    return render_template('signup.html', ss=ss_aux, admin_var=admin_var)


@app.route('/logout') #pagina de logout
def logout():
    if session['loggedin'] == False:
        return "Eroare! Nu poti da log-out daca nu esti logat"

    session.pop('loggedin', None) #stergem totul din sesiune si redirectam catre login
    session.pop('id', None)
    session.pop('username', None)
    # Redirect to login page
    session.clear()
    return redirect('/login')


@app.route('/my', methods=['GET', 'POST']) #pagina contului meu
def my():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not ss_aux:
        return "Eroare! Nu esti logat. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    curr_id = session['id']
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM utilizatori WHERE ID_Utilizator = %s', str(curr_id)) #selectez informatiile despre user din bd
    account = cur.fetchone()

    if request.method == 'POST': #acesta poate updata orice data despre el. luam inputul lui si l scriem in bd cu update
        #fetch form data
        userDetails = request.form

        password = userDetails['pass']
        nume = userDetails['nume']
        prenume = userDetails['prenume']
        varsta = userDetails['varsta']
        nr_telefon = userDetails['nr_telefon']
        strada = userDetails['strada']
        nr_strada = userDetails['nr_strada']
        cod_postal = userDetails['cod_postal']
        oras = userDetails['oras']
        judet = userDetails['judet']

        cur.execute('UPDATE utilizatori SET Parola = %s, Nume = %s, Prenume = %s, Varsta = %s, Nr_Telefon = %s,'
                    'Strada = %s, Numar_Strada = %s, Cod_Postal = %s, Oras = %s, Judet = %s WHERE ID_Utilizator = %s'
                    , ((password, nume, prenume, varsta, nr_telefon, strada, nr_strada, cod_postal, oras, judet, str(curr_id))))

        mysql.connection.commit()
        cur.close()
        return render_template('succes.html')

    return render_template('/my.html', ss=ss_aux, acc=account, admin_var=admin_var)

@app.route('/succes') #pagina de succes
def succes():
    return render_template('/succes.html')


@app.route('/eroare_add_to_cart') #in caz ca add_to_cart ne da eroare se afiseaza pagina asta
def eroare_add_to_cart():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    return render_template('/eroare_add_to_cart.html', ss_aux=ss_aux, admin_var=admin_var)


@app.route('/cart', methods=['GET', 'POST']) #pagina cartului
def cart():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    cart = session['cart'] # iau informatia din sesiune
    produse_cart = []
    cantitate_cart = []

    for i in cart:
        produse_cart.append(i[0])
        cantitate_cart.append(i[1])

    prod = []
    cur = mysql.connection.cursor()
    for p in produse_cart:
        cur.execute('SELECT * FROM produse where Nume_produs = "{}"'.format(p)) #luam toate infromatiile despre un produs
        rez = cur.fetchone()
        prod.append(rez)

    prod_list = [] #in aceasta variabila salvam datele necesare din database

    for i in prod:
        prod_list.append(list(i))

    for i in range(len(prod)):
        id_c = prod[i][1]
        id_b = prod[i][2]

        cur.execute(
            "SELECT c.Nume_Categorie, b.Nume_brand FROM categorie_hrana c join produse p on p.ID_Categorie = c.ID_Categorie "
            "JOIN brand b on p.ID_Brand = b.ID_Brand "
            "WHERE c.ID_Categorie = {} and b.ID_Brand = {}".format(id_c, id_b))

        rez = cur.fetchone()

        prod_list[i][1] = rez[0]
        prod_list[i][2] = rez[1]

    for i in range(len(prod_list)):
        prod_list[i].append(cantitate_cart[i])


    total_plata = 0
    for prod in prod_list:
        total_plata += prod[4] * int(prod[10])

    for prod in prod_list:
        total_plata_produs = prod[4] * int(prod[10])
        prod.append(total_plata_produs)


    if request.method == "POST":
        if 'comanda' in request.form: #daca se apasa butonul comanda
            session['cart'] = [] #sterg informatiile despre cart din sesiune

            id_utilizator = session['id'] #salvez id utilizator si scriu in tabelele comanda_utilizator si detalii_comanda

            cur.execute("INSERT INTO comanda_utilizator(ID_Utilizator, Total_Plata, Data_Comanda) VALUES(%s, %s, NOW())", (str(id_utilizator), str(total_plata)))

            ##selectez numarul ULTIMEI COMENZI al utilizatorului acesta pentru a insera in tabela de legatura
            cur.execute('SELECT ID_Comanda FROM comanda_utilizator WHERE ID_Utilizator = {} ORDER BY ID_Comanda DESC LIMIT 1'.format(id_utilizator))

            id_comanda = cur.fetchone()[0]

            for prod in prod_list:
                cur.execute("INSERT INTO detalii_comanda(ID_Comanda, ID_Produs, Cantitate) VALUES (%s, %s, %s)", (str(id_comanda), str(prod[0]), prod[10]))

            mysql.connection.commit()
            cur.close()

            return redirect('/comenzile_mele')

        if 'sterge' in request.form: #daca se apasa butonul de stergere sterg informatia din sesiune si redirectez la home
            session['cart'] = []
            return redirect('/home')


    return render_template('/cart.html', ss=ss_aux, admin_var=admin_var, prods=prod_list, produse_cart=produse_cart, total_plata=total_plata)


@app.route('/admin', methods=['GET', 'POST']) #pagina de admin
def admin():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var: #poate fi accesata numai de admin
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    cur = mysql.connection.cursor() #selectez informatiile despre comenzi din bd
    cur.execute("SELECT c.ID_Comanda, u.Email, count(dc.id_produs) as nr_produse, c.Total_Plata, c.Data_Comanda "
                "FROM comanda_utilizator c JOIN utilizatori u ON c.ID_utilizator = u.ID_Utilizator "
                "join detalii_comanda dc on dc.id_comanda = c.id_comanda "
                "group by dc.id_comanda")

    rez = cur.fetchall()

    if request.method == "POST":
        if 'stat1' in request.form: #daca se apasa butonul pentru statistica 1 ma redirecteaza pe pagina aferenta
            return redirect('/statistici1_admin')

        if 'stat2' in request.form: #daca se apasa butonul pentru statistica 2 ma redirecteaza pe pagina aferenta
            return redirect('/statistici2_admin')

        session['detalii_comanda_utilizator'] = list(request.form.keys())[0]
        return redirect('/detalii_comanda')


    return render_template('/admin.html', ss=ss_aux, admin_var=admin_var, rez=rez)



#pe pagina admin sunt 4 butoane. ele arata tabelele utilizatori, produse, categorii si branduri
#pentru fiecare tabela sunt mai multe pagini de insert update delete care fac acelasi lucru (e mult cod repetat)
#voi descrie functionaliatea pentru tabela utilizatori si aceasta se aplica si pentru celelalte tabele
@app.route('/AdminUtilizatori', methods=['GET', 'POST']) #pagina cu tabela utilizatori
def AdminUtilizatori():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM utilizatori') #iau informatia din bd
    table = list(cur.fetchall())

    if request.method == 'POST': #daca vreau sa dau search unui utilizator
        data = request.form
        email = data['email']
        session['utilizator_search'] = email #salvez in sesiune inputul de la admin
        return redirect("/AdminUtilizatoriSearch") #redirect pe pagina aferenta

    return render_template('/AdminUtilizatori.html', ss=ss_aux, admin_var=admin_var, table=table)

@app.route('/AdminUtilizatoriSearch') #pagina ce-mi ofera rezultatul cautarii mele
def AdminUtilizatoriSearch():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    email = session['utilizator_search'] #iau informatia din sesiune
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM utilizatori where Email = "{}"'.format(email)) #si iau ce trebuie din bd
    rez = cur.fetchone()

    return render_template('/AdminUtilizatoriSearch.html', ss=ss_aux, admin_var=admin_var, i=rez)

@app.route('/AdminUtilizatoriInsert', methods=['GET', 'POST'])
def AdminUtilizatoriInsert(): #pagina in care pot insera un camp in tabela
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if request.method == 'POST': #iau inputul de la admin
        #fetch form data
        userDetails = request.form
        email = userDetails['email']
        password = userDetails['pass']
        nume = userDetails['nume']
        prenume = userDetails['prenume']
        varsta = userDetails['varsta']
        nr_telefon = userDetails['nr_telefon']
        strada = userDetails['strada']
        nr_strada = userDetails['nr_strada']
        cod_postal = userDetails['cod_postal']
        oras = userDetails['oras']
        judet = userDetails['judet']

        try: #inserez in bd
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO utilizatori(Email, Parola, Nume, Prenume, Varsta, Nr_Telefon, Strada, Numar_Strada, "
                        "Cod_Postal, Oras, Judet) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (email, password,
                         nume, prenume, varsta, nr_telefon, strada, nr_strada, cod_postal, oras, judet))
        except:
            return "Eroare! Emailul a mai fost folosit pentru alt cont. Incearca cu alt email. <a href='/AdminUtilizatoriInsert'>Apasa aici pentru a te intoarce la pagina.</a>"
        mysql.connection.commit()
        cur.close()

        return "<h1> Succes </h1>" \
           "<h2> <a href='/AdminUtilizatori'>Intoarce-te la pagina utilizatori</a> </h2>"

    return render_template('/AdminUtilizatoriInsert.html', ss=ss_aux, admin_var=admin_var)

@app.route('/AdminUtilizatoriDelete', methods=['GET', 'POST']) #pagina in care pot sterge un camp din tabela
def AdminUtilizatoriDelete():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if request.method == 'POST': #iau informatia din input
        #fetch form data
        userDetails = request.form
        email = userDetails['email']

        if email:
            try:
                cur = mysql.connection.cursor()
                cur.execute("DELETE FROM utilizatori WHERE Email = '{}'".format(email)) #sterg informatia din bd
            except:
                return "Eroare! Contul nu exista. Incearca altul. <a href='/AdminUtilizatoriDelete'>Apasa aici pentru a te intoarce la pagina.</a>"
            mysql.connection.commit()
            cur.close()

            return "<h1> Succes </h1>" \
               "<h2> <a href='/AdminUtilizatori'>Intoarce-te la pagina utilizatori</a> </h2>"

        else:
            return "Eroare! Contul nu exista. Incearca altul. <a href='/AdminUtilizatoriDelete'>Apasa aici pentru a te intoarce la pagina.</a>"

    return render_template('/AdminUtilizatoriDelete.html', ss=ss_aux, admin_var=admin_var)


@app.route('/AdminUtilizatoriUpdate', methods=['GET', 'POST']) #pagina in care pot updata un camp din tabela
def AdminUtilizatoriUpdate():
    ss_aux = session.get('loggedin')
    email = ""
    account = ()
    curr_id = 0

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if request.method == 'POST': #caut informatii despre un utilizator cu ajutorul emailului
        if 'submit1' in request.form:
            #fetch form data
            userDetails = request.form
            email = userDetails['email']

            if email:
                try:
                    cur = mysql.connection.cursor()
                    cur.execute("SELECT * FROM utilizatori WHERE Email = '{}'".format(email))
                    account = cur.fetchone()

                    mysql.connection.commit()
                    cur.close()

                except:
                    return "Eroare! Contul nu exista. Incearca altul. <a href='/AdminUtilizatoriUpdate'>Apasa aici pentru a te intoarce la pagina.</a>"

            else:
                return "Eroare! Contul nu exista. Incearca altul. <a href='/AdminUtilizatoriUpdate'>Apasa aici pentru a te intoarce la pagina.</a>"


        if 'submit2' in request.form: #aici updatez efectiv. iau datele din input

            userDetails2 = request.form
            email = userDetails2['email']
            password = userDetails2['pass']
            nume = userDetails2['nume']
            prenume = userDetails2['prenume']
            varsta = userDetails2['varsta']
            nr_telefon = userDetails2['nr_telefon']
            strada = userDetails2['strada']
            nr_strada = userDetails2['nr_strada']
            cod_postal = userDetails2['cod_postal']
            oras = userDetails2['oras']
            judet = userDetails2['judet']

            try:
                cur = mysql.connection.cursor() #si dau update in bd
                cur.execute('UPDATE utilizatori SET Parola = "{}", Nume = "{}", Prenume = "{}", Varsta = {}, Nr_Telefon = "{}",'
                            'Strada = "{}", Numar_Strada = {}, Cod_Postal = "{}", Oras = "{}", Judet = "{}" WHERE Email = "{}"'.format(
                    password, nume, prenume, varsta, nr_telefon, strada, nr_strada, cod_postal, oras, judet, email))

                mysql.connection.commit()
                cur.close()

                return "<h1> Succes </h1>" \
                       "<h2> <a href='/AdminUtilizatori'>Intoarce-te la pagina utilizatori</a> </h2>"

            except:
                return "Eroare! <a href='/AdminUtilizatoriUpdate'>Apasa aici pentru a te intoarce la pagina.</a>"

    return render_template('/AdminUtilizatoriUpdate.html', ss=ss_aux, admin_var=admin_var, email=email, acc=account)





########################################################################################################################



@app.route('/AdminBrand', methods=['GET', 'POST'])
def AdminBrand():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM brand')
    table = list(cur.fetchall())

    if request.method == 'POST':
        data = request.form
        brand = data['nume_brand']
        session['brand_search'] = brand
        return redirect("/AdminBrandSearch")

    return render_template('/AdminBrand.html', ss=ss_aux, admin_var=admin_var, table=table)

@app.route('/AdminBrandSearch')
def AdminBrandSearch():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    brand = session['brand_search']
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM brand where Nume_Brand = "{}"'.format(brand))
    rez = cur.fetchone()

    return render_template('/AdminBrandSearch.html', ss=ss_aux, admin_var=admin_var, i=rez)


@app.route('/AdminBrandInsert', methods=['GET', 'POST'])
def AdminBrandInsert():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if request.method == 'POST':
        #fetch form data
        brandDetails = request.form
        nume_brand = brandDetails['nume_brand']

        try:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO brand(Nume_Brand) VALUES ('{}')".format(nume_brand))

        except:
           return "Eroare! <a href='/AdminBrandInsert'>Apasa aici pentru a te intoarce la pagina.</a>"

        mysql.connection.commit()
        cur.close()

        return "<h1> Succes </h1>" \
           "<h2> <a href='/AdminBrand'>Intoarce-te la pagina Brand.</a> </h2>"

    return render_template('/AdminBrandInsert.html', ss=ss_aux, admin_var=admin_var)

@app.route('/AdminBrandDelete', methods=['GET', 'POST'])
def AdminBrandDelete():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if request.method == 'POST':
        #fetch form data
        brandDetails = request.form
        nume_brand = brandDetails['nume_brand']

        if nume_brand:
            try:
                cur = mysql.connection.cursor()
                cur.execute("DELETE FROM brand WHERE Nume_Brand = '{}'".format(nume_brand))
            except:
                return "Eroare! Brandul nu exista. Incearca altul. <a href='/AdminBrandDelete'>Apasa aici pentru a te intoarce la pagina.</a>"
            mysql.connection.commit()
            cur.close()

            return "<h1> Succes </h1>" \
               "<h2> <a href='/AdminBrand'>Intoarce-te la pagina brand</a> </h2>"

        else:
            return "Eroare! Brandul nu exista. Incearca altul. <a href='/AdminBrandDelete'>Apasa aici pentru a te intoarce la pagina.</a>"

    return render_template('/AdminBrandDelete.html', ss=ss_aux, admin_var=admin_var)


@app.route('/AdminBrandUpdate', methods=['GET', 'POST'])
def AdminBrandUpdate():
    return render_template('/AdminBrandUpdate.html')




########################################################################################################################



@app.route('/AdminCategorii', methods=['GET', 'POST'])
def AdminCategorii():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM categorie_hrana')
    table = list(cur.fetchall())

    if request.method == 'POST':
        data = request.form
        categorii = data['nume_categorii']
        session['categorii_search'] = categorii
        return redirect("/AdminCategoriiSearch")

    return render_template('/AdminCategorii.html', ss=ss_aux, admin_var=admin_var, table=table)

@app.route('/AdminCategoriiSearch')
def AdminCategoriiSearch():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    categorii = session['categorii_search']
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM categorie_hrana where Nume_Categorie = "{}"'.format(categorii))
    rez = cur.fetchone()

    return render_template('/AdminCategoriiSearch.html', ss=ss_aux, admin_var=admin_var, i=rez)


@app.route('/AdminCategoriiInsert', methods=['GET', 'POST'])
def AdminCategoriiInsert():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if request.method == 'POST':
        #fetch form data
        cDetails = request.form
        nume_categorie = cDetails['nume_categorie']

        try:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO categorie_hrana(Nume_Categorie) VALUES ('{}')".format(nume_categorie))

        except:
            return "Eroare! <a href='/AdminCategoriiInsert'>Apasa aici pentru a te intoarce la pagina.</a>"

        mysql.connection.commit()
        cur.close()

        return "<h1> Succes </h1>" \
           "<h2> <a href='/AdminCategorii'>Intoarce-te la pagina Categorii.</a> </h2>"

    return render_template('/AdminCategoriiInsert.html', ss=ss_aux, admin_var=admin_var)

@app.route('/AdminCategoriiDelete', methods=['GET', 'POST'])
def AdminCategoriiDelete():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if request.method == 'POST':
        #fetch form data
        cDetails = request.form
        nume_categorie = cDetails['nume_categorie']

        if nume_categorie:
            try:
                cur = mysql.connection.cursor()
                cur.execute("DELETE FROM categorie_hrana WHERE Nume_Categorie = '{}'".format(nume_categorie))
            except:
                return "Eroare! Categoria nu exista. Incearca altul. <a href='/AdminCategoriiDelete'>Apasa aici pentru a te intoarce la pagina.</a>"
            mysql.connection.commit()
            cur.close()

            return "<h1> Succes </h1>" \
               "<h2> <a href='/AdminCategorii'>Intoarce-te la pagina Categorii</a> </h2>"

        else:
            return "Eroare! Categoria nu exista. Incearca altul. <a href='/AdminCategoriiDelete'>Apasa aici pentru a te intoarce la pagina.</a>"

    return render_template('/AdminCategoriiDelete.html', ss=ss_aux, admin_var=admin_var)


@app.route('/AdminCategoriiUpdate', methods=['GET', 'POST'])
def AdminCategoriiUpdate():
    return render_template('/AdminCategoriiUpdate.html')



########################################################################################################################



@app.route('/AdminProduse', methods=['GET', 'POST'])
def AdminProduse():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM produse')
    table = list(cur.fetchall())

    table_list = []
    for i in table:
        table_list.append(list(i))

    for i in range(len(table_list)):
        curr_id_categorie = table_list[i][1]
        curr_id_brand = table_list[i][2]

        cur.execute("SELECT c.Nume_Categorie, b.Nume_brand FROM categorie_hrana c join produse p on p.ID_Categorie = c.ID_Categorie "
                    "JOIN brand b on p.ID_Brand = b.ID_Brand "
                    "WHERE c.ID_Categorie = {} and b.ID_Brand = {}".format(curr_id_categorie, curr_id_brand))

        rez = cur.fetchone()

        table_list[i][1] = rez[0]
        table_list[i][2] = rez[1]

    if request.method == 'POST':
        data = request.form
        nume_produs = data['nume_produs']
        session['produs_search'] = nume_produs
        return redirect("/AdminProduseSearch")


    return render_template('/AdminProduse.html', ss=ss_aux, admin_var=admin_var, table=table_list)

@app.route('/AdminProduseSearch')
def AdminProduseSearch():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    nume_produs = session['produs_search']
    cur = mysql.connection.cursor()

    cur.execute('SELECT * FROM produse where Nume_Produs = "{}"'.format(nume_produs))
    rez = cur.fetchone()

    if rez:
        table = list(rez)

        curr_id_categorie = table[1]
        curr_id_brand = table[2]

        cur.execute(
            "SELECT c.Nume_Categorie, b.Nume_brand FROM categorie_hrana c join produse p on p.ID_Categorie = c.ID_Categorie "
            "JOIN brand b on p.ID_Brand = b.ID_Brand "
            "WHERE c.ID_Categorie = {} and b.ID_Brand = {} and p.Nume_Produs = '{}'".format(curr_id_categorie, curr_id_brand, nume_produs))

        rez = cur.fetchone()

        table[1] = rez[0]
        table[2] = rez[1]

    else:
        table = []

    return render_template('/AdminProduseSearch.html', ss=ss_aux, admin_var=admin_var, i=table)


@app.route('/AdminProduseInsert', methods=['GET', 'POST'])
def AdminProduseInsert():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if request.method == 'POST':
        #fetch form data
        prodDetails = request.form
        nume_categorie = prodDetails['nume_categorie']
        nume_brand = prodDetails['nume_brand']
        nume = prodDetails['nume']
        pret = prodDetails['pret']
        tip = prodDetails['tip']
        varsta = prodDetails['varsta']
        cantitate_ramasa = prodDetails['cantitate_ramasa']
        gramaj = prodDetails['gramaj']
        poza = prodDetails['poza']

        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT ID_Brand from brand where Nume_Brand = '{}' ".format(nume_brand))
            id_brand = cur.fetchone()

            cur.execute("SELECT ID_Categorie from categorie_hrana where Nume_Categorie = '{}'".format(nume_categorie))
            id_categorie = cur.fetchone()

            cur.execute("INSERT INTO produse(ID_Categorie, ID_brand, Nume_Produs, Pret, Tip, Varsta, Cantitate_Ramasa,"
                        "Gramaj, Poza) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)", (id_categorie, id_brand,
                         nume, pret, tip, varsta, cantitate_ramasa, gramaj, poza))
        except:
            return "Eroare! <a href='/AdminProduseInsert'>Apasa aici pentru a te intoarce la pagina.</a>"

        mysql.connection.commit()
        cur.close()

        return "<h1> Succes </h1>" \
           "<h2> <a href='/AdminProduse'>Intoarce-te la pagina Produse</a> </h2>"

    return render_template('/AdminProduseInsert.html', ss=ss_aux, admin_var=admin_var)

@app.route('/AdminProduseDelete', methods=['GET', 'POST'])
def AdminProduseDelete():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if request.method == 'POST':
        #fetch form data
        prodDetails = request.form
        nume = prodDetails['nume']

        if nume:
            try:
                cur = mysql.connection.cursor()
                cur.execute("DELETE FROM produse WHERE Nume_Produs = '{}'".format(nume))
            except:
                return "Eroare! Produsul nu exista. Incearca altul. <a href='/AdminProduseDelete'>Apasa aici pentru a te intoarce la pagina.</a>"
            mysql.connection.commit()
            cur.close()

            return "<h1> Succes </h1>" \
               "<h2> <a href='/AdminProduse'>Intoarce-te la pagina Produse</a> </h2>"

        else:
            return "Eroare! Produsul nu exista. Incearca altul. <a href='/AdminProduseDelete'>Apasa aici pentru a te intoarce la pagina.</a>"

    return render_template('/AdminProduseDelete.html', ss=ss_aux, admin_var=admin_var)


@app.route('/AdminProduseUpdate', methods=['GET', 'POST'])
def AdminProduseUpdate():
    ss_aux = session.get('loggedin')
    nume = ""
    produse = ()
    produse_list = []

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if request.method == 'POST':
        if 'submit1' in request.form:
            #fetch form data
            userDetails = request.form
            nume = userDetails['nume']

            if nume:
                try:
                    cur = mysql.connection.cursor()
                    cur.execute("SELECT * FROM produse WHERE Nume_Produs = '{}'".format(nume))
                    produse = cur.fetchone()
                    produse_list = list(produse)

                    cur.execute("SELECT c.Nume_Categorie, b.Nume_Brand FROM categorie_hrana c JOIN produse p on p.ID_Categorie = c.ID_Categorie "
                                "JOIN brand b on b.ID_Brand = p.ID_Brand "
                                "WHERE c.ID_Categorie = {} and b.ID_Brand = {}".format(produse[1], produse[2]))

                    rez = cur.fetchone()

                    mysql.connection.commit()
                    cur.close()

                    produse_list[1] = rez[0]
                    produse_list[2] = rez[1]
                except:
                    return "Eroare! Produsul nu exista. Incearca altul. <a href='/AdminProduseUpdate'>Apasa aici pentru a te intoarce la pagina.</a>"

            else:
                return "Eroare! Produsul nu exista. Incearca altul. <a href='/AdminProduseUpdate'>Apasa aici pentru a te intoarce la pagina.</a>"


        if 'submit2' in request.form:

            prodDetails = request.form
            nume_categorie = prodDetails['nume_categorie']
            nume_brand = prodDetails['nume_brand']
            nume = prodDetails['nume']
            pret = prodDetails['pret']
            tip = prodDetails['tip']
            varsta = prodDetails['varsta']
            cantitate_ramasa = prodDetails['cantitate_ramasa']
            gramaj = prodDetails['gramaj']
            poza = prodDetails['poza']

            try:
                cur = mysql.connection.cursor()
                cur.execute("SELECT ID_Brand from brand where Nume_Brand = '{}' ".format(nume_brand))
                id_brand = cur.fetchone()

                cur.execute(
                    "SELECT ID_Categorie from categorie_hrana where Nume_Categorie = '{}'".format(nume_categorie))
                id_categorie = cur.fetchone()

                cur.execute("UPDATE produse SET ID_Categorie = {}, ID_Brand = {}, Pret = {}, Tip = '{}', "
                    "Varsta = '{}', Cantitate_Ramasa = {}, Gramaj = {}, Poza = '{}' WHERE Nume_Produs = '{}'".format(id_categorie[0],
                id_brand[0], pret, tip, varsta, cantitate_ramasa, gramaj, poza, nume))

                mysql.connection.commit()
                cur.close()

                return "<h1> Succes </h1>" \
                       "<h2> <a href='/AdminProduse'>Intoarce-te la pagina Produse</a> </h2>"

            except:
               return "Eroare! <a href='/AdminProduseUpdate'>Apasa aici pentru a te intoarce la pagina.</a>"

    return render_template('/AdminProduseUpdate.html', ss=ss_aux, admin_var=admin_var, nume=nume, prod=produse_list)


@app.route('/toate_produsele', methods=['GET', 'POST']) #pagina in care afisez toate produsele
def toate_produsele():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM produse') #selectez tot
    prod = cur.fetchall()

    prod_list = [] #prelucrez putin datele ca in aceasta lista sa am fix informatiile de care am nevoie

    for i in prod:
        prod_list.append(list(i))

    random.shuffle(prod_list)

    for i in range(len(prod)):
        id_c = prod[i][1]
        id_b = prod[i][2]

        cur.execute(
            "SELECT c.Nume_Categorie, b.Nume_brand FROM categorie_hrana c join produse p on p.ID_Categorie = c.ID_Categorie "
            "JOIN brand b on p.ID_Brand = b.ID_Brand "
            "WHERE c.ID_Categorie = {} and b.ID_Brand = {}".format(id_c, id_b))

        rez = cur.fetchone()

        prod_list[i][1] = rez[0]
        prod_list[i][2] = rez[1]

    if request.method == "POST": #partea de add_to_cart fix la ca pagina principala (index.html)
        if ss_aux:
            nume_produs = list(request.form.keys())[0]
            cantitate_produs = list(request.form.values())[0]

            cart_list = session['cart']

            for i in cart_list:
                if i[0] == nume_produs:
                    return redirect('/eroare_add_to_cart')

            cart_list.append((nume_produs, cantitate_produs))
            session['cart'] = cart_list

            return redirect('/cart')
        else:
            return redirect('/login')


    return render_template('/toate_produsele.html', ss=ss_aux, admin_var=admin_var, prods=prod_list)


@app.route('/hrana_caini', methods=['GET', 'POST']) #pagina in care afisez doar produsele din categorie hrana caini
def hrana_caini():                                  #fix acelasi principiu ca la pagina toate produsele numai ca selectez categoria din bd
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM produse p JOIN categorie_hrana c on p.ID_Categorie = c.ID_Categorie '
                'WHERE c.Nume_Categorie = "Hrana Caini"')

    prod = cur.fetchall()

    prod_list = []

    for i in prod:
        prod_list.append(list(i))

    random.shuffle(prod_list)

    for i in range(len(prod)):
        id_c = prod[i][1]
        id_b = prod[i][2]

        cur.execute(
            "SELECT c.Nume_Categorie, b.Nume_brand FROM categorie_hrana c join produse p on p.ID_Categorie = c.ID_Categorie "
            "JOIN brand b on p.ID_Brand = b.ID_Brand "
            "WHERE c.ID_Categorie = {} and b.ID_Brand = {}".format(id_c, id_b))

        rez = cur.fetchone()

        prod_list[i][1] = rez[0]
        prod_list[i][2] = rez[1]

    if request.method == "POST":
        if ss_aux:
            nume_produs = list(request.form.keys())[0]
            cantitate_produs = list(request.form.values())[0]

            cart_list = session['cart']

            for i in cart_list:
                if i[0] == nume_produs:
                    return redirect('/eroare_add_to_cart')

            cart_list.append((nume_produs, cantitate_produs))
            session['cart'] = cart_list

            return redirect('/cart')
        else:
            return redirect('/login')


    return render_template('/hrana_caini.html', ss=ss_aux, admin_var=admin_var, prods=prod_list)


@app.route('/hrana_pisici', methods=['GET', 'POST'])   #pagina in care afisez doar produsele din categorie hrana caini
def hrana_pisici():                                    #fix acelasi principiu ca la pagina toate produsele numai ca selectez categoria din bd
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM produse p JOIN categorie_hrana c on p.ID_Categorie = c.ID_Categorie '
                'WHERE c.Nume_Categorie = "Hrana Pisici"')

    prod = cur.fetchall()
    prod_list = []

    for i in prod:
        prod_list.append(list(i))

    random.shuffle(prod_list)

    for i in range(len(prod)):
        id_c = prod[i][1]
        id_b = prod[i][2]

        cur.execute(
            "SELECT c.Nume_Categorie, b.Nume_brand FROM categorie_hrana c join produse p on p.ID_Categorie = c.ID_Categorie "
            "JOIN brand b on p.ID_Brand = b.ID_Brand "
            "WHERE c.ID_Categorie = {} and b.ID_Brand = {}".format(id_c, id_b))

        rez = cur.fetchone()

        prod_list[i][1] = rez[0]
        prod_list[i][2] = rez[1]

    if request.method == "POST":
        if ss_aux:
            nume_produs = list(request.form.keys())[0]
            cantitate_produs = list(request.form.values())[0]

            cart_list = session['cart']

            for i in cart_list:
                if i[0] == nume_produs:
                    return redirect('/eroare_add_to_cart')

            cart_list.append((nume_produs, cantitate_produs))
            session['cart'] = cart_list

            return redirect('/cart')
        else:
            return redirect('/login')

    return render_template('/hrana_pisici.html', ss=ss_aux, admin_var=admin_var, prods=prod_list)


@app.route('/produse_filtrate', methods=['GET', 'POST']) #pagina in care se afiseaza produsele conform filtrelor puse de utilizator
def produse_filtrate():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    interval_pret = session['filtre_interval_pret'] #luam informatia din sesiune
    categorie = session['filtre_categorie']
    brand = session['filtre_brand']
    tip_hrana = session['filtre_tip_hrana']
    varsta = session['filtre_varsta']
    gramaj = session['filtre_gramaj']

    cur = mysql.connection.cursor()
    cur.execute('SELECT * from produse')

    rez1 = rez2 = rez3 = rez4 = rez5 = rez6 = set()

    #multe queryuri cu joinuri care ne returneaza informatia corespunzatoare
    if interval_pret:
        if interval_pret == "1":
            cur.execute('SELECT * FROM produse p JOIN categorie_hrana c on p.ID_Categorie = c.ID_Categorie '
                'join brand b on p.ID_Brand = b.ID_Brand '
                'WHERE p.pret >= 10 and p.pret <= 20')
            rez1 = set(cur.fetchall())


        elif interval_pret == "2":
            cur.execute('SELECT * FROM produse p JOIN categorie_hrana c on p.ID_Categorie = c.ID_Categorie '
                        'join brand b on p.ID_Brand = b.ID_Brand '
                        'WHERE p.pret >= 21 and p.pret <= 30')
            rez1 = set(cur.fetchall())

        elif interval_pret == "3":
            cur.execute('SELECT * FROM produse p JOIN categorie_hrana c on p.ID_Categorie = c.ID_Categorie '
                        'join brand b on p.ID_Brand = b.ID_Brand '
                        'WHERE p.pret >= 31')
            rez1 = set(cur.fetchall())


    if categorie:
        cur.execute('SELECT * FROM produse p JOIN categorie_hrana c on p.ID_Categorie = c.ID_Categorie '
                    'join brand b on p.ID_Brand = b.ID_Brand '
                    'WHERE c.Nume_Categorie = "{}"'.format(categorie))
        rez2 = set(cur.fetchall())

    if brand:
        cur.execute('SELECT * FROM produse p JOIN categorie_hrana c on p.ID_Categorie = c.ID_Categorie '
                    'join brand b on p.ID_Brand = b.ID_Brand '
                    'WHERE b.Nume_Brand = "{}"'.format(brand))
        rez3 = set(cur.fetchall())

    if tip_hrana:
        cur.execute('SELECT * FROM produse p JOIN categorie_hrana c on p.ID_Categorie = c.ID_Categorie '
                    'join brand b on p.ID_Brand = b.ID_Brand '
                    'WHERE p.Tip = "{}"'.format(tip_hrana))
        rez4 = set(cur.fetchall())

    if varsta:
        cur.execute('SELECT * FROM produse p JOIN categorie_hrana c on p.ID_Categorie = c.ID_Categorie '
                    'join brand b on p.ID_Brand = b.ID_Brand '
                    'WHERE p.Varsta = "{}"'.format(varsta))
        rez5 = set(cur.fetchall())

    if gramaj:
        cur.execute('SELECT * FROM produse p JOIN categorie_hrana c on p.ID_Categorie = c.ID_Categorie '
                    'join brand b on p.ID_Brand = b.ID_Brand '
                    'WHERE p.Gramaj = "{}"'.format(gramaj))
        rez6 = set(cur.fetchall())

    try:
        result = set.intersection(*(s for s in [rez1, rez2, rez3, rez4, rez5, rez6] if s)) #facem intersectii intre rezultatele acestor queryuri
        #cu informatia din result vom afisa produsele corespunzatoare pe pagina
    except:
        return redirect('/home')

    if request.method == "POST": #functionalitatea de add_to_cart
        if ss_aux:
            nume_produs = list(request.form.keys())[0]
            cantitate_produs = list(request.form.values())[0]

            cart_list = session['cart']

            for i in cart_list:
                if i[0] == nume_produs:
                    return redirect('/eroare_add_to_cart')

            cart_list.append((nume_produs, cantitate_produs))
            session['cart'] = cart_list

            return redirect('/cart')
        else:
            return redirect('/login')


    return render_template("/produse_filtrate.html", ss=ss_aux, admin_var=admin_var, prods=result)

@app.route('/comenzile_mele', methods=['GET', 'POST']) #pagina in care un utilizator poate sa vada toate comenzile lui
def comenzile_mele():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not ss_aux: #daca nu esti logat te redirecteaza pe pagina de login
        return redirect('/login')

    account_id = session['id'] #luam id ul contului din sesiune
    cur = mysql.connection.cursor()
    cur.execute("SELECT c.ID_Comanda, c.ID_Utilizator, c.Total_Plata, c.Data_Comanda, u.Email FROM " #selectam informatia din baza de date pe baza id_ului
                "comanda_utilizator c JOIN utilizatori u ON c.ID_utilizator = u.ID_Utilizator "
                "WHERE c.ID_Utilizator = {}".format(account_id))

    rez = cur.fetchall()
    rez_list = []
    email = ""

    if rez:
        for i in rez:
            rez_list.append(list(i))

        email = rez[0][4]
        cur.execute("SELECT d.id_comanda, count(d.id_produs) from detalii_comanda d " #query in care aflam numarul de produse pentru o anumita comanda
                    "where d.id_Comanda in "
	                    "(SELECT c.ID_Comanda FROM comanda_utilizator c WHERE c.ID_Utilizator = {}) "
                    "group by d.id_comanda".format(account_id))
        nr_prod = cur.fetchall()
        print(nr_prod)

        for i in range(len(rez_list)):
            rez_list[i][1] = nr_prod[i][1] #salvam in rezlist


    cur.execute('select distinct nume_brand from brand') #informatie din bd pentru formul in care putem alege categorie si brand la statistici2,3
    b = cur.fetchall()

    cur.execute('select distinct nume_categorie from categorie_hrana')
    c = cur.fetchall()

    if request.method == "POST":
        if 'stat1' in request.form: #daca apasam butonul de statistici ne duce la pagina corespunzatoare
            return redirect('/statistici1_user')

        if 'stat2' in request.form:
            if request.form['brand'] == '':
                return redirect('/comenzile_mele')

            session['stat2_brand'] = request.form['brand'] #salvam in sesiune brandul selectat
            return redirect('/statistici2_user')

        if 'stat3' in request.form:
            if request.form['categorie'] == '':
                return redirect('/comenzile_mele')

            session['stat3_categorie'] = request.form['categorie'] #salvam in sesiune categoria selectata
            return redirect('/statistici3_user')

        session['detalii_comanda_utilizator'] = list(request.form.keys())[0] #salvam in sesiune numarul comenzii pentru pagina detalii comanda
        return redirect('/detalii_comanda')

    return render_template('/comenzile_mele.html', ss=ss_aux, admin_var=admin_var, email = email, rez=rez_list, b=b, c=c)

@app.route('/detalii_comanda') #pagina in care vedem produsele dintr-o comanda
def detalii_comanda():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    id_comanda = session['detalii_comanda_utilizator'] #luam nr_comenzii din sesiune
    print(id_comanda)
    cur = mysql.connection.cursor()

    cur.execute("select distinct p.Nume_Produs, p.Pret, c.Nume_Categorie, b.Nume_brand, p.tip, p.varsta, " #selectam informatiile de care avem nevoie din bd
                "p.gramaj, dc.cantitate, p.poza, (p.pret * dc.cantitate) as pret_total from produse p " 
                "join categorie_hrana c on p.id_categorie = c.id_categorie "
                "join brand b on p.id_brand = b.id_brand "
                "join detalii_comanda dc on p.id_produs = dc.id_produs "
                 "where dc.id_comanda = {}".format(id_comanda))

    rez = cur.fetchall() #salvam in rez si vom afisa in html
    print(rez)

    mysql.connection.commit()
    cur.close()

    return render_template('/detalii_comanda.html', ss=ss_aux, admin_var=admin_var, prods=rez, id_comanda=id_comanda)

#pagini aferente pentru statistici user
# fiecare efectueaza un query ce ne ofera informatii ce vor fi afisate pe paginile de statistici
@app.route('/statistici1_user', methods=['GET', 'POST'])
def statistici1_user():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not ss_aux:
        return redirect('/login')

    account_id = session['id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT d.id_comanda, count(d.id_produs) as nr_produse, c.total_plata, c.data_comanda, u.email from detalii_comanda d "
                "join comanda_utilizator c on c.id_comanda = d.id_comanda "
                "join utilizatori u on u.id_utilizator = c.id_utilizator "
                "where d.id_Comanda in " 
                    "(SELECT c2.ID_Comanda FROM comanda_utilizator c2 WHERE c2.ID_Utilizator = {}) "
                "group by d.id_comanda "
                "order by nr_produse DESC "
                "LIMIT 1 ".format(account_id))

    rez = cur.fetchall()
    email = rez[0][4]

    if request.method == "POST":
        session['detalii_comanda_utilizator'] = list(request.form.keys())[0]
        return redirect('/detalii_comanda')

    return render_template('/statistici1_user.html', ss=ss_aux, admin_var=admin_var, email = email, rez=rez)

#pagina statistici
@app.route('/statistici2_user', methods=['GET', 'POST'])
def statistici2_user():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not ss_aux:
        return redirect('/login')

    account_id = session['id']
    brand = session['stat2_brand']

    cur = mysql.connection.cursor()
    cur.execute("select c.id_comanda, count(dc.id_produs) as nr_produse, c.total_plata, c.data_comanda, u.email from comanda_utilizator c "
                "join detalii_comanda dc on c.id_comanda = dc.id_comanda "
                "join utilizatori u on u.id_utilizator = c.id_utilizator "
                "where c.total_plata = "
                "(select max(c2.total_plata) from comanda_utilizator c2 "
                "join utilizatori u2 on c2.ID_utilizator = u2.id_utilizator "
                "join detalii_comanda dc2 on c2.ID_Comanda = dc2.ID_Comanda "
                "join produse p on dc2.id_produs = p.id_produs "
                "join brand b on p.id_brand = b.id_brand "
                "where u2.id_utilizator = {} and b.nume_brand = '{}' )".format(account_id, brand))

    rez = cur.fetchall()
    if rez[0][0] is None:
        return redirect('/comenzile_mele')
    email = ''

    if rez:
        email = rez[0][4]

        if request.method == "POST":
            session['detalii_comanda_utilizator'] = list(request.form.keys())[0]
            return redirect('/detalii_comanda')

    return render_template('/statistici2_user.html', ss=ss_aux, admin_var=admin_var, email = email, rez=rez)

#pagina statistici
@app.route('/statistici3_user', methods=['GET', 'POST'])
def statistici3_user():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not ss_aux:
        return redirect('/login')

    account_id = session['id']
    categorie = session['stat3_categorie']

    cur = mysql.connection.cursor()
    cur.execute("select c.id_comanda, count(dc.id_produs) as nr_produse, c.total_plata, c.data_comanda, u.email from comanda_utilizator c "
                "join detalii_comanda dc on c.id_comanda = dc.id_comanda "
                "join utilizatori u on u.id_utilizator = c.id_utilizator "
                "where c.data_comanda = "
                "(select min(c2.data_comanda) from comanda_utilizator c2 "
                 "join utilizatori u2 on c2.ID_utilizator = u2.id_utilizator "
                 "join detalii_comanda dc2 on c2.ID_Comanda = dc2.ID_Comanda " 
                 "join produse p on dc2.id_produs = p.id_produs "
                 "join categorie_hrana cat on p.id_categorie = cat.id_categorie "
                 "where u2.id_utilizator = {}  and cat.nume_categorie = '{}') "
                "order by c.id_comanda ASC limit 1".format(account_id, categorie))

    rez = cur.fetchall()
    if rez[0][0] is None:
        return redirect('/comenzile_mele')

    if rez:
        email = rez[0][4]

        if request.method == "POST":
            session['detalii_comanda_utilizator'] = list(request.form.keys())[0]
            return redirect('/detalii_comanda')

    return render_template('/statistici3_user.html', ss=ss_aux, admin_var=admin_var, email = email, rez=rez)

#avem doua statistici si pentru pagina de admin, diferite fata de cele pentru user
@app.route('/statistici1_admin', methods=['GET', 'POST'])
def statistici1_admin():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if not ss_aux:
        return redirect('/login')

    cur = mysql.connection.cursor()
    cur.execute("select u.email, count(c.id_comanda) as nr_comenzi from comanda_utilizator c "
                "join utilizatori u on u.id_utilizator = c.id_utilizator "
                "group by u.email " 
                "order by nr_comenzi DESC LIMIT 1")

    rez = cur.fetchone()
    print(rez)

    return render_template('/statistici1_admin.html', ss=ss_aux, admin_var=admin_var, rez=rez)

#a doua statistica admin
@app.route('/statistici2_admin', methods=['GET', 'POST'])
def statistici2_admin():
    ss_aux = session.get('loggedin')

    if ss_aux:
        admin_var = (session['id'] == 1)
    else:
        admin_var = False

    if not admin_var:
        return "Eroare! Nu poti accesa pagina de admin. <a href='/home'>Apasa aici pentru a te intoarce la home.</a>"

    if not ss_aux:
        return redirect('/login')

    cur = mysql.connection.cursor()
    cur.execute("select u.email, sum(c.total_plata) as suma_platita_total from comanda_utilizator c "
                "join utilizatori u on u.id_utilizator = c.id_utilizator "
                "group by u.email "
                "order by suma_platita_total DESC LIMIT 1")

    rez = cur.fetchone()

    return render_template('/statistici2_admin.html', ss=ss_aux, admin_var=admin_var, rez=rez)


if __name__ == '__main__': #rularea aplicatiei efective
    app.run(debug=True)