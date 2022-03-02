# Toy_Groupchat
A simple group chat app that sends messages through sockets. 

Run with python3. The socketio and eventlet 
python packages are required.

When run, groupchat.py will prompt a user to start a server
or join a server. The user will then be asked on which port
they would like to open their server or which port
they would like to connect to (Depending on if they are
running or joining a server). If the user is running
a server, the user will become a client on their own
server. In any case, users will be prompted to name
themselves before they enter the group chat. If the
original creator of the server leaves, the group
chat is shut down. Individual users can leave
anytime they like.
