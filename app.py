from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# Homepage
@app.route('/')
def homepage():
    return render_template('index.html')

# Serve static files safely
@app.route('/static/<path:filename>')
def staticfiles(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

if __name__ == '__main__':
    app.run(debug=True)
