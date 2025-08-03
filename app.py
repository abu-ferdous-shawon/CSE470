from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def homepage():
    return render_template("homepage.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/logout")
def logout():
    return render_template("homepage.html")


@app.route("/dashboard/buyer")
def buyer_dashboard():
    return render_template("buyer_dashboard.html")


@app.route("/dashboard/seller")
def seller_dashboard():
    return render_template("seller_dashboard.html")



if __name__ == "__main__":
    app.run(debug=True)
