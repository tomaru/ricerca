import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
from werkzeug import secure_filename

from pymongo import MongoClient
import imagehash
from PIL import Image

app = Flask(__name__)

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = os.urandom(24)

client = MongoClient('localhost', 27017)
db = client['test-database']
collection = db["Index"]

def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/')
def index():
#	if 'username' in session:
		return render_template('index.html')
#	return '''
#		<p>Require Rogin</p>
#	'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		username = request.form['username']
		if username == 'admin':
			session['username'] = request.form['username']
			return redirect(url_for('index'))
		else:
			return '''<p>MissMath User Name</p>'''
	return '''
		<form action="" method="post">
			<p><input type="text" name="username">
			<p><input type="submit" value="Login">
		</form>
	'''

@app.route('/logout')
def logout():
	session.pop('username', None)
	return redirect(url_for('index'))

@app.route('/send', methods=['GET', 'POST'])
def send():
	if request.method == 'POST':
		img_file = request.files['img_file']
		img_file.filename = img_file.filename.replace('/',os.sep)
		if img_file and allowed_file(img_file.filename):
			filename = secure_filename(img_file.filename)
			img_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)
			img_file.save(img_url)
			hash = imagehash.dhash(Image.open(img_url))
			entry=collection.find_one({'dhash': unicode(hash)})
			if entry:
				return render_template('index.html', img_url=img_url,dhash = unicode(hash), web_url = entry['img_url'] )
			else:
				return render_template('index.html', img_url=img_url,dhash = unicode(hash))
		else:
			return ''' <p>Not Allow Extension</p> '''
	else:
		return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
	return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
#=====================================================#

	client = MongoClient('localhost', 27017)
	db = client['test-database']
	collection = db["Index"]
	
	app.debug = True
	app.run()