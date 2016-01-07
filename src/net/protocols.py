'''
Created on 13/mar/2015

@author: Gian Paolo Jesi
'''

import time
from twisted.internet import protocol
from twisted.internet.protocol import DatagramProtocol
from twisted.protocols.basic import LineReceiver

class LogProtocol(LineReceiver):
    def __init__(self, factory):
        self.factory = factory
        self.users = self.factory.users  # ip_port -> username 
        self.files = self.factory.files  # ip_port -> file
        self.users_shoe = self.factory.users_shoe  # username ->specific shoe file
        self.name = ''  # name of the connection ip_port
        self.base_file_name = self.factory.base_file_name  # output base name
        self.current_fh = None  # actual file handle
         
        if self.factory.server_shoe_file:  # if not None
            self.shoe_lines = open(self.factory.server_shoe_file).readlines()
        
    def connectionMade(self):
        """At connection records the ip port tuple.
        """
        adr = self.transport.getPeer()
        self.name = adr.host + '_' + str(adr.port)
        print 'Connected ' + adr.host + '_' + str(adr.port)
        
    def connectionLost(self, reason):
        """If the user (ip:port) is present, it is removed and its corresponding 
        file is removed as well.  
        """
        if self.users.has_key(self.name):
            username = self.users[self.name]
            del self.users[self.name]
            
            if self.files[self.name]:
                for f in self.files[self.name].values():
                    f.close()
                    # self.files[self.name].close()  # close file
                
                del self.files[self.name]
            
            # TODO: would be better to hide this in the factory: notify the 
            # app that the connection is lost    
            self.factory.app.client_leave(username)
        

    def lineReceived(self, line):
        """The protocol itself. 
        Manages the login and ask for shoe_file procedure and logs to file all 
        the rest.
        """
        if line.startswith('login '):  # handle 'login' command
            # generates files for both moves and times
            username = line.replace('login ', '')
            username = username.strip()
            if username not in self.users.values():  # the same client can login once
                self.factory.app.new_client(username)
                self.users[self.name] = username
            
                fh_m = open(self.base_file_name + 'MOVES-' + username + '-' + self.name + '-' + 
                            time.strftime('%d%m%Y-%H%M') + '.txt', 'w')
                fh_t = open(self.base_file_name + 'TIMES-' + username + '-' + self.name + '-' + 
                  time.strftime('%d%m%Y-%H%M') + '.txt', 'w')
            
                self.files[self.name] = {'MOVES': fh_m, 'TIMES': fh_t}
                self.current_fh = fh_m
                self.factory.app.handle_message(line, self.name, self.users[self.name])
        
        elif line.startswith('ask'):  # sends the shoe_file
            lines = 'ask_reply\n'
            slines = ''
            
            # if the user is listed in the 'users.txt' file, 
            # then the corresponding she file is sent
            if self.users_shoe.get(self.users[self.name], None):
                print "Serving file: '%s' to user: '%s'" % (self.users_shoe[self.users[self.name]], self.users[self.name])
                slines = open(self.users_shoe[self.users[self.name]]).readlines()
            else:
                print "Serving file: '%s' to user '%s'" % (self.factory.server_shoe_file, self.users[self.name])
                slines = self.shoe_lines
            
            for item in slines:
                item = item.strip()
                lines += item + '\n'
                
            self.sendLine(lines)
        
        elif line.startswith('log:'):  # set the correct log where to write to
            log = line.replace('log:', '')
            if self.files[self.name].has_key(log):  # log file exists
                self.current_fh = self.files[self.name][log]
            else:  # create this new log file following the same signature
                fh = open(self.base_file_name + log + '-' + username + '-' + self.name + '-' + 
                  time.strftime('%d%m%Y-%H%M') + '.txt', 'w')
                self.users[self.name][log] = fh
                self.current_fh = fh
        
        # elif self.files[self.name][self.current_fh]:  # non login string are logged
        else:
            # self.files[self.name][self.current_fh].write(line + '\n')
            # self.files[self.name][self.current_fh].flush()
            self.current_fh.write(line + '\n')
            self.current_fh.flush()
            self.factory.app.handle_message(line, self.name, self.users[self.name])
        
        # if response:
        #    self.sendLine(response)


class LogProtocolFactory(protocol.Factory):
    protocol = LogProtocol
    
    def __init__ (self, app, base_file_name='logoutput-',
                  server_shoe_file="data/server-game.txt",
                  users_shoe_file="data/users.txt"):
        self.app = app
        self.base_file_name = base_file_name
        self.server_shoe_file = server_shoe_file
        self.users_shoe_file = users_shoe_file 
        self.users_shoe = {}  # map user names to a specific shoe file
        self.files = {}  # map users (ip_port string tuple) -> file handle
        self.users = {}  # map  ip_port tuple -> user names
        self._init_users_shoe()
    
    def _init_users_shoe(self):
        with open(self.users_shoe_file, 'r') as f:
            lines = f.read().splitlines()
            for line in lines:
                if line.startswith('#'):
                    continue
                items = line.split()
                self.users_shoe[items[0]] = items[1]
                print "Collecting user: '%s' bind to shoe file: '%s'" % (items[0], items[1])
        
    def buildProtocol(self, addr):
        return LogProtocol(self)

    
class LogClient(LineReceiver):
    """ A simple Client that send messages to the echo server"""

    def connectionMade(self):
        # passes the protocol instance to the app
        self.factory.app.on_connection(self) 

    def lineReceived(self, line):
        # LineReceiver.lineReceived(self, line)
        self.factory.app.receive(line) 
    

class LogClientFactory(protocol.ClientFactory):
    protocol = LogClient

    def __init__ (self, app):
        self.app = app
        
    def clientConnectionLost(self, conn, reason):
        # self.app.print_message("connection lost")
        print "connection lost"
        
    def clientConnectionFailed(self, conn, reason):
        self.app.on_connection_failed(reason)
        print "connection failed"

                
class TTTMulticastDiscoveryCI(DatagramProtocol):
    """This is the Client Initiated TTT discovery protocol based on multicast.
    The server waits for clients which broadcast a query.
    It replies with a multicast packet holding the application service port as
    a string.
    """
    PORT = 8005
    MULTICAST_ADDR = ('228.0.0.5', PORT)
    CMD_PING = "SRVQ"
    CMD_REPLY = 'SRVQ_R'
    MODES = {'client': 0, 'server': 1}

    def __init__(self, mode=MODES['client'], service_port=8080):
        self.mode = mode
        self.servers = dict()  # IP -> port
        self.service_port = service_port  # The port number over which the server is listening for the app protocol
        
    def startProtocol(self):
        """
        Called after protocol has started listening.
        """
        # Set the TTL>1 so multicast will cross router hops:
        self.transport.setTTL(5)
        # Join a specific multicast group:
        self.transport.joinGroup(TTTMulticastDiscoveryCI.MULTICAST_ADDR[0])

    def query(self, msg=CMD_PING):
        """Send the query to the server using multicast.
        """
        try:
            self.transport.write(msg, TTTMulticastDiscoveryCI.MULTICAST_ADDR)
        except Exception as e:
            print e
        
            
    def datagramReceived(self, datagram, address):
        print "Datagram %s received from %s, I am %s" % (repr(datagram),
                                                         repr(address), self.mode)
        
        if self.mode == TTTMulticastDiscoveryCI.MODES['server'] and \
            datagram.startswith(TTTMulticastDiscoveryCI.CMD_PING):
            # multicast reply to the client
            self.transport.write('%d' % self.service_port,
                                 TTTMulticastDiscoveryCI.MULTICAST_ADDR)
            
        elif self.mode == TTTMulticastDiscoveryCI.MODES['client'] and \
            not datagram.startswith(TTTMulticastDiscoveryCI.CMD_PING):
            adr = datagram.strip()
            if not self.servers.has_key(address[0]):
                self.servers[address[0]] = int(adr)


class EchoProtocol(protocol.Protocol):
    def __init__(self, factory, base_file_name='logoutput-'):
        self.factory = factory
        self.users = self.factory.users  # ip_port -> username 
        self.files = self.factory.files  # ip_port -> file
        self.name = ''  # name of the connection ip_port
        self.base_file_name = base_file_name
        
    def connectionMade(self):
        """At connection records the ip port tuple.
        """
        adr = self.transport.getPeer()
        # self.factory.app.new_client(adr)
        self.name = adr.host + '_' + str(adr.port)
        print 'Connected ' + adr.host + '_' + str(adr.port)
        
    def connectionLost(self, reason):
        if self.users.has_key(self.name):
            username = self.users[self.name]
            del self.users[self.name]
            
            if self.files[self.name]:
                self.files[self.name].close()  # close file
                del self.files[self.name]
                
            self.factory.app.client_leave(username)
        
                
    def dataReceived(self, data):
        """Return the full data including the line terminator.
        However, when writing to file, the line is stripped. 
        """
        if data.startswith('login '):
            username = data.replace('login ', '')
            username = username.strip()
            self.factory.app.new_client(username)
            fh = open(self.base_file_name + username + '-' + self.name + '-' + 
                  time.strftime('%d%m%Y-%H%M') + '.txt', 'w')
            self.users[self.name] = username
            self.files[self.name] = fh
        
        elif self.files[self.name]:  # non login string are logged
            self.files[self.name].write(data.strip() + '\n')
            self.files[self.name].flush()
            
        response = self.factory.app.handle_message(data, self.name, self.users[self.name])
        if response:
            self.transport.write(response)


class EchoFactory(protocol.Factory):
    protocol = EchoProtocol
    
    def __init__ (self, app):
        self.app = app
        self.files = {}  # map users (ip_port string tuple) -> file handle
        self.users = {}  # map  ip_port tuple -> user names
     
    def buildProtocol(self, addr):
        return EchoProtocol(self)    


class EchoClient(protocol.Protocol):
    """ A simple Client that send messages to the echo server"""

    def connectionMade(self):
        self.factory.app.on_connection(self.transport)

    def dataReceived(self, data):
        self.factory.app.print_message(data)


class EchoClientFactory(protocol.ClientFactory):
    protocol = EchoClient

    def __init__ (self, app):
        self.app = app

    def clientConnectionLost(self, conn, reason):
        self.app.print_message("connection lost")

    def clientConnectionFailed(self, conn, reason):
        self.app.print_message("connection failed")

