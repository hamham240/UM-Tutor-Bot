#imports
import discord
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime
import discord_token

# Firestore set up
cred = credentials.Certificate('key.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

#Discord.py set up
client = discord.Client()

#Display message for when bot starts up
@client.event
async def on_ready():
	print("We have logged in as {0.user}".format(client))

#Asynchronous function for whenever a message appears in a server
@client.event
async def on_message(message):
	#If message comes from this bot or another then do nothing
	if message.author == client.user or message.author.bot == True:
		return


	#Tutor command
	#If the tutor wants to start the tutoring session
	if message.content.startswith('t!start'):
		#store the server's unique id in variable serverId
		serverId = str(message.channel.guild.id)

		#set the boolean located in firestore for this server's tutoring status as true
		db.collection(u'server-status').document(serverId).set({
			u'status' : True
		})

		#get the current time and format
		dateTime = datetime.now()
		minutes = dateTime.minute
		if (minutes < 10):
			minutes = "0" + str(minutes)
		else:
			minutes = str(minutes)

		#print out that the session has begun
		await message.channel.send("The tutor has begun tutoring at " + str(dateTime.hour) + ":" + minutes + ".")



	#Tutor command
	#If the tutor wants to end the current tutoring session
	if message.content.startswith('t!end'):
		#store the server's unique id in variable serverId
		serverId = str(message.channel.guild.id)

		#set the boolean located in firestore for this server's tutoring status as false
		db.collection(u'server-status').document(serverId).set({
			u'status' : False
		})

		#get the current time and format
		dateTime = datetime.now()
		minutes = dateTime.minute
		if (minutes < 10):
			minutes = "0" + str(minutes)
		else:
			minutes = str(minutes)

		#print out that the session has ended
		await message.channel.send("The tutor has ended tutoring at " + str(dateTime.hour) + ":" + minutes + ".")


	#Student/Tutor command
	#If the student/tutor wants to see the queue
	if message.content.startswith('!q'):
		#store the server's unique id in variable serverId
		serverId = str(message.channel.guild.id)

		#create a snapshot of the this server's document in the 'server-status' collection located in firestore
		doc_ref = db.collection(u'server-queues').document(serverId).get()
		doc = doc_ref.to_dict()

		#check to see if the server exists in the database, else create a default entry in the db and reinitialize variables
		try:
			doc["queue-size"]
		except:
			db.collection(u'server-queues').document(serverId).set({
				u'queue-size' : 0,
				u'queue' : {}
			})
			doc_ref = db.collection(u'server-queues').document(serverId).get()
			doc = doc_ref.to_dict()

		queueSize = doc['queue-size']
		currentQueue = doc["queue"]

		#if queue is empty then print out that the queue is empty
		if queueSize == 0:
			await message.channel.send("The queue is currently empty.")
		else:
			#Queue is not empty so print out queue size and display current queue
			output = "Current queue size is " + str(queueSize) + ". Here is the current queue: \n"

			#loop through the queue once it is sorted based on the values
			for key in sorted(currentQueue, key=currentQueue.get):
				#try to display the user's discord username otherwise just display the user's id in the db
				try: 
					user = client.get_user(int(key)).name
				except:
					user = key

				#if the author of the message wants to see the q then point towards their position, also add "Currently being tutored" to the student in the very first position
				if str(message.author.id) == key:
					output += str(currentQueue[key] + 1) + ". " + user + " <---- You (Currently being tutored)\n" if currentQueue[key] == 0 else str(currentQueue[key] + 1) + ". " + user + " <---- You\n"
				else:
					output += str(currentQueue[key] + 1) + ". " + user + " (Currently being tutored)\n" if currentQueue[key] == 0 else str(currentQueue[key] + 1) + ". " + user + "\n"

			#send the message once its constructed
			await message.channel.send(output)


	#Student command
	#If the student wants to see the status of the tutor
	if message.content.startswith('!status'):
		#store the server's unique id in variable serverId
		serverId = str(message.channel.guild.id)

		#create a snapshot of the this server's document in the 'server-status' collection located in firestore
		doc_ref = db.collection(u'server-status').document(serverId).get()
		doc = doc_ref.to_dict()

		#Try to reference this server's status, if it doesnt exist then we need to register this server in firestore and set to false as default
		try:
			doc["status"]
		except:
			db.collection(u'server-status').document(serverId).set({
				u'status' : False
			})
			doc_ref = db.collection(u'server-status').document(serverId).get()
			doc = doc_ref.to_dict()


		#Based on the boolean located in the document for this server in firestore, send a message whether the tutor is online or not
		if doc['status']:
			await message.channel.send("The tutor is currently online.")
		else:
			await message.channel.send("The tutor is currently offline.")



	#Student command
	#If the student wants to join the queue
	if message.content.startswith('!joinq'):
		#store the server's unique id in variable serverId
		serverId = str(message.channel.guild.id)

		#create a snapshot of the this server's document in the 'server-status' collection located in firestore
		doc_ref = db.collection(u'server-queues').document(serverId).get()
		doc = doc_ref.to_dict()

		#check to see if the server exists in the database, else create a default entry in the db and reinitialize variables
		try:
			doc["queue-size"]
		except:
			db.collection(u'server-queues').document(serverId).set({
				u'queue-size' : 0,
				u'queue' : {}
			})
			doc_ref = db.collection(u'server-queues').document(serverId).get()
			doc = doc_ref.to_dict()

		#initialize variables which store data from the db (the size of the current queue as well as the queue itself)
		queueSize = doc["queue-size"]
		currentQueue = doc["queue"]

		#If a user tries to join the queue but is already in the queue, print out that they are already in the queue
		if str(message.author.id) in currentQueue.keys():
			await message.channel.send("You are already in the queue. Your position is " + currentQueue[str(message.author.id)] + ".")
			return

		#insert updated queue into database
		try:
			currentQueue.update({str(message.author.id) : queueSize})

			queueSize = len(currentQueue)
			db.collection(u'server-queues').document(serverId).set({
				u'queue-size' : queueSize,
				u'queue' : currentQueue
			})
			await message.channel.send("Joined the queue! Your position in the queue is " + str(queueSize) + ".")
		except:
			await message.channel.send("Unable to join queue at the time.")






	#Student command
	#If the student wants to leave the queue
	if message.content.startswith('!leaveq'):
		#store the server's unique id in variable serverId
		serverId = str(message.channel.guild.id)

		#create a snapshot of the this server's document in the 'server-status' collection located in firestore
		doc_ref = db.collection(u'server-queues').document(serverId).get()
		doc = doc_ref.to_dict()

		#check to see if the server exists in the database, else create a default entry in the db and reinitialize variables
		try:
			doc["queue-size"]
		except:
			db.collection(u'server-queues').document(serverId).set({
				u'queue-size' : 0,
				u'queue' : {}
			})
			doc_ref = db.collection(u'server-queues').document(serverId).get()
			doc = doc_ref.to_dict()

		#initialize variables which store data from the db (the size of the current queue as well as the queue itself)
		queueSize = doc["queue-size"]
		currentQueue = doc["queue"]

		#if the author of the message is not in the queue then return
		if not str(message.author.id) in currentQueue.keys():
			await message.channel.send("You are not in the queue.")
			return
		#otherwise pop out their entry in the dictionary and store their position in a variable
		else:
			authorPosition = currentQueue.pop(str(message.author.id))

		#readjust the queue, moving everyone who was above the author down in position
		for key, value in currentQueue.items():
			if value > authorPosition:
				currentQueue[key] = value - 1;

		#insert updated queue into database
		try:
			db.collection(u'server-queues').document(serverId).set({
				u'queue-size' : (queueSize - 1),
				u'queue' : currentQueue
			})
			await message.channel.send("Left the queue! The current queue size is " + str(queueSize-1) + ".")
		except:
			await message.channel.send("Unable to leave queue at the time.")



#Run the bot with the bot's token as the argument
client.run(discord_token.token())