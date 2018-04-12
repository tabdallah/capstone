import multiprocessing
import Queue
import puck_tracker as pt
import user_interface as ui

if __name__ == '__main__':
    # create queues for bidirectional communication with other processes
    ui_rx = multiprocessing.Queue()
    ui_tx = multiprocessing.Queue()
    pt_rx = multiprocessing.Queue()
    pt_tx = multiprocessing.Queue()
    
    # create seperate processes for the UI and Puck Tracker and give them Queues for IPC
    ui_process = multiprocessing.Process(target=ui.ui_process, name="ui", args=(ui_rx, ui_tx))
    pt_process = multiprocessing.Process(target=pt.pt_process, name="pt", args=(pt_rx, pt_tx))
        
    # start child processes
    ui_process.start()
    pt_process.start()
    
    #pt_rx.put("pt_state_cmd_calibrate")
    pt_rx.put("pt_state_cmd:track")
    #ui_rx.put("RunUI")
    
    # read messages
    while True:
        try:
            pt_data = pt_tx.get(False)
        except Queue.Empty:
            pt_data = 0
        else:
            print pt_data
        
        try:
            ui_data = ui_tx.get(False)
        except Queue.Empty:
            ui_data = 0
        else:
            print ui_data