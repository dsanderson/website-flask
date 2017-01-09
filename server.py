from flask import Flask, session, redirect, url_for, escape, request
import secrets
app = Flask(__name__)

@app.route('/')
def hello_world():
	if 'username' in session:
		return "Hello {}!".format(session['username'])
	else:
		return "Hello Guest!"

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		name = request.form['username']
		passwd = request.form['password']
		if name in secrets.users.keys():
			if secrets.users[name] == passwd:
				session['username'] = request.form['username']
				return redirect(url_for('index'))
	return '''
	<form method="post">
	<p><input type=text name=username>
	<p><input type=password name=password>
	<p><input type=submit value=Login>
	</form>
	'''

@app.route('/logout')
def logout():
	# remove the username from the session if it's there
	session.pop('username', None)
	return redirect(url_for('index'))

@app.route('/aircon/contoller',methods=["GET"])
def aircon_controller():
	pass

@app.route('/aircon/contoller',methods=["POST"])
def aircon_setter():
	pass

@app.route('/aircon/command'):
def aircon_command():
	pass

# set the secret key.  keep this really secret:
app.secret_key = secrets.key

if __name__ == '__main__':
	app.run()
