#table to store tokens.  All we do is store the token, so we can look it up later/analyze, and do fast searches
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import aliased
import sqlalchemy as sqla
import datetime
import csv
import secrets
import json
import copy
import numpy as np
import units as Units
import keyword_extractor
import re
import itertools

engine = sqla.create_engine(secrets.engine, echo=False)
Base = declarative_base()

part_types = [("", "None"),("mass", "Mass (kg)"),("length","Length (m)"),("angle","Angle (rad)"),("time","Time (s)"),
    ("money","Money ($)"),("voltage","Voltage (V)"),("current","Current (A)"),("force","Force (N)"),
    ("torque","Torque (Nm)"),("speed","Speed (m/s)"),("angular_speed","Angular Speed (rad/s)"),("current_capacity","Current Storage (As)")]

parts_dict = {d[0]:d[1] for d in part_types}

# All the ORM classes we need
class Token(Base):
    __tablename__ = 'tokens'
    token = sqla.Column(sqla.types.Unicode(), primary_key=True)
    version = sqla.Column(sqla.Integer)

    def repr(self):
        return u"<Token(token={},version={})>".format(token,version)

class Scraped_Site(Base):
    __tablename__ = 'scraped_sites'
    id = sqla.Column(sqla.Integer,primary_key=True)
    url = sqla.Column(sqla.String)
    source = sqla.Column(sqla.String(2048))
    date_added = sqla.Column(sqla.types.DateTime())
    version = sqla.Column(sqla.Integer)
    raw = sqla.Column(sqla.types.Unicode())
    text = sqla.Column(sqla.types.Unicode())

    def repr(self):
        return "<Scraped_Site(url={})>".format(url)

class Unit_Num(Base):
    __tablename__ = 'unit_nums'
    id = sqla.Column(sqla.Integer,primary_key=True)
    source = sqla.Column(sqla.Integer, sqla.ForeignKey('scraped_sites.id'))
    date_added = sqla.Column(sqla.types.DateTime())
    raw = sqla.Column(sqla.types.Unicode())
    value = sqla.Column(sqla.types.Float())
    loc_bottom = sqla.Column(sqla.Integer)
    loc_top = sqla.Column(sqla.Integer)
    unit_type = sqla.Column(sqla.String(100))

    def repr(self):
        return "<Unit_Num(val={},type={})>".format(url,unit_type)

class Unit_Text(Base):
    __tablename__ = 'unit_texts'
    id = sqla.Column(sqla.Integer,primary_key=True)
    unit = sqla.Column(sqla.Integer, sqla.ForeignKey('unit_nums.id'))
    document = sqla.Column(sqla.Integer, sqla.ForeignKey('scraped_sites.id'))
    text = sqla.Column(sqla.types.Unicode())

    def repr(self):
        return "<Unit_Text(id={})>".format(id)

class Word(Base):
    __tablename__ = 'words'
    word = sqla.Column(sqla.types.Unicode(), sqla.ForeignKey('tokens.token'), index=True)
    doc = sqla.Column(sqla.Integer, sqla.ForeignKey('scraped_sites.id'), primary_key=True)
    loc = sqla.Column(sqla.Integer, primary_key=True)
    force = sqla.Column(sqla.Integer)
    mass = sqla.Column(sqla.Integer)
    angle = sqla.Column(sqla.Integer)
    length = sqla.Column(sqla.Integer)
    time = sqla.Column(sqla.Integer)
    money = sqla.Column(sqla.Integer)
    voltage = sqla.Column(sqla.Integer)
    current = sqla.Column(sqla.Integer)
    torque = sqla.Column(sqla.Integer)
    speed = sqla.Column(sqla.Integer)
    angular_speed = sqla.Column(sqla.Integer)
    current_capacity = sqla.Column(sqla.Integer)
    number = sqla.Column(sqla.Integer)

    def repr(self):
        return "<Word(word={},doc={})>".format(word,doc)

def get_data(keywords, win_min, win_max):
    """Fetch unit data for the window around the given keywords"""
    Session = sqla.orm.sessionmaker(bind=engine)
    session = Session()
    root_word = aliased(Word)
    res = session.query(
                sqla.func.max(Word.doc),
                sqla.func.max(root_word.loc),
                sqla.func.array_agg(Word.word),
                sqla.func.array_agg(Word.loc),
                sqla.func.array_agg(Word.force),
                sqla.func.array_agg(Word.mass),
                sqla.func.array_agg(Word.angle),
                sqla.func.array_agg(Word.length),
                sqla.func.array_agg(Word.time),
                sqla.func.array_agg(Word.money),
                sqla.func.array_agg(Word.voltage),
                sqla.func.array_agg(Word.current),
                sqla.func.array_agg(Word.torque),
                sqla.func.array_agg(Word.speed),
                sqla.func.array_agg(Word.angular_speed),
                sqla.func.array_agg(Word.current_capacity),
                sqla.func.array_agg(Word.number))\
                    .join(root_word, Word.doc==root_word.doc)\
                    .filter(
                        sqla.or_(
                            *[root_word.word==k for k in keywords]))\
                    .filter(
                        sqla.and_(
                            Word.loc>=root_word.loc+win_min,
                            Word.loc<=root_word.loc+win_max))\
                    .group_by(root_word.doc, root_word.loc)\
                    .all()
    session.close()
    return res

def pad_numbers(l, r, win_min, win_max):
    """Pad the {0,1} vectors returned by get_data with zeros, so all vectors are the same length,
    even if cut off by the document"""
    l_ = [0]*(abs(win_min)-len(l))+l
    r_ = r+[0]*(abs(win_max+1)-len(r))
    full = l_+r_
    return full

def join_vectors(left, right, doc_urls, win_min=-3, win_max=20):
    """In order to pad the unit vectors appropriatly, we need to fetch the left and right sides of the vector separatly.
    This function will take the left and right values, as well a a dictionary mapping urls to indicies (for fast lookups),
    and return a list of tuples containing the document url, the raw text as a list of tokens, and the full unit array"""
    l_dict = {tuple(l[:2]):l[2:] for l in left}
    #join the vectors, including padding
    out = []
    for r_full in right:
        url = doc_urls[r_full[0]]
        r = r_full[2:]
        if tuple(r_full[:2]) in l_dict:
            l = l_dict[tuple(r_full[:2])]
        else:
            l = [[] for _ in xrange(len(left[0][2:]))]
        txt_l = l[0]
        txt_l = ["***"]*(abs(win_min)-len(txt_l))+txt_l
        txt_r = r[0]
        txt_r = txt_r+["***"]*(abs(win_max+1)-len(txt_r))
        txt = txt_l+txt_r
        nums_r = [pad_numbers(l[i], r[i], win_min, win_max) for i in xrange(2, len(r))]
        nums = np.array(nums_r)
        nums = np.transpose(nums)
        out.append((url, txt, nums))
    return out

def get_url_dict():
    Session = sqla.orm.sessionmaker(bind=engine)
    session = Session()
    doc_urls = session.query(Scraped_Site.id, Scraped_Site.url).all()
    session.close()
    url_dict = {u[0]:u[1] for u in doc_urls}
    return url_dict

def get_most_common_unit(data):
    """Return the most common unit type in the data, excluding raw numbers as a type (presumes raw numbers are at end)"""
    vs = [np.sum(d[2], axis=0) for d in data]
    vs2 = np.sum(np.array(vs), axis=0)
    #print vs2
    mi = np.argmax(vs2[:-1])
    ma = vs2[mi]
    return mi, ma

def extract_tokens_cond(datum, cov, inds):
    """extract the relevant tokens from a unit vector, conditioned on the desired unit types"""
    vec = condition_weak(inds, datum[2])
    res = np.multiply(np.dot(cov, vec), vec)
    tokens = []
    for i in xrange(len(datum[1])):
        if res[i]>0:
            tokens.append(datum[1][i])
    return tokens

def condition_weak(inds, vec):
    """Given the unit indicies we care about, fold the vector row-wise, setting the value to 1 iff only the desired units
    appear in that token, else 0"""
    data = []
    for row in vec:
        val = 0.0
        #print inds, row
        if any([row[i]==1 for i in inds]):
            val = 1.0
        #for i, v in enumerate(row):
            #if i in inds and v==1:
            #    continue
            #elif i not in inds and v==0:
            #    continue
            #else:
            #    val = 0.0
        data.append(val)
    return np.array(data)

def condition(inds, vec):
    """Given the unit indicies we care about, fold the vector row-wise, setting the value to 1 iff only the desired units
    appear in that token, else 0"""
    data = []
    for row in vec:
        val = 1.0
        for i, v in enumerate(row):
            if i in inds and v==1:
                continue
            elif i not in inds and v==0:
                continue
            else:
                val = 0.0
        data.append(val)
    return np.array(data)

def build_cov_cond(vecs, inds):
    """Build the covariance matrix of the data, after conditioning on the unit data"""
    vs = [condition_weak(inds, v) for v in vecs]
    vl = len(vs[0])
    cvecs = np.concatenate([v.reshape(1,vl) for v in vs])
    cov = np.cov(cvecs.transpose())
    return cov

def extract_and_normalize(vec, unit, number_position):
    """Given a text vector, unit, and number position relative to the unit, return the normalized values affiliated with that unit"""
    Number = Units.Number
    unit_string = r"(\W|[0-9])(?P<unit>"+unit.regex+r")(\W|[0-9])"
    number_string = r"(?P<num>"+Number+r")"
    #print search_string
    unit_regex = re.compile(unit_string)
    number_regex = re.compile(number_string)
    #first, get the indicies of potential unit matches
    units = []
    for i, v in enumerate(vec):
        for m in unit_regex.finditer(" "+v.lower()+" "):
            #print m.group(0)
            raw = m.group(0)
            span = m.span()
            raw_unit = m.group('unit')
            converter = unit.convert(raw_unit)
            units.append((i, span[0], raw_unit, converter))
    vals = []
    for i, v in enumerate(vec):
        for m in number_regex.finditer(" "+v.lower()+" "):
            #print m.group(0)
            raw = m.group(0)
            span = m.span()
            raw_num = float(m.group('num').replace(",",""))
            #locate the correct unit to affiliate with the number
            num_unit = None
            for j, u in enumerate(units):
                if number_position == "before":
                    if (j>0 and u[0]>=i and units[j-1][0]<i) or (j==0 and u[0]>=i):
                        val = raw_num*u[3]
                        vals.append(val)
                        break
                elif number_position == "after":
                    if (j<len(units)-1 and u[0]<=i and units[j+1][0]>i):
                        val = raw_num*u[3]
                        vals.append(val)
                        break
                    elif (j==len(units)-1 and u[0]<=i):
                        val = raw_num*u[3]
                        vals.append(val)
                        break
    return vals

def search(keywords):
    """Executes a search over the database for the given keywords, returning the assumed unit and a list of (url, data)
    tuples"""
    r = get_data(keywords, 0, 20)
    l = get_data(keywords, -3, -1)
    url_dict = get_url_dict()
    data = join_vectors(l, r, url_dict, -3, 20)
    r_list = [(keyword_extractor.make_regex(u[0].regex), u[1]) for u in Units.exported]
    r_list += [(re.compile(Units.Number), 'number')]
    unit_names = {r[1].lower().strip():i for i, r in enumerate(r_list)}
    ui, uc = get_most_common_unit(data)
    for k in keywords:
        if k.lower().strip() in unit_names:
            ui = unit_names[k.lower().strip()]
    inds = [ui, 12] #add 12 so we capture numbers
    cov = build_cov_cond([d[2] for d in data], inds)
    out = []
    for datum in data:
        tokens = extract_tokens_cond(datum, cov, inds)
        res = extract_and_normalize(tokens, Units.exported[ui][0], Units.exported[ui][2])
        out.append((datum[0], tuple(res)))
    return (Units.exported[ui][1], out)

def joint_search(page_filter, keywords):
    """execute a search over multiple keywords sets, filtering pages for another set of keywords,
    and sensibly merge the results"""
    Session = sqla.orm.sessionmaker(bind=engine)
    session = Session()
    db_query = session.query(Scraped_Site.url)\
                    .filter(
                        sqla.or_(
                            *[Scraped_Site.text.ilike(u'%{}%'.format(f)) for f in page_filter]))
    pages = db_query.all()
    session.close()
    pages = [p[0] for p in pages]
    #for each keyword, extract all the relevant documents
    results = []
    for ks in keywords:
        results.append(search(ks))
    #build a dict for each keyword for fast lookup of properties
    result_dicts = []
    for res in results:
        rd = {}
        for i, r in enumerate(res[1]):
            if r[0] not in rd:
                rd[r[0]] = [i]
            else:
                rd[r[0]].append(i)
        result_dicts.append(copy.deepcopy(rd))
    #build an array of the results
    parts = []
    for url in pages:
        if all([url in rd for rd in result_dicts]):
            nums_iter = itertools.product(*[rd[url] for rd in result_dicts])
            for n in nums_iter:
                #print n
                res = [results[i][1][j][1] for i, j in enumerate(n)]
                out = tuple([url]+res)
                if all([len(o)>0 for o in out]):
                    parts.append(tuple([url]+res))
    labels = ["url"]+[r[0] for r in results]
    return parts, labels

def size_cols(data):
    """calculate the maximum width of each column"""
    lens = [[] for d in data[0][1:]]
    for d in data:
        for i, ds in enumerate(d[1:]):
            lens[i].append(len(ds))
    maxs = [max(l) for l in lens]
    return maxs

def write_document(data, path, labels, reducer=None):
    #build the csv, using average as the aggreagtor for now
    sizes = size_cols(data)
    def pad_empty(sizes, row):
        #print sizes, row
        out = []
        for i, r in enumerate(row):
            out = out+r+[""]*(sizes[i]-len(r))
        return out
    with open(path+'.csv', 'w') as csv_file:
        csvw = csv.writer(csv_file)
        row = ["url"]+pad_empty(sizes, [[l] for l in labels[1:]])
        csvw.writerow(row)
        for d in data:
            row = [d[0]]+pad_empty(sizes, [[abs(_k) for _k in k] for k in d[1:]])
            csvw.writerow(row)

def write_document_d3(data, path, labels):
    with open(path+'.csv', 'w') as csv_file:
        csvw = csv.writer(csv_file)
        row = ["url"]
        for l in labels[1:]:
            row = row + [l+" (min)", l+" (max)"]
        csvw.writerow(row)
        for d in data:
            row = [d[0]]
            for k in d[1:]:
                _k = [abs(x) for x in k]
                row = row+[min(_k), max(_k)]
            csvw.writerow(row)
