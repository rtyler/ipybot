import clr
clr.AddReference('System.Data')
clr.AddReference('Mono.Data.SqliteClient')
clr.AddReferenceToFile('Meebey.SmartIrc4net.dll')

import System
from System import *
from System.Collections import *
from System.Data import *
from System.IO import *
from System.Net import *
from System.Text import *
from System.Threading import *

from Meebey.SmartIrc4net import *
from Mono.Data.SqliteClient import *


VERSION_STRING = 'IpyBot v0.1-dev'

DEFAULT_NICK = 'IpyBotDev'
DEFAULT_SERVER = 'chat.freenode.net'
DEFAULT_PORT = 8001
DEFAULT_CHANNELS = ['#ipybot']
DEFAULT_AUTHORIZED = ['rtyler']
DEFAULT_COMMAND = '!'

class IpyBot(object):
	server = None
	port = 0
	channel = None
	client = None
	db = None

	def OnQueryMessage(self, sender, args):
		t = args.Data.MessageArray[0]
		if t == 'dump_channel':
			req = e.Data.MessageArray[1]
			chan = self.client.GetChannel(req)
			self.client.SendMessage(SendType.Message, e.Data.Nick, 'Topic: %s' % (chan.Topic))

	def OnError(self, sender, args):
		self.Print('*** ERROR! : %s' % args.ErrorMessage)
		Environment.Exit(1)

	def OnRawMessage(self, sender, args):
		if 'PRIVMSG' in args.Data.RawMessage:
			contents = args.Data.RawMessage.split(':')
			who = contents[1].split('!')[0]
			if contents[2].strip() == DEFAULT_NICK:
				self.OnMessageToMe(who, contents)
			elif len(contents) >= 3:
				self.OnMessageToChannel(who, contents)

	def OnMessageToMe(self, who, data):
		self.Print('%s said to me: %s' % (who, data))

	def OnMessageToChannel(self, who, data):	
		message = ':'.join(data[2:])
		print (who, message)
		if message.startswith(DEFAULT_COMMAND) and len(message) > len(DEFAULT_COMMAND):
			message = message[1:].split(' ')
			if len(message):
				getattr(self, 'IpyBotCommand_%s_Handler' % (message[0]), self.IpyBotCommand_Default_Handler)(who, message)
################################################
##	IpyBot Command Handlers
	def CheckAuthorized(self, who):
		return who in DEFAULT_AUTHORIZED

	def IpyBotCommand_learn_Handler(self, who, data):
		if not len(data) >= 4 or not data[2] == 'is' or not self.CheckAuthorized(who):
			return
		command = data[1]
		contents = ' '.join(data[3:])
		self.Print('Learning that %s is %s' % (command, contents))
		self.Store_Command(command, contents)

	def IpyBotCommand_version_Handler(self, who, data):
		self.client.SendMessage(SendType.Action, self.channel, 'is %s' % VERSION_STRING)

	def IpyBotCommand_panic_Handler(self, who, data):
		self.client.SendMessage(SendType.Action, self.channel, 'is srsly liek panicking. OMFGOMFGOMFGLOLWUT?')

	def IpyBotCommand_Default_Handler(self, who, message):
		if not len(message):
			return
		target = ''
		if len(message) == 3 and message[1] == '@':
			target = message[2] + ': '
		val = self.Fetch_Command(message[0])
		if not val:
			self.client.SendMessage(SendType.Message, self.channel, '"%s" is an invalid IpyBot command :(' % (message[0]))
		else:
			self.client.SendMessage(SendType.Message, self.channel, '%s%s is %s' % (target, message[0], val))
################################################


################################################
##	IpyBot Sqlite Layer
	def Store_Command(self, command, contents):
		sql = '''
			INSERT INTO %s (command, contents) 
			VALUES (:cmd, :cnts) 
			''' % (self.CurrentChannel())
		c = self.db.CreateCommand()
		c.CommandText = sql
		c.Parameters.Add('cmd', command)
		c.Parameters.Add('cnts', contents)
		try:
			c.ExecuteNonQuery()
			return True
		except Exception, ex:
			self.Print(ex)
		return False
	def Fetch_Command(self, command):
		self.Print('Finding %s'  % command)
		sql = '''
			SELECT contents FROM %s WHERE command = "%s"
			''' % (self.CurrentChannel(), command)
		c = self.db.CreateCommand()
		c.CommandText = sql
		try:
			return c.ExecuteScalar()
		except Exception, ex:
			self.Print(ex)
		return None
################################################
	
	def Print(self, message):
		print '<%s> %s' % (Thread.CurrentThread.Name, message)

	def CurrentChannel(self):
		return self.channel.replace('#', '')

	def __CreateBotTable(self, name):
		sql = '''
			CREATE TABLE %s (
				command		TEXT PRIMARY KEY,
				contents	TEXT);
			''' % (name)
		command = self.db.CreateCommand()
		command.CommandText = sql
		try:
			command.ExecuteNonQuery()
		except Exception, ex:
			pass

	def __init__(self, *args, **kwargs):
		self.server = kwargs.get('server')
		self.port = kwargs.get('port')
		self.channel = kwargs.get('channel')
		assert self.server and self.port and self.channel, 'Missing arguments for IpyBot() constructor!'

		self.client = IrcClient()
		self.client.Encoding = Text.Encoding.UTF8
		self.client.SendDelay = 200
		self.client.ActiveChannelSyncing = True

		connection = 'URI=file:%s_ipybot.db' % (self.CurrentChannel())
		self.db = SqliteConnection(connection)
		self.db.Open()
		self.__CreateBotTable(self.CurrentChannel())

		self.client.OnQueryMessage += IrcEventHandler(self.OnQueryMessage)
		self.client.OnError += IrcEventHandler(self.OnError)
		self.client.OnRawMessage += IrcEventHandler(self.OnRawMessage)

	def __del__(self):
		if self.db:
			self.db.Close()

	def ReadCommands(self):
		while True:
			self.client.WriteLine(Console.ReadLine())
		
	def Run(self):
		try:
			self.client.Connect(self.server, self.port)
		except ConnectionException, ex:
			self.Print("Couldn't connect! %s" % ex.Message)
			return

		try:
			self.client.Login(DEFAULT_NICK, 'IpyBot LOLZ!', 0, 'IpyBot')
			self.client.RfcJoin(self.channel)

			self.client.SendMessage(SendType.Action, self.channel, "clears its throat")

			Thread(ThreadStart(self.ReadCommands)).Start()

			self.client.Listen()
			self.client.Disconnect()
		except Exception, ex:
			self.Print(ex)
			return

if __name__ == '__main__':
	for channel in DEFAULT_CHANNELS:
		b = IpyBot(server=DEFAULT_SERVER, port=DEFAULT_PORT, channel=channel)
		t = Thread(ThreadStart(b.Run))
		t.Name = channel
		t.Start()
