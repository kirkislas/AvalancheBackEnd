from sqlalchemy import Column, Integer, String, Float
from database import Base


class Accident(Base):
    __tablename__ = "accidents_silver"

    id = Column(Integer, primary_key=True, index=True)

    source_id = Column(String, unique=True, index=True, nullable=False)

    season = Column(String(50))
    date = Column(String(10))          # YYYY-MM-DD
    display_date = Column(String(10))  # MM-DD-YYYY

    state = Column(String(50))
    location = Column(String)

    summary_description = Column(String)
    full_description = Column(String)

    fatalities = Column(Integer)

    latitude = Column(Float)
    longitude = Column(Float)

    refined_location = Column(String)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
