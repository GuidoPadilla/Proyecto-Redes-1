import asyncio
from slixmpp.exceptions import IqError, IqTimeout
import xmpp

from slixmpp import ClientXMPP

#Compatiblity with windows and asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

#General Class for XMPP client chat
class Client(ClientXMPP):
    def __init__(self, jid, password, status, status_message):
        ClientXMPP.__init__(self, jid, password)
        #Plugins
        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0199') # Ping
        self.register_plugin('xep_0004') # Data Forms
        self.register_plugin('xep_0060') # PubSub
        self.register_plugin('xep_0085') # Chat State Notifications
        self.register_plugin('xep_0045') # MUC
        #attributes
        self.local_jid = jid
        self.nick = jid[:jid.index("@")]
        self.status = status
        self.status_message = status_message
        # App logic
        self.messages = {}
        self.contacts = self.roster[self.jid]
        self.actual_room = ""
        self.chat = None
        self.is_client_offline = True
        # Auto authorize & subscribe on subscription received
        self.roster.auto_authorize = True
        self.roster.auto_subscribe = True
        self.outter_presences = asyncio.Event()
        # Event handlers
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)
        self.add_event_handler("groupchat_message", self.muc_message)

    #room join function
    def muc_join(self, room):
        try:
            self.actual_room = room
            self['xep_0045'].join_muc(self.actual_room, self.local_jid)
        except:
            print('Problem joining room')
       
    #room exit function 
    def muc_exit(self):
        try:
            self.plugin['xep_0045'].leave_muc(self.actual_room, self.local_jid)
            self.actual_room = None
            self.nick = ''
        except:
            print('Problem leaving room')
    #start of xmpp client
    def start(self, event):
        self.send_presence(pshow=self.status, pstatus=self.status_message)
        try:
            self.get_roster()
            print("\n Login success: ", self.local_jid)
        except:
            print("Error on login")
            self.disconnect()
    #room mesasge funciton for receiving
    async def muc_message(self, message = ""):
        final_msg = ": " + message["body"]
        print(final_msg)
        """ if msg["from"] != self.local_jid:
            print("chimon", msg, final_msg) """
    #room message function for sending
    def muc_send_message(self, message= ""):
        try:
            self.send_message(mto=self.actual_room, mbody=message, mtype="groupchat")
        except:
            print('Unexpected error while sending message to group', self.actual_room)
    #Function for change status of client 
    def change_presence(self, presence, status_message):
        try:
            self.status = presence
            self.status_message = status_message
            self.send_presence(pshow=presence, pstatus=status_message)
        except:
            print("Could not update status and status message.")
    #Add contact
    def add_contact(self, recipient):
        try:
            self.send_presence_subscription(recipient, self.local_jid)
            print("Contact added: ", recipient)
        except:
            print("ERROR ON SUBSCRIBE")

    #function for list all contacts
    def show_contacts(self):
        try:
            self.get_roster()
            contacts = self.roster[self.local_jid]
            self.contacts = contacts

            if(len(self.contacts.keys()) == 0):
                print("0 contacts")

            for contact in self.contacts.keys():
                if contact != self.local_jid:
                    contact_message = f"Contact: {contact}, status: "
                    contact_info = list(self.client_roster.presence(contact).values())
                    if contact_info != []:
                        if contact_info[0]['status'] != '':
                            contact_message += f"{contact_info[0]['status']}, message_status: "
                        else:
                            contact_message += f"None, message_status: "
                        if contact_info[0]['show'] != '':
                            contact_message += f"{contact_info[0]['show']}"
                        else:
                            contact_message += f"None"
                        print(contact_message)
        except:
            print('Contacts failed to retrieve')
        
    #show contact specific info       
    def show_user_info(self, username):
        try:
            self.get_roster()
            contacts = self.roster[self.local_jid]
            self.contacts = contacts

            if(len(self.contacts.keys()) == 0):
                print("Not contacts available")

            if username in self.contacts.keys():
                contact_message = f"Contact: {username}, status: "
                contact_info = list(self.client_roster.presence(username).values())
                if contact_info[0]['status'] != '':
                    contact_message += f"{contact_info[0]['status']}, message_status: "
                else:
                    contact_message += f"None, message_status: "
                if contact_info[0]['show'] != '':
                    contact_message += f"{contact_info[0]['show']}"
                else:
                    contact_message += f"None"
                print(contact_message)
            else:
                print('Unavaible contact with user: ', username)
        except:
            print('Something went wrong with showing user info')
    #funciton for sending 1 to 1 message
    def direct_message(self, recipient, message=""):
        self.send_message(
            mto = recipient, 
            mbody = message, 
            mtype = 'chat', 
            mfrom = self.local_jid
        )

        recipient = recipient[:recipient.index("@")]
        sender = self.local_jid[:self.local_jid.index("@")]
        final_msg = sender + ":" + message

        if recipient in self.messages.keys():
            self.messages[recipient]["messages"].append(final_msg)
        else:
            self.messages[recipient] = {"messages":[final_msg]}
    #Function for receive 1 to 1 messages
    async def message(self, message):
        if message['type'] == 'chat':

            sender = str(message['from'])
            sender = sender[:sender.index("@")]
            body = str(message['body'])
            
            current_message = sender + ":" + body

            if sender in self.messages.keys():
                self.messages[sender]["messages"].append(current_message)
            else:
                self.messages[sender] = {"messages": [current_message]}

            if not self.chat == sender:
                print("\n Message from", sender)
            else:
                print("\n",current_message)
                print(">", end="")

#Class for unregister client
class UnregisterClient(ClientXMPP):

    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)

        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0004') # Data forms
        self.register_plugin('xep_0066') # Out-of-band Data
        self.register_plugin('xep_0077') # In-band Registration

        self.add_event_handler("session_start", self.start)

    async def start(self, event):
        self.send_presence()
        await self.get_roster()
        await self.unregister()
        self.disconnect()

    async def unregister(self):
        print('unregister')
        response = self.Iq()
        response['type'] = 'set'
        response['from'] = self.boundjid.user
        response['password'] = self.password
        response['register']['remove'] = 'remove'

        try:
            await response.send()
            print(f"Account unregistered successfully: {self.boundjid}!")
        except IqError as e:
            print(f"Couldn't unregister account: {e.iq['error']['text']}")
            self.disconnect()
        except IqTimeout:
            print("No response from server.")
            self.disconnect()
#Function to create user with xmpp
def createUser(user, password):
    usuario = user
    password = password
    jid = xmpp.JID(usuario)
    cli = xmpp.Client(jid.getDomain(), debug=[])
    cli.connect()

    if xmpp.features.register(cli, jid.getDomain(), {'username': jid.getNode(), 'password': password}):
        return True
    else:
        return False    
condition = True
user = None

#Main loop for handling all actions of user
""" try: """
while condition:
    if user:
        option = input('''1. Mostrar todos los usuarios/contactos y su estado\n2. Agregar un usuario a los contactos\n3. Mostrar detalles de contacto de un usuario\n4. Comunicación 1 a 1 con cualquier usuario/contacto\n5. Participar en conversaciones grupalesn\n6. Definir mensaje de presencia\n7. Enviar/recibir notificaciones\n8. Enviar/recibir archivos\n9. Logout\nIngrese una opcion: ''')
        if option == '1':
            user.show_contacts()
            user.process(timeout=3)
        elif option == '2':
            contact_to_add = input("username: ")
            user.add_contact(contact_to_add)
            user.process(timeout=3)
        elif option == '3':
            username = input('Username: ')
            user.show_user_info(username)
            user.process(timeout=3)
        elif option == '4':
            person_to_message = str(input('username: '))
            user_to_message = person_to_message[:person_to_message.index("@")]
            if person_to_message in user.contacts.keys():
                if user_to_message in user.messages.keys():
                    for message in user.messages[user_to_message]: 
                        print(message)
                message_condition = True
                user.chat = user_to_message
                while (message_condition):
                    message_to_send = input('>')
                    if message_to_send == 'close':
                        message_condition = False
                    else:
                        user.direct_message(person_to_message, message_to_send)
                        user.process(timeout=3)
            else:
                print("Contact doesnt exist")
            user.chat = None
        elif option == '5':
            room = input("Room: ")
            user.muc_join(room)
            user.process(timeout=5)
            while True:
                try:
                    msg = input('> ')
                    if msg == 'close':
                        break
                    user.muc_send_message(msg)
                    user.process(timeout=3)
                except:
                    continue
            user.muc_exit()
            user.process(timeout=5)
        elif option == '6':
            status= input("Status: ")
            status_message = input("Status message: ")
            user.change_presence(status, status_message)
            user.process(timeout=3)
        elif option == '9':
            """ condition = False """
            if user.is_connected():
                user.disconnect()
            user = None
    else:
        option = input('''1.Create User\n2. Login\n3.Delete account\n4. Exit\nIngrese una opcion: ''')
        if option == '1':
            jid = input('Username: ')
            password  = input('Password: ')
            """ args.jid = 'pad19200@alumchat.fun'
            args.password  = 'clabe1' """

            response = createUser(jid, password)
            if response:
                print('User finally created')
                user = Client(jid, password, 'Available', 'HELLO')
                user.connect()
                user.process(timeout=3)
            else:
                print('Failed to create user')

        elif option == '2':
            """ jid = input('Username: ')
            password  = input('Password: ') """
            """ args.jid = 'pad19200@alumchat.fun'
            args.password  = 'clabe1' """
            """ jid = 'prueba23@alumchat.fun'
            password  = 'prueba23' """
            jid = 'prueba100@alumchat.fun'
            password  = 'prueba100'
            """ jid = 'otrapr@alumchat.fun'
            password  = 'otrapr' """
            """ jid = 'coco@alumchat.fun'
            password  = 'coco1' """

            user = Client(jid, password, 'Available', 'HELLO')
            user.connect()
            user.process(timeout=3)
        elif option == '3':
            username = input("Username: ")
            password = input("Password: ")
            user = UnregisterClient(username, password)
            user.connect()
            user.process(timeout=5)
            user = None
        elif option == '4':
            condition = False
