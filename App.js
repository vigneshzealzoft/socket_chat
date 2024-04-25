import { View, Text } from 'react-native'
import React from 'react'
import Login from './Login'
import { NavigationContainer } from '@react-navigation/native'
import { createStackNavigator } from '@react-navigation/stack';
import Chat from './chat';
import Home from './Home';

const Stack = createStackNavigator();


export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator>
      <Stack.Screen name="Login" component={Login} />
      <Stack.Screen name="home" component={Home}/>
      <Stack.Screen name="chat" component={Chat} />

      </Stack.Navigator>
      
    </NavigationContainer>
  )
}