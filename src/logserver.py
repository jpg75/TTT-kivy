'''
Created on 05/mar/2015

@author: Gian Paolo Jesi
'''

# install_twisted_rector must be called before importing
import glob
from config import Configuration
from util.tttaggregate import aggregate
from kivy.config import Config
from kivy.support import install_twisted_reactor
from kivy.properties import ObjectProperty
from kivy.app import App
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup

install_twisted_reactor()

from twisted.internet import reactor 
from net.protocols import TTTMulticastDiscoveryCI, LogProtocolFactory


class LogServer(AnchorLayout):
    panel = ObjectProperty()

    def save_on_press_callback(self):
        """Use ttt-aggregate service to aggregate multi player runs.
        """
        i_files = glob.glob('./logoutput-MOVES-*')  # input  files
        n = aggregate(i_files, 'aggregated_output.txt')
        self.show_aggregation_result(n)
    
    def show_aggregation_result(self, howmany):
        popup = Popup(title='Aggregation result', size_hint=(0.7, 0.7))
        l = BoxLayout(orientation='vertical')
        l.add_widget(Label(text='Processed %d distinct hands' % (howmany), font_size='25sp'))
        popup.add_widget(l)        
        popup.open()        
        
    def info_on_press_callback(self):
        pass
     
    def generate_panel_tab(self, txt):
        tpi = TabbedPanelItem(text=txt)
        tpi.content = TextInput(text='Waiting data...', readonly=True)                           
                                         
        self.panel.add_widget(tpi)


class LogServerApp(App):
    s = None
    port = 8080  # server listening port
    service_p = None
    
    def build(self):
        server = LogServer()
        cfg = Configuration(config_file='server-config.txt')
        cfg.purgelines()
        cfg.initialize()
        
        try:
            reactor.listenTCP(LogServerApp.port, LogProtocolFactory(self,
                        server_shoe_file='data/' + cfg.getParam('shoe_file'), 
                        users_shoe_file='data/' + cfg.getParam('users_shoe_file')))
            
            LogServerApp.service_p = TTTMulticastDiscoveryCI(TTTMulticastDiscoveryCI.MODES['server'], LogServerApp.port)
            reactor.listenMulticast(TTTMulticastDiscoveryCI.PORT, LogServerApp.service_p, listenMultiple=True)
        except Exception as e:
            print e
            pass
        
        LogServerApp.s = server
        return server
    
    def handle_message(self, msg, name, username):
        c = None
        # print msg
        
        if msg.startswith('login'):
            return msg
        
        for item in LogServerApp.s.panel.tab_list:
            print "text ", item.text
            if item.text == username:
                c = item.content
                break
            
        if c.text == 'Waiting data...':
            c.text = msg.strip() + '\n'
        else:
            c.text += msg.strip() + '\n'
            
        return msg

    def new_client(self, label_name):
        """On connection generate a new tabbed panel.
        """
        LogServerApp.s.generate_panel_tab(label_name)

    def client_leave(self, tab_name):
        """On client leave, remove the corresponding panel.
        """
        c = None
        for item in LogServerApp.s.panel.tab_list:
            # print "text ", item.text
            if item.text == tab_name:
                c = item
                break
        
        if c != None:
            LogServerApp.s.panel.remove_widget(c)
    
    
if __name__ == '__main__':
    Config.set('graphics', 'fullscreen', '0') 
    LogServerApp().run()
    
