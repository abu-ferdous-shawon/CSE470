from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from werkzeug.utils import secure_filename
import pymysql.cursors
from flask import send_from_directory
import datetime



app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="pethouse",
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route("/")
def homepage():
    return render_template("homepage.html")



@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        try:
            conn = get_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)  
            cursor.execute(
                "SELECT * FROM users WHERE email = %s AND role = %s",
                (email, role)
            )
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user and user["password"] == password:
                session["user_id"] = user["id"]
                session["name"] = user["name"]
                session["role"] = user["role"]
                flash("Login successful!", "success")

      
                if role == "buyer":
                    return redirect(url_for("buyer_dashboard"))
                elif role == "seller":
                    return redirect(url_for("seller_dashboard"))
                elif role == "vet":
                    return redirect(url_for("vet_dashboard"))
                elif role == "admin":
                    return redirect(url_for("admin_dashboard"))
                else:
                    flash("Invalid role", "danger")
                    return redirect(url_for("login"))

            else:
                flash("Invalid email, password, or role", "danger")
                return redirect(url_for("login"))

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")
        phone_number = request.form.get("phone")


        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (name, email, password, role, phone_number, profile_pic) VALUES (%s,%s,%s, %s, %s, %s)",
                (name, email, password, role, phone_number,'default.png'),
            )

            user_id = cur.lastrowid
            if role == "vet":
                location = request.form.get("location")
                speciality = request.form.get("speciality")
                cur.execute(
                    """INSERT INTO vets_info (vet_id, location, speciality)
                       VALUES (%s, %s, %s)""",
                    (user_id, location, speciality)
                )

            conn.commit()
            cur.close()
            conn.close()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear() 
    flash("You have been logged out.", "success") 
    return redirect(url_for("login"))

@app.route('/dashboard/buyer')
def buyer_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT name, category, location, price, status, phone_number, image FROM pets")
    pets_data = cursor.fetchall()
    cursor.close()
    conn.close()

    pets = []
    for pet in pets_data:
        images_str = pet['image'] or ""
        image_urls = [img.strip() for img in images_str.split(",")] if images_str else ["/static/default_pet.png"]
        pet['image_urls'] = image_urls  
        pet['phone'] = pet['phone_number']
        pets.append(pet)

    return render_template('buyer_dashboard.html', pets=pets)





@app.route('/dashboard/seller')
def seller_dashboard():
    if 'user_id' not in session or session.get('role') != 'seller':
        flash("Access denied", "danger")
        return redirect(url_for('login'))
    return render_template('seller_dashboard.html')


@app.route('/post_pet', methods=['POST'])
def post_pet():
    if 'user_id' not in session or session.get('role') != 'seller':
        flash("Unauthorized access", "danger")
        return redirect(url_for('login'))

    name = request.form.get('name')
    location = request.form.get('location')
    price = request.form.get('price')
    status = request.form.get('status')
    phone = request.form.get('phone')
    seller_id = session.get('user_id')
    category =  request.form.get('category')
    image_files = request.files.getlist('images')

    image_urls = []
    for image in image_files:
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            counter = 1
            while os.path.exists(filepath):
                name_part, ext = os.path.splitext(filename)
                filename = f"{name_part}_{counter}{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                counter += 1

            image.save(filepath)
            image_urls.append(f"/{filepath}") 

    images_str = ",".join(image_urls) if image_urls else None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pets (name, location, price, status, phone_number, image, user_id, category, is_approved)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, location, price, status, phone, images_str, seller_id, category, "Pending"))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Pet posted successfully!", "success")
        return redirect(url_for('seller_dashboard'))

    except Exception as e:
        flash(f"Database error: {str(e)}", "danger")
        return redirect(url_for('seller_dashboard'))
    

@app.route('/dashboard/vet')
def vet_dashboard():
    if 'role' not in session or session['role'] != 'vet':
        return redirect('/login')

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT users.name, users.email, users.phone_number, ap.id, ap.status, ap.date FROM appointments AS ap JOIN users ON ap.user_id = users.id")
    appointments = cursor.fetchall()

    return render_template("vet_dashboard.html", appointments=appointments)


@app.route("/available_vets")
def available_vets():
    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    cur.execute("""
        SELECT 
            users.name, users.email, users.phone_number,
            vets_info.location, vets_info.speciality,
            vets_info.id AS vet_info_id
        FROM vets_info
        JOIN users ON vets_info.vet_id = users.id
    """)
    vets = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template("available_vet.html", vets=vets)

@app.route('/appoint_doctor', methods=['POST'])
def appoint_doctor():
    if 'user_id' not in session:
        flash("You must be logged in to appoint a doctor.", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']
    vet_id = request.form.get('vet_id')
    status = "pending"
    date = datetime.date.today()
    print("DEBUG: vet_id =", vet_id)
    print("DEBUG: user_id =", user_id)

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO appointments (vet_id, user_id, status, date) VALUES (%s, %s, %s, %s)",
            (vet_id, user_id, status, date)
        )
        connection.commit()
        flash("Appointment requested successfully.", "success")
    except Exception as e:
        connection.rollback()
        flash(f"Error making appointment: {str(e)}", "error")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('available_vets'))

@app.route("/accept_appointment", methods=["POST"])
def accept_appointment():
    if "user_id" not in session or session.get("role") != "vet":
        flash("Unauthorized access", "error")
        return redirect(url_for("login"))

    appointment_id = request.form.get("appointment_id")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("UPDATE appointments SET status = %s WHERE id = %s", ("Accepted", appointment_id))
        connection.commit()
        flash("Appointment accepted successfully.", "success")
    except Exception as e:
        connection.rollback()
        flash(f"Error updating appointment: {str(e)}", "error")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("vet_dashboard"))


@app.route("/view_appointments")
def view_appointments():
    if "user_id" not in session or session.get("role") not in ["buyer", "seller"]:
        flash("Unauthorized access", "danger")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        query = """
            SELECT 
                a.id,
                a.date,
                a.status,
                c.name,
                v.speciality,
                c.phone_number,
                c.email
            FROM appointments AS a
            JOIN vets_info AS v ON a.vet_id = v.id
            JOIN users AS c ON v.vet_id = c.id
            WHERE a.user_id = %s
            ORDER BY a.date DESC
        """
        cursor.execute(query, (user_id,))
        appointments = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("view_appointments.html", appointments=appointments)




if __name__ == "__main__":
    app.run(debug=True)
