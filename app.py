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
from sephora import Sephora
import api.connect_tables as connect_tables 


app = Flask(__name__)
app.json.sort_keys = False

@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        clinique = Clinique()
        clinique.run(export=1)
        sephora = Sephora()
        sephora.scrape(export=1)
        return redirect(url_for('download'))
    return render_template('upload.html')

@app.route("/download")
def download():
    # Takes in all the files from downloads after it was processed by process_csv
    return render_template("download.html", files=os.listdir("downloads"))

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory("downloads", filename)

@app.route('/link')
def link_dataset():
    response = connect_tables.link(directory='downloads/')
    if response:
        return {
            'message': 'success', 
            'linked': response[0], 
            'unlinked': response[1], 
            } 

if __name__ == "__main__":
    app.run(debug=True, port="8000")
