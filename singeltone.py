from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql.cursors
import os


class DatabaseConnection:
    __instance = None  

    def __init__(self):
        if DatabaseConnection.__instance is not None:
            raise Exception("This class is a singleton! Use get_instance() instead.")

        self.connection = pymysql.connect(
            host="localhost",
            user="root",
            password="",
            database="pethouse",
            cursorclass=pymysql.cursors.DictCursor
        )
        DatabaseConnection.__instance = self

    @staticmethod
    def get_instance():
        if DatabaseConnection.__instance is None:
            DatabaseConnection()
        return DatabaseConnection.__instance

    def get_connection(self):
        return self.connection



def get_db_connection():
    return DatabaseConnection.get_instance().get_connection()

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)





@app.route("/")
def homepage():
    return render_template("homepage.html")



@app.route('/dashboard/buyer')
def buyer_dashboard():
    buyer_id=session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT id,user_id, name, category, location, price, status, phone_number, image FROM pets WHERE is_approved = 'approved' AND status != 'sold'")
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

    return render_template('buyer_dashboard.html', pets=pets, buyer_id=buyer_id)




if __name__ == "__main__":
    app.run(debug=True)
