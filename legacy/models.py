from sqlalchemy import Column, Float, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

Base = declarative_base()

class Users(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key = True)
    firstName = Column(String(80), nullable = True)
    lastName = Column(String(80), nullable = True)
    genre = Column(String(6), nullable = True)
    dateOfBirth = Column(Date, nullable = True)
    username = Column(String(20), nullable = False)
    password = Column(String(80), nullable = False)
    
    @property
    def serialize(self):
       return {
            'id': self.id,
            'username': self.username,
            'firstName': self.firstName,
            'lastName' : self.lastName,
            'genre' : self.genre,
            'dateOfBirth' : self.dateOfBirth
       }

class Measurements(Base):
    __tablename__ = 'measurement'

    id = Column(Integer, primary_key = True)
    userId = Column(Integer, nullable = False)
    measurementDate = Column(Date, nullable = False)
    height = Column(Float, nullable = True)
    weight = Column(Float, nullable = True)
    fatTotal = Column(Float, nullable = True)
    bodyMass = Column(Float, nullable = True)
    fatVisceral = Column(Integer, nullable = True)
    waistline = Column(Float, nullable = True)
    
    @property
    def serialize(self):
       return {
            'id': self.id,
            'measurementDate': self.measurementDate,
            'height' : self.height,
            'weight' : self.weight,
            'fatTotal' : self.fatTotal,
            'bodyMass' : self.bodyMass,
            'fatVisceral' : self.fatVisceral,
            'waistline' : self.waistline
       }
 

engine = create_engine('mysql://bdimensions:fatty@localhost/bdimensions')
#engine = create_engine('sqlite:///bdimension.db')
Base.metadata.create_all(engine)
