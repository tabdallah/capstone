import numpy as np
import cv2
import sys

cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640);
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480);
cap.set(cv2.CAP_PROP_FPS, 224);

ret, image = cap.read()

masking = True
tracking = False

def nothing(*arg):
    pass

def onMouse(event, x, y, flags, param):
    # grab references to the global variables

    if event == cv2.EVENT_MOUSEMOVE:
        refPt = [(x, y)]
        (blue, green, red) = event[refPt[0]]
        #cv2.setTrackbarPos('mouseOver - red', 'RGB', red)
        #cv2.setTrackbarPos('mouseOver - green', 'RGB', green)
        #cv2.setTrackbarPos('mouseOver - blue', 'RGB', blue)


def setBlue():
    cv2.setTrackbarPos('lower - hue', 'HSV', 0)
    cv2.setTrackbarPos('lower - sat', 'HSV', 0)
    cv2.setTrackbarPos('lower - val', 'HSV', 0)
    cv2.setTrackbarPos('upper - hue', 'HSV', 179)
    cv2.setTrackbarPos('upper - sat', 'HSV', 255)
    cv2.setTrackbarPos('upper - val', 'HSV', 255)

cv2.namedWindow('HSV')
#cv2.setMouseCallback('RGB', onMouse)
cv2.createTrackbar('lower - hue', 'HSV', 0, 179, nothing)
cv2.createTrackbar('lower - sat', 'HSV', 0, 255, nothing)
cv2.createTrackbar('lower - val', 'HSV', 0, 255, nothing)

cv2.createTrackbar('upper - hue', 'HSV', 1, 179, nothing)
cv2.createTrackbar('upper - sat', 'HSV', 1, 255, nothing)
cv2.createTrackbar('upper - val', 'HSV', 1, 255, nothing)

#cv2.createTrackbar('mouseOver - red', 'RGB', 0, 255, nothing)
#cv2.createTrackbar('mouseOver - green', 'RGB', 0, 255, nothing)
#cv2.createTrackbar('mouseOver - blue', 'RGB', 0, 255, nothing)

setBlue()

if masking:
    while True:
        # Capture frame-by-frame
        ret, image = cap.read()

	cv2.imshow('Raw', image)

        thrs1 = cv2.getTrackbarPos('lower - hue', 'HSV')
        thrs2 = cv2.getTrackbarPos('lower - sat', 'HSV')
        thrs3 = cv2.getTrackbarPos('lower - val', 'HSV')
        thrs4 = cv2.getTrackbarPos('upper - hue', 'HSV')
        thrs5 = cv2.getTrackbarPos('upper - sat', 'HSV')
        thrs6 = cv2.getTrackbarPos('upper - val', 'HSV')
        #thrs7 = cv2.getTrackbarPos('mouseOver - red', 'RGB')
        #thrs8 = cv2.getTrackbarPos('mouseOver - green', 'RGB')
        #thrs9 = cv2.getTrackbarPos('mouseOver - blue', 'RGB')

        if (thrs1 > thrs4):
            cv2.setTrackbarPos('lower - hue', 'HSV', thrs4 - 1)
        if (thrs2 > thrs5):
            cv2.setTrackbarPos('lower - sat', 'HSV', thrs5 - 1)
        if (thrs3 > thrs6):
            cv2.setTrackbarPos('lower - val', 'HSV', thrs6 - 1)

        # define the list of boundaries
        boundaries = [
            ([thrs1, thrs2, thrs3], [thrs4, thrs5, thrs6])
        ]

        # loop over the boundaries
        for (lower, upper) in boundaries:
            # create NumPy arrays from the boundaries
            lower = np.array(lower, dtype="uint8")
            upper = np.array(upper, dtype="uint8")

	    #fiducials = pt.get_fiducial_coordinates()
	    #image = pt.correct_image_perspective(image, fiducials)
            # find the colors within the specified boundaries and apply
            image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(image, lower, upper)
	    cv2.imshow('Mask', mask)

            #kernel = np.ones((2,2),np.uint8)
            #erode1 = cv2.erode(mask, kernel, iterations=3)
	    #cv2.imshow('ErodeFirst', erode1)
	    #dilateSecond = cv2.dilate(erodeFirst, kernel, iterations=1)
	    #cv2.imshow('DilateSecond', dilateSecond)

	    median2 = cv2.medianBlur(mask, 5)
	    cv2.imshow('Median', median2)

	    kernel1 = np.ones((15,15), np.float32)/225
	    smoothed = cv2.filter2D(mask, -1, kernel1)

	    cv2.imshow('Smoothed', smoothed)
	    

	    color = cv2.bitwise_and(image, image, mask = mask)
	    cv2.imshow('Color', color)

            
	    #mask = cv2.dilate(mask, None, iterations=1)
            #cv2.imshow('Dilate', mask)
	    #kernel = np.ones((2,2),np.uint8)
	    #mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
	    #cv2.imshow('Erode', mask)
#            output = cv2.bitwise_and(image, image, mask=mask)
#	    cv2.imshow('Color', output)
 #           cv2.imshow('image', image)

        # Display the resulting frame
        if cv2.waitKey(1) & 0xFF == ord('q'):
            masking = False
            break

    # When everything done, release the capture
    cap.release()
    cv2.destroyAllWindows()

if tracking:

    # initialize the list of tracked points, the frame counter,
    # and the coordinate deltas
    linelength = 16
    pts = deque(maxlen=linelength)
    counter = 0
    (dX, dY) = (0, 0)
    direction = ""

    count = 0

    while True:
        # Capture frame-by-frame
        (grabbed, image) = cap.read()

        thrs1 = cv2.getTrackbarPos('lower - hue', 'HSV')
        thrs2 = cv2.getTrackbarPos('lower - sat', 'HSV')
        thrs3 = cv2.getTrackbarPos('lower - val', 'HSV')
        thrs4 = cv2.getTrackbarPos('upper - hue', 'HSV')
        thrs5 = cv2.getTrackbarPos('upper - sat', 'HSV')
        thrs6 = cv2.getTrackbarPos('upper - val', 'HSV')
        #thrs7 = cv2.getTrackbarPos('mouseOver - red', 'RGB')
        #thrs8 = cv2.getTrackbarPos('mouseOver - green', 'RGB')
        #thrs9 = cv2.getTrackbarPos('mouseOver - blue', 'RGB')

        if (thrs1 > thrs4):
            cv2.setTrackbarPos('lower - hue', 'HSV', thrs4 - 1)
        if (thrs2 > thrs5):
            cv2.setTrackbarPos('lower - sat', 'HSV', thrs5 - 1)
        if (thrs3 > thrs6):
            cv2.setTrackbarPos('lower - val', 'HSV', thrs6 - 1)

        colourLower = (thrs1, thrs2, thrs3)
        colourUpper = (thrs4, thrs5, thrs6)

        # resize the frame, blur it, and convert it to the HSV
        # color space
        image = imutils.resize(image, width=600)
        # blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        # hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # construct a mask for the object colour, then perform
        # a series of dilations and erosions to remove any small
        # blobs left in the mask
	cv2.imshow('thing', image)
        mask = cv2.inRange(image, colourLower, colourUpper)
        cv2.imshow('mask', mask)
	mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # find contours in the mask and initialize the current
        # (x, y) center of the ball
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)[-2]
        center = None

        # only proceed if at least one contour was found
        if len(cnts) > 0:
            # find the largest contour in the mask, then use
            # it to compute the minimum enclosing circle and
            # centroid
            c = max(cnts, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

            # only proceed if the radius meets a minimum size
            if radius > 10:
                # draw the circle and centroid on the frame,
                # then update the list of tracked points
                cv2.circle(image, (int(x), int(y)), int(radius),
                           (0, 255, 255), 2)
                cv2.circle(image, center, 5, (0, 0, 255), -1)
  #              pts.appendleft(center)

        # loop over the set of tracked points
 #     for i in np.arange(1, len(pts)):
            # if either of the tracked points are None, ignore
            # them
 #           if pts[i - 1] is None or pts[i] is None:
 #               continue

            # otherwise, compute the thickness of the line and
            # draw the connecting lines
 #           thickness = int(np.sqrt(linelength / float(i + 1)) * 2.5)
 #           cv2.line(image, pts[i - 1], pts[i], (0, 0, 255), thickness)

        # show the frame to our screen and increment the frame counter
        cv2.imshow("RGB", image)
        #cv2.imwrite("new_image" + "-" + str(count)+ ".jpg", image)
        count = count + 1
        key = cv2.waitKey(1) & 0xFF
        counter += 1

        if cv2.waitKey(1) & 0xFF == ord('q'):
            tracking = False
            break

    # When everything done, release the capture
    cap.release()
    cv2.destroyAllWindows()
