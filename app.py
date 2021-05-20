from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect    
import time
import random
import math
import serial # pre arduino connection

async_mode = None

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

ser = serial.Serial('/dev/ttyS1', 9600)
ser.flushInput()


def background_thread(args):
    count = 0             
    while True:
        val = dict(args).get('val')
        PID = dict(args).get('PID')
        
        print(args)

        socketio.sleep(0.2)
        
        count += 1
        
        if(ser.in_waiting > 0):
            data = ser.readline().decode('ascii')
        else:
            data = 0        
        
        if val:
            socketio.emit('my_response', {'data': data, 'count': count}, namespace='/test')
        

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@socketio.on('my_event', namespace='/test')
def test_message(message):   
    session['receive_count'] = session.get('receive_count', 0) + 1 
    session['PID'] = message['value']
    print(message)
    print(message['value'])
    temp = "<"+message['value']+">"
    print(str(temp).encode('utf-8'))    
    ser.write(str(temp).encode('utf-8')) # odosielanie PID a Setpoint do Arduina
    #TODO: ulozit message['value'] do databazy + voltage ?
 
@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()

@socketio.on('connect', namespace='/test')
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