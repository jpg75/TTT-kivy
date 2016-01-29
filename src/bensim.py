'''
Created on 24/ott/2014

@author: giampa
'''
# install_twisted_rector must be called before importing the reactor
from kivy.support import install_twisted_reactor
install_twisted_reactor()
from twisted.internet import reactor
from net.protocols import TTTMulticastDiscoveryCI, LogClientFactory

from config import Configuration
from kivy.app import App
from kivy.lang import Builder
from kivy.config import Config
from kivy.clock import Clock
from tttgame import TTTGame


Builder.load_file('gametable.kv')
Builder.load_file('bottombar.kv')    
Builder.load_file('popups.kv')

class TTTGameApp(App):
    connection = None
    g = None

    def build(self):
        global g 
        self.nr = 0
        self.config = Configuration()
        self.config.purgelines()
        self.config.initialize()
        game = TTTGame()
        self.g = game
                
        self.mp = TTTMulticastDiscoveryCI(TTTMulticastDiscoveryCI.MODES['client'])
            
        reactor.listenMulticast(TTTMulticastDiscoveryCI.PORT, self.mp, listenMultiple=True)
        
        Clock.schedule_once(lambda dt: game.post_init())
        Clock.schedule_once(lambda dt: self.discover_server(), 1)
        return game

    def connect_to_server(self, host, port):
        reactor.connectTCP(host, port, LogClientFactory(self))
        # reactor.connectTCP(host, port, EchoClientFactory(self))   
    
    def on_connection(self, connection):
        self.connection = connection
        print 'Connected to server!'
        self.g.console.text += 'Connected to server %s\n' % connection.transport.getPeer()
        
        self.g.connection_popup.quit()
        self.login()
    
    def login(self):
        self.g.show_login_popup()
        
    def on_connection_failed(self, reason):
        self.g.connection_popup.update_label(' Connection FAILED')
        
    def send_message(self, data):
        """Send the whole data content to the connection handle.
        """
        if data and self.connection:
            self.connection.sendLine(str(data))

    def discover_server(self):
        if self.nr < 3: 
            if len(self.mp.servers) == 0:
                print "No servers yet"
                self.mp.query()
                Clock.schedule_once(lambda dt: self.discover_server(), 5)
                self.nr += 1
            else:
                ips = self.mp.servers.keys()
                # print 'Discovered server: %s at port %d\n' % (ips[0], self.mp.servers[ips[0]])
                self.g.console.text += 'Discovered server: %s @ port %d\n' % (ips[0], self.mp.servers[ips[0]])
                self.connect_to_server(ips[0], self.mp.servers[ips[0]])
        else:
            print "Multicast failed, trying direct connection..."
            self.connect_to_server(self.config.getParam('server'), int(self.config.getParam('server_port')))
            
        
    def receive(self, msg):
        if msg.startswith('ask_reply'):
            lines = msg.split('\n')
            lines = [x for x in lines if x != '' and not x.startswith('#') and 
                     not x.startswith('//') ]
            print lines[1:]
            self.g.shoe_config.content = lines[1:]
            self.g.total_runs = len(self.g.shoe_config.content) # updates counter in GUI
            # g.console.text += msg + '\n'
            
    def log(self, msg, log='MOVES',):
        self.send_message('log:' + log)
        self.send_message(msg)
        
        
if __name__ == '__main__':
    #from kivy.core.window import Window
    #Window.size = (1280, 720)
    #Window.fullscreen = True
    Config.set('graphics', 'fullscreen', '0')  # fullscreen mode
    TTTGameApp().run()
    
