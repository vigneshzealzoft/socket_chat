import { useEffect, useState } from 'react';
import { View, FlatList, Text, TouchableOpacity } from 'react-native';
import axios from 'axios';
import io from 'socket.io-client';

const socket = io.connect('http://192.168.1.5:5000');

const UserListScreen = ({ navigation, route }) => {
    const [users, setUsers] = useState([]);
    const suserid = route.params.userid;

    console.log(suserid)
    // Function to mark messages as read



useEffect(() => {
    // Fetch the list of users from the backend
    axios.get(`http://192.168.1.5:5000/userlist`)
        .then(response => {
            const data = response.data.filter(item => item.userid !== suserid);
            setUsers(data);
        })
        .catch(error => {
            console.error('Error fetching users:', error);
        });

    // Listen for the update event
    socket.on('update_user_list', (data) => {
        // Update the user list with the latest message and unread count
        setUsers(prevUsers => {
            return prevUsers.map(user => {
                if (user.userid === data.sender_id || user.userid === data.receiver_id) {
                    // Update the user data with the latest message and unread count
                    return {
                        ...user,
                        latest_message: data.latest_message,
                        unread_count: data.unread_count
                    };
                }
                return user;
            });
        });
    });

    // Cleanup the socket event listener when the component unmounts
    return () => {
        socket.off('update_user_list');
    };
}, [suserid]);


    const handleUserPress = (user) => {
        // Navigate to the chat room screen and pass the selected user as a parameter
        navigation.navigate('chat', { user, suserid });
    };

    return (
        <View>
            <FlatList
                data={users}
                keyExtractor={(item) => item.userid.toString()}
                renderItem={({ item }) => (
                    <TouchableOpacity
                        style={{ marginVertical: 10, marginHorizontal: 10, backgroundColor: "skyblue" }}
                        onPress={() => handleUserPress(item)}
                    >
                        <Text style={{ fontSize: 20, textAlign: "center", padding: 10 }}>{item.username}</Text>
                        {/* Display the latest message */}
                        <Text style={{ fontSize: 14, textAlign: "center", padding: 5 }}>{item.latest_message}</Text>
                        {/* Display the unread message count if greater than 0 */}
                        {item.unread_count > 0 && (
                            <Text style={{ fontSize: 14, textAlign: "center", padding: 5, color: 'red' }}>
                                {item.unread_count} unread messages
                            </Text>
                        )}
                    </TouchableOpacity>
                )}
            />
        </View>
    );
};

export default UserListScreen;
