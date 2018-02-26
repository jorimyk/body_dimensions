from bd_api import db

from datetime import datetime

class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    measurementDate = db.Column(db.Date, nullable = False)
    height = db.Column(db.Float, nullable = True)
    weight = db.Column(db.Float, nullable = True)
    fatTotal = db.Column(db.Float, nullable = True)
    bodyMass = db.Column(db.Float, nullable = True)
    fatVisceral = db.Column(db.Integer, nullable = True)
    waistline = db.Column(db.Float, nullable = True)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'timestamp': self.timestamp,
            'measurementDate': self.measurementDate,
            'height' : self.height,
            'weight' : self.weight,
            'fatTotal' : self.fatTotal,
            'bodyMass' : self.bodyMass,
            'fatVisceral' : self.fatVisceral,
            'waistline' : self.waistline
        }

    measurement_keys = ['measurementDate',
                        'height',
                        'weight',
                        'fatTotal',
                        'bodyMass',
                        'fatVisceral',
                        'waistline']
