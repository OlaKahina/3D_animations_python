from psychopy import event, monitors
import psychopy.visual,psychopy.event,psychopy.core

import random
import numpy as np
import pickle
from typing import List, Tuple
import ctypes
import pyglet.gl as GL
import psychopy.tools.viewtools as vt
import psychopy.tools.mathtools as mt
import ratcave as rc


#Monitor settings
widthPix = 1920 # screen width in px
heightPix = 1080 # screen height in px
monitorwidth = 53.1 # monitor width in cm
viewdist = 60. # viewing distance in cm
monitorname = 'BOE CQ LCD'
scrn = 0 # 0 to use main screen, 1 to use external screen
mon = monitors.Monitor(monitorname, width=monitorwidth, distance=viewdist)
mon.setSizePix((widthPix, heightPix))


# Frustum Parameters
scrDist = 0.50;     # 50cm is the distance from the view in cm. Measured from the center of the eyes.
scrWidth = 0.53;    # 53cm is the display's width.
scrAspect = 1.0;    # Aspect ratio of the display (width/height).
eyeOffset = 0.0;    # Half the inter-ocular separation (i.e. the horizontal distance between the nose 
                    # and the center of the pupil) in m. If eyeOffset is 0.0, a symmetric frustum is returned.
near_z = -10.0;
far_z = -50.0;

# Number of spheres and their speed
nSpheres = 400;
speed = 3;          #degrees/seconds


# True if we want to generate new coordinates, and False if there are already generated coordinates.
generate_coordinate = True


# Create a window

win = psychopy.visual.Window(
    monitor=mon, 
    size=(1000, 1000),
    #size=(widthPix,heightPix),
    color='Black',
    colorSpace='rgb',
    units='deg',
    screen=scrn,
    allowGUI=True,
    fullscr=False)

# Get the framerate
frameRate = win.getActualFrameRate()

clock = psychopy.core.Clock()

# Do the necessary transformations to create a perspective projection
def get_view_matrix(z):
  return mt.translationMatrix((0.0, 0.0, -z)).astype(np.float32)

frustum = vt.computeFrustum(scrWidth, scrAspect, scrDist, eyeOffset =0.0, nearClip=0.05, farClip=50.0)

transformations = rc.UniformCollection()
transformations['view_matrix'] = get_view_matrix(z=scrDist)
transformations['projection_matrix'] = vt.perspectiveProjectionMatrix(*frustum).astype(np.float32)


# Make Shader

VERT_SHADER = """
#version 120

attribute vec4 vertexPosition;
uniform mat4 model_matrix, view_matrix, projection_matrix;

void main()
  {   
     // Calculate Position on Screen
    
      gl_Position = projection_matrix * view_matrix * model_matrix * vertexPosition; 
  }
"""

FRAG_SHADER = """
#version 120
#extension GL_NV_shadow_samplers_cube : enable

void main()
{
    gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);
 }
"""

shader = rc.Shader(vert=VERT_SHADER, frag=FRAG_SHADER)
    
# Make Stimuli
reader = rc.WavefrontReader(rc.resources.obj_primitives)

spheres = [reader.get_mesh("Circle", scale=0.06) for _ in range(nSpheres)]


# Function initial coordinates : random X, Y, Z: fill X, Y and Z coordinates with uniform random values that serve as coordinates 
    
def initial_coord():

    for sphere in spheres:

        sphere.position.xy = np.random.uniform(-25, 25, size=2)
        z = np.random.uniform(near_z, far_z)

        sphere.position.z = z
        sphere.position.x *= z/-50
        sphere.position.y *= z/-50

        sphere.theta_deg = np.random.rand(1) * 360
        sphere.phi_deg = np.random.rand(1) * 360

        theta_rad = sphere.theta_deg * np.pi / 180
        phi_rad = sphere.phi_deg* np.pi / 180
        
        
        sphere.dx = speed * np.sin(-phi_rad - theta_rad) / frameRate
        sphere.dy = -speed * np.cos(phi_rad + theta_rad) / frameRate
        sphere.dz = -speed * np.cos(theta_rad) / frameRate
        
    return spheres
        
initial_coord()
    
    
# Function updated coordinates at each frame 

def updated_coord(initial_coord):
    
    offline_coord_set = []

    for sphere in spheres:

        sphere_coord_set = []
    
        for Nframes in range (200):           # order is first by frame then by sphere

            # Update Spheres Positions
            sphere.position.x += sphere.dx
            sphere.position.y += sphere.dy
            sphere.position.z += sphere.dz


            sphere_coord_set = np.append(sphere_coord_set,[sphere.position.xyz]) # For one sphere with coord x,y,z:
                                                                                 # frame 1 : [x1,y1,z1]
                                                                                 # frame 2 : [x1,y1,z1,x2,y2,z2]
            #print(sphere_coord_set)
        offline_coord_set = np.append(offline_coord_set, sphere_coord_set)      # Final outcome of sphere_coord_set: coord of one sphere in all frames in one array                                                           
        #print(offline_coord_set)                                               # [x1,y1,z1,x2,y2,z2]
    
    offline_coord_set = np.reshape (offline_coord_set, (nSpheres, -1, 3))       # Final outcome of offline_coord_set order in a number of rows (frames) by 3 (x,y,z) structure
                                                                                # frame 1 : [x1,y1,z1]
                                                                                # frame 2 : [x2,y2,z2]
                                                                                # 3 is for format [x,y.z] and -1 when we don't know how many rows (frames) we want. It adapts automatically to the number of rows we put in the loop.
    #print(offline_coord_set)
    return offline_coord_set
    

# If the offline coordinates are already generated, then load the coordinates, and put generate_coordinates to False.

if (generate_coordinate):
    offline_coord_set = updated_coord(initial_coord)
    pickle.dump(offline_coord_set, open('offline_coord_set.pickle', 'wb'))
else:
    offline_coord_set = pickle.load(open('offline_coord_set.pickle', 'rb'))
    
# Play the animation
for Nframes in range(200):
    
    #clock.reset()
    
    with shader:  
        
        transformations['view_matrix'] = get_view_matrix(z=scrDist)
        transformations.send()
    
        sphere_index = 0
    
        for sphere in spheres:
    
            # Update Spheres Positions
            sphere.position.x = offline_coord_set[sphere_index, Nframes, 0]
            sphere.position.y = offline_coord_set[sphere_index, Nframes, 1]
            sphere.position.z = offline_coord_set[sphere_index, Nframes, 2]
            
            # Draw the spheres
            sphere.draw()
            sphere_index += 1
        
    
    # Get the back buffer frames
    #win.getMovieFrame(buffer='back')

    win.flip()
    
    # check events to break out of the loop!

    if len(event.getKeys())>0:
        break
    event.clearEvents()

# Save the frames into a movie with format mp4
#win.saveMovieFrames('control_random.gif')

win.close()
