'''
Created on 27/ott/2014

@author: giampa
'''

import sys, time
import random
import itertools
from collections import deque
from os.path import dirname, abspath
from util.stopwatch import StopWatch
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.properties import NumericProperty, ObjectProperty, StringProperty, BooleanProperty, ListProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scatter import Scatter
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.animation import Animation
from kivy.graphics import Line, Color
from config import Configuration
from kivy.clock import Clock
import kivy.app as ap
    
class TTTGame(AnchorLayout):
    bottom_bar = ObjectProperty(None)
    game_table = ObjectProperty(None)
    side_bar = ObjectProperty(None)
    console = ObjectProperty(None)
    timer = ObjectProperty(None)
    hand = ListProperty()

    total_moves = NumericProperty(0)
    moves = NumericProperty(0)
    current_player = StringProperty('ck')  # instead of self.turn!
    run = NumericProperty(1)
    total_runs = NumericProperty()

    history_record = {'move': '', 'hand': '', 'up':'', 'target':''}
    
    game_card_file = StringProperty('data/card_back_blue.jpeg')
        
    """ Default covered cards for each position on table"""
    TTT_COVERED_CARDS_ZONES = {"Up Position": False, "DownC Position": True,
                               "DownN Position": True, "Target Position": False,
                               "Color Position": False, "Number Position": False}

    """'linear' card layout. See 'format' parameter in config file."""
    LINEAR_CARD_LAYOUT = ["DownC Position",
            "Color Position", "Up Position", "Target Position",
            "DownN Position", "Number Position" ]
    
    """'circular' card layout. This is the default format. See 'format'
    parameter in config file."""
    CIRCULAR_CARD_LAYOUT = ["Number Position",
            "DownN Position", "Up Position", "DownC Position",
            "Color Position", "Target Position" ]

    """file names for each card. The file holds the corresponding card picture.
    It follows the order in HOME_CARDS_COORDINATES"""
    cards_files = ["h2red.jpeg", "h3red.jpeg",
            "h4red.jpeg", "c2black.jpeg", "c3black.jpeg", "c4black.jpeg"]

    """card names, they corresponds to the card agent names"""
    cards_names = ["2H", "3H", "4H", "2C", "3C", "4C"]

    """zones names here follow the order in HOME_CARDS_COORDINATES array"""
    cards_zones_names = [ "Color Position", "Target Position", "Number Position",
                          "DownC Position", "Up Position", "DownN Position"]
        
    """Allowed zones in which players can exchange/move cards. The 'Target' zone
    is subjected to extra restrictions."""
    allowed_moving_zones = ["Up Position", "Target Position", "DownC Position",
                            "DownN Position"]
    
    """map zones -> moves"""
    ZONES_MOVES = {"Up Position": "u", "DownC Position" :"c",
                   "DownN Position": "n", "Target Position": "t", "Pass": "p"}


    """map card name -> card picture file"""
    cards_names_files = {"2H": "h2red.jpeg", "3H": "h3red.jpeg", "4H": "h4red.jpeg",
                         "2C": "c2black.jpeg", "3C": "c3black.jpeg", "4C": "c4black.jpeg"}
    
    """map card name -> color """
    cards_colors = {"2H": "red", "3H": "red", "4H": "red",
                         "2C": "black", "3C": "black", "4C": "black"}
    
    """map card name -> number """
    cards_numbers = {"2H": 2, "3H": 3, "4H": 4,
                         "2C": 2, "3C": 3, "4C": 4}
    
    
    """Map zone name -> card name. Tracks the zone in which a card is located.
    It is updated according to the game moves."""
    zones_cards = dict()
    
    help_txt = open('data/help_eng.txt', 'r').read()
    
    hand_history = []  # history related to the current hand
    
    def __init__(self, *pars, **kpars):
        AnchorLayout.__init__(self, *pars, **kpars)
        self.cur_dir = dirname(abspath('file'))
        config = Configuration()
        config.purgelines()
        config.initialize()
        
        # do not use '-' or other chars in the name!
        self.username = '' 
        
        self.turnables = config.getParam('turnable')
        self.cards_unturnable = bool(int(config.getParam('cards_unturnable')))
        
        # enables the automatic player agent, playing as NK as default. 
        self.auto_player = bool(int(config.getParam('auto_player')))
        
        self.format = config.getParam('format')
        self.help_file = config.getParam('help_file')
        self.shoe_file = config.getParam('shoe_file')
        
        self.srv = config.getParam('server')
        self.srv_port = config.getParam('server_port')
        
        if self.format == 'circular':
            self.turnable = dict(zip(TTTGame.CIRCULAR_CARD_LAYOUT, [bool(int(x)) for x in self.turnables.split(',') ]))
        else:
            self.turnable = dict(zip(TTTGame.LINEAR_CARD_LAYOUT, [bool(int(x)) for x in self.turnables.split(',') ]))
        
        self.timer_start = int(config.getParam('timer_start'))
            
        # load default shoe_file:
        self.shoe_config = Configuration(config_file=self.shoe_file)
        self.shoe_config.purgelines()
        
        # self.turn = ''  # current player turn
        self.current_target_card = ''  # the target card stated in the shoe_file ("2H" usually)
        
        print self.shoe_config.content
        
        self.hands = []  # store all hands
        # file names are in the form: output-<dmY>-<HM>.txt
        # Here we just create a reference. The actual obj is made when the login popup is dismissed
        self.fout_handle = None
        self.fout_time_handle = None
        
        self.timeHistory = []  # list holding the strings: <move> <time>\n
        self.stopwatch = StopWatch()
        
        self.nk_history_q = deque([], 2)  # nk history of the last 2 hands. Required for automatic agent
        self.ck_history_q = deque([], 2)  # ck history of the last 2 hands. Required for automatic agent

    def update(self, dt):
        pass

    def post_init(self):
        self.total_runs = len(self.shoe_config.content)  
        self.connection_popup = ConnectionPopup()
        self.connection_popup.open()
        # self.connection_popup()  
        # self.show_login_popup()
        # self.generate_hand()
    
    def count_down(self, seconds):
        """Manage the count down clock."""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        self.timer.text = "Timer: %d:%02d:%02d" % (h, m, s)
        
        if seconds > 0 :
            Clock.schedule_once(lambda dt: self.count_down(seconds - 1), 1);
        else:
            self.quit_popup()  # end game
        
    
    def save_local_data(self):
        """Save data locally about moves.
        The format is the following:
        <current hand>\n
        \n
        <moves>\n
        \n
        """
        hand_s = ''
        for x in self.hand[:6]:  # only first 6 elements
            hand_s = hand_s + x + ' '
        hand_s = hand_s.strip()
        self.fout_handle.write(hand_s + '\n\n')
        self.fout_handle.flush()
        
        s = ''
        for x in self.hand_history: 
            s = s + x
        s = s.strip()
        s = s.upper()
        self.fout_handle.write(s + '\n\n')
        self.fout_handle.flush()
        
        s = ''
        self.fout_time_handle.write(hand_s + '\n\n')
        for x in self.timeHistory:
            x = x.strip()
            x = x.upper()
            self.fout_time_handle.write(x + '\n')
            
        self.fout_time_handle.write('\n')
        self.fout_time_handle.flush()
        
    def save_data_remote(self):
        s = ''
        for x in self.hand[:6]:  # only first 6 elements
            s = s + x + ' '
        s = s.strip()
        
        s = s + '\n\n'
        
        h = ''
        for x in self.hand_history: 
            h = h + x
        h = h.strip()
        h = h.upper()

        # print h
        
        # s = s + h + '\n'
        ap.App.get_running_app().log(s + h + '\n', 'MOVES')
        
        
        for x in self.timeHistory:
            x = x.strip()
            x = x.upper()
            s = s + x + '\n'
        
        ap.App.get_running_app().log(s, 'TIMES')
        

    def cover_cards(self):
        """ Cover all cards on the table. Cards show the back picture file.
        """
        print "COVER CARDS"
        for w in self.game_table.children:
            print "child"
            if isinstance(w, CardWidget):
                print "covering: %s" % w.name
                w.to_front = False

    def show_cards(self, game_rules_on=False):
        """ Show all cards on the table. Cards show the front picture file.
        if 'game_rules_on', cards are turned face up only if the game rules allows.
        """
        for w in self.game_table.children:
            if isinstance(w, CardWidget):
                if game_rules_on:
                    if not TTTGame.TTT_COVERED_CARDS_ZONES[w.zone]:
                        print "card in zone %s moved to front" % w.zone
                        w.to_front = True
                    else:
                        print "card in zone %s moved to back" % w.zone
                        w.to_front = False
                        
                    if w.zone == 'Color Position' and self.current_player == 'nk':
                        w.to_front = False
                    
                    if w.zone == 'Number Position' and self.current_player == 'ck':
                        w.to_front = False
                    
                else:    
                    w.to_front = True             
                           
    def score(self, current_card=None, opponent_card=None, move='Pass'):
        """Score a valid move for the current player and updates the current player.
        The move is added to the history of moves.
        Cards in NumberKeeper and Colorkeeper positions are flip according to the
        current player.
        """
        self.moves += 1
        self.total_moves += 1
        move_time = self.stopwatch.split()    
        move_str = ''
        h_record = dict(TTTGame.history_record)  # make a new one
        
        # Search who is in the target and up positions 
        for w in self.game_table.children:
            if isinstance(w, CardWidget):
                if w.zone == 'Target Position':
                    cur_target = w.name
                elif w.zone == 'Up Position':
                    cur_up = w.name
                elif w.zone == 'Color Position' and self.current_player == 'ck':
                    cur_hand = w.name
                elif w.zone == 'Number Position' and self.current_player == 'nk':
                    cur_hand = w.name
                elif w.zone == 'DownC Position':
                    cur_c = w.name
                elif w.zone == 'DownN Position':
                    cur_n = w.name
                else:
                    print "Unmatched card zone string!"
        
        if current_card == None and opponent_card == None:
            move_str = TTTGame.ZONES_MOVES[move] + ' ' + self.stopwatch.to_string(move_time)                                                    
            
            TTTGame.hand_history.append(TTTGame.ZONES_MOVES[move])
            # No move, the same as before:
            h_record['move'] = TTTGame.ZONES_MOVES[move]
            h_record['up'] = cur_up
            h_record['target'] = cur_target
            h_record['hand'] = cur_hand
                
        else:
            move_str = TTTGame.ZONES_MOVES[current_card.zone] + ' ' + self.stopwatch.to_string(move_time)
            
            TTTGame.hand_history.append(TTTGame.ZONES_MOVES[current_card.zone])
            h_record['move'] = TTTGame.ZONES_MOVES[current_card.zone]
            # when the move is 't' or 'u', simply swap the card name in hand 
            # position (relative to the color or number keeper) with the respective position (target or up).
            if h_record['move'] == 't':
                h_record['up'] = cur_up
                h_record['target'] = cur_hand
                h_record['hand'] = cur_target
                
            elif h_record['move'] == 'u':
                h_record['up'] = cur_hand
                h_record['target'] = cur_target
                h_record['hand'] = cur_up
            
            elif h_record['move'] == 'n':
                h_record['up'] = cur_up
                h_record['target'] = cur_target
                h_record['hand'] = cur_n
                
            elif h_record['move'] == 'c':
                h_record['up'] = cur_up
                h_record['target'] = cur_target
                h_record['hand'] = cur_c
                
            else:
                print "Unmached move when extracting history situation."
                
        self.timeHistory.append(move_str) 
        
        # swap players for the next round:            
        if self.current_player == 'ck':
            self.ck_history_q.appendleft(h_record)
            self.current_player = 'nk'
        else:
            self.nk_history_q.appendleft(h_record)
            self.current_player = 'ck'
        
        self.adjust_keeper_cards()  # flip the opponent card
        self.adjust_cards_border()  # highlight the player card
        
        
    def adjust_cards_border(self):
        """ Highlight the player card's.
        """
        # resets for sure: not nice programming! :-(
        for w in [x for x in self.game_table.children if isinstance(x, CardWidget)]:   
            w.show_border(off=True)  # resets
            
        for w in [x for x in self.game_table.children if isinstance(x, CardWidget)]:   
            if w.zone == 'Color Position' and self.current_player == 'ck':
                w.show_border()
            
            elif w.zone == 'Number Position' and self.current_player == 'nk':
                w.show_border()
            
            else:
                # pass
                w.show_border(off=True)
               
        
    def adjust_keeper_cards(self):
        """Flip a keeper card according to the current player.
        """
        for w in [x for x in self.game_table.children if isinstance(x, CardWidget) 
                  and (x.zone == 'Color Position' or x.zone == 'Number Position')]:   
            
            if w.zone == 'Color Position' :
                if self.current_player == 'nk':
                    w.to_front = False
                else:
                    w.to_front = True
            
            if w.zone == 'Number Position':
                if self.current_player == 'ck':
                    w.to_front = False
                else:
                    w.to_front = True
    

    def generate_hand(self):
        """Generate a new handle from the description found in the shoe file.
        the hand is injected in the hand property.
        Before generating the handle:
        - manage the count-down clock.
        - save local and remote data
        - generate the popup to signal the new hand to the user
        """
        # self.cover_cards() 
        run_index = self.run - 1
        self.total_runs = len(self.shoe_config.content)
        
        if not self.stopwatch.running:
            self.stopwatch.start()
        
        if run_index < len(self.shoe_config.content):  # hand available
            if run_index >= 1:
                if self.stopwatch.running:
                    self.stopwatch.stop()
                
                self.save_local_data()
                self.save_data_remote()
                
                self.stopwatch.reset()
                self.stopwatch.start()
                            
            self.hand = self.shoe_config.content[run_index].split()
            cards = [x for x in self.game_table.children if isinstance(x, CardWidget)]
            
            # self.console.text += 'New hand: ' + str(self.hand[:6]) + '\n\n'
                
            print "New hand: ", self.hand
            nk = dn = up = dc = ck = t = gc = cur_player = ''
        
            if len(self.hand) != 8:
                print "Invalid line in shoe file '%s' : %s" % (self.shoe_file, self.hand)
            elif self.format == 'circular':
                nk, dn, up, dc, ck, t, gc, cur_player = self.hand
            else:  # linear layout
                dn, ck, up, t, dn, t, gc, cur_player = self.hand
                
            # self.turn = cur_player
            self.current_player = cur_player
            self.hand_history[:] = []  # resets the history for the next hand
            self.timeHistory[:] = []  # resets the time history of each move

            for c in cards:
                if c.zone == 'Color Position':
                    c.front_pic_file = 'data/' + TTTGame.cards_names_files[ck]
                    c.color = TTTGame.cards_colors[ck]
                    c.name = ck
                    c.number = TTTGame.cards_numbers[ck]
                elif c.zone == 'Target Position':
                    c.front_pic_file = 'data/' + TTTGame.cards_names_files[t]
                    c.color = TTTGame.cards_colors[t]
                    c.name = t
                    c.number = TTTGame.cards_numbers[t]
                    c.to_front = True
                elif c.zone == 'Number Position':
                    c.front_pic_file = 'data/' + TTTGame.cards_names_files[nk]
                    c.color = TTTGame.cards_colors[nk]
                    c.name = nk
                    c.number = TTTGame.cards_numbers[nk]
                elif c.zone == 'DownC Position':
                    c.front_pic_file = 'data/' + TTTGame.cards_names_files[dc]
                    c.color = TTTGame.cards_colors[dc]
                    c.name = dc
                    c.number = TTTGame.cards_numbers[dc]
                elif c.zone == 'Up Position':
                    c.front_pic_file = 'data/' + TTTGame.cards_names_files[up]
                    c.color = TTTGame.cards_colors[up]
                    c.name = up
                    c.number = TTTGame.cards_numbers[up]
                    c.to_front = True
                elif c.zone == 'DownN Position':
                    c.front_pic_file = 'data/' + TTTGame.cards_names_files[dn]
                    c.color = TTTGame.cards_colors[dn]
                    c.name = dn
                    c.number = TTTGame.cards_numbers[dn]
                 
                else: print "Warning: unknown position '%s'!" % c.zone
             
            
            # check if the card has changed before the popup
            if run_index >= 1:    
                if self.current_target_card != self.hand[6]:
                    self.intra_hand_popup(goal_changed=True)
                else:
                    self.intra_hand_popup()
                    
            self.game_card_file = 'data/' + TTTGame.cards_names_files[gc]
            self.current_target_card = gc
            self.show_cards(game_rules_on=True)
            self.adjust_cards_border()
            self.moves = 0  # reset current hand moves
        
        else:  # run out of runs!
            self.save_local_data()
            self.save_data_remote()

            self.quit_popup()
    
    def show_login_popup(self):
        l_popup = LoginPopup()
        l_popup.open()
        
    def intra_hand_popup(self, goal_changed=False):
        """Generate a popup to emphasize the start of a new hand.
        By clicking over the button, it disappears.
        """
        popup = Popup(title='Next Hand Window', size_hint=(0.3, 0.3))
        l = BoxLayout(orientation='vertical')
        if goal_changed:
            l.add_widget(Label(text='Your Goal card has changed', font_size='30sp'))
            
        l.add_widget(Button(text='Next hand', font_size='40sp', on_press=popup.dismiss))
        popup.add_widget(l)        
        popup.open()
                
    def quit_popup(self):
        popup = Popup(title='Score Summary Window', size_hint=(0.7, 0.7))
        l = BoxLayout(orientation='vertical')
        l.add_widget(Label(text='Game Over', font_size='40sp'))
        l.add_widget(Label(text='Total moves played: %d' % self.total_moves, font_size='25sp'))
        popup.add_widget(l)        
        popup.bind(on_dismiss=self.summary_popup_dismiss)
        popup.open()
        
        
    def summary_popup_dismiss(self, *pars):
        sys.exit()
    
    
    def help_on_press_callback(self):
        """Callback for 'help' button.
        """
        popup = Popup(title='Help Window',
                      content=TextInput(text=unicode(TTTGame.help_txt, errors='replace'),
                                        readonly=True, auto_indent=True, cursor=(1, 1)),
                      size_hint=(None, None), size=(400, 400))
        popup.open()
        
    def pass_on_press_callback(self):
        """Callback for 'pass' button.
        """
        self.score(None, None)
        
    def connect_on_press_callback(self):
        """Tries to connect to the server using first the network discovery service.
        If it fails, try the address in config.txt. 
        If it fails again: no connection.
        The exit status is displayed on the right console widget.
        """
        s = ap.App.get_running_app().mp.servers
        if s != None and len(s) >= 1:
            print "server found: %s" % s[0]
            self.srv = s[0] 
            # ap.App.get_running_app().connect_to_server(self.srv, 8080)
        # else:
        ap.App.get_running_app().connect_to_server(self.srv, 8080)
        

class ConnectionPopup(Popup):
    
    def quit(self):
        self.dismiss()
        
    def skip_connection(self):
        self.dismiss()
        ap.App.get_running_app().login()
        
    def update_label(self, reason):
        self.label.text = self.label.text + ' ' + reason
    
class LoginPopup(Popup):
    t_input = ObjectProperty(None)
    
    def quit(self):
        # print "Dismissing login popup"
        name = self.validate_callback()
        self.dismiss()
        
        # file names are in the form: output-<dmY>-<HM>.txt
        ap.App.get_running_app().g.fout_handle = open('output-' + name + '-' + 
                                time.strftime('%d%m%Y-%H%M') + '.txt', 'w')
        ap.App.get_running_app().g.fout_time_handle = open('output-time-' + name + '-' + 
                                     time.strftime('%d%m%Y-%H%M') + '.txt', 'w')
        # login on the server
        ap.App.get_running_app().send_message('login ' + name)
        
        # ask for shoe file if required:
        ask = bool(int(ap.App.get_running_app().config.getParam('ask_shoe')))
        if ask:  # ask for a shoe file
            ap.App.get_running_app().send_message('ask')
        
        # generate the new hand (1st):
        ap.App.get_running_app().g.generate_hand()
        
        # starts the count down clock:
        Clock.schedule_once(lambda dt: ap.App.get_running_app().g.
                            count_down(ap.App.get_running_app().g.timer_start))
    
    
    def validate_callback(self):
        if self.t_input.text != '':
            name = self.t_input.text.strip()
            ap.App.get_running_app().g.username = name
            ap.App.get_running_app().g.console.text += "Set username '%s'\n" % name
            return name
    
    def get_rand_user(self):
        return 'User%0.6d' % random.randint(0, 999999)
    
class SideBar(AnchorLayout):
    ttt = ObjectProperty(None)
    

class BottomBar(AnchorLayout):
    ttt = ObjectProperty(None)
        

class GameTable(RelativeLayout):
    ttt = ObjectProperty()
    
    
class CardWidget(Scatter):
    """Manage a card. The actual bitmaps are managed by an Image child.
    The CardWidget auto locate itself over the board according to its name.
    """
    source = StringProperty()
    start_flipped = BooleanProperty(False)  # USELESS! TODO: REMOVE IT!
    to_front = BooleanProperty(False)
    front_pic_file = StringProperty()
    # back_pic_file = StringProperty()
    zone = StringProperty()
    
    def __init__(self, **kargs):
        Scatter.__init__(self, **kargs)
        # self.front = True;
        self.back_pic_file = 'data/card_back_blue.jpeg'
        self.name = kargs.get('card_name', '')
        self.old_x, self.old_y = self.pos
        self.busy_anim = False
        self.color = None
        self.num = None
        self.moving = False
        self.selected = None
        self.border = None
        
    def on_start_flipped(self, instance, value):
        """Perform some final initialization such as saving the front card file.
        TODO: don't like this method. The 'to_front' property is sufficient.
        """
        self.front_pic_file = self.source
        self.source = self.back_pic_file
        self.front = False
    
    def on_to_front(self, instance, value):
        """Set a card to front or back. It is imperative: it ignores any game rule. 
        """
        self.to_front = value
        print "to front action: zone %s: value %s" % (self.zone, value)
        if value:  # true!
            self.source = self.front_pic_file
        else:  # false!
            self.source = self.back_pic_file

    def on_front_pic_file(self, instance, value):
        """Called when the front picture file is changed. The picture is 
        visualized as soon as the change happen.
        By default the card goes in front state (to_front property True). 
        """
        self.front_pic_file = value
        self.source = self.front_pic_file
        self.to_front = True
        
    def on_zone(self, instance, value):
        """Zone property change event. used to hide or show the card according 
        to position on the table. 
        """
        print "Card %s now in zone: %s" % (self.name, value)
        self.zone = value
        # Check the basic rules about cover/front: WARNING: the meaning of 
        # flip and covered is the opposite, this is why we have 'not'
        self.to_front = not TTTGame.TTT_COVERED_CARDS_ZONES[self.zone]
        if self.to_front:  # true!
            self.source = self.front_pic_file
        else:  # false!
            self.source = self.back_pic_file
        
    def show_border(self, off=False):
        """Draw a green rectangle around the card.
        """
        if off:
            if self.border:
                self.canvas.remove(self.border)
            
            self.border = None
            
        else:
            with self.canvas:
                Color(0.1, 1, 0.3)
                self.border = Line(rectangle=(0, 0, self.width + 5, self.height + 5),
                                    width=2)
                
             
    def select(self):
        """Commodity method, select the clicked card.
        """
        if not self.selected:
            self.old_x = self.x
            self.old_y = self.y
            self.selected = True
            
    def check_for_taps(self, touch):
        """Check for a DOUBLE tap. If detected, the card flips.
        Handles the rules for which a card can or cannot flip.
        """
        if touch.is_double_tap and not self.parent.parent.parent.cards_unturnable \
            and self.parent.parent.parent.turnable[self.zone]:
            if self.front:
                # flip the card from front to back
                self.source = self.back_pic_file
                self.front = False
            else:  # flip the card from back to front
                self.source = self.front_pic_file
                self.front = True
    
    def is_goal(self, card):
        """ Check whether the move accomplish the hand goal or not""" 
        if card.zone == 'Target Position' :
            if self.zone == 'Color Position' and self.color == card.color:
                print "card zone: %s , color: %s, other color: %s" % (self.zone, self.color, card.color)
                return True
            if self.zone == 'Number Position' and self.number == card.number:
                print "card zone: %s , color: %s, other color: %s" % (self.zone, self.number, card.number)
                return True
        
        return False
                
    def relocate(self, other_card):
        """Set the new zone for the current and companion card and set up the 
        animations for both cards.
        """
        temp_x = self.old_x
        temp_y = self.old_y
        # print "selfzone: ", self.zone
        temp_zone = self.zone 
        # print "tempzone: ", temp_zone
                        
        # print "w zone: ", other_card.zone
        anim1 = Animation(pos=other_card.pos, t='in_quad', d=0.5)
        anim2 = Animation(pos=(temp_x, temp_y) , t='in_quad', d=0.5)
        anim1.start(self)
        anim2.start(other_card)
        self.zone = other_card.zone
        other_card.zone = temp_zone

                
    def on_touch_down(self, touch):
        # self.check_for_taps(touch)
        # Only cards in NK or CK positions can move according to the player turn
        if self.collide_point(touch.x, touch.y):
            self.check_for_taps(touch)
            
            # tries to wait until the card is back on position
            if self.busy_anim:
                return super(CardWidget, self).on_touch_down(touch)
    
            # manage only number keeper as auto player!
            if self.parent.parent.parent.auto_player and self.parent.parent.parent.current_player == 'nk':
                return super(CardWidget, self).on_touch_down(touch)
             
            if ((self.zone == 'Color Position' and self.parent.parent.parent.current_player == 'ck')  \
                or (self.zone == 'Number Position' and self.parent.parent.parent.current_player == 'nk') or (self.zone == 'Color Position' and self.parent.parent.parent.current_player == 'ck')  \
                or (self.zone == 'Color Position' and self.parent.parent.parent.current_player == 'ck')):
                self.select()
           
                super(CardWidget, self).on_touch_down(touch)
                return True  # tell the parent we managed the event
        
        # otherwise propagate to children and return their response
        return super(CardWidget, self).on_touch_down(touch)
    
    
    def on_touch_up(self, touch):
        """Overloading method.
        All active widgets receive, in turn, this touch event and have to decide 
        if its relevant or not.
        Unfortunately, in our scenario, this event is relevant for two widgets 
        (cards) when they swap their position. This stems issues.
        We impose that the widget moved by the user is the 'master' and actually 
        manages the event. 
        """
        if (self.selected and self.collide_point(touch.x, touch.y)):
            relocated = False
            # check if it is over any other card:
            for w in self.parent.children:
                if w != self and isinstance(w, CardWidget):
                    if w.collide_point(touch.x, touch.y) and w.zone in TTTGame.allowed_moving_zones:  # collision!
                        if w.zone == 'Target Position' :
                            if self.is_goal(w):
                                # check if its is the current target
                                print "NAME: %s - target: %s" % (self.name, self.parent.parent.parent.current_target_card)
                                if self.name == self.parent.ttt.current_target_card:
                                    # ended current run!
                                    self.parent.ttt.run += 1
                                    self.parent.ttt.console.text += 'Hand successful!\n'
                                    Clock.schedule_once(lambda dt: self.parent.parent.parent.generate_hand())
                                    
                                self.relocate(w)
                                relocated = True
                                self.parent.ttt.score(self, w)
                                                                 
                        else:
                            self.relocate(w)
                            relocated = True
                            self.parent.ttt.score(self, w)
                        
            # if it is not a valid move, bring the card to the original position 
            if (not relocated and (self.x != self.old_x or self.y != self.old_y)):
                anim = Animation(x=self.old_x, y=self.old_y, t='in_quad', d=0.5)
                
                anim.bind(on_start=self.on_start_animation)
                anim.bind(on_complete=self.on_complete_animation)
                
                anim.start(self)
                
            self.selected = None
            super(CardWidget, self).on_touch_up(touch)
            return True  # tell the parent we managed the event
        
        # otherwise propagate to children and return their response
        return super(CardWidget, self).on_touch_up(touch)
    
    
    def on_touch_move(self, touch):
        """A card can only move if previously selected and if it has the mouse on it.
        Otherwise, the routing stops.
        """
        if self.selected:
            super(CardWidget, self).on_touch_move(touch)
            return True
        
        #=======================================================================
        # if self.selected and self.collide_point(touch.x, touch.y):
        #     super(CardWidget, self).on_touch_move(touch)
        #     return True
        #=======================================================================
        
        # return Scatter.on_touch_move(self, touch)
        # return super(CardWidget, self).on_touch_move(touch)
    
    def on_start_animation(self, instance, value):
        self.busy_anim = True
        
    def on_complete_animation(self, instance, value):
        self.busy_anim = False


class RuleParser(object):
    def __init__(self, file_name='data/arules.txt'):
        self.filename = file_name
        self.rules = []
        self.rates = dict()  # maps score -> [rule1, rule2,...]
    
    def load_rules(self):
        with open(self.filename) as f:
            lines = [line.rstrip('\n') for line in f]
        
        for line in lines:
            if line.startswith('#') or line.startswith('//') or line == '' or line.isspace():
                continue
            else:
                self.rules.append(line.split())

        # check the basics for rule correctness: length
        counter = 1
        for rule in self.rules:
            if len(rule) not in [4, 7, 11, 14, 18]:
                print "Warning: rule -%s- has non standard size: %d" % (str(rule), len(rule))
                       
            counter += 1   
        
        print "Rules loaded: ", len(self.rules)
    
    def match(self, hand, up, target, ck_knowledge, nk_knowledge, auto_player='nk',):
        """Calculate the rule match and return the rule to apply.
        The rule to apply is selected according to the rate scored.
        If multiple rules scored the same, then a rule is selected at random 
        """
        if not ck_knowledge:
            ckk = []
        else: 
            ckk = [ [i.get(k) for k in TTTGame.history_record.iterkeys() if k != 'hand'] for i in ck_knowledge]
        
        if not nk_knowledge:
            nkk = []
        else:
            nkk = [ [i.get(k) for k in TTTGame.history_record.iterkeys() ] for i in nk_knowledge]
        
        nksize = len(nkk) * 4
        cksize = len(ckk) * 3
        print "ckk: %s" % ckk
        print "nkk: %s" % nkk
        rl = [x for x in self.rules if len(x) - 1 <= cksize + nksize + 4]
        print "Size nk: %d , ck: %s" % (nksize, cksize)
        print "Avail rules:\n %s" % rl
        
        # makes a single list where alternatively puts ck_knowlodge and 
        # nk_knowledge elements 'hand' elements are removed from ck_knowledge
        iters = [iter(ckk), iter(nkk)]
        knowledge = [hand, up, target] + list(it.next() for it in itertools.cycle(iters))
        print "Knowledge: %s" % knowledge
            
        for rule in rl:
            score = 0    
            comparison = zip(rule[1:], knowledge)
            # print "COMPARING: %s"%comparison
            for r, k in comparison:
                if r == k:
                    score += 1
                elif r == '#':
                    pass
                else:
                    break  # goes to the next rule                    
                
                if self.rates.get(score):
                    self.rates[score].append(rule)
                else:
                    self.rates[score] = []
                    self.rates[score].append(rule)
            
        highest_score = max(self.rates.keys())
        result = self.rates[highest_score]
        print "Highest score: %d" % highest_score
        print "Result set is: %s" % result
        if len(result) == 1:
            return result[0]
        else: 
            return random.choice(result)
                    
    def show_rule_rates(self, how_many=5):
        txt = ''
        s = sorted(self.rates.iterkeys())
        for k in s[min(how_many, len(s))]:
            txt += self.rates[k] + '\n'
        
        return txt

#===============================================================================
# Debugging from console with:    
# 
# rp.match('3C','2C','4C',[{'hand':'2C','move':'U','up':'2H','target':'4C'}],[])
#===============================================================================
