import sys
import user_interface as ui
import multiprocessing
import Queue

if __name__ == '__main__':
    data_to_ui = multiprocessing.Queue()
    data_from_ui = multiprocessing.Queue()
    ui_process = multiprocessing.Process(target=ui.ui_process, name="ui", args=(data_to_ui, data_from_ui))
    ui_process.start()
    data_to_ui.put("ui_state_cmd:run_ui")

    while True:
        # get data from user interface
        try:
            ui_data = data_from_ui.get(False)
        except Queue.Empty:
            ui_data = 0
        else:
            print ui_data
