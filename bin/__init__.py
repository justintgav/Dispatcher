from flask import Flask
from flask import jsonify
from flask.ext.mysql import MySQL
import bin.sms.send_sms
app = Flask(__name__)


#MySQL Connection
mysql = MySQL()
 
# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'dispatcher'
app.config['MYSQL_DATABASE_PASSWORD'] = 'dispatcher'
app.config['MYSQL_DATABASE_DB'] = 'dispatcher'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)
conn = mysql.connect()
cursor = conn.cursor()


@app.route("/")
def hello():
        return "Hello World!"

@app.route("/create_job")
def create_job():
	#TODO grab info from post request here, throw into correct vars
	#merchant ID is the only thing that is required, rest just pass in empty string if you don't want to worry about it for now
	_merchID = 1
	_jobTitle = 'My Job'
	_jobDesc = 'Job Description'
	_fromLoc = '123 Wallaby Lane'
	_toLoc = '567 Pizza Pls'
	_businessContactPhone = '12345670962'
	
	#call database stored proc
	#CALL `dispatcher`.`create_job`(<{IN p_merch_id CHAR(32)}>, <{IN p_title VARCHAR(64)}>, <{IN p_desc VARCHAR(256)}>, <{IN p_from_loc VARCHAR(256)}>, <{IN p_to_loc VARCHAR(256)}>, <{IN p_bus_phone CHAR(15)}>);
	cursor.callproc('create_job',(_merchID,_jobTitle,_jobDesc,_fromLoc,_toLoc,_businessContactPhone))
	
	data = cursor.fetchall()
 
	if len(data) is 0:
		return "ERROR: Empty Response"
	if data[0] is 'error':
		return data[1]
	
	
	res = ""
	for row in data:
		# row will contain a phone number that needs to recieve message. literally just do
		# sms.send_sms.send(row)
		res = res + str(row)
	
	#commit changes to DB
	conn.commit()
	
	return res 


@app.route("/receive_text", methods=['Get', 'Post'])
def receive_text():
	return "receive"

if __name__ == "__main__":
        app.run(debug=True)

