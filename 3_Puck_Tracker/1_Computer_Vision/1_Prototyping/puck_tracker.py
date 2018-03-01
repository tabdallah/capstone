import cv2
import numpy
import json

def retrieve_puck_color():
	with open('camera_parameters.json', 'r') as fp:
                camParam = json.load(fp)
                fp.close()

        # the HSV range for the air hockey puck
        puckLowerHSV = (camParam['puck']['color']['hue']['lower'],
                        camParam['puck']['color']['sat']['lower'],
                        camParam['puck']['color']['val']['lower'])
        puckUpperHSV = (camParam['puck']['color']['hue']['upper'],
                        camParam['puck']['color']['sat']['upper'],
                        camParam['puck']['color']['val']['upper'])

	return puckLowerHSV, puckUpperHSV

def track_puck(frame, puckLowerHSV, puckUpperHSV):
	# convert the frame to HSV color space
        frameHSV = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # create a mask for the fiducial color
        mask = cv2.inRange(frameHSV, puckLowerHSV, puckUpperHSV)

        # find contours in the mask
        contourList = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

        # proceed if a contour is found
        if len(contourList) > 0:
        	# find the largest contour in the mask, then use
		# it to compute the minimum enclosing circle and
		# centroid
		contour = max(contourList, key=cv2.contourArea)
		((x, y), radius) = cv2.minEnclosingCircle(contour)
		M = cv2.moments(contour)

		if M["m00"] != 0:
                       	puckCenter = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

		# only proceed if the radius meets a minimum size
		if radius > 5:
			# draw the circle and centroid on the frame,
			# then update the list of tracked points
			cv2.circle(frame, (int(x), int(y)), int(radius),
				(0, 255, 255), 2)
			cv2.circle(frame, puckCenter, 5, (0, 0, 255), -1)

	return frame, puckCenter
