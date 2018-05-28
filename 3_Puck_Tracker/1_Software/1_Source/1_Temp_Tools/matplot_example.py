"""
THIS IS SAMPLE PLOTTING CODE

puckPositionX = np.array([])
puckPositionY = np.array([])
puckVelocityX = np.array([])
puckVelocityY = np.array([])

puckPositionX = np.append(puckPositionX, puck_position_mm_xy[0])
puckPositionY = np.append(puckPositionY, puck_position_mm_xy[1])
puckVelocityX = np.append(puckVelocityX, puckpuck_velocity_mmps_xy[0])
puckVelocityY = np.append(puckVelocityY, puckpuck_velocity_mmps_xy[1])

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

