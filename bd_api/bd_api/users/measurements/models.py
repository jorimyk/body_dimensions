from bd_api import db

from datetime import datetime

class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    measurementDate = db.Column(db.Date, nullable = False)
    height = db.Column(db.Float, nullable = True)
    weight = db.Column(db.Float, nullable = True)
    fatTotal = db.Column(db.Float, nullable = True)
    bodyMass = db.Column(db.Float, nullable = True)
    fatVisceral = db.Column(db.Integer, nullable = True)
    waistline = db.Column(db.Float, nullable = True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


    @property
    def serialize(self):
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'timestamp': self.timestamp.isoformat(),
            'measurementDate': self.measurementDate.isoformat(),
            'height' : self.height,
            'weight' : self.weight,
            'fatTotal' : self.fatTotal,
            'bodyMass' : self.bodyMass,
            'fatVisceral' : self.fatVisceral,
            'waistline' : self.waistline
        }

    measurement_keys = ['height',
                        'weight',
                        'fatTotal',
                        'bodyMass',
                        'fatVisceral',
                        'waistline']
