import cv2
import json
import numpy as np
import imutils

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

		# find contours in the mask
		contourList = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

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

def retrieve_fiducials():
	with open('camera_parameters.json', 'r') as fp:
		camParam = json.load(fp)
		fp.close()

	fiducials = np.array([
			[camParam['fiducial']['coordinates']['tl']['x'],
			 camParam['fiducial']['coordinates']['tl']['y']],
			[camParam['fiducial']['coordinates']['tr']['x'],
			 camParam['fiducial']['coordinates']['tr']['y']],
			[camParam['fiducial']['coordinates']['br']['x'],
			 camParam['fiducial']['coordinates']['br']['y']],
			[camParam['fiducial']['coordinates']['bl']['x'],
			 camParam['fiducial']['coordinates']['bl']['y']]], dtype = "float32")

	return fiducials

def perspective_correction(frame, fiducials):
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
	warped = cv2.warpPerspective(frame, M, (maxWidth, maxHeight))

	# return the warped image
	return warped

#if __name__ == "__main__":
#	cameraStream = cv2.VideoCapture(0)
#	success = find_fiducials(cameraStream)
#	fiducials = retrieve_fiducials()
#	# continously grab a new frame
#	while True:
#		(grabbed, frame) = cameraStream.read()
#
#		warpedImage = perspective_correction(frame, fiducials)
#		cv2.imshow("Output", warpedImage)
#		key = cv2.waitKey(1) & 0xFF
#
#		if key == ord("q"):
#			break
#
#	cameraStream.release()
#	cv2.destroyAllWindows()
