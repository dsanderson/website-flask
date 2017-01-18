from flask import Flask, session, redirect, url_for, escape, request, Response
import secrets
import time, json, os
app = Flask(__name__)

### Index block
@app.route('/')
def hello_world():
	if 'username' in session:
		return "Hello {}!".format(session['username'])
	else:
		return "Hello Guest!"

### User management block
@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		name = request.form['username']
		passwd = request.form['password']
		if name in secrets.users.keys():
			if secrets.users[name] == passwd:
				session['username'] = request.form['username']
				return redirect('/')
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

### Aircon control block
@app.route('/aircon/controller',methods=["GET"])
def aircon_controller():
	if 'username' in session:
		data = '''<body><h1>DSA's aircon controller</h1>
	<form action="" method="post">
	  <input type=radio name=action value="on">ON<br/>
	  <input type=radio name=action value="off">OFF<br/>
	  <input type=submit value=send command>
	</form>
</body>'''
		return data
	return redirect('/')

@app.route('/aircon/controller',methods=["POST"])
def aircon_setter():
	if 'username' in session:
		action = request.form['action']
		with open(os.path.join(app.root_path,'aircon_command.json'),'r') as f:
			command_id = json.loads(f.read())['id']
		command_id += 1
		timestamp = time.time()
		command = {'command':action, 'id':command_id, 'timestamp':timestamp}
		with open(os.path.join(app.root_path,'aircon_command.json'),'w') as f:
			f.write(json.dumps(command))
		return redirect('aircon/controller')
	return redirect('/')

@app.route('/aircon/command')
def aircon_command():
	with open(os.path.join(app.root_path,'aircon_command.json'),'r') as f:
		dat = json.loads(f.read())
	#resp = Response(response=dat, status=200, mimetype="application/json")
	return json.dumps(dat)#resp

### Ferris Brewler block
import ferris_stuff

@app.route('/ferris/sensor/<sensor>')
def get_ferris_data(sensor):
	window_size = datetime.datetime.utcnow() - datetime.timedelta(days=1)
	raw_data = ferris_stuff.get_data(sensor, time=window_size)
	data = json.dumps(raw_data)
	return data


# set the secret key.  keep this really secret:
app.secret_key = secrets.key

if __name__ == '__main__':
	app.run()
