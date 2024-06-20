from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template,
    send_from_directory,
)
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from clinique import Clinique


# ALLOWED_EXTENSIONS = set(["csv"])
ALLOWED_EXTENSIONS = set(['xlsx'])
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)

@app.route("/")
@app.route("/upload", methods=["POST", "GET"])
def upload():
    if request.method == "POST":
        file = request.files["file"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            new_filename = f'{filename.split(".")[0]}_{str(datetime.now())}.xlsx'
            safe_filename = new_filename.replace(":", "-")
            save_location = os.path.join("uploads", safe_filename)
            file.save(save_location)

            # NOTE: using the uploaded file for processing in another script
            ppe = PPE(save_location)
            ppe.run(export=1)
            return redirect(
                url_for("download")
            )  # redirects to "download" once upload is complete
    return render_template("upload.html")

@app.route("/download")
def download():
    # Takes in all the files from downloads after it was processed by process_csv
    return render_template("download.html", files=os.listdir("downloads"))

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory("downloads", filename)


if __name__ == "__main__":
    app.run(debug=True, port="8000")
