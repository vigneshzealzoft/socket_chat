import axios from 'axios';
import React, { useState, useEffect } from 'react';
import { View, FlatList, Text, TextInput, Button } from 'react-native';
import io from 'socket.io-client';

const Chat = ({ route, navigation }) => {
    const { user } = route.params;
    const suserid=route.params.suserid
    const [messages, setMessages] = useState([]);
    const [message, setMessage] = useState('');
    const [roomId,setroomId]=useState("")
    const socket = io('http://192.168.1.5:5000');

    useEffect(() => {
        // Join the room with the specified user
        socket.emit('create_or_join_room', { user1_id: suserid, user2_id: user.userid });
    
        // Listen for existing messages
        socket.on('existing_messages', (data) => {
            setroomId(data.room_id);
            setMessages(data.messages);
        });
    
        // Listen for new messages
        socket.on('receive_message', (newMessage) => {
            setMessages((prevMessages) => [...prevMessages, newMessage]);
        });
    
        // Handle reconnection
        socket.on('connect', () => {
            // Rejoin the room after reconnection
            socket.emit('create_or_join_room', { user1_id: suserid, user2_id: user.userid });
        });
    
        // Cleanup: Remove event listeners when component unmounts
        return () => {
            socket.off('existing_messages');
            socket.off('receive_message');
            socket.disconnect();
        };
    }, [suserid, user.userid]);
    

    const sendMessage = () => {
        const messageData = {
            room_id: roomId, // The room ID you received when joining the room
            sender_id: suserid, // Your current user ID
            receiver_id: user.userid,
            message: message,
        };
    
        // Emit the message to the server
        socket.emit('send_message', messageData);
    
        // Mark messages as read
        // markMessagesAsRead(roomId, user.userid);
    
        // Clear the message input
        setMessage('');
    };
    
    // Function to mark messages as read
    // const markMessagesAsRead = (room_id, receiver_id) => {
    //     axios.post('http://192.168.1.5:5000/mark_messages_as_read', {
    //         room_id: room_id,
    //         receiver_id: receiver_id
    //     })
    //     .then(() => {
    //         // Emit an event to update the user list
    //         socket.emit('mark_as_read', {
    //             room_id: room_id,
    //             receiver_id: receiver_id
    //         });
    //     })
    //     .catch(error => {
    //         console.error('Error marking messages as read:', error);
    //     });
    // };
    

    console.log(messages)

    return (
        <View style={{flex:1,padding:10}}>
            <FlatList
                data={messages}
                keyExtractor={(item, index) => index.toString()}
                renderItem={({ item }) => (
                    <View
                    style={{
                        flexDirection: 'row',
                        justifyContent: item.sender_id === suserid ? 'flex-end' : 'flex-start',
                        marginVertical: 5,
                    }}
                >
        
                    <Text style={{backgroundColor: item.sender_id === suserid ? '#d1f0ff' : '#f0d1ff',
                    padding: 10,
                    borderRadius: 5,
                    maxWidth: '70%',padding:10,marginVertical:10}}>{`${item.sender_id === suserid ? 'You' : user.username}: ${item.message}`}</Text>
                    </View>
                )}
            />

            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                <TextInput
                    style={{ flex: 1, borderWidth: 1, borderColor: '#ccc', marginRight: 8 }}
                    value={message}
                    onChangeText={setMessage}
                    placeholder="Type a message"
                />
                <Button title="Send" onPress={sendMessage} />
            </View>
        </View>
    );
};

export default Chat;
