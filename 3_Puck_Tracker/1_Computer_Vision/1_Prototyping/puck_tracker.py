# import necessary modules
import cv2
import numpy as np
import json
import time
import math
import matplotlib.pyplot as plt

# define global variables
lastPuckPositionMmX = 0
lastPuckPositionMmY = 0
lastTime = 0
pixelToMmFactors = (0,0)
tableWidthMm = 622
tableLengthMm = 1397
puckMinimumArea = 40
puckMaximumArea = 130

def get_puck_color():
    """Return the upper and lower HSV thresholds for the puck color"""
    with open('camera_parameters.json', 'r') as fp:
        camParams = json.load(fp)
        fp.close()

    puckLowerHSV = (camParams['puck']['color']['hue']['lower'],
                    camParams['puck']['color']['sat']['lower'],
                    camParams['puck']['color']['val']['lower'])
    puckUpperHSV = (camParams['puck']['color']['hue']['upper'],
                    camParams['puck']['color']['sat']['upper'],
                    camParams['puck']['color']['val']['upper'])

    return puckLowerHSV, puckUpperHSV

def get_fiducial_coordinates():
    with open('camera_parameters.json', 'r') as fp:
        camParams = json.load(fp)
        fp.close()

    fiducialCoordinates = np.array([
        [camParams['fiducial']['coordinates']['tl']['x'],
         camParams['fiducial']['coordinates']['tl']['y']],
        [camParams['fiducial']['coordinates']['tr']['x'],
         camParams['fiducial']['coordinates']['tr']['y']],
        [camParams['fiducial']['coordinates']['br']['x'],
         camParams['fiducial']['coordinates']['br']['y']],
        [camParams['fiducial']['coordinates']['bl']['x'],
         camParams['fiducial']['coordinates']['bl']['y']]], dtype = "float32")

    return fiducialCoordinates

def get_puck_position(frame, puckLowerHSV, puckUpperHSV):
    """Return the location of the puck in x, y coordinates (mm)"""
    # convert the frame to HSV color space
    frameHSV = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # create a mask for the puck color
    puckMask = cv2.inRange(frameHSV, puckLowerHSV, puckUpperHSV)

    # apply median blur filter (helps with noise)
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
                puckSizedContour = contour
                puckLocated = True
        
        if puckLocated:
            ((x, y), radius) = cv2.minEnclosingCircle(puckSizedContour)
            M = cv2.moments(puckSizedContour)

            if M["m00"] != 0:
                puckCenterCoords = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
                cv2.circle(frame, puckCenterCoords, int(radius), (0, 255, 255), 1)
                puckPositionMmX = puckCenterCoords[0]*mmPerPixelX
                puckPositionMmY = puckCenterCoords[1]*mmPerPixelY
                
    return frame, (puckPositionMmX, puckPositionMmY)

def get_puck_velocity(puckPositionMmXy):
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
        velocityMmPerSX = int(distanceTraveledMmX/travelTime)
    
    if currentPuckPositionMmY != 0 and lastPuckPositionMmY != 0:
        distanceTraveledMmY = currentPuckPositionMmY - lastPuckPositionMmY
        velocityMmPerSY = int(distanceTraveledMmY/travelTime)
    
    lastPuckPositionMmX = currentPuckPositionMmX
    lastPuckPositionMmY = currentPuckPositionMmY
    lastTime = currentTime
    
    return (velocityMmPerSX, velocityMmPerSY)

def get_pixel_to_mm_factors(fiducialCoordinates):
    (tl, tr, br, bl) = fiducialCoordinates
    mmPerPixelX = int(tableLengthMm/(br[0] - bl[0]))
    mmPerPixelY = int(tableWidthMm/(bl[1] - tl[1]))
    
    return mmPerPixelX, mmPerPixelY

def correct_image_perspective(frame, fiducials):
    (tl, tr, br, bl) = fiducials

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

    # compute the perspective transform matrix and then apply it
    M = cv2.getPerspectiveTransform(fiducials, dst)
    correctedFrame = cv2.warpPerspective(frame, M, (maxWidth, maxHeight), cv2.INTER_NEAREST)

    # return the warped image
    return correctedFrame

"""----------------------------MAIN---------------------------"""
if __name__ == '__main__':
    capture = cv2.VideoCapture(0)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    capture.set(cv2.CAP_PROP_FPS, 224)

    fiducialCoordinates = get_fiducial_coordinates()
    mmPerPixelX, mmPerPixelY = get_pixel_to_mm_factors(fiducialCoordinates)
    puckLowerHSV, puckUpperHSV = get_puck_color()

    puckPositionX = np.array([])
    puckPositionY = np.array([])
    puckVelocityX = np.array([])
    puckVelocityY = np.array([])

    while True:
	ret, frame = capture.read()
        frameCorrected = correct_image_perspective(frame, fiducialCoordinates)
        frame, puckPositionMmXy = get_puck_position(frameCorrected, puckLowerHSV, puckUpperHSV)
        puckVelocityMmPerSXy = get_puck_velocity(puckPositionMmXy)
        
        puckPositionX = np.append(puckPositionX, puckPositionMmXy[0])
        puckPositionY = np.append(puckPositionY, puckPositionMmXy[1])
        puckVelocityX = np.append(puckVelocityX, puckVelocityMmPerSXy[0])
        puckVelocityY = np.append(puckVelocityY, puckVelocityMmPerSXy[1])

        #print "Puck Position mm (x,y): ({0}, {1})".format(puckPositionMmXy[0], puckPositionMmXy[1])
        #print "Puck Velocity mm/s (x,y): ({0}, {1})".format(puckVelocityMmPerSXy[0], puckVelocityMmPerSXy[1])
        
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
    capture.release()
    cv2.destroyAllWindows()








def find_fiducials(cameraStream):
	# the frame width/height
	frameWidth = cameraStream.get(cv2.CAP_PROP_FRAME_WIDTH)
	frameHeight = cameraStream.get(cv2.CAP_PROP_FRAME_HEIGHT)

	with open('camera_parameters.json', 'r') as fp:
		camParam = json.load(fp)
		fp.close()

	# the HSV range for detecting playing surface fiducials
	fiducialLowerHSV = (camParam['fiducial']['color']['hue']['lower'],
			    camParam['fiducial']['color']['sat']['lower'],
			    camParam['fiducial']['color']['val']['lower'])
	fiducialUpperHSV = (camParam['fiducial']['color']['hue']['upper'],
                            camParam['fiducial']['color']['sat']['upper'],
                            camParam['fiducial']['color']['val']['upper'])

	# array to hold the 4 fiducial coordinates (x, y)
	#fiducials = np.zeros((4, 2), dtype =  "float32")
	fiducials = [0, 0, 0, 0]

	while True:
		# continously grab a new frame
		(grabbed, frame) = cameraStream.read()

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
						print "Error: Fiducial out of range"

		if 0 in fiducials:
			print "Not all fiducials found, looking again"
		else:
			break

	# if all coordinates for the playing surface are found, save to json
	with open('camera_parameters.json', 'r+') as fp:
		camParam = json.load(fp)
		camParam['fiducial']['coordinates']['tl']['x'] = fiducials[0][0]
		camParam['fiducial']['coordinates']['tl']['y'] = fiducials[0][1]
		camParam['fiducial']['coordinates']['tr']['x'] = fiducials[1][0]
		camParam['fiducial']['coordinates']['tr']['y'] = fiducials[1][1]
		camParam['fiducial']['coordinates']['br']['x'] = fiducials[2][0]
		camParam['fiducial']['coordinates']['br']['y'] = fiducials[2][1]
		camParam['fiducial']['coordinates']['bl']['x'] = fiducials[3][0]
		camParam['fiducial']['coordinates']['bl']['y'] = fiducials[3][1]
		fp.seek(0)
		json.dump(camParam, fp, indent=4)
		fp.close()

	return True









"""
                            # velocity calculation
                            startTime = time.time()
                            startPositionX = puckCenter[0]
                            startPositionY = puckCenter[1]

                            distancePixels = math.sqrt((abs(startPositionX-endPositionX))**2 + (abs(startPositionY-endPositionY))**2)
                            scalingFactor = 0.001348
                            distanceMeters = distancePixels*scalingFactor
                            time1 = abs(startTime - endTime)
                            velocity = distanceMeters/time1
                            velocity = format(velocity, '.2f')

                            x1 = startPositionX
                            y1 = startPositionY
                            if distancePixels != 0:
                                    x1 = int(startPositionX + (startPositionX - endPositionX) / distancePixels * 30)
                                    y1 = int(startPositionY + (startPositionY - endPositionY) / distancePixels * 30)

                            cv2.putText(frame, str(velocity), (int(x+30), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 1, 100)
                            cv2.arrowedLine(frame, (endPositionX, endPositionY), (x1, y1), (0, 255, 0), 2, 8, 0, 0.3)

                            endTime = startTime
                            endPositionX = startPositionX
                            endPositionY = startPositionY
"""