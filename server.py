from flask import Flask, session, redirect, url_for, escape, request, Response
import secrets
import time, json, os, datetime, time, glob
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
	raw_data = ferris_stuff.get_data(sensor, window_size)
	data = json.dumps(raw_data)
	resp = Response(response=data, status=200, mimetype="application/json")
	return resp

###Personal wiki block
@app.route('/wiki/<page>', methods=["GET","POST"])
def wiki(page):
	if 'username' in session:
		if request.method == 'GET':
			with open(get_current_path(page), 'r') as f:
				content = f.read()
			with open(os.path.join(app.root_path,'src','wiki-template.html'), 'r') as f:
				txt = f.read()
				txts = txt.split('******split here******')
				txt = txts[0]+content+txts[1]
			return txt
		elif request.method == 'POST':
			path = get_current_path(page)
			new_path = '.'.join(path.split('.')[:-1])+'.'+str(int(path.split('.')[-1])+1)
			with open(new_path, 'w') as f:
				f.write(request.form['text'])
			return "Saved"
	return redirect('/')

def get_current_path(page):
	path = os.path.join(app.root_path, 'wiki', page)
	folder = os.path.dirname(path)
	if not os.path.exists(folder):
		os.makedirs(folder)
	fs = glob.glob(path+'.md.*')
	if fs==[]:
		f = open(path+'.md.0','w')
		f.write('New file\n')
		f.close()
		return path+'.md.0'
	else:
		max_fnum = max([int(f.split('.')[-1]) for f in fs])
		return path+'.md.'+str(max_fnum)

# set the secret key.  keep this really secret:
app.secret_key = secrets.key

if __name__ == '__main__':
	app.run()
