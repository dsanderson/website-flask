from flask import Flask, session, redirect, url_for, escape, request, Response
import secrets
import time, json, os, datetime, time, glob, urllib2, pickle, math
from collections import namedtuple
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
@app.route('/wiki/<path:page>', methods=["GET","POST"])
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

@app.route('/wiki/')
def redirect_to_wiki():
	return redirect('/flask/wiki/index')

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


###Sethlui stuff
@app.route('/shiok')
def food_reviews():
	if request.method == "POST":
		loc = request.form["loc"]
		dist = float(request.form["dist"])
		search = request.form["search"]
		results = food_search(loc, dist, search)
		page = food_renderer(results, loc, dist, search)
	elif request.method == "GET":
		page = food_renderer([], '', '', '')
	return page

def food_search(loc, dist, search):
	#get the coordinates for the given location
	opener = urllib2.build_opener()
    opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
	url = 'https://developers.onemap.sg/commonapi/search?searchVal={}&returnGeom=Y&getAddrDetails=Y'.format(loc)
	response = opener.open(url)
    f = response.read()
    response.close()
    data = json.loads(f)
	if int(data['found'])>0:
        lat = float(data['results'][0]["LATITUDE"])
        lon = float(data['results'][0]["LONGITUDE"])
    else:
        return "Error, please enter an acceptable location"
	#skim over places, culling based on distance, to speed up search
	#search text
	tokens = search.split()
	tokens = [t.strip().lower() for t in tokens]
	results = []
	for f in FOOD_PAGES:
		if dist(lat, lon, f.lat, f.lon)<dist:
			if any([t in f.content.lower() for t in tokens]):
				results.append((f, dist(lat, lon, f.lat, f.lon)))
	results.sort(key=lambda x: x[0].date)
	return results

def food_renderer(data, loc, dist, search):
	form = """<!-- Simple form which will send a POST request -->
<form action="" method="post">
  <label for="loc">Search Location:</label>
  <input id="loc" type="text" name="loc" value={}>
  <label for="dist">Search Radius:</label>
  <input id="dist" type="text" name="dist" value={}>
  <label for="search">Search Terms (enter words separated by spaces):</label>
  <input id="search" type="text" name="search" value={}>
  <input type="submit" value="Search">
</form>""".format(loc, dist, search)
	results = ""
	for res in data:
		blurb = '<div class="result"><h2>{}</h2><p>{}, {} mi.</p><a href="{}">{}</a><p>{}</p></div>\n'.format(res[0].name, res[0].date, res[1], res[0].url, res[0].url, res[0].content)
		results += blurb
	return form+results

def dist(lat1,lon1, lat2, lon2):
	LAT_RATE = 69.094
	LON_RATE = 69.056
	x = LAT_RATE*(lat1-lat2)
	y = LON_RATE*(lon1-lon2)
	return math.sqrt(x**2+y**2)

#load page data
pkl = open(os.path.join(app.root_path, 'seth_out.pkl'), 'rb')
FOOD_PAGES = pickle.load(pkl)
pkl.close()

# set the secret key.  keep this really secret:
app.secret_key = secrets.key

if __name__ == '__main__':
	app.run()
