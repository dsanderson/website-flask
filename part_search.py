from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
import sqlalchemy as sqla
import datetime
import secrets
import csv
import json

engine = sqla.create_engine(secrets.engine, echo=False)
Base = declarative_base()

part_types = [("", "None"),("mass", "Mass (kg)"),("length","Length (m)"),("angle","Angle (rad)"),("time","Time (s)"),
    ("money","Money ($)"),("voltage","Voltage (V)"),("current","Current (A)"),("force","Force (N)"),
    ("torque","Torque (Nm)"),("speed","Speed (m/s)"),("angular_speed","Angular Speed (rad/s)"),("current_capacity","Current Storage (As)")]

parts_dict = {d[0]:d[1] for d in part_types}

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

def fetch_document_ids_by_query(query):
    Session = sqla.orm.sessionmaker(bind=engine)
    session = Session()
    db_query = session.query(Scraped_Site.id, Scraped_Site.url)
    #units_query = session.query(Unit_Num).join(Unit_Text).filter(Unit_Num.date_added > datetime.datetime(2017, 9, 1)).filter(Unit_Num.source==Scraped_Site.id).filter(Unit_Text.unit==Unit_Num.id)
    #TODO: return unit text queries (for bearings, etc.), need to fix the unit_num.id portion of unit_texts
    units_query = session.query(Unit_Num).filter(Unit_Num.date_added > datetime.datetime(2017, 9, 1)).filter(Unit_Num.source==Scraped_Site.id)
    for i, q in enumerate(query):
        keywords = [t.strip().lower() for t in q[0].split(',')]
        if q[1]=='':
            db_query = db_query.filter(sqla.or_(*[Scraped_Site.text.ilike(u'%{}%'.format(t)) for t in keywords]))
        else:
            if q[0] == '':
                db_query = db_query.filter(units_query.filter(Unit_Num.unit_type==q[1]).exists())
            else:
                raise NotImplemented
                #db_query = db_query.filter(units_query.filter(Unit_Num.unit_type==q[1]).filter(sqla.or_(*[sqla.and_(Unit_Text.unit==Unit_Num.id, Unit_Text.text.ilike(u'%{}%'.format(t))) for t in keywords])).exists())
        #if i>0:
        #    db_query = db_query.filter(Scraped_Site.id.in_([q_[0] for q_ in qs]))
    res = db_query.order_by(Scraped_Site.id.desc()).all()
    session.close()
    return res

def fetch_document_data(doc_ids, query):
    Session = sqla.orm.sessionmaker(bind=engine)
    session = Session()
    data = [tuple([d[1] for d in doc_ids])]
    ids = [d[0] for d in doc_ids]
    for q in query:
        if q[1]!='':
            keywords = [t.strip().lower() for t in q[0].split(',')]
            #db_query = session.query(Scraped_Site.id, sqla.func.array_agg(Unit_Num.value)).join(Unit_Num).join(Unit_Text).filter(Scraped_Site.id==Unit_Num.source).filter(Unit_Text.unit==Unit_Num.id).filter(Unit_Text.document==Scraped_Site.id).filter(Unit_Num.unit_type==q[1]).filter(sqla.or_(*[sqla.and_(Unit_Text.unit==Unit_Num.id, Unit_Text.text.ilike('%{}%'.format(t))) for t in keywords])).filter(Scraped_Site.id.in_(ids)).group_by(Scraped_Site.id)
            #TODO fix unit_text part
            db_query = session.query(Scraped_Site.id, sqla.func.array_agg(Unit_Num.value)).join(Unit_Num).filter(Unit_Num.date_added > datetime.datetime(2017, 9, 1)).filter(Scraped_Site.id==Unit_Num.source).filter(Unit_Num.unit_type==q[1]).filter(Scraped_Site.id.in_(ids)).group_by(Scraped_Site.id)
            vals = db_query.order_by(Scraped_Site.id.desc()).all()
            vals = [v[1] for v in vals]
            data.append(tuple(vals))
    session.close()
    return zip(*data)

def search_documents(query):
    ms = fetch_document_ids_by_query(query)
    docs = fetch_document_data(ms, query)
    return docs

def avg(d):
    try:
        return sum(d)/float(len(d))
    except:
        return d

def write_document(data, path, query, reducer=None):
    #build the csv, using average as the aggreagtor for now
    with open(path+'.csv', 'w') as csv_file:
        csv_writer = csv.writer(csv_file)
        names = ['url']
        for q in query:
            if q[1]!='':
                if q[0]!='':
                    names.append(q[0]+' ('+parts_dict[q[1]]+')')
                else:
                    names.append(parts_dict[q[1]])
        csv_writer.writerow(names)
        for d in data:
            l = [avg(x) for x in d[1:]]
            l = [d[0]]+l
            csv_writer.writerow(l)
    #build the json document, using the units as keys from the query
    data_out = []
    for d in data:
        data_out.append({n:d for n,d in zip(names, d[1:])})
    json_data = json.dumps(data_out)
    with open(path+'.json', 'w') as json_file:
        json_file.write(json_data)
