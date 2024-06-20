from flask import (
    Flask,
    redirect,
    url_for,
    render_template,
    send_from_directory,
)
import os
from clinique import Clinique


# ALLOWED_EXTENSIONS = set(["csv"])
ALLOWED_EXTENSIONS = set(['xlsx'])
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)

@app.route("/")
def home():
    clinique = Clinique()
    clinique.run(1)
    return redirect(url_for('download'))

@app.route("/download")
def download():
    # Takes in all the files from downloads after it was processed by process_csv
    return render_template("download.html", files=os.listdir("downloads"))

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory("downloads", filename)


if __name__ == "__main__":
    app.run(debug=True, port="8000")
