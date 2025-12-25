from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Scotitrust Bank OK"

if __name__ == "__main__":
    app.run()
