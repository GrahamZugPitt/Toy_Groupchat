import socketio
import socket
import eventlet
import multiprocessing as mp
import os

#Global variables

#Name of individual clients.
my_name = None
#Set to true when a client is in a chatroom (They are connected to a server AND have set their name).
in_a_chatroom = False
#Set to true when a client is choosing their name in a chatroom.
setting_name = False
#Dictionary table. The server remembers everyone's name here.
name_hash_table = dict()

#This is where all of the talking happens. Messages are sent to the
#server and relayed by the server to all chat participants via
#socket events. This returns True if the client disconnects
#voluntarily and False if the client does not. 
def conversation_loop(sio, my_name):
	global in_a_chatroom
	while in_a_chatroom:
		next_line = input(my_name + ": ")
		if next_line == "\exit":
			in_a_chatroom = False
			return True
		if in_a_chatroom:
			sio.emit('my_message_server', next_line)
	return False

#A simple function that writes the current user's username.
#The primary purpose of this is prepending the user's username
#to their own messages on their own screen.
def add_name():
	print("\n" + my_name + ": ", end = '')

#All client socket events
def initialize_client_events(sio):
	#Called on client connection
	@sio.event
	def connect():
	    print("Connection Successful!")

	#called on client disconnection. if the client is "in a chatroom" when they disconnect,
	#they lost their connection and did not choose to disconnect.
	@sio.event
	def disconnect():
		global in_a_chatroom
		#We invoke setting_name here because the user is not yet considered to be in a chatroom and 
		#if they are setting their name, then they must not have disconnected voluntarily. 
		if in_a_chatroom or setting_name:
			print("\r\033[K" + "\nConnection to the groupchat has been lost. Press enter to continue.\n\n")
			in_a_chatroom = False
			return	
		print('You have left the groupchat.\n\n')

	#Prints a message recieved from the server.
	#The message is recieved as a two item list. the first
	#item is the name of the original sender and the second
	#item is the message to the chatroom. 
	@sio.event
	def my_message_client(data):
		#Blocks a user's own message from printing
		if data[0] == my_name or not in_a_chatroom:
			return
		print("\r\033[K" + data[0] + ": " + data[1], end = ""),
		add_name()
	#Prints a message from the server to this
	#user when a user joins the chat.
	@sio.event
	def client_joined_message(data):
		if not in_a_chatroom:
			return
		print("\r\033[K" + data + " has joined the chat!", end = ""),
		add_name()
	#Prints a message from the server to this
	#user when a user leaves the chat.
	@sio.event
	def client_left_message(data):
		if not in_a_chatroom:
			return
		print("\r\033[K" + data + " has left the groupchat.", end = ""),
		add_name()
		
#All server socket events
def initialize_server_events(sio):
	#Called when a user connects to the server.
	@sio.event
	def connect(sid, environ):
		pass

	#When a client disconnects, other clients are notified with this function.
	#The disconnecting client's name is erased in the hash table
	#and can be taken by other users.
	@sio.event
	def disconnect(sid):
		sio.emit('client_left_message', name_hash_table[sid])
		name_hash_table.pop(sid, None)

	#Prints a recieved message to the server and broadcasts it to all other users. 
	@sio.event
	def my_message_server(sid, data):
		sio.emit("my_message_client", [name_hash_table[sid], data])

	#Tells the other users when a new user has joined the server. This doesn't happen on connect because
	#in this implementation, there is a time where you are connected where you are choosing your name
	#and cannot see messages in the chatroom.
	@sio.event
	def join_server(sid):
		sio.emit("client_joined_message", name_hash_table[sid])

	#Called when a new user joins the client. The server checks if 
	#There is currently a user using the requested name and requests
	#A new name from the client if their chosen name is in use.
	@sio.event 
	def set_name(sid, data):
		if data in name_hash_table.values():
			return False
		name_hash_table[sid] = data
		return True

#Makes the user become a client of a server.
#This is called for both servers and clients.
#(Users who run servers become clients of 
#the servers they are running)
def run_client(is_host, port):
	#Try to connect to the server.
	try:
		if port == -1:
			print("Connect to server on what port?")
			port = input()
		#This function initializes a socketIO client, reconnection is set to False
		#so that the client isn't trying to reconnect to servers on the same port
		#indefinitely. 
		sio = socketio.Client(reconnection = False)
		initialize_client_events(sio)
		sio.connect('http://localhost:' + str(port))
	except:
		print("Failed to connect to server.\n")
		return
	global my_name
	global setting_name
	setting_name = True
	my_name = input("Choose a name to represent yourself in the groupchat:")
	#The "call" method here just means that the server is giving information back
	#The server tells the client if the client's name is taken or not.
	while sio.connected and not sio.call('set_name', my_name):
		my_name = input("That name is already in use. Please choose a different name:")
	setting_name = False
	global in_a_chatroom
	print("\n")
	print("\n")
	if is_host:
		print("Type \exit to close the server.")
	#This check here to catch the case where the server shuts
	#Down while the client is choosing their name.
	if sio.connected:
		if not is_host:
			print("Type \exit to leave the server.")
		sio.emit('join_server')
		in_a_chatroom = True
	#Begin conversation
	if conversation_loop(sio, my_name):
		sio.disconnect()

#Checks whether a given port number is in use.
#Does this by creating a socket (Not a socketIO object)
#and attempting to connect to that port. If it succeeds,
#the port is considered to be in use. 
def port_is_in_use(port):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	return s.connect_ex(('localhost', port)) == 0

#Attempt to run a server
def run_server():
	if __name__ == '__main__':
		#Try to open server.
		try:
		#Get port number from user
			print("Host on what port number?")
			port = input()
			port = int(port)
			if port_is_in_use(port):
				print("That port is currently in use so the server cannot be opened.\n")
				return
			#Socket is initialized as a server socket 
			sio = socketio.Server() 
			#Function called upon server activation. 
			handler = socketio.WSGIApp(sio)
			#Event initialization. 
			initialize_server_events(sio)
			if os.name == 'nt':
				mp.set_start_method('spawn')
			#Creates the server process using eventlet. log_output set to false so that the host can participate in the chat.
			server_proc = mp.Process(target = eventlet.wsgi.server, args = (eventlet.listen(('', port)), handler), kwargs = {"log_output" : False})
		except:
			print("Failed to initialize server.\n")
			return 
		server_proc.start()
		#Open client and connect to own server
		run_client(True, port)
		server_proc.terminate()

#Gets user input in the beginning. User can start their own server,
#connect to an existing server, or exit.
def get_user_input():
	user_input = 0
	while user_input != "1" and user_input != "2" and user_input != "3":
		print("Enter the number that corresponds with what you wish to do:")
		print("1. Start a new group chat.")
		print("2. Enter an existing group chat.")
		print("3. Exit")
		user_input = input()
	user_input = int(user_input)
	return user_input
#The start of the program
def begin():
	while True:
		user_input = get_user_input()
		if user_input == 1:	
			run_server()
		if user_input == 2:
			run_client(False, -1)
		if user_input == 3:
			exit()
#Call of the start of the program
begin()
