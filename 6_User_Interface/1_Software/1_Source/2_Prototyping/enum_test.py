import multiprocessing as mp 
from enum import Enum
import json

def enum(list):
    enums = dict(zip(list, range(len(list))))
    return type('Enu', (), enums)


if __name__ == "__main__":
    
    with open("enum.json", 'r') as fp:
        enums = json.load(fp)
        fp.close()

    print str(enums['puck_tracker_state_enum'])

    state = enum(enums['puck_tracker_state_enum'])


    print state.calibrate
            
    #proc = mp.Process(target=thing, args=[s])
    #proc.start()


    #print s[:]
