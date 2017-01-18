import json
import calendar
import datetime
import time
import secrets

from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sqla

### Define ORM
Base = declarative_base()
engine = sqla.create_engine(secrets.engine, echo=False)

class Event(Base):
    __tablename__ = 'ferris_events'
    id = sqla.Column(sqla.Integer,primary_key=True)
    event = sqla.Column(sqla.types.Unicode())
    timestamp = sqla.Column(sqla.types.DateTime())
    value = sqla.Column(sqla.types.Float)
    text = sqla.Column(sqla.types.Unicode())

def get_ferris_data(sensor, start_time):
    Session = sqla.orm.sessionmaker(bind=engine)
    session = Session()
    events = session.query(Event).filter(sqla.and_(Event.event == unicode(sensor), Event.timestamp > start_time)).all()
    #construct data to return
    data = []
    for e in events:

        t = int(time.mktime(e.timestamp.timetuple()))
        data.append({'name':e.event, 'time':t, 'value':e.value})
    return data
