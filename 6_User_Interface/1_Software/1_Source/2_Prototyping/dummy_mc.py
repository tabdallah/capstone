import sys
import user_interface as ui
import puck_tracker as pt
import multiprocessing
import Queue

if __name__ == '__main__':
    data_to_ui = multiprocessing.Queue()
    data_to_pt = multiprocessing.Queue()
    data_from_ui = multiprocessing.Queue()
    data_from_pt = multiprocessing.Queue(1)
    data_visualization = multiprocessing.Queue()
    ui_process = multiprocessing.Process(target=ui.ui_process, name="ui", args=(data_to_ui, data_from_ui, data_visualization))
    pt_process = multiprocessing.Process(target=pt.pt_process, name="pt", args=(data_to_pt, data_from_pt, data_visualization))
    ui_process.start()
    pt_process.start()

    data_to_ui.put("ui_state_cmd:run_ui")
    data_to_pt.put("pt_state_cmd:track")

    while True:
        # get data from user interface
        try:
            ui_data = data_from_ui.get(False)
        except Queue.Empty:
            ui_data = 0
        else:
            if ui_data == "quitRequest":
                data_to_pt.put("pt_state_cmd:quit")
            print ui_data

        # get data from user interface
        try:
            pt_data = data_from_pt.get(False)
        except Queue.Empty:
            pt_data = 0
        else:
            print pt_data