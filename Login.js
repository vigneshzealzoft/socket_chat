import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import axios from 'axios';
import { useNavigation } from '@react-navigation/native';

export default function Login() {
    const [name, setName] = useState('');
    const [pass, setPass] = useState('');
    const [loading, setLoading] = useState(false);
    const [userid,setUserId]=useState()
    const navigation=useNavigation()

    const handleSubmit = async () => {
        setLoading(true);  // Show loading indicator
        try {
            // Send a POST request to the login API
            const response = await axios.post('http://192.168.1.5:5000/login', {
                username: name,
                password: pass,
            });
          
           
            // Handle successful response
            response.status==200?
            navigation.navigate("home",{userid:response.data.userid}):Alert.alert("Something went Wrong!!!try again")
            // Perform further actions after successful login (e.g., navigation)

        } catch (error) {
            // Handle error response
            console.error(error);
            Alert.alert('Error', 'Login failed. Please try again.');
        } finally {
            setLoading(false);  // Hide loading indicator
        }
    };

    return (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
            <Text style={{ marginVertical: 20, fontSize: 20 }}>Login</Text>
            <TextInput
                placeholder="Username"
                value={name}
                style={{ borderWidth: 1, width: '80%', height: 50, marginBottom: 20, padding: 10 }}
                onChangeText={setName}
            />
            <TextInput
                placeholder="Password"
                value={pass}
                style={{ borderWidth: 1, width: '80%', height: 50, padding: 10 }}
                secureTextEntry={true}
                onChangeText={setPass}
            />
            <TouchableOpacity
                onPress={handleSubmit}
                style={{ marginVertical: 10, width: 100, height: 40, backgroundColor: 'black', justifyContent: 'center' }}
            >
                {loading ? (
                    <ActivityIndicator color="#fff" />  // Show loading indicator
                ) : (
                    <Text style={{ color: '#fff', textAlign: 'center' }}>Login</Text>
                )}
            </TouchableOpacity>
        </View>
    );
}
