from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_sock import Sock
from influxdb_client_3 import InfluxDBClient3
import os

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()
sock = Sock()



# Global Influx Client
influx_client = InfluxDBClient3(
    host=os.environ.get('INFLUX_HOST', "http://localhost:8181"),
    token=os.environ.get('INFLUX_TOKEN', "apiv3_CgOaF6faKN0zISCCoGE6oxg2bBAxfvg9HSEnZ1F-AXn3hlV7hlVeFEVlu30_GKcKtkAm8r0ClZGwHAuULVAsuA"),
    org=os.environ.get('INFLUX_ORG', "YOUR_ORG"),
    database=os.environ.get('INFLUX_DATABASE', "sensor_data_db")
)