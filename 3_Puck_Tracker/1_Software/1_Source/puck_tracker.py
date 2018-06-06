# import necessary modules
import cv2
import sys
import numpy as np
import Queue
import json
import time

# define global variables
settings_path = "../../../6_User_Interface/1_Software/4_Json/"
last_puck_position_mm_x = 0
last_puck_position_mm_y = 0
last_time = 0
table_width_mm = 774.7
table_length_mm = 1692.275
puck_minimum_area = 300
puck_maximum_area = 500
puck_minimum_radius = 10
puck_maximum_radius = 20
camera_vertical_resolution = 480
camera_horizontal_resolution = 640
camera_fps = 224

def get_puck_tracker_settings():
    """Get the stored settings for the puck tracker"""
    global puck_lower_hsv
    global puck_upper_hsv
    global fiducial_lower_hsv
    global fiducial_upper_hsv
    global fiducial_coordinates

    with open((settings_path + "settings.json"), 'r') as fp:
        settings = json.load(fp)
        fp.close()

    puck_lower_hsv = (settings['puck_tracker']['puck']['color']['hue']['lower'],
                      settings['puck_tracker']['puck']['color']['sat']['lower'],
                      settings['puck_tracker']['puck']['color']['val']['lower'])
    puck_upper_hsv = (settings['puck_tracker']['puck']['color']['hue']['upper'],
                      settings['puck_tracker']['puck']['color']['sat']['upper'],
                      settings['puck_tracker']['puck']['color']['val']['upper'])
    
    fiducial_lower_hsv = (settings['puck_tracker']['fiducial']['color']['hue']['lower'],
                          settings['puck_tracker']['fiducial']['color']['sat']['lower'],
                          settings['puck_tracker']['fiducial']['color']['val']['lower'])
    fiducial_upper_hsv = (settings['puck_tracker']['fiducial']['color']['hue']['upper'],
                          settings['puck_tracker']['fiducial']['color']['sat']['upper'],
                          settings['puck_tracker']['fiducial']['color']['val']['upper'])
    
    fiducial_coordinates = np.array([
        [settings['puck_tracker']['fiducial']['coordinates']['tl']['x'],
         settings['puck_tracker']['fiducial']['coordinates']['tl']['y']],
        [settings['puck_tracker']['fiducial']['coordinates']['tr']['x'],
         settings['puck_tracker']['fiducial']['coordinates']['tr']['y']],
        [settings['puck_tracker']['fiducial']['coordinates']['br']['x'],
         settings['puck_tracker']['fiducial']['coordinates']['br']['y']],
        [settings['puck_tracker']['fiducial']['coordinates']['bl']['x'],
         settings['puck_tracker']['fiducial']['coordinates']['bl']['y']]], dtype = "float32")

def get_puck_position(frame):
    """Get the location of the puck in x, y coordinates (mm)"""
    global puck_position_mm_x
    global puck_position_mm_y

    # convert the frame to HSV color space
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # create a mask for the puck color
    puck_mask = cv2.inRange(frame_hsv, puck_lower_hsv, puck_upper_hsv)

    # apply median blur filter
    puck_mask_filtered = cv2.medianBlur(puck_mask, 5)

    # find contours in the mask
    contour_list = cv2.findContours(puck_mask_filtered.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    
    # proceed if a contour is found
    if len(contour_list) > 0:
        puck_found = False
        for contour in contour_list:
            contour_area = cv2.contourArea(contour)
            if puck_minimum_area < contour_area < puck_maximum_area:
                ((x, y), radius) = cv2.minEnclosingCircle(contour)
                if puck_minimum_radius < radius < puck_maximum_radius:
                    puck_sized_contour = contour
                    puck_found = True
                    break

        if puck_found:      
            M = cv2.moments(puck_sized_contour)
            if M["m00"] != 0:
                puck_center_coords = (M["m10"] / M["m00"], M["m01"] / M["m00"])
                cv2.circle(frame, (int(puck_center_coords[0]), int(puck_center_coords[1])), int(radius + 2), (0, 255, 255), 2)
                puck_position_mm_x = puck_center_coords[0]*mm_per_pixel_x
                puck_position_mm_y = puck_center_coords[1]*mm_per_pixel_y

    return frame

def get_puck_velocity():
    """Get the puck velocity in x, y coordinates (mmps)"""
    global puck_velocity_mmps_x
    global puck_velocity_mmps_y
    global last_puck_position_mm_x
    global last_puck_position_mm_y
    global last_time
    
    current_puck_position_mm_x = puck_position_mm_x
    current_puck_position_mm_y = puck_position_mm_y
    current_time = time.time()
    travel_time = current_time - last_time
    
    if current_puck_position_mm_x != 0 and last_puck_position_mm_x != 0:
        distance_traveled_mm_x = current_puck_position_mm_x - last_puck_position_mm_x
        puck_velocity_mmps_x = distance_traveled_mm_x / travel_time
    
    if current_puck_position_mm_y != 0 and last_puck_position_mm_y != 0:
        distance_traveled_mm_y = current_puck_position_mm_y - last_puck_position_mm_y
        puck_velocity_mmps_y = distance_traveled_mm_y / travel_time
    
    last_puck_position_mm_x = current_puck_position_mm_x
    last_puck_position_mm_y = current_puck_position_mm_y
    last_time = current_time

def get_mm_per_pixel_factors():
    """Get the scaling factors for mm per pixel conversion"""
    global mm_per_pixel_x
    global mm_per_pixel_y

    (tl, tr, br, bl) = fiducial_coordinates
    
    mm_per_pixel_x = table_length_mm/(br[0] - bl[0])
    mm_per_pixel_y = table_width_mm/(bl[1] - tl[1])

def get_perspective_transform_matrix():
    """Get the calculated perspective transform matrix for perspective correction"""
    global max_frame_width
    global max_frame_height
    global perspective_transform_matrix

    (tl, tr, br, bl) = fiducial_coordinates

    # compute the width of the new image, which will be the
    # maximum distance between bottom-right and bottom-left
    # x-coordiates or the top-right and top-left x-coordinates
    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_frame_width = max(int(width_a), int(width_b))

    # compute the height of the new image, which will be the
    # maximum distance between the top-right and bottom-right
    # y-coordinates or the top-left and bottom-left y-coordinates
    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_frame_height = max(int(height_a), int(height_b))

    # now that we have the dimensions of the new image, construct
    # the set of destination points to obtain a "birds eye view",
    # (i.e. top-down view) of the image, again specifying points
    # in the top-left, top-right, bottom-right, and bottom-left
    # order
    destination = np.array([
            [0, 0],
            [max_frame_width - 1, 0],
            [max_frame_width - 1, max_frame_height - 1],
            [0, max_frame_height - 1]], dtype = "float32")

    # compute the perspective transform matrix
    perspective_transform_matrix = cv2.getPerspectiveTransform(fiducial_coordinates, destination)

def find_fiducials(frame):
    """Locate the fiducials marking the playing surface and save their coordinates"""
    ret = False
    
    # array to hold the 4 fiducial coordinates (x, y)
    fiducials = [0, 0, 0, 0]

    # convert the frame to HSV color space
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # create a mask for the fiducial color
    fiducial_mask = cv2.inRange(frame_hsv, fiducial_lower_hsv, fiducial_upper_hsv)

    # apply a median blur filter to the mask (helps with image noise)
    fiducial_mask_filtered = cv2.medianBlur(fiducial_mask, 5)

    # find contours in the mask
    contour_list = cv2.findContours(fiducial_mask_filtered.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

    # proceed if a contour is found
    if len(contour_list) > 0:
        for contour in contour_list:
            # find the minimum enclosing circle for the contour
            ((x, y), radius) = cv2.minEnclosingCircle(contour)

            # use moments to find an accurate centroid for the fiducial
            M = cv2.moments(contour)
    
            # check for divide by zero
            if M["m00"] != 0:
                fiducial_center = (M["m10"] / M["m00"], M["m01"] / M["m00"])

                if (fiducial_center[0] < (camera_horizontal_resolution/2)) and (fiducial_center[1] < (camera_vertical_resolution)/2):
                    fiducials[0] = fiducial_center
                elif (fiducial_center[0] > (camera_horizontal_resolution/2)) and (fiducial_center[1] < (camera_vertical_resolution)/2):
                    fiducials[1] = fiducial_center
                elif (fiducial_center[0] > (camera_horizontal_resolution/2)) and (fiducial_center[1] > (camera_vertical_resolution)/2):
                    fiducials[2] = fiducial_center
                elif (fiducial_center[0] < (camera_horizontal_resolution/2)) and (fiducial_center[1] > (camera_vertical_resolution)/2):
                    fiducials[3] = fiducial_center
                else:
                    pass

        if 0 in fiducials:
            ret = False
        else:
            ret = True
            
            # if all coordinates for the playing surface are found, save to json
            with open((settings_path + "settings.json"), 'r') as fp:
                settings = json.load(fp)
                fp.close()
            
            settings['puck_tracker']['fiducial']['coordinates']['tl']['x'] = fiducials[0][0]
            settings['puck_tracker']['fiducial']['coordinates']['tl']['y'] = fiducials[0][1]
            settings['puck_tracker']['fiducial']['coordinates']['tr']['x'] = fiducials[1][0]
            settings['puck_tracker']['fiducial']['coordinates']['tr']['y'] = fiducials[1][1]
            settings['puck_tracker']['fiducial']['coordinates']['br']['x'] = fiducials[2][0]
            settings['puck_tracker']['fiducial']['coordinates']['br']['y'] = fiducials[2][1]
            settings['puck_tracker']['fiducial']['coordinates']['bl']['x'] = fiducials[3][0]
            settings['puck_tracker']['fiducial']['coordinates']['bl']['y'] = fiducials[3][1]
            
            with open((settings_path + "settings.json"), 'w+') as fp:
                json.dump(settings, fp, indent=4)
                fp.close()
                    
    return ret

def enum(list):
    enums = dict(zip(list, range(len(list))))
    return type('Enum', (), enums)

def get_enums():
    global pt_state_cmd_enum
    global pt_state_enum
    global pt_error_enum
    global pt_rx_enum
    global pt_tx_enum

    # get settings from file
    with open((settings_path + 'settings.json'), 'r') as fp:
        settings = json.load(fp)
        fp.close()

    pt_state_cmd_enum = enum(settings['puck_tracker']['enumerations']['pt_state_cmd'])
    pt_state_enum = enum(settings['puck_tracker']['enumerations']['pt_state'])
    pt_error_enum = enum(settings['puck_tracker']['enumerations']['pt_error'])   
    pt_rx_enum = enum(settings['puck_tracker']['enumerations']['pt_rx'])
    pt_tx_enum = enum(settings['puck_tracker']['enumerations']['pt_tx'])

"""----------------------------Puck Tracker Process--------------------------"""
def pt_process(pt_rx, pt_tx, visualization_data):
    """All things puck tracker happen here. Communicates directly with master controller"""
    # collect enums
    get_enums()

    while True:
        video_stream = cv2.VideoCapture(0)
        if video_stream.isOpened() == True:
            video_stream.set(cv2.CAP_PROP_FRAME_WIDTH, camera_horizontal_resolution)
            video_stream.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_vertical_resolution)
            video_stream.set(cv2.CAP_PROP_FPS, camera_fps)
            break
        else:
            pt_tx[pt_tx_enum.state] = pt_state_enum.error
            pt_tx[pt_tx_enum.error] = pt_error_enum.camera
    
    pt_state = pt_state_enum.idle
    pt_error = pt_error_enum.idle
    calibration_attempts = 0
    
    while True:
        # retrieve commands from master controller
        mc_cmd = int(pt_rx[pt_rx_enum.state_cmd])
        color_lower = (int(pt_rx[pt_rx_enum.lower_hue]),
                       int(pt_rx[pt_rx_enum.lower_sat]),
                       int(pt_rx[pt_rx_enum.lower_val]))
        color_upper = (int(pt_rx[pt_rx_enum.upper_hue]),
                       int(pt_rx[pt_rx_enum.upper_sat]),
                       int(pt_rx[pt_rx_enum.upper_val]))

        # set state of puck tracker to that commanded by mc and do required setup   
        if mc_cmd == pt_state_cmd_enum.calibrate and pt_state != pt_state_enum.calibrate:
            pt_state = pt_state_enum.calibrate    
            # update settings
            get_puck_tracker_settings()
        elif mc_cmd == pt_state_cmd_enum.track and pt_state != pt_state_enum.tracking::
            pt_state = pt_state_enum.tracking
            # update settings
            get_puck_tracker_settings()
            get_mm_per_pixel_factors()
            get_perspective_transform_matrix()
        elif mc_cmd == pt_state_cmd_enum.find_fiducials_puck and pt_state != pt_state_enum.find_fiducials_puck:
            pt_state = pt_state_enum.find_fiducials_puck
        elif mc_cmd == pt_state_cmd_enum.idle and pt_state != pt_state_enum.idle:
            pt_state = pt_state_enum.idle   
        elif mc_cmd == pt_state_cmd_enum.quit and pt_state != pt_state_enum.quit:
            pt_state = pt_state_enum.quit
        else:
            pass
        
        # perform puck tracker state tasks
        if pt_state == pt_state_enum.calibrate:
            ret, frame = video_stream.read()
            if ret == False:
                pt_tx[pt_tx_enum.error] = pt_error_enum.camera
                
            fiducials_found = find_fiducials(frame)
            
            if fiducials_found:
                pt_state = pt_state_enum.calibrated
                calibration_attempts = 0
            else:
                calibration_attempts += 1

            if calibration_attempts >= 5:
                pt_state = pt_state_enum.error
                pt_error = pt_error_enum.calibration_failed
                calibration_attempts = 0            
        elif pt_state == pt_state_enum.tracking:
            ret, frame = video_stream.read()
            if ret == False:
                pt_tx[pt_tx_enum.error] = pt_error_enum.camera
            
            frame_warped = cv2.warpPerspective(frame, perspective_transform_matrix, (max_width, max_height), cv2.INTER_LINEAR)
            frame = get_puck_position(frame_warped)
            get_puck_velocity()

            pt_tx[pt_tx_enum.puck_position_x] = puck_position_mm_y
            pt_tx[pt_tx_enum.puck_position_y] = puck_position_mm_x
            pt_tx[pt_tx_enum.puck_velocity_x] = puck_velocity_mmps_y
            pt_tx[pt_tx_enum.puck_velocity_y] = puck_velocity_mmps_x
    
            try:
                visualization_data.get_nowait()
                visualization_data.put(frame)
            except Queue.Empty:
                visualization_data.put(frame)
        elif pt_state == pt_state_enum.find_fiducials_puck:
            ret, frame = video_stream.read()
            if ret == False:
                pt_tx[pt_tx_enum.error] = pt_error_enum.camera

            frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            frame_mask = cv2.inRange(frame_hsv, color_lower, color_upper)            
            frame_mask_filtered = cv2.medianBlur(frame_mask, 5)
            frame = cv2.bitwise_and(frame, frame, mask=frame_mask_filtered)
            
            try:
                visualization_data.get_nowait()
                visualization_data.put(frame)
            except Queue.Empty:
                visualization_data.put(frame)
        elif pt_state == pt_state_enum.quit:
            pt_tx[pt_tx_enum.state] = pt_state_enum.quit
            video_stream.release() 
            cv2.destroyAllWindows()
            quit(0)

        # update state/error
        pt_tx[pt_tx_enum.error] = pt_error
        pt_tx[pt_tx_enum.state] = pt_state