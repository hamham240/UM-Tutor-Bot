#imports
import discord
from discord.ext import commands
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
client = commands.Bot(command_prefix = ('!', 't!'))


###Bot Startup Event Handler###
@client.event
async def on_ready():
	print("Bot is running as " + client.user.name)


###Server Join Handler###
@client.event
async def on_guild_join(guild):
	category = await guild.create_category("command-channels")
	tutorRole = await guild.create_role(name="UM Tutors", colour=discord.Colour(0xA83232), hoist=True)
	tutorChannel = await guild.create_text_channel('tutor-commands', category=category, overwrites = {
		guild.default_role: discord.PermissionOverwrite(send_messages = False),
		guild.me: discord.PermissionOverwrite(send_messages = True),
		tutorRole: discord.PermissionOverwrite(send_messages = True)
		})
	studentChannel = await guild.create_text_channel('student-commands', category=category)
	if tutorChannel and studentChannel:
		await tutorChannel.send("Thanks for inviting me!\n The purpose of the UM-Tutor-Bot is to manage this tutoring server. This involves stuff like checking the status of the tutor and joining a queue for tutoring. \n " +
			"Tutor commands start with t! and student commands just start with !. \n Type !help to see a list of commands!")
		await studentChannel.send("Thanks for inviting me!\n The purpose of the UM-Tutor-Bot is to manage this tutoring server. This involves stuff like checking the status of the tutor and joining a queue for tutoring. \n " +
			"Tutor commands start with t! and student commands just start with !. \n Type !help to see a list of commands!")


###Discord Commands###
#Student/Tutor command
#!help displays a list of commands
@client.remove_command("help")
@client.command()
async def help(ctx):
	await ctx.message.channel.send("Student Commads (start with '!')\n"
			+"!screensharing --- Gives instructions on how to share your screen\n"
			+"!status --- Tells you if the tutor is online or not \n"
			+"!q --- View the current queue of students waiting to be tutored\n"
			+"!joinq --- Join the queue to get tutored\n"
			+"!leaveq --- Allows you to leave the queue, if you are finished getting tutored or need to leave for some reason then use this command\n"
			+"Tutor Commands (start with 't!')\n"
			+"t!start --- start a tutoring session\n"
			+"t!end --- end the current tutoring session\n"
			+"t!next --- pop the student you just tutored off the queue\n"
			+"t!wipeq --- reset the queue\n"
			+"Note: Please try to only use commands in the #tutor-commands and #student-commands channels (#tutor-commmands is only for tutors)")


#Student/Tutor command
#!screensharing displays information on how to share your screen on discord
@client.command()
async def screensharing(ctx):
	await ctx.message.channel.send("1. First make sure you have discord installed on your laptop/desktop and that you are not using discord in a browser, also you can only stream in a voice channel so make sure you are in one to begin with\n"
		+"2. Navigate to the tutoring server (if you are reading this then you are already here, but every time you want to share your screen with a tutor on a server, make sure you navigate to it first)\n"
		+"3. Look in the bottom left of discord you should see a button that resembles a monitor with an arrow on it. This is the screen sharing button, click on it. It looks like this:")
	await ctx.message.channel.send(file=discord.File('images/screensharing1.png'))
	await ctx.message.channel.send("4. It should open an interface which will allow you to select if you want to share your entire screen or just a certain application (for example: if you wanted to just stream your text editor). "
		+"If you have sensitive information on your screen then its probably a good idea to just stream your application. It should look like this:")
	await ctx.message.channel.send(file=discord.File('images/screensharing2.png'))
	await ctx.message.channel.send("5. Once you've selected the application/screen you wish to stream, just click the go live button at the bottom of the interface and discord will start streaming your application/screen")


#Tutor command
#t!start starts a new tutoring session
@client.command()
async def start(ctx):
	if not isTutor(ctx.message.author):
		await ctx.message.channel.send("Sorry you are not a tutor. \n(If you are then ask the server owner to provide you with a UM Tutors role which this bot creates upon joining a server)")
		return

	serverId = str(ctx.message.channel.guild.id)

	currentStatus = getStatus(serverId)
	if (currentStatus):
		await ctx.message.channel.send("You already started a tutoring session.")
		return

	currentQueue = getQueue(serverId)
	nextUserId = 0
	for key, value in currentQueue.items():
		if value == 0:
			nextUserId = key

	try:
		setStatus(serverId, True)
		if not nextUserId:
			await ctx.message.channel.send("The tutor has begun tutoring.")
		else:
			await ctx.message.channel.send("The tutor has begun tutoring.\n" + client.get_user(int(nextUserId)).mention + " You're up first!")
	except:
		await ctx.message.channel.send("Error, unable to start tutoring at the moment.")



#Tutor command
#t!end ends the current ongoing tutoring session
@client.command()
async def end(ctx):
	if not isTutor(ctx.message.author):
		await ctx.message.channel.send("Sorry you are not a tutor. \n(If you are then ask the server owner to provide you with a UM Tutors role which this bot creates upon joining a server)")
		return

	serverId = str(ctx.message.channel.guild.id)
	currentStatus = getStatus(serverId)
	if (not currentStatus):
		await ctx.message.channel.send("There is no session to end.")
		return

	try:
		setStatus(serverId, False)
		await ctx.message.channel.send("The tutor has ended tutoring.")
	except:
		await ctx.message.channel.send("Error, unable to end tutoring at the moment.")



#Tutor command
#t!next dequeues the student from the tutoring queue
@client.command()
async def next(ctx):
	if not isTutor(ctx.message.author):
		await ctx.message.channel.send("Sorry you are not a tutor. \n(If you are then ask the server owner to provide you with a UM Tutors role which this bot creates upon joining a server)")
		return

	serverId = str(ctx.message.channel.guild.id)
	currentQueue = getQueue(serverId)
	
	if len(currentQueue) == 0:
		await ctx.message.channel.send("Queue is empty. Unable to get next student.")
		return

	for key, value in currentQueue.items():
		if value == 0:
			tutoredUserId = key
		if value == 1:
			nextUserId = key
		currentQueue[key] = value - 1;

	currentQueue.pop(tutoredUserId)

	try:
		setQueue(serverId, currentQueue)
		if (len(currentQueue) == 0):
			await ctx.message.channel.send("The tutor has finished tutoring " + client.get_user(int(tutoredUserId)).name + ". The queue is now empty.")
		else:
			await ctx.message.channel.send("The tutor has finished tutoring " + client.get_user(int(tutoredUserId)).name + ". The queue size is now " + str(len(currentQueue)) + ".\n" + client.get_user(int(nextUserId)).mention + " You're up next!")
	except:
		await ctx.message.channel.send("Error, unable to dequeue student at the moment.")


#Tutor command
#t!wipeq wipes the queue
@client.command()
async def wipeq(ctx):
	if not isTutor(ctx.message.author):
		await ctx.message.channel.send("Sorry you are not a tutor. \n(If you are then ask the server owner to provide you with a UM Tutors role which this bot creates upon joining a server)")
		return

	serverId = str(ctx.message.channel.guild.id)

	try:
		setQueue(serverId, {})
		await ctx.message.channel.send("The queue has been successfully wiped.")
	except:
		await ctx.message.channel.send("Error, unable to wipe queue at the moment.")

#Student/Tutor command
#!q displays the current queue
@client.command()
async def q(ctx):

	serverId = str(ctx.message.channel.guild.id)
	currentQueue = getQueue(serverId)
	queueSize = len(currentQueue)
	status = getStatus(serverId)
	print(type(currentQueue))

	try:
		if queueSize == 0:
			await ctx.message.channel.send("The queue is currently empty.")
		else:
			output = "Current queue size is " + str(queueSize) + ". Here is the current queue: \n"

			for key in sorted(currentQueue, key=currentQueue.get):
				print(type(currentQueue[key]))
				try: 
					user = client.get_user(int(key)).name
				except:
					user = key

				if status:
					if str(ctx.message.author.id) == key:
						output += str(currentQueue[key] + 1) + ". " + user + " <---- You (Currently being tutored)\n" if currentQueue[key] == 0 else str(currentQueue[key] + 1) + ". " + user + " <---- You\n"
					else:
						output += str(currentQueue[key] + 1) + ". " + user + " (Currently being tutored)\n" if currentQueue[key] == 0 else str(currentQueue[key] + 1) + ". " + user + "\n"
				else:
					if str(ctx.message.author.id) == key:
						output += str(currentQueue[key] + 1) + ". " + user + " <---- You \n" if currentQueue[key] == 0 else str(currentQueue[key] + 1) + ". " + user + " <---- You\n"
					else:
						output += str(currentQueue[key] + 1) + ". " + user + " \n" if currentQueue[key] == 0 else str(currentQueue[key] + 1) + ". " + user + "\n"
		await ctx.message.channel.send(output)
	except:
		await ctx.message.channel.send("Error, unable to display queue at the moment.")


#Student/Tutor command
#!status will display if a tutor session is going on or not
@client.command()
async def status(ctx):
	serverId = str(ctx.message.channel.guild.id)

	try:
		if getStatus(serverId):
			await ctx.message.channel.send("The tutor is currently online.")
		else:
			await ctx.message.channel.send("The tutor is currently offline.")
	except:
		await ctx.message.channel.send("Unable to retrieve status at the moment.")


#Student command
#!joinq will enqueue a student in the tutoring queue
@client.command()
async def joinq(ctx):
	if isTutor(ctx.message.author):
		await ctx.message.channel.send("Tutors are not allowed to join/leave queues.")
		return

	serverId = str(ctx.message.channel.guild.id)
	currentQueue = getQueue(serverId)
	queueSize = len(currentQueue)

	if str(ctx.message.author.id) in currentQueue.keys():
		await ctx.message.channel.send("You are already in the queue. Your position is " + str(currentQueue[str(message.author.id)] + 1) + ".")
		return

	try:
		currentQueue.update({str(ctx.message.author.id) : queueSize})
		setQueue(serverId, currentQueue)
		await ctx.message.channel.send("Joined the queue! Your position in the queue is " + str(len(currentQueue)) + ".")
	except:
		await ctx.message.channel.send("Unable to join queue at the time.")


#Student command
#!leaveq will deqqueue the student from the tutoring queue
@client.command()
async def leaveq(ctx):
	if isTutor(ctx.message.author):
		await ctx.message.channel.send("Tutors are not allowed to join/leave queues.")
		return

	serverId = str(ctx.message.channel.guild.id)
	currentQueue = getQueue(serverId)
	queueSize = len(currentQueue)

	if not str(ctx.message.author.id) in currentQueue.keys():
		await ctx.message.channel.send("You are not in the queue.")
		return
	else:
		authorPosition = currentQueue.pop(str(ctx.message.author.id))

	for key, value in currentQueue.items():
		if value > authorPosition:
			currentQueue[key] = value - 1;
		if value == 1:
			nextUserId = key

	try:
		if authorPosition == 0 and nextUserId:
			await ctx.message.channel.send(message.author.name + "has left the queue.  The current queue size is " + str(len(currentQueue)) + ".\n" + client.get_user(int(nextUserId)).mention + " You're up next!")
		else:
			await ctx.message.channel.send("Left the queue! The current queue size is " + str(len(currentQueue)) + ".")
	except:
		await ctx.message.channel.send("Unable to leave queue at the time.")


###Helper Function###
#Functions called by commands
def isTutor(user):
	for role in user.roles:
		if role.name == "UM Tutors":
			return True
	return False

def getStatus(serverId):
	doc_ref = db.collection(u'server-status').document(serverId).get()
	doc = doc_ref.to_dict()

	try:
		doc["status"]
	except:
		db.collection(u'server-status').document(serverId).set({
			u'status' : False
		})
		doc_ref = db.collection(u'server-status').document(serverId).get()
		doc = doc_ref.to_dict()

	return doc['status']

def setStatus(serverId, newStatus):
		db.collection(u'server-status').document(serverId).set({
			u'status' : newStatus
		})

def getQueue(serverId):
	doc = db.collection(u'server-queues').document(serverId).get().to_dict()

	try:
		doc["queue"]
	except:
		db.collection(u'server-queues').document(serverId).set({
			u'queue' : {}
		})
		doc = db.collection(u'server-queues').document(serverId).get().to_dict()

	return doc["queue"]

def setQueue(serverId, newQueue):
	doc = db.collection(u'server-queues').document(serverId).get().to_dict()

	db.collection(u'server-queues').document(serverId).set({
		u'queue' : newQueue
	})



#Run the bot with the bot's token as the argument
client.run(discord_token.token())


