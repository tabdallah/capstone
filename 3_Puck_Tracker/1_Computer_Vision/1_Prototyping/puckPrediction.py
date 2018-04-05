lastPuckPositionMmX = 0
lastPuckPositionMmY = 0
lastPuckVelocityMmPerSY = 0
minPuckVelocityMmPerSY = -180
puckPredictionAveragedWindowSize = 5
puckPredictionAveragedArray = np.zeros(puckPredictionAveragedWindowSize)
puckPredictionAveragedIndex = 0

def get_paddle_defense_position(puckPositionMmX, puckPositionMmY, puckVelocityMmPerSY):
    global lastPuckPositionMmX
    global lastPuckPositionMmY
    global lastPuckVelocityMmPerSY
    global puckPredictionAveragedArray
    global puckPredictionAveragedWindowSize
    global puckPredictionAveragedIndex
    global minPuckVelocityMmPerSY
    
    puckPredictionMmX = 0
    puckPredictionAveragedMmX = 0
    
    # check if the puck is moving towards the robot
    if puckVelocityMmPerSY < minPuckVelocityMmPerSY:
        # using the equation of a line y = mx + b, find predicted x position when y = 0
        vectorY = int(puckPositionMmY - lastPuckPositionMmY)
        vectorX = int(puckPositionMmX - lastPuckPositionMmX)
        
        if vectorX == 0:
            # avoid divide by zero
            slope = 999999
        else:
            slope = vectorY/vectorX
        
        # b = y - mx
        yIntercept = puckPositionMmY - (slope * puckPositionMmX)
        
        if slope != 0:
            puckPredictionMmX = -yIntercept / slope
        else:
            puckPredictionMmX = 0
            
        # now that we have a predicted x position, take an average to improve accuracy  
        puckPredictionAveragedArray[puckPredictionAveragedIndex] = puckPredictionMmX
        numNonZeroValues = np.count_nonzero(puckPredictionAveragedArray)
        
        if numNonZeroValues != 0:
            puckPredictionAveragedMmX = (np.sum(puckPredictionAveragedArray)) / numNonZeroValues
        else:
            puckPredictionAveragedMmX = 0
        
        # manage index for array
        puckPredictionAveragedIndex += 1
        if puckPredictionAveragedIndex < puckPredictionAveragedWindowSize:
            pass
        else:
            puckPredictionAveragedIndex = 0
            
    if puckVelocityMmPerSY > minPuckVelocityMmPerSY and lastPuckVelocityMmPerSY < minPuckVelocityMmPerSY:
        puckPredictionAveragedArray.fill(0)
        puckPredictionAveragedIndex = 0

    lastPuckVelocityMmPerSY = puckVelocityMmPerSY
    lastPuckPositionMmX = puckPositionMmX
    lastPuckPositionMmY = puckPositionMmY
    
    return (puckPredictionAveragedMmX, 0)