from flask import (
    Flask,
    redirect,
    request,
    url_for,
    render_template,
    send_from_directory,
)
import os
from clinique import Clinique


app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        clinique = Clinique()
        clinique.run(1)
        return redirect(url_for('download'))
    return render_template('upload.html')

@app.route("/download")
def download():
    # Takes in all the files from downloads after it was processed by process_csv
    return render_template("download.html", files=os.listdir("downloads"))

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory("downloads", filename)


if __name__ == "__main__":
    app.run(debug=True, port="8000")
