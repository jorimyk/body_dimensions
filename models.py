from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

Base = declarative_base()

class Users(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key = True)
    firstName = Column(String(80), nullable = False)
    lastName = Column(String(80), nullable = False)
    genre = Column(String(6), nullable = False)
    dateOfBirth = Column(String(10), nullable = False)
    
    @property
    def serialize(self):
       return {
            'id': self.id,
            'firstName': self.firstName,
            'lastName' : self.lastName,
            'genre' : self.genre,
            'dateOfBirth' : self.dateOfBirth
       }

class UserData(Base):
    __tablename__ = 'user_data'

    id = Column(Integer, primary_key = True)
    userId = Column(Integer, nullable = False)
    measurementDate = Column(String(10), nullable = False)
    height = Column(Integer, nullable = True)
    weight = Column(Integer, nullable = True)
    fatTotal = Column(Integer, nullable = True)
    bodyMass = Column(Integer, nullable = True)
    fatVisceral = Column(Integer, nullable = True)
    bodyMass = Column(Integer, nullable = True)
    waistline = Column(Integer, nullable = True)
    
    @property
    def serialize(self):
       return {
            'id': self.id,
            'userId': self.userId,
            'measurementDate': self.measurementDate,
            'height' : self.height,
            'weight' : self.weight,
            'fatTotal' : self.fatTotal,
            'bodyMass' : self.bodyMass,
            'fatVisceral' : self.fatVisceral,
            'waistline' : self.waistline
       }
 


engine = create_engine('sqlite:///bdimension.db')
Base.metadata.create_all(engine)
