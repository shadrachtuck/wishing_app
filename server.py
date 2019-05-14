from flask import Flask, render_template, request, redirect, session, flash
from mysqlconnection import connectToMySQL
from flask_bcrypt import Bcrypt
import re
# import the function that will return an instance of a connection
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key="aye shush"
# create a regular expression object that we'll use later   
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
PASSWORD_REGEX = re.compile(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$')

@app.route('/')
def index():
    return render_template("login_reg.html")

@app.route('/register', methods=['POST'])
def registration():
    # First name
    if len(request.form['fname']) < 2:
        flash("Please provide a first name", 'registration')
        return redirect('/')
    # Last name
    if len(request.form['lname']) < 2:
        flash("Please provide a last name", 'registration')
        return redirect('/')
    # Email
    if not EMAIL_REGEX.match(request.form['email']):
        flash("Invalid email address!", 'registration')
        return redirect('/')
    # Password
    if not PASSWORD_REGEX.match(request.form['password']):
        flash("Invalid password. Password must contain a minimum of 8 characters, at least one letter, one number and one special character", 'registration')
        return redirect('/')
    if request.form['password'] != request.form['confirm']:
        flash("Passwords do not match", 'registration')
        return redirect('/')
    # Validate that the provided email is unique from all emails currently in the database by checking to see if any users in the database have that email
        check_db_for_email = connectToMySQL("wish")
        any_users_wih_email = "SELECT * FROM users where email=%(em)s;"
        data = {
            'em': request.form['email']
        }
        check_db_for_email.query_db(any_users_wih_email, data)
    
    else:
        # input user into database with hashed password
        pw_hash = bcrypt.generate_password_hash(request.form['password']) 
        print(pw_hash)  
        # connect o database
        mysql = connectToMySQL("wish")
        # query string (INSERT statement)
        query = "INSERT INTO users(first_name, last_name, email, password, created_at, updated_at) VALUES (%(fn)s, %(ln)s, %(em)s, %(pw)s, NOW(), NOW());"
        #data
        data = {
            "fn": request.form["fname"],
            "ln": request.form["lname"],
            "em": request.form["email"],
            "pw": pw_hash,
        }
        # send query to database and recieve back the new user's id
        id_from_db = mysql.query_db(query, data)
        # store id in session
        session['user_id'] = id_from_db
        # store name in session
        session['first_name'] = request.form['fname']
        #redirect to dashboard
        return redirect('/dashboard')


@app.route('/login', methods=['POST'])
def login():
    # Try to get the user's info from the datbase based on email
    # connect to db
    mysql = connectToMySQL("wish")
    # query to retrieve user
    retrieve_user = "SELECT * FROM users WHERE email = %(em)s;"
    print(retrieve_user)
    data = { "em" : request.form["email"] }
     # send query to database and recieve back the new user's id
    result = mysql.query_db(retrieve_user, data)
    # VALIDATIONS
    # if no results are under 2 char, return with errors
    # if no user was found, return with errors
    possible_user = request.form['email']
    # if len(request.form['email']) < 2:
    #     flash("Must input email", 'login')
    if len(possible_user)==0:
        flash("Must input email", 'login')
        return redirect('/')
    #  if user was found but password is incorrect, return with errors
    if result:
            if bcrypt.check_password_hash(result[0]['password'], request.form['password']):
                session['user_id'] = result[0]['id']
                session['first_name'] = result[0]['first_name']
                session['last_name'] = result[0]['last_name']
                session['email'] = result[0]['email']
                return redirect('/dashboard')
    flash("Invalid login credentials", 'login')
    return redirect("/")

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():

    mysql = connectToMySQL('wish')
    query = "SELECT * FROM wishes WHERE granted_id is NULL AND users_id = %(u_id)s ;"
    data = {
        'u_id': session['user_id']
    }
    wish_list = mysql.query_db(query, data)
    print(wish_list)

    mysql = connectToMySQL('wish')
    query = "SELECT * FROM wishes WHERE granted_id IS NOT NULL;"
    wishes_granted = mysql.query_db(query)
    print(wishes_granted)

    if session['user_id'] in session:
        flash("Logged In", 'success')
        return redirect('/dashboard')
    return render_template("dashboard.html", wish_list = wish_list, wishes_granted = wishes_granted)

@app.route('/wishes/grant/<id>', methods=['POST'])
def grant(id):
    db = connectToMySQL('wish')
    query = "UPDATE wishes SET granted_id = %(gr_id)s, granted_on = NOW() WHERE id = %(w_id)s;"
    data = {
        'w_id': request.form['submit_wish_id'],
        'gr_id': request.form['submit_granted_id'],
    }
    insert_granted_id = db.query_db(query, data)
    print(insert_granted_id)
    return redirect('/dashboard')

@app.route('/wishes')
def load_create():
    return render_template("create_wish.html")
    return redirect('/wishes/new')

@app.route('/wishes/new', methods=['POST'])
def create_wish():
 
    if len(request.form['wish']) < 3:
        flash("Wish item must consist of at least 3 characters!", 'error')
        return redirect('/wishes')
    if len(request.form['description']) < 1:
        flash("Wish description must be provided!", 'error')
        return redirect('/wishes')
    else:
        db = connectToMySQL("wish")
        query = "INSERT INTO wishes (wish, description, wisher, users_id, created_at, updated_at, granted_on) VALUES (%(w)s, %(d)s, %(w_n)s, %(u_id)s, NOW(), NOW(), NOW());"
        data = {
            'w': request.form['wish'],
            'd': request.form['description'],
            'w_n': session['first_name'],
            'u_id': session['user_id']
        }
        create_wish = db.query_db(query, data)
        print(create_wish)
        flash("Wish successfully added!", 'success')
        return redirect('/dashboard')


@app.route('/wishes/edit/<id>', methods= ['GET'])
def show_edit(id):

    db = connectToMySQL('wish')
    query = "SELECT id, wish, description, created_at, updated_at FROM wishes WHERE wishes.id = %(id)s;"
    data = {'id': id, }
    wish_info = db.query_db(query, data)
    print(wish_info)
    return render_template("edit_wish.html", wish_info = wish_info)

@app.route('/wishes/edit/<id>/update', methods = ['POST'])
def edit_wish(id):

    if len(request.form['wish']) < 3:
        flash("Wish title must consist of at least 3 characters!", 'error')
        return redirect('/wishes/edit/'+ str(id))
    if len(request.form['description']) < 1:
        flash("Wish description must be provided!", 'error')
        return redirect('/wishes/edit/'+ str(id))
    else:
        db = connectToMySQL("wish")
        query = "UPDATE wishes SET wish = %(w)s, description = %(d)s, users_id = %(u_id)s, created_at =  NOW(), updated_at = NOW() WHERE wishes.id = %(id)s;"
        data = {
            'w': request.form['wish'],
            'd': request.form['description'],
            'u_id': session['user_id'],
            'id': id,
        }
        update_wish = db.query_db(query, data)
        print(update_wish)
        flash("Wish successfully updated!", 'success')
        return redirect('/dashboard')

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect('/')
    flash('Logged Out', 'removed')

@app.route('/wishes/remove/<id>', methods=['GET'])
def remove(id):
    db = connectToMySQL('wish')
    query = "DELETE FROM wishes WHERE id=%(id)s;"
    data = {'id': id,}
    db.query_db(query, data)
    print(query)
    return redirect('/dashboard')

# @app.route('/wishes/stats/<id>', methods=['GET'])
# def stats(id):
#     # Shows wish id and related info
#     # Join user id to wish id in order to display specific wish info
#     db = connectToMySQL('wish')
#     # select specific wish info from wish id
#     query = "SELECT wishes.wish, wishes., wishes.description, wishes.created_at, wishes.updated_at, users.first_name, wishes.id FROM wishes JOIN users ON users.id = wishes.users_id WHERE wishes.id = %(id)s;"
#     data = {
#         'id': id,
#     }
#     display_wish = db.query_db(query, data)
#     print(display_wish)
#     return render_template("stats.html", display_wish = display_wish)

if __name__=="__main__":
    app.run(debug=True)
