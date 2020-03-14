from flask import Flask, session, redirect, url_for, escape, request, Response, send_from_directory, render_template
import secrets
import time, json, os, datetime, time, glob, urllib2, pickle, math, hashlib
from collections import namedtuple
import part_search
import part_search_v2
import sbf_qr
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
@app.route('/shiok', methods=["GET","POST"])
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
		if f[6]!=None and f[7]!=None:
			if distance(lat, lon, f[6], f[7])<dist:
				if any([t in f[5].lower() for t in tokens]):
					results.append((f, distance(lat, lon, f[6], f[7])))
	results.sort(key=lambda x: x[0][3], reverse=True)
	return results

def food_renderer(data, loc, dist, search):
	form = u"""<!-- Simple form which will send a POST request -->
<form action="" method="post">
  <label for="loc">Search Location (postal code):</label>
  <input id="loc" type="text" name="loc" value={}></br>
  <label for="dist">Search Radius (mi.):</label>
  <input id="dist" type="text" name="dist" value={}></br>
  <label for="search">Search Terms (enter words separated by spaces):</label>
  <input id="search" type="text" name="search" value={}></br>
  <input type="submit" value="Search">
</form>""".format(loc, dist, search)
	results = u""
	for res in data:
		content = res[0][5]
		if len(content)>400:
			content = content[:397]+u'...'
		if res[0][3]!=None:
			blurb = u'<div class="result"><h2>{}</h2><p>{}, {:0.2f} mi., (${:0.2f})</p><a href="{}">{}</a><p>{}</p></div>\n'.format(res[0][0], res[0][2], res[1], res[0][3], res[0][1], res[0][1], content)
		else:
			blurb = u'<div class="result"><h2>{}</h2><p>{}, {} mi.</p><a href="{}">{}</a><p>{}</p></div>\n'.format(res[0][0], res[0][2], res[1], res[0][1], res[0][1], content)
		results += blurb
	with open(os.path.join(app.root_path,'src','shiok.css'), 'r') as fcss:
		css = fcss.read()
	page = u"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Shiok Search</title>
	<link href='https://fonts.googleapis.com/css?family=Lato' rel='stylesheet' type='text/css'>
    <link href='https://fonts.googleapis.com/css?family=Raleway' rel='stylesheet' type='text/css'>
	<style>{}</style>
  </head>
  <body>
    <div class='content'>
		<h1>Shiok Search</h2><p>A search engine for Singaporean food blogs</p>{}\n{}</div></body>
    </div>
  </body>
</html>""".format(css, form, results)
	return page

def distance(lat1,lon1, lat2, lon2):
	LAT_RATE = 69.094
	LON_RATE = 69.056
	x = LAT_RATE*(lat1-lat2)
	y = LON_RATE*(lon1-lon2)
	return math.sqrt(x**2+y**2)

#load page data
Place = namedtuple("Place",["name","url","date","price","zip","content","lat","lon","loc"])
pkl = open(os.path.join(app.root_path, 'seth_out.pkl'), 'rb')
FOOD_PAGES = pickle.load(pkl)
pkl.close()

##Pages for parts search
@app.route('/parts', methods=["GET","POST"])
def search_parts():
	if request.method == "POST":
		request_data = []
		max_i = 0
		searching=True
		while searching:
			max_i+=1
			if 'data{}_txt'.format(max_i) not in request.form:
				searching = False
		for i in range(max_i):
			request_data.append((request.form["data{}_txt".format(i)],request.form["data{}_unit".format(i)]))
		if not validate(request_data):
			return "Please enter a valid search."
		docs = part_search.search_documents(request_data)
		if len(docs)==0:
			page = u"""<!DOCTYPE html>
			<html lang="en">
			  <head>
			    <meta charset="utf-8">
			    <title>Part Search</title>
				<link href='https://fonts.googleapis.com/css?family=Lato' rel='stylesheet' type='text/css'>
			    <link href='https://fonts.googleapis.com/css?family=Raleway' rel='stylesheet' type='text/css'>
				<link rel="stylesheet" href="/css/article.css">
				<style>{}</style>
			  </head>
			  <body>
			  	<a href="/flask/parts">Search Again</a>
				<p>Sorry, we couldn't find any parts that match that description. Try removing some keywords and try again!</p>
			  </body>
			</html>"""
			return page
		else:
			name = hashlib.md5(str(request_data)).hexdigest()
			path = os.path.join(app.root_path,'parts','results',name)
			part_search.write_document(docs,path,request_data)
			return redirect("/flask/parts/result/{}".format(name))
	else:
		#with open(os.path.join(app.root_path,'parts','parts_page.html'),'r') as p:
		#	page = p.read()
		return render_template("parts_page.html", values=part_search.part_types)

@app.route("/parts/result/<string:name>")
def return_results_page(name):
	return render_template("results_page.html", name=name)

@app.route("/parts/res/f/<path:filename>")
def return_part_results(filename):
	return send_from_directory(os.path.join(app.root_path,'parts','results'),filename,as_attachment=True)

def validate(request_data):
	#TODO: Validate request
	valid = True
	valid = valid and len(request_data)>0
	valid = valid and all([t[0] != '' or t[1] != '' for t in request_data])
	return valid

### SBF Logo Project stuff here
#@app.route("/sbf/sbf/set/<string:cube>")
def sbf_logo_write_cube(cube):
	try:
		cube = int(cube)
	except ValueError:
		return ""
	#TODO figure out transformer
	timestamp = time.time()
	command = {'cube':cube, 'timestamp':timestamp}
	with open(os.path.join(app.root_path,'sbf_cube.json'),'w') as f:
		f.write(json.dumps(command))
	return str(cube)

@app.route("/sbf/sbf/get")
def sbf_logo_get_cube():
	with open(os.path.join(app.root_path,'sbf_cube.json'),'r') as f:
		data = json.loads(f.read())
	ts = time.time()
	if ts-data['timestamp']>5:
		return "-1"
	return str(int(data["cube"]))

#@app.route("/sbf/sbff/set/<string:cube>")
def sbff_logo_write_cube(cube):
	try:
		cube = int(cube)
	except ValueError:
		return ""
	#TODO figure out transformer
	timestamp = time.time()
	command = {'cube':cube, 'timestamp':timestamp}
	with open(os.path.join(app.root_path,'sbff_cube.json'),'w') as f:
		f.write(json.dumps(command))
	return str(cube)

@app.route("/sbf/sbff/get")
def sbff_logo_get_cube():
	with open(os.path.join(app.root_path,'sbff_cube.json'),'r') as f:
		data = json.loads(f.read())
	ts = time.time()
	if ts-data['timestamp']>5:
		return "-1"
	return str(int(data["cube"]))

@app.route("/sbf/display-scan/<string:cube>")
def sbf_dispatch_cube(cube):
	try:
		cube = int(cube)
	except ValueError:
		return ""
	data = lookup_cube(cube)
	if data["sign"]=="SBFF":
		return sbff_logo_write_cube(data["sign_number"])
	else:
		return sbf_logo_write_cube(data["sign_number"])

def lookup_cube(cube):
	return sbf_qr.log_and_fetch(cube)

@app.route("/sbf/display")
def return_sbf_display():
	return render_template("sbf_display.html")

### Block for SBF qr code scanning
@app.route("/sbf/qr-lookup/<string:code>")
def return_qr_data(code):
	data = sbf_qr.log_and_fetch(int(code))
	return json.dumps(data)

## Pages for part search v2
##Pages for parts search
@app.route('/p', methods=["GET","POST"])
def search_parts_v2():
	if request.method == "POST":
		request_data = [request.form['{}'.format(i)] for i in xrange(5)]
		request_data = [r for r in request_data if r.strip()!='']
		request_data = [r.split(",") for r in request_data]
		request_data = [[_.lower().strip() for _ in r] for r in request_data]
		parts, labels = part_search_v2.joint_search(request_data[0], request_data[1:])
		if len(parts)==0:
			page = u"""<!DOCTYPE html>
			<html lang="en">
			  <head>
			    <meta charset="utf-8">
			    <title>Part Search</title>
				<link href='https://fonts.googleapis.com/css?family=Lato' rel='stylesheet' type='text/css'>
			    <link href='https://fonts.googleapis.com/css?family=Raleway' rel='stylesheet' type='text/css'>
				<link rel="stylesheet" href="/css/article.css">
				<style>{}</style>
			  </head>
			  <body>
			  	<a href="/flask/parts">Search Again</a>
				<p>Sorry, we couldn't find any parts that match that description. Try removing some keywords and try again!</p>
			  </body>
			</html>"""
			return page
		else:
			name = hashlib.md5(str(request_data)).hexdigest()
			path = os.path.join(app.root_path,'parts','results',name)
			d3_path = path+"_d3"
			labels_ext = [r[0]+" " for r in request_data[1:]]
			labels_ext = [labels_ext[i] + part_search_v2.parts_dict[labels[i+1]] for i in range(len(labels[1:]))]
			labels_ext = ['url']+labels_ext
			part_search_v2.write_document(parts,path,labels_ext)
			part_search_v2.write_document_d3(parts,d3_path,labels_ext)
			return redirect("/flask/p/result/{}".format(name))
	else:
		#with open(os.path.join(app.root_path,'parts','parts_page.html'),'r') as p:
		#	page = p.read()
		return render_template("p2_page.html")

@app.route("/p/result/<string:name>")
def return_results_page_v2(name):
	return render_template("p2_results_page.html", name=name)

@app.route("/p/res/f/<path:filename>")
def return_part_results_v2(filename):
	return send_from_directory(os.path.join(app.root_path,'parts','results'),filename,as_attachment=True)

@app.route("/zk")
def zk():
	return render_template("zettelkasten.html", content=zettelkasten.zk())

# set the secret key.  keep this really secret:
app.secret_key = secrets.key

if __name__ == '__main__':
	app.run()
