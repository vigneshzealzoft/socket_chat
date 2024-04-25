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
    query = "SELECT password ,userid FROM user WHERE username = %s"
    cursor.execute(query, (username,))
    result = cursor.fetchone()
    cursor.close()
    print(result)

    if result:
        hashed_password = result[0]  # Get the hashed password from the database
        # Convert the hashed password to bytes format
        userid=result[1]

        hashed_password_bytes = hashed_password.encode('utf-8')
        
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password_bytes):
            return jsonify({'message': 'Login successful'},userid), 200
        else:
            return jsonify({'message': 'Invalid credentials'}), 401
    else:
        return jsonify({'message': 'User not found'}), 404
    

@app.route('/userlist', methods=['GET'])
def userlist():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT username, userid FROM user ")
    result = cursor.fetchall()
    cursor.close()
    print(result)
    
    user_list = []
    for result in result:
        username, userid = result
        user_list.append({
            'username': username,
            'userid': userid
        })
    
    # Return the list of users as a JSON response
    return jsonify(user_list)



@socketio.on('connect')
def handle_connect():
    print('A user connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('A user disconnected')

@socketio.on('create_or_join_room')
def handle_create_or_join_room(data):
    print(data)
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
            
            # Fetch existing messages from the conversation column
            query = """
                SELECT conversation
                FROM messages
                WHERE room_id = %s
            """
            
            # Execute the query to fetch messages for the given room_id
            cursor.execute(query, (room_id,))
            
            # Fetch the result of the query as a list of tuples
            existing_messages_tuple = cursor.fetchall()
            
            # Extract and parse the existing messages
            if existing_messages_tuple:
                # Assuming there should be one tuple in the list for the given room_id
                existing_messages = existing_messages_tuple[0][0]
                
                # Parse the JSON data if needed (assuming messages are stored as JSON strings)
                messages = json.loads(existing_messages)
                print(messages)
            else:
                messages = []  # If no messages found, use an empty list
            
            # Emit existing messages to the frontend
            emit('existing_messages', {'room_id': room_id, 'messages': messages}, room=request.sid)

        else:
            
            # Generate a unique 6-character room ID consisting of alphabets and numbers
            room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            # Create a new room with the unique room ID
            print(room_id)
            query = "INSERT INTO rooms (room_id, user1_id, user2_id) VALUES (%s, %s, %s)"
            cursor.execute(query, (room_id, user1_id, user2_id))
            mysql.connection.commit()
            print(f"New room created with room_id: {room_id}")

        # Join the room
        join_room(room_id)

        # Notify the user
        emit('room_created', {'room_id': room_id}, room=request.sid)
    except Exception as e:
        print(f"Error creating or joining room: {e}")
    finally:
        cursor.close()

@socketio.on('mark_as_read')
def handle_mark_as_read(data):
    room_id = data['room_id']
    receiver_id = data['receiver_id']
    
    # Update the unread messages to be marked as read
    cursor = mysql.connection.cursor()
    query = """
        UPDATE messages
        SET conversation = JSON_SET(conversation, '$.unread', false)
        WHERE room_id = %s AND receiver_id = %s AND JSON_EXTRACT(conversation, '$.unread') = true
    """
    cursor.execute(query, (room_id, receiver_id))
    mysql.connection.commit()
    
    # Emit an update event to the frontend to reset the unread count
    emit('update_user_list', {'room_id': room_id, 'receiver_id': receiver_id, 'unread_count': 0}, to=receiver_id)

def get_unread_count(sender_id, receiver_id):
    cursor = mysql.connection.cursor()
    # Use room_id to get the unread count for the receiver from unread_messages
    query = """
        SELECT unread_count
        FROM unread_messages
        WHERE user_id = %s AND room_id IN (
            SELECT room_id
            FROM rooms
            WHERE (user1_id = %s AND user2_id = %s) OR (user1_id = %s AND user2_id = %s)
        )
    """
    cursor.execute(query, (receiver_id, sender_id, receiver_id, receiver_id, sender_id))
    result = cursor.fetchone()
    cursor.close()

    if result:
        # Return the unread count if it exists
        return result[0]
    else:
        # If there is no unread count, return 0
        return 0


@socketio.on('send_message')
def handle_send_message(data):
    room_id = data['room_id']
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    message = data['message']

    cursor = mysql.connection.cursor()
    try:
        # Check if a conversation already exists for the given sender and receiver (in either order)
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
            # Conversation exists, retrieve existing message ID and conversation array
            existing_message_id = result[0]
            conversation = result[1]
            
            # Convert the conversation from JSON format to a Python list
            conversation_list = json.loads(conversation)
            
            # Add the new message to the conversation list
            new_message = {"sender_id": sender_id, "receiver_id": receiver_id, "message": message}
            conversation_list.append(new_message)
            
            # Convert the updated conversation list back to JSON format
            updated_conversation = json.dumps(conversation_list)
            
            # Update the conversation in the database
            update_query = """
                UPDATE messages
                SET conversation = %s, timestamp = NOW()
                WHERE message_id = %s
            """
            cursor.execute(update_query, (updated_conversation, existing_message_id))
        else:
            # No existing conversation; create a new one
            # Generate a unique message ID (3 characters long, consisting of uppercase letters and digits)
            message_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
            
            # Create a new conversation list with the new message
            new_conversation = [{"sender_id": sender_id, "receiver_id": receiver_id, "message": message}]
            
            # Convert the conversation list to JSON format
            conversation_json = json.dumps(new_conversation)
            
            # Insert the new conversation into the database
            insert_query = """
                INSERT INTO messages (message_id, room_id, sender_id, receiver_id, conversation, timestamp)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(insert_query, (message_id, room_id, sender_id, receiver_id, conversation_json))
        
        # Commit the transaction
        mysql.connection.commit()
        
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



if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', debug=True, port=5002)