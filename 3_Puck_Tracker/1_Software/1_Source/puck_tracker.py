# import necessary modules
import cv2
import sys
import numpy as np
import Queue
import json
import time
import math
import matplotlib.pyplot as plt

# define global variables
settings_path = "../../../6_User_Interface/1_Software/4_Json/"
settings_file_path = "../../../3_Puck_Tracker/1_Software/1_Source/puck_tracker_settings.json"
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
pt_state_cmd_enum = 0
pt_state_enum = 0
pt_error_enum = 0
pt_rx_enum = 0
pt_tx_enum = 0

def get_puck_tracker_settings():
    """Return the stored settings for the puck tracker"""
    with open(settings_file_path, 'r') as fp:
        pt_settings = json.load(fp)
        fp.close()

    puck_lower_hsv = (pt_settings['puck']['color']['hue']['lower'],
                      pt_settings['puck']['color']['sat']['lower'],
                      pt_settings['puck']['color']['val']['lower'])
    puck_upper_hsv = (pt_settings['puck']['color']['hue']['upper'],
                      pt_settings['puck']['color']['sat']['upper'],
                      pt_settings['puck']['color']['val']['upper'])
    
    fiducial_lower_hsv = (pt_settings['fiducial']['color']['hue']['lower'],
                          pt_settings['fiducial']['color']['sat']['lower'],
                          pt_settings['fiducial']['color']['val']['lower'])
    fiducial_upper_hsv = (pt_settings['fiducial']['color']['hue']['upper'],
                          pt_settings['fiducial']['color']['sat']['upper'],
                          pt_settings['fiducial']['color']['val']['upper'])
    
    fiducial_coordinates = np.array([
        [pt_settings['fiducial']['coordinates']['tl']['x'],
         pt_settings['fiducial']['coordinates']['tl']['y']],
        [pt_settings['fiducial']['coordinates']['tr']['x'],
         pt_settings['fiducial']['coordinates']['tr']['y']],
        [pt_settings['fiducial']['coordinates']['br']['x'],
         pt_settings['fiducial']['coordinates']['br']['y']],
        [pt_settings['fiducial']['coordinates']['bl']['x'],
         pt_settings['fiducial']['coordinates']['bl']['y']]], dtype = "float32")

    return (puck_lower_hsv, puck_upper_hsv), (fiducial_lower_hsv, fiducial_upper_hsv), fiducial_coordinates

def get_puck_position(frame, puck_lower_hsv, puck_upper_hsv, mm_per_pixel_x, mm_per_pixel_y):
    """Return the location of the puck in x, y coordinates (mm)"""
    # convert the frame to HSV color space
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # create a mask for the puck color
    puck_mask = cv2.inRange(frame_hsv, puck_lower_hsv, puck_upper_hsv)

    # apply median blur filter
    puck_mask_filtered = cv2.medianBlur(puck_mask, 5)

    # find contours in the mask
    contour_list = cv2.findContours(puck_mask_filtered.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

    puck_position_mm_x = 0
    puck_position_mm_y = 0
    
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

    return frame, (puck_position_mm_x, puck_position_mm_y)

def get_puck_velocity(puck_position_mm_xy):
    """Return the puck velocity"""
    global last_puck_position_mm_x
    global last_puck_position_mm_y
    global last_time
    
    current_puck_position_mm_x = puck_position_mm_xy[0]
    current_puck_position_mm_y = puck_position_mm_xy[1]
    current_time = time.time()
    
    puck_velocity_mmps_x = 0
    puck_velocity_mmps_y = 0
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
    
    return (puck_velocity_mmps_x, puck_velocity_mmps_y)

def get_mm_per_pixel_factors(fiducial_coordinates):
    """Return the scaling factors for mm per pixel conversion"""
    (tl, tr, br, bl) = fiducial_coordinates
    
    mm_per_pixel_x = table_length_mm/(br[0] - bl[0])
    mm_per_pixel_y = table_width_mm/(bl[1] - tl[1])

    return mm_per_pixel_x, mm_per_pixel_y

def get_perspective_transform_matrix(fiducial_coordinates):
    """Return the calculated perspective transform matrix for perspective correction"""
    (tl, tr, br, bl) = fiducial_coordinates

    # compute the width of the new image, which will be the
    # maximum distance between bottom-right and bottom-left
    # x-coordiates or the top-right and top-left x-coordinates
    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))

    # compute the height of the new image, which will be the
    # maximum distance between the top-right and bottom-right
    # y-coordinates or the top-left and bottom-left y-coordinates
    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b))

    # now that we have the dimensions of the new image, construct
    # the set of destination points to obtain a "birds eye view",
    # (i.e. top-down view) of the image, again specifying points
    # in the top-left, top-right, bottom-right, and bottom-left
    # order
    destination = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]], dtype = "float32")

    # compute the perspective transform matrix
    perspective_transform_matrix = cv2.getPerspectiveTransform(fiducial_coordinates, destination)
    
    return perspective_transform_matrix, max_width, max_height

def find_fiducials(frame, fiducial_lower_hsv, fiducial_upper_hsv):
    ret = False
    
    # array to hold the 4 fiducial coordinates (x, y)
    #fiducials = np.zeros((4, 2), dtype =  "int16")
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
            with open(settings_file_path, 'r') as fp:
                pt_settings = json.load(fp)
                fp.close()
            
            pt_settings['fiducial']['coordinates']['tl']['x'] = fiducials[0][0]
            pt_settings['fiducial']['coordinates']['tl']['y'] = fiducials[0][1]
            pt_settings['fiducial']['coordinates']['tr']['x'] = fiducials[1][0]
            pt_settings['fiducial']['coordinates']['tr']['y'] = fiducials[1][1]
            pt_settings['fiducial']['coordinates']['br']['x'] = fiducials[2][0]
            pt_settings['fiducial']['coordinates']['br']['y'] = fiducials[2][1]
            pt_settings['fiducial']['coordinates']['bl']['x'] = fiducials[3][0]
            pt_settings['fiducial']['coordinates']['bl']['y'] = fiducials[3][1]
            
            with open(settings_file_path, 'w+') as fp:
                json.dump(pt_settings, fp, indent=4)
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

    pt_state_cmd_enum = enum(settings['enumerations']['pt_state_cmd'])
    pt_state_enum = enum(settings['enumerations']['pt_state'])
    pt_error_enum = enum(settings['enumerations']['pt_error'])   
    pt_rx_enum = enum(settings['enumerations']['pt_rx'])
    pt_tx_enum = enum(settings['enumerations']['pt_tx'])


"""----------------------------Puck Tracker Process--------------------------"""
def pt_process(pt_rx, pt_tx, visualization_data):
    """All things puck tracker happen here. Communicates directly with master controller"""
    global pt_state_cmd_enum
    global pt_state_enum
    global pt_error_enum
    global pt_rx_enum
    global pt_tx_enum

    global camera_horizontal_resolution
    global camera_vertical_resolution
    global camera_fps

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
            pt_tx[pt_tx_enum.error] = pt_error_enum.camera
    
    pt_state = pt_state_enum.idle
    pt_error = pt_error_enum.idle
    calibration_attempts = 0
    
    while True:
        # retrieve commands from master controller
        mc_cmd = int(pt_rx[pt_rx_enum.state_cmd])

        # set desired state of puck tracker to that commanded by mc    
        if mc_cmd == pt_state_cmd_enum.calibrate:
            pt_desired_state = pt_state_cmd_enum.calibrate
        elif mc_cmd == pt_state_cmd_enum.track:
            pt_desired_state = pt_state_cmd_enum.track
        elif mc_cmd == pt_state_cmd_enum.quit:
            pt_desired_state = pt_state_cmd_enum.quit
        else:
            pt_desired_state = pt_state_cmd_enum.idle    

        # do the required setup to enter state requested by mc
        if pt_desired_state == pt_state_cmd_enum.calibrate and pt_state != pt_state_enum.calibrate:
            pt_desired_state = pt_state_cmd_enum.idle
            pt_state = pt_state_enum.calibrate
            
            # retrieve fiducial_hsv range from settings file
            puck_hsv, fiducial_hsv, fiducial_coordinates = get_puck_tracker_settings()

        elif pt_desired_state == pt_state_cmd_enum.track and pt_state != pt_state_enum.track:
            pt_desired_state = pt_state_cmd_enum.idle
            pt_state = pt_state_enum.track
            
            puck_hsv, fiducial_hsv, fiducial_coordinates = get_puck_tracker_settings()
            mm_per_pixel_x, mm_per_pixel_y = get_mm_per_pixel_factors(fiducial_coordinates)
            perspective_transform_matrix, max_width, max_height = get_perspective_transform_matrix(fiducial_coordinates)
            
        elif pt_desired_state == pt_state_cmd_enum.quit and pt_state != pt_state_enum.quit:
            pt_desired_state = pt_state_cmd_enum.idle
            pt_state = pt_state_enum.quit
              
        else:
            pass
            # stay in current state
        
        # perform puck tracker state tasks
        if pt_state == pt_state_enum.calibrate:
            ret, frame = video_stream.read()
            
            if ret == False:
                pt_tx[pt_tx_enum.error] = pt_error_enum.camera
                
            fiducials_found = find_fiducials(frame, fiducial_hsv[0], fiducial_hsv[1])
            
            if fiducials_found:
                pt_state = pt_state_enum.idle
                calibration_attempts = 0
            else:
                calibration_attempts += 1

            if calibration_attempts >= 5:
                pt_state = pt_state_enum.idle
                pt_error = pt_error_enum.calibration_failed
                calibration_attempts = 0

        elif pt_state == pt_state_enum.track:
            ret, frame = video_stream.read()
	   
            if ret == False:
                pt_tx[pt_tx_enum.error] = pt_error_enum.camera

            frame_warped = cv2.warpPerspective(frame, perspective_transform_matrix, (max_width, max_height), cv2.INTER_LINEAR)
            frame, puck_position_mm_xy = get_puck_position(frame_warped, puck_hsv[0], puck_hsv[1], mm_per_pixel_x, mm_per_pixel_y)
            puck_velocity_mmps_xy = get_puck_velocity(puck_position_mm_xy)

            pt_tx[pt_tx_enum.puck_position_x] = puck_position_mm_xy[1]
            pt_tx[pt_tx_enum.puck_position_y] = puck_position_mm_xy[0]
            pt_tx[pt_tx_enum.puck_velocity_x] = puck_velocity_mmps_xy[1]
            pt_tx[pt_tx_enum.puck_velocity_y] = puck_velocity_mmps_xy[0]

            visualization_data.send(frame)

        elif pt_state == pt_state_enum.quit:
            print "hey"
            pt_tx[pt_tx_enum.state] = pt_state_enum.quit
            video_stream.release() 
            cv2.destroyAllWindows()
            quit(0)

        # update state/error
        pt_tx[pt_tx_enum.error] = pt_error
        pt_tx[pt_tx_enum.state] = pt_state