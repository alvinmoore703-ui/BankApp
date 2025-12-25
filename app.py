from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Scotitrust Bank OK"
    
@app.route("/login")
def login():
    return "Login page"

if __name__ == "__main__":
    app.run()
