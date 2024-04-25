from flask import Flask, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_cors import CORS
from flask_mysqldb import MySQL
import bcrypt
import random
import string
import json
import datetime

app = Flask(__name__)
CORS(app, origins="*")
socketio = SocketIO(app)

# Configure MySQL connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'chat'

mysql = MySQL(app)

# Define a dictionary to track users' presence in rooms
user_rooms = {}

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    cursor = mysql.connection.cursor()
    query = "INSERT INTO user (username, password) VALUES (%s, %s)"
    cursor.execute(query, (username, hashed_password))
    mysql.connection.commit()
    cursor.close()

    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    cursor = mysql.connection.cursor()
    query = "SELECT password, userid FROM user WHERE username = %s"
    cursor.execute(query, (username,))
    result = cursor.fetchone()
    cursor.close()

    if result:
        hashed_password = result[0]
        userid = result[1]

        # Check password using bcrypt
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
            return jsonify({'message': 'Login successful', 'userid': userid}), 200
        else:
            return jsonify({'message': 'Invalid credentials'}), 401
    else:
        return jsonify({'message': 'User not found'}), 404

@app.route('/userlist', methods=['GET'])
def userlist():
    cursor = mysql.connection.cursor()
    query = "SELECT username, userid FROM user"
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()

    user_list = []
    for username, userid in result:
        user_list.append({'username': username, 'userid': userid})

    return jsonify(user_list)

@socketio.on('connect')
def handle_connect():
    print('A user connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('A user disconnected')

# Modify 'handle_create_or_join_room' to track user's presence in a room
@socketio.on('create_or_join_room')
def handle_create_or_join_room(data):
    user1_id = data.get('user1_id')
    user2_id = data.get('user2_id')

    cursor = mysql.connection.cursor()
    try:
        # Check if a room already exists for the two users
        query = """
            SELECT room_id FROM rooms
            WHERE (user1_id = %s AND user2_id = %s) OR (user1_id = %s AND user2_id = %s)
        """
        cursor.execute(query, (user1_id, user2_id, user2_id, user1_id))
        result = cursor.fetchone()

        if result:
            room_id = result[0]

            # Add the user to the room tracking dictionary
            if user1_id not in user_rooms:
                user_rooms[user1_id] = set()
            user_rooms[user1_id].add(room_id)

            if user2_id not in user_rooms:
                user_rooms[user2_id] = set()
            user_rooms[user2_id].add(room_id)

            # Emit existing messages to the frontend
            query = "SELECT conversation FROM messages WHERE room_id = %s"
            cursor.execute(query, (room_id,))
            existing_messages_tuple = cursor.fetchone()

            if existing_messages_tuple:
                existing_messages = json.loads(existing_messages_tuple[0])
            else:
                existing_messages = []

            emit('existing_messages', {'room_id': room_id, 'messages': existing_messages}, room=request.sid)
        else:
            # Generate a unique 6-character room ID
            room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

            # Create a new room
            query = "INSERT INTO rooms (room_id, user1_id, user2_id) VALUES (%s, %s, %s)"
            cursor.execute(query, (room_id, user1_id, user2_id))
            mysql.connection.commit()

            # Add the user to the room tracking dictionary
            if user1_id not in user_rooms:
                user_rooms[user1_id] = set()
            user_rooms[user1_id].add(room_id)

            if user2_id not in user_rooms:
                user_rooms[user2_id] = set()
            user_rooms[user2_id].add(room_id)

            # Emit empty messages to the frontend
            emit('existing_messages', {'room_id': room_id, 'messages': []}, room=request.sid)

        join_room(room_id)

        # Notify the user of the room creation
        emit('room_created', {'room_id': room_id}, room=request.sid)
    except Exception as e:
        print(f"Error creating or joining room: {e}")
    finally:
        cursor.close()

# Modify 'handle_send_message' to manage unread counts and updates
@socketio.on('send_message')
def handle_send_message(data):
    room_id = data['room_id']
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    message = data['message']

    cursor = mysql.connection.cursor()
    try:
        # Check if a conversation exists for the given sender and receiver
        query = """
            SELECT message_id, conversation FROM messages
            WHERE room_id = %s AND (
                (sender_id = %s AND receiver_id = %s) OR
                (sender_id = %s AND receiver_id = %s)
            )
        """
        cursor.execute(query, (room_id, sender_id, receiver_id, receiver_id, sender_id))
        result = cursor.fetchone()

        if result:
            existing_message_id = result[0]
            conversation = json.loads(result[1])

            # Add the new message to the conversation
            new_message = {"sender_id": sender_id, "receiver_id": receiver_id, "message": message}
            conversation.append(new_message)

            # Update the conversation in the database
            updated_conversation = json.dumps(conversation)
            update_query = "UPDATE messages SET conversation = %s, timestamp = NOW() WHERE message_id = %s"
            cursor.execute(update_query, (updated_conversation, existing_message_id))
        else:
            # Create a new message
            message_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
            new_conversation = [{"sender_id": sender_id, "receiver_id": receiver_id, "message": message}]
            conversation_json = json.dumps(new_conversation)

            # Insert the new conversation into the database
            insert_query = "INSERT INTO messages (message_id, room_id, sender_id, receiver_id, conversation, timestamp) VALUES (%s, %s, %s, %s, %s, NOW())"
            cursor.execute(insert_query, (message_id, room_id, sender_id, receiver_id, conversation_json))

        # Commit the transaction
        mysql.connection.commit()

        # Check if the receiver is in the room or not
        receiver_in_room = room_id in user_rooms.get(receiver_id, set())

        if not receiver_in_room:
            # Increase the unread count if the receiver is not in the room
            increase_unread_count(room_id, receiver_id)

        # Emit the message to the room
        emit('receive_message', data, room=room_id)

        # Emit an update event to the sender and receiver to update the user list
        update_data = {
            'room_id': room_id,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'latest_message': message,
            'unread_count': get_unread_count(sender_id, receiver_id)
        }

        # Emit to both the sender and receiver to update their user list
        emit('update_user_list', update_data, to=sender_id)
        emit('update_user_list', update_data, to=receiver_id)

    except Exception as e:
        print(f"Error sending message: {e}")
    finally:
        cursor.close()

# Function to increase unread count in the database
def increase_unread_count(room_id, receiver_id):
    cursor = mysql.connection.cursor()
    query = "UPDATE unread_messages SET unread_count = unread_count + 1 WHERE room_id = %s AND receiver_id = %s"
    cursor.execute(query, (room_id, receiver_id))
    mysql.connection.commit()
    cursor.close()

# Function to get unread count for a user in a room
def get_unread_count(room_id, receiver_id):
    cursor = mysql.connection.cursor()
    query = """
        SELECT unread_count
        FROM unread_messages
        WHERE room_id = %s AND receiver_id = %s
    """
    cursor.execute(query, (room_id, receiver_id))
    unread_count = cursor.fetchone()

    if unread_count is not None:
        return unread_count[0]
    else:
        return 0
    cursor.close()

if __name__ == '__main__':
    socketio.run(app,host='0.0.0.0' ,debug=True)
