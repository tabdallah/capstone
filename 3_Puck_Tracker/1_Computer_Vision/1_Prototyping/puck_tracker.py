# import necessary modules
import cv2
import numpy as np
import Queue
import json
import time
import math
import matplotlib.pyplot as plt

# define global variables
lastPuckPositionMmX = 0
lastPuckPositionMmY = 0
lastTime = 0
pixelToMmFactors = (0,0)
tableWidthMm = 774.7
tableLengthMm = 1692.275
puckMinimumArea = 40
puckMaximumArea = 160
puckMinimumRadius = 3
puckMaximumRadius = 8

def get_puck_tracker_settings():
    """Return the stored settings for the puck tracker"""
    with open('puck_tracker_settings.json', 'r') as fp:
        ptSettings = json.load(fp)
        fp.close()

    puckLowerHSV = (ptSettings['puck']['color']['hue']['lower'],
                    ptSettings['puck']['color']['sat']['lower'],
                    ptSettings['puck']['color']['val']['lower'])
    puckUpperHSV = (ptSettings['puck']['color']['hue']['upper'],
                    ptSettings['puck']['color']['sat']['upper'],
                    ptSettings['puck']['color']['val']['upper'])
    
    fiducialLowerHSV = (ptSettings['fiducial']['color']['hue']['lower'],
                        ptSettings['fiducial']['color']['sat']['lower'],
                        ptSettings['fiducial']['color']['val']['lower'])
    fiducialUpperHSV = (ptSettings['fiducial']['color']['hue']['upper'],
                        ptSettings['fiducial']['color']['sat']['upper'],
                        ptSettings['fiducial']['color']['val']['upper'])
    
    fiducialCoordinates = np.array([
        [ptSettings['fiducial']['coordinates']['tl']['x'],
         ptSettings['fiducial']['coordinates']['tl']['y']],
        [ptSettings['fiducial']['coordinates']['tr']['x'],
         ptSettings['fiducial']['coordinates']['tr']['y']],
        [ptSettings['fiducial']['coordinates']['br']['x'],
         ptSettings['fiducial']['coordinates']['br']['y']],
        [ptSettings['fiducial']['coordinates']['bl']['x'],
         ptSettings['fiducial']['coordinates']['bl']['y']]], dtype = "float32")

    return (puckLowerHSV, puckUpperHSV), (fiducialLowerHSV, fiducialUpperHSV), fiducialCoordinates

def get_puck_position(frame, puckLowerHSV, puckUpperHSV, mmPerPixelX, mmPerPixelY):
    """Return the location of the puck in x, y coordinates (mm)"""
    # convert the frame to HSV color space
    frameHSV = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # create a mask for the puck color
    puckMask = cv2.inRange(frameHSV, puckLowerHSV, puckUpperHSV)

    # apply median blur filter
    puckMaskFiltered = cv2.medianBlur(puckMask, 5)

    # find contours in the mask
    contourList = cv2.findContours(puckMaskFiltered.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

    puckPositionMmX = 0
    puckPositionMmY = 0
    
    # proceed if a contour is found
    if len(contourList) > 0:
        puckLocated = False
        for contour in contourList:
            contourArea = cv2.contourArea(contour)
            if puckMinimumArea < contourArea < puckMaximumArea:
                ((x, y), radius) = cv2.minEnclosingCircle(contour)
                if puckMinimumRadius < radius < puckMaximumRadius:
                    puckSizedContour = contour
                    puckLocated = True
                    break

        if puckLocated:      
            M = cv2.moments(puckSizedContour)
            if M["m00"] != 0:
                puckCenterCoords = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
                cv2.circle(frame, puckCenterCoords, int(radius + 2), (0, 255, 255), 2)
                puckPositionMmX = puckCenterCoords[0]*mmPerPixelX
                puckPositionMmY = puckCenterCoords[1]*mmPerPixelY

    return frame, (puckPositionMmX, puckPositionMmY)

def get_puck_velocity(puckPositionMmXy):
    """Return the puck velocity"""
    global lastPuckPositionMmX
    global lastPuckPositionMmY
    global lastTime
    
    currentPuckPositionMmX = puckPositionMmXy[0]
    currentPuckPositionMmY = puckPositionMmXy[1]
    currentTime = time.time()
    
    velocityMmPerSX = 0
    velocityMmPerSY = 0
    travelTime = currentTime - lastTime
    
    if currentPuckPositionMmX != 0 and lastPuckPositionMmX != 0:
        distanceTraveledMmX = currentPuckPositionMmX - lastPuckPositionMmX
        velocityMmPerSX = int(distanceTraveledMmX / travelTime)
    
    if currentPuckPositionMmY != 0 and lastPuckPositionMmY != 0:
        distanceTraveledMmY = currentPuckPositionMmY - lastPuckPositionMmY
        velocityMmPerSY = int(distanceTraveledMmY / travelTime)
    
    lastPuckPositionMmX = currentPuckPositionMmX
    lastPuckPositionMmY = currentPuckPositionMmY
    lastTime = currentTime
    
    return (velocityMmPerSX, velocityMmPerSY)

def get_pixel_to_mm_factors(fiducialCoordinates):
    """Return the scaling factors for pixel to mm conversion"""
    (tl, tr, br, bl) = fiducialCoordinates
    
    mmPerPixelX = int(tableLengthMm/(br[0] - bl[0]))
    mmPerPixelY = int(tableWidthMm/(bl[1] - tl[1]))
    
    return mmPerPixelX, mmPerPixelY

def get_perspective_transform_matrix(fiducialCoordinates):
    """Return the calculated perspective transform matrix for perspective correction"""
    (tl, tr, br, bl) = fiducialCoordinates

    # compute the width of the new image, which will be the
    # maximum distance between bottom-right and bottom-left
    # x-coordiates or the top-right and top-left x-coordinates
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    # compute the height of the new image, which will be the
    # maximum distance between the top-right and bottom-right
    # y-coordinates or the top-left and bottom-left y-coordinates
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    # now that we have the dimensions of the new image, construct
    # the set of destination points to obtain a "birds eye view",
    # (i.e. top-down view) of the image, again specifying points
    # in the top-left, top-right, bottom-right, and bottom-left
    # order
    dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype = "float32")

    # compute the perspective transform matrix
    perspectiveTransformMatrix = cv2.getPerspectiveTransform(fiducialCoordinates, dst)
    
    return perspectiveTransformMatrix, maxWidth, maxHeight

def find_fiducials(frame, fiducialLowerHSV, fiducialUpperHSV):
    ret = False
    frameWidth = 640
    frameHeight = 480
    
    # array to hold the 4 fiducial coordinates (x, y)
    #fiducials = np.zeros((4, 2), dtype =  "int16")
    fiducials = [0, 0, 0, 0]

    # convert the frame to HSV color space
    frameHSV = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # create a mask for the fiducial color
    mask = cv2.inRange(frameHSV, fiducialLowerHSV, fiducialUpperHSV)

    # apply a median blur filter to the mask (helps with image noise)
    medianBlur = cv2.medianBlur(mask, 5)

    # find contours in the mask
    contourList = cv2.findContours(medianBlur.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

    # proceed if a contour is found
    if len(contourList) > 0:
        for contour in contourList:
            # find the minimum enclosing circle for the contour
            ((x, y), radius) = cv2.minEnclosingCircle(contour)

            # use moments to find an accurate centroid for the fiducial
            M = cv2.moments(contour)
    
            # check for divide by zero
            if M["m00"] != 0:
                fiducialCenter = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

                if (fiducialCenter[0] < (frameWidth/2)) and (fiducialCenter[1] < (frameHeight)/2):
                    fiducials[0] = fiducialCenter
                elif (fiducialCenter[0] > (frameWidth/2)) and (fiducialCenter[1] < (frameHeight)/2):
                    fiducials[1] = fiducialCenter
                elif (fiducialCenter[0] > (frameWidth/2)) and (fiducialCenter[1] > (frameHeight)/2):
                    fiducials[2] = fiducialCenter
                elif (fiducialCenter[0] < (frameWidth/2)) and (fiducialCenter[1] > (frameHeight)/2):
                    fiducials[3] = fiducialCenter
                else:
                    pass

        if 0 in fiducials:
            ret = False
        else:
            ret = True
            
            # if all coordinates for the playing surface are found, save to json
            with open('puck_tracker_settings.json', 'r') as fp:
                ptSettings = json.load(fp)
                fp.close()
            
            ptSettings['fiducial']['coordinates']['tl']['x'] = int(fiducials[0][0]/2)
            ptSettings['fiducial']['coordinates']['tl']['y'] = int(fiducials[0][1]/2)
            ptSettings['fiducial']['coordinates']['tr']['x'] = int(fiducials[1][0]/2)
            ptSettings['fiducial']['coordinates']['tr']['y'] = int(fiducials[1][1]/2)
            ptSettings['fiducial']['coordinates']['br']['x'] = int(fiducials[2][0]/2)
            ptSettings['fiducial']['coordinates']['br']['y'] = int(fiducials[2][1]/2)
            ptSettings['fiducial']['coordinates']['bl']['x'] = int(fiducials[3][0]/2)
            ptSettings['fiducial']['coordinates']['bl']['y'] = int(fiducials[3][1]/2)
            
            with open('puck_tracker_settings.json', 'w+') as fp:
                json.dump(ptSettings, fp, indent=4)
                fp.close()
                    
    return ret



"""----------------------------Puck Tracker Process--------------------------"""
def ptProcess(dataToPT, dataFromPT):
    """All things puck tracker happen here. Communicates directly with master controller"""
    while True:
        videoStream = cv2.VideoCapture(0)
        
        if videoStream.isOpened() == True:
            break
        else:
            dataFromPT.put("Error: Camera Disconnected")
    
    ptState = "Idle"
    puckPositionX = np.array([])
    puckPositionY = np.array([])
    puckVelocityX = np.array([])
    puckVelocityY = np.array([])
    
    while True:
        # retrieve commands from master controller
        try:
            mcCmd = dataToPT.get(False)
        except Queue.Empty:
            mcCmd = "Idle"
            
        # set desired state of puck tracker to that commanded by mc    
        if mcCmd == "Calibrate":
            ptDesiredState = "Calibrate"
        elif mcCmd == "TrackPuck":
            ptDesiredState = "TrackPuck"
        else:
            ptDesiredState = "Idle"
    
        # do the required setup to enter state requested by mc
        if ptDesiredState == "Calibrate" and ptState != "Calibrate":
            ptDesiredState = "Idle"
            ptState = "Calibrate"
            
            # setup for puck tracker calibration, use higher resolution and lower fps for more accurate fiducial detection
            videoStream.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            videoStream.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            videoStream.set(cv2.CAP_PROP_FPS, 30)
            
            # retrieve fiducialHSV range from settings file
            puckHSV, fiducialHSV, fiducialCoordinates = get_puck_tracker_settings()
            
        elif ptDesiredState == "TrackPuck" and ptState != "TrackPuck":
            ptDesiredState = "Idle"
            ptState = "TrackPuck"
            
            # setup for puck tracking
            videoStream.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            videoStream.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            videoStream.set(cv2.CAP_PROP_FPS, 224)
            
            puckHSV, fiducialHSV, fiducialCoordinates = get_puck_tracker_settings()
            mmPerPixelX, mmPerPixelY = get_pixel_to_mm_factors(fiducialCoordinates)
            perspectiveTransformMatrix, maxWidth, maxHeight = get_perspective_transform_matrix(fiducialCoordinates)
            
        else:
            pass
            # stay in current state
        
        # perform puck tracker state tasks
        if ptState == "Calibrate":
            ret, frame = videoStream.read()
            
            if ret == False:
                dataFromPT.put("Error: Camera Disconnected")
                
            fiducialsFound = find_fiducials(frame, fiducialHSV[0], fiducialHSV[1])
            
            if fiducialsFound:
                dataFromPT.put("Calibration Complete")
                ptState = "Idle"
            else:
                dataFromPT.put("Calibrating...")
            
        elif ptState == "TrackPuck":
            ret, frame = videoStream.read()
	
            if ret == False:
                dataFromPT.put("Error: Camera Disconnected")

            frameCorrected = cv2.warpPerspective(frame, perspectiveTransformMatrix, (maxWidth, maxHeight), cv2.INTER_NEAREST)
            frame, puckPositionMmXy = get_puck_position(frameCorrected, puckHSV[0], puckHSV[1], mmPerPixelX, mmPerPixelY)
            puckVelocityMmPerSXy = get_puck_velocity(puckPositionMmXy)
            
            puckPositionX = np.append(puckPositionX, puckPositionMmXy[0])
            puckPositionY = np.append(puckPositionY, puckPositionMmXy[1])
            puckVelocityX = np.append(puckVelocityX, puckVelocityMmPerSXy[0])
            puckVelocityY = np.append(puckVelocityY, puckVelocityMmPerSXy[1])

            try:
                dataFromPT.put("puck_position_mm_x: {0}".format(puckPositionMmXy[0]))
                dataFromPT.put("puck_position_mm_y: {0}".format(puckPositionMmXy[1]))
                dataFromPT.put("puck_velocity_mmps_x: {0}".format(puckVelocityMmPerSXy[0]))
                dataFromPT.put("puck_velocity_mmps_x: {0}".format(puckVelocityMmPerSXy[1]))
            except Queue.Full:
                print "Queue Full?"
        
            #print "Time for 1 Frame: ", time.time()-start
            cv2.imshow('Table', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    plt.figure()
    plt.subplot(2,2,1)
    plt.plot(puckPositionX)
    plt.title('Puck Position X')
    plt.xlabel('Samples')
    plt.ylabel('Position (mm)')
    plt.subplot(2,2,2)
    plt.plot(puckPositionY)
    plt.title('Puck Position Y')
    plt.xlabel('Samples')
    plt.ylabel('Position (mm)')
    plt.subplot(2,2,3)
    plt.plot(puckVelocityX)
    plt.title('Puck Velocity X')
    plt.xlabel('Samples')
    plt.ylabel('Velocity (mm/s)')
    plt.subplot(2,2,4)
    plt.plot(puckVelocityY)
    plt.title('Puck Velocity Y')
    plt.xlabel('Samples')
    plt.ylabel('Velocity (mm/s)')    
    plt.tight_layout()
    plt.show()
        
    # When everything done, release the capture
    videoStream.release()
    cv2.destroyAllWindows()
	

"""
THIS IS SAMPLE PLOTTING CODE

puckPositionX = np.array([])
puckPositionY = np.array([])
puckVelocityX = np.array([])
puckVelocityY = np.array([])

puckPositionX = np.append(puckPositionX, puckPositionMmXy[0])
puckPositionY = np.append(puckPositionY, puckPositionMmXy[1])
puckVelocityX = np.append(puckVelocityX, puckVelocityMmPerSXy[0])
puckVelocityY = np.append(puckVelocityY, puckVelocityMmPerSXy[1])

plt.figure()
plt.subplot(2,2,1)
plt.plot(puckPositionX)
plt.title('Puck Position X')
plt.xlabel('Samples')
plt.ylabel('Position (mm)')
plt.subplot(2,2,2)
plt.plot(puckPositionY)
plt.title('Puck Position Y')
plt.xlabel('Samples')
plt.ylabel('Position (mm)')
plt.subplot(2,2,3)
plt.plot(puckVelocityX)
plt.title('Puck Velocity X')
plt.xlabel('Samples')
plt.ylabel('Velocity (mm/s)')
plt.subplot(2,2,4)
plt.plot(puckVelocityY)
plt.title('Puck Velocity Y')
plt.xlabel('Samples')
plt.ylabel('Velocity (mm/s)')    
plt.tight_layout()
plt.show()
"""

