from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect    
import time
import random
import math
import serial # pre arduino connection
import MySQLdb    
import configparser as ConfigParser

async_mode = None

app = Flask(__name__)

config = ConfigParser.ConfigParser()   # DP stuff
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')
print(myhost)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

ser = serial.Serial('/dev/ttyS1', 9600)
ser.flushInput()


def background_thread(args):
    count = 0
    dataCounter = 0
    dataCounter2 = 0
    dataList = []
    dataList2 = []  
    db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
    
    Kp = 1   #default values
    Ki = 0.7
    Kd = 0
    Setpoint = 500
     
    while True:        
        if args:
          val = dict(args).get('val') 
          dbV = dict(args).get('db_value')
          fileV = dict(args).get('file_value')
            
          if dict(args).get('Kp') != None:  # pozriem sa ci nemam null hodnoty ak nie tak prepisem
              Kp = dict(args).get('Kp')
              Kd = dict(args).get('Kd')
              Ki = dict(args).get('Ki')
              Setpoint = dict(args).get('Setpoint')   
        else:          
          dbV = 'nieco'
          fileV = 'nieco'
          
        #val = dict(args).get('val')       
        #dbV = dict(args).get('db_value')
        #fileV = dict(args).get('file_value')
        
        print(args)

        socketio.sleep(0.2)
        
        count += 1        
        
        if(ser.in_waiting > 0):
            data = ser.readline().decode('ascii')  
        else:
            data = 0            
        
        if val:  # if data start
            socketio.emit('my_response', {'data': data, 'count': count}, namespace='/test')
            
            if dbV == 'start':   # if db start/stop then send voltage data to DB
                data = data.replace("\n","")
                data = data.replace("\r","")
                dataCounter +=1
                dataDict = {
                    "P": Kp,
                    "I": Ki,
                    "D": Kd,
                    "Setpoint": Setpoint,
                    "voltage": data,
                    "count": dataCounter}
                dataList.append(dataDict)
            else:
                if len(dataList)>0:                    
                    fuj = str(dataList).replace("'", "\"")
                    print("Zapisujem do databazy")
                    cursor = db.cursor()
                    cursor.execute("SELECT MAX(id) FROM zfinal")
                    maxid = cursor.fetchone()
                    cursor.execute("INSERT INTO zfinal (id, data) VALUES (%s, %s)", (maxid[0] + 1, fuj))
                    db.commit()
                dataList = []
                dataCounter = 0
                
            if fileV == 'start':   # if db start/stop then send voltage data to DB
                data = data.replace("\n","")
                data = data.replace("\r","")
                dataCounter2 +=1
                dataDict = {
                    "P": Kp,
                    "I": Ki,
                    "D": Kd,
                    "Setpoint": Setpoint,
                    "voltage": data,
                    "count": dataCounter2}
                dataList2.append(dataDict)
            else:
                if len(dataList2)>0:                    
                    fuj2 = str(dataList2).replace("'", "\"")
                    print("Zapisujem do suboru")
                    f = open("voltageData.txt", "a")
                    f.write(fuj2)
                    f.write("\n")
                    f.close()                    
                dataList2 = []
                dataCounter2 = 0    
                
    db.close()                 
            
            
@socketio.on('db_event', namespace='/test')
def db_message(message):   
#    session['receive_count'] = session.get('receive_count', 0) + 1
    print(message)
    session['db_value'] = message['value']
    
@socketio.on('file_event', namespace='/test')
def file_message(message):   
#    session['receive_count'] = session.get('receive_count', 0) + 1
    print(message)
    session['file_value'] = message['value']   

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@app.route('/dbtab', methods=['GET', 'POST'])
def dbtab():
    return render_template('dbtab.html', async_mode=socketio.async_mode)

@socketio.on('my_event', namespace='/test')
def test_message(message):   
    session['receive_count'] = session.get('receive_count', 0) + 1 
    print(message)
    print(message['value'])
    temp = "<"+message['value']+">"    
    print(str(temp).encode('utf-8'))    
    ser.write(str(temp).encode('utf-8')) # odosielanie PID a Setpoint do Arduina
      
    # parser a ukladam si posielane PID do globalnej premennej odkial si vsetko zapisujem do db
    my_string = temp
    # split the string at 'a'
    step_0 = my_string.split('a')

    step_1 = step_0[0]
    Ki = step_0[1]
    Kd = step_0[2]
    Setpoint = step_0[3]

    # split the string at '<'
    step_10 = step_1.split('<')
    Kp = step_10[1]
    
    session['Kp']=Kp
    session['Ki']=Ki
    session['Kd']=Kd
    session['Setpoint']=Setpoint
    print(Kp)
    print(Ki)
    print(Kd)
    print(Setpoint)
    
 
@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()

@socketio.on('connect_request', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())
    emit('my_response', {'data': 'Connected', 'count': 0})

@socketio.on('start_request', namespace='/test')
def start():   
    session['val'] = 1
    print(session['val'])
    
@socketio.on('stop_request', namespace='/test')
def stop():
    session['val'] = 0
    print(session['val'])

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)