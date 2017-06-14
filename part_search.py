from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
import sqlalchemy as sqla
import datetime
import secrets
import csv
import json

engine = sqla.create_engine(secrets.engine, echo=False)
Base = declarative_base()

part_types = [("", "None"),("mass", "Mass"),("length","Length"),("angle","Angle"),("time","Time"),
    ("money","Money"),("voltage","Voltage"),("current","Current"),("force","Force"),
    ("torque","Torque"),("speed","Speed"),("angular_speed","Angular Speed")]

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

def fetch_document_ids_by_unit_types(unit_types):
    Session = sqla.orm.sessionmaker(bind=engine)
    session = Session()
    matches = []
    q = session.query(Unit_Num.source).\
        group_by(Unit_Num.source).\
        having(sqla.and_(*[sqla.func.string_agg(Unit_Num.unit_type, ' ').like('%'+t+'%') for t in unit_types]))
    matches = q.all()
    matches = [m[0] for m in matches]
    session.close()
    return matches

def fetch_document_ids_by_text(query):
    #construct the query
    components = [sqla.or_(*[Scraped_Site.text.ilike('%{}%'.format(t.strip().lower())) for t in q[0].split(',')]) for q in query if q[0]!='']
    sql_filter = sqla.and_(*components)
    Session = sqla.orm.sessionmaker(bind=engine)
    session = Session()
    q = session.query(Scraped_Site.id).filter(sql_filter).all()
    session.close()
    q = [q_[0] for q_ in q]
    return q

def search_document_by_unit_text(query):
    pass

def search_documents(query):
    Session = sqla.orm.sessionmaker(bind=engine)
    session = Session()
    unit_types = [q[1] for q in query]
    doc_ids_by_unit = fetch_document_ids_by_unit_types(unit_types)
    doc_ids_by_text = fetch_document_ids_by_text(query)
    print len(doc_ids_by_text), len(doc_ids_by_unit), doc_ids_by_text[0], doc_ids_by_unit[0]
    doc_ids = set(doc_ids_by_unit).intersection(set(doc_ids_by_text))
    print len(doc_ids)
    matched_documents = []
    for doc_id in doc_ids:
        doc = session.query(Scraped_Site).filter(Scraped_Site.id==doc_id).all()[0]
        units = session.query(Unit_Num).filter(Unit_Num.source==doc.id).all()
        #iterate over query, checking against units and text content
        query_results = []
        query_values = []
        for q in query:
            query_texts = q[0].split(',')
            query_texts = [t.strip().lower() for t in query_texts]
            if q[1]=='':
                query_results.append(any([t in doc.text.lower() for t in query_texts]))
            else:
                unit = session.query(Unit_Num).filter(Unit_Num.source==doc.id, Unit_Num.unit_type==q[1]).all()
                vals = [u.value for u in unit]
                lower_loc = [u.loc_bottom for u in unit]
                found=False
                if q[0]!='':
                    #search radius
                    rad = 15
                    matched_units = []
                    for l in lower_loc:
                        matched_unit = False
                        for t in query_texts:
                            fragment = doc.text.lower()[max(0,l-len(t)-rad):l+1]
                            if t in fragment:
                                matched_unit = True
                                break
                        matched_units.append(matched_unit)
                    if any(matched_units):
                        found=True
                        vals=[v[0] for v in zip(vals, matched_units) if v[1]]
                else:
                    found=True
                if found:
                    query_results.append(True)
                    query_values.append(tuple(vals))
                else:
                    query_results.append(False)
        if all(query_results):
            matched_documents.append(tuple([doc.id]+query_values+[doc.url]))
    return matched_documents

def avg(d):
    return sum(d)/float(len(d))

def write_document(data, path, query, reducer=None):
    #build the csv, using average as the aggreagtor for now
    with open(path+'.csv', 'w') as csv_file:
        csv_writer = csv.writer(csv_file)
        names = [q[0]+' ('+q[1]+')' for q in query if q[1]!='']
        names = ['url']+names
        csv_writer.writerow(names)
        for d in data:
            l = [avg(x) for x in d[1:-1]]
            l = [d[-1]]+l
            csv_writer.writerow(l)
    #build the json document, using the units as keys from the query
    names = [q[0]+' ('+q[1]+')' for q in query if q[1]!='']
    names = names+['url']
    data_out = []
    for d in data:
        data_out.append({n:d for n,d in zip(names, d[1:])})
    json_data = json.dumps(data_out)
    with open(path+'.json', 'w') as json_file:
        json_file.write(json_data)
