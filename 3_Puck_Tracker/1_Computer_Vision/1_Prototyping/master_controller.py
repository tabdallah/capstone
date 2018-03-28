import multiprocessing
import Queue
import puck_tracker as pt
import user_interface as ui

if __name__ == '__main__':
    # create queues for bidirectional communication with other processes
    dataToUI = multiprocessing.Queue()
    dataFromUI = multiprocessing.Queue()
    dataToPT = multiprocessing.Queue()
    dataFromPT = multiprocessing.Queue()
    
    # create seperate processes for the UI and Puck Tracker and give them Queues for IPC
    uiProcess = multiprocessing.Process(target=ui.uiProcess, name="ui", args=(dataToUI, dataFromUI))
    ptProcess = multiprocessing.Process(target=pt.ptProcess, name="pt", args=(dataToPT, dataFromPT))
        
    # start child processes
    uiProcess.start()
    ptProcess.start()
    
    # read messages
    while True:
        try:
            ptData = dataFromPT.get(False)
        except Queue.Empty:
            ptData = 0
        else:
            print ptData
        
        try:
            uiData = dataFromUI.get(False)
        except Queue.Empty:
            uiData = 0
        else:
            print uiData