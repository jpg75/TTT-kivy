'''
Created on 30/jan/2015

@author: Gian Paolo Jesi
'''

from argparse import ArgumentParser
import os

def main(parser):
    args = vars(parser.parse_args())
    
            
    if len(args) == 0:
        parser.print_help()
        
    else: 
        aggregate(args['input_file'], args['output_file'])
        
        
def aggregate(input_files=[], output_file='aggregated-output.txt',
              companion_file='aggregated-output-companion.txt'):
    """Actually aggregate the files in input. The input must be a list. 
    I no files are provided, nothing is done.
    
    Return the number of hands processed.
    """
    user_data = dict() # maps <user> -> { <hand> -> <seq> }
    ordered_hands = [] # hands in the order they appear
    current_hand = None
    usernames = [] # user names in the order they appear (alphabetical since it is file based
    
    for ifile in input_files:
        # get the user names from the filename
        split_res = ifile.split('-')
        name = split_res[2]
        usernames.append(name)
        user_data[name] = dict()
        
        for line in file(ifile):
            line = line.strip('-')
                
            if line == '' or line == '\n':  # skip empty lines
                continue
                
            if line.find(' ') != -1:    
                current_hand = line
                current_hand = current_hand.strip()
                
                # keep track of the hands order:
                if not current_hand in ordered_hands:
                    ordered_hands.append(current_hand)
                    
                    print "Found hand: ", current_hand
                
            else:
                # a move list
                if current_hand != None:
                    # data[current_hand].append(line)
                    line = line.strip()
                    user_data[name][current_hand] = line
                else:
                    print "Found a moves description, but not a corresponding hand!"
          
    print "Processed %d distinct hands." % len(ordered_hands)
    
    
    for hand in ordered_hands:
        with open(output_file, 'a') as f:
            f.write(hand + os.linesep + os.linesep)
            
            for user in usernames:
                if user_data[user].has_key(hand):
                    f.write(user_data[user][hand] + os.linesep)
                else:
                    # when the corresponding hand is not available for the current peer name 
                    f.write('NA' + os.linesep) 
            f.write(os.linesep)    
    
           
    # actually writes the companion file
    with open(companion_file, 'a') as f:
        for item in usernames:
            f.write(item + os.linesep)
            
    return len(ordered_hands)


if __name__ == '__main__':
    parser = ArgumentParser(description="""TTT aggregate \n
                            Aggregates multiple TTT game output into a single output (file) in Nemik format.
                            """)

    parser.add_argument('input_file', metavar='in-file', type=str, nargs='+',
                   help='an input file in Nemic format')
    
    parser.add_argument('output_file', metavar='out-file', type=str, help="the output filename")
    
    main(parser)
    
