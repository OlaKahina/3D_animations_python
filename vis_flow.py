from psychopy import event, monitors
import psychopy.visual,psychopy.event,psychopy.core
import random
from random import randrange
import numpy as np
from typing import List, Tuple
import ctypes
import pyglet.gl as GL
import psychopy.tools.viewtools as vt
import psychopy.tools.mathtools as mt
import ratcave as rc


# ------------------------------ Define Frustum, Animation and Stim Parameters -------------------------


# Frustum Parameters
scrDist = 0.50;     # 50cm is the distance from the view in cm. Measured from the center of the eyes.
scrWidth = 0.53;    # 53cm is the display's width.
scrAspect = 1.0;    # Aspect ratio of the display (width/height).
eyeOffset = 0.0;    # Half the inter-ocular separation (i.e. the horizontal distance between the nose 
                    # and the center of the pupil) in m. If eyeOffset is 0.0, a symmetric frustum is returned.

# Animation parameters
nCircles = 700;
near_z = -10.0;
far_z = -50.0;
camera_z = -0.055


# Stim parameters
pre_demo_msg = "start demo"
pre_demo_duration_s = 2.0;
interv_color_chg = 100 #random.randrange(300,601);   # between frames 300 to 600 change color


# ------------------------------------------ Monitor and Window -----------------------------------------


#Monitor settings
widthPix = 1920 # screen width in px
heightPix = 1080 # screen height in px
monitorwidth = 53.1 # monitor width in cm
viewdist = 60. # viewing distance in cm
monitorname = 'BOE CQ LCD'
scrn = 0 # 0 to use main screen, 1 to use external screen
mon = monitors.Monitor(monitorname, width=monitorwidth, distance=viewdist)
mon.setSizePix((widthPix, heightPix))

# Create a window
win = psychopy.visual.Window(
    monitor=mon, 
    size=(1000, 800),
    #size=(widthPix,heightPix),
    color='Black',
    colorSpace='rgb',
    units='deg',
    screen=scrn,
    allowGUI=True,
    fullscr=False)    


# Get the framerate
frameRate = win.getActualFrameRate()

# Initialize Clock
clock = psychopy.core.Clock()


# ---------------------------------- Create Perspective Projection ---------------------------------------


# Transformation for points (model/view matrix)
def get_view_matrix(z):
  return mt.translationMatrix((0.0, 0.0, -z)).astype(np.float32)

frustum = vt.computeFrustum(scrWidth, scrAspect, scrDist, eyeOffset =0.0, nearClip=.05, farClip=2000.0)
transformations = rc.UniformCollection()
transformations['view_matrix'] = get_view_matrix(z=camera_z)
transformations['projection_matrix'] = vt.perspectiveProjectionMatrix(*frustum).astype(np.float32)


# ------------------------------------------- Visual Stim ------------------------------------------------


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
FRAG_SHADER2 = """
#version 120
#extension GL_NV_shadow_samplers_cube : enable

void main()
{
    gl_FragColor = vec4(1.0, 1.0, 0.0, 1.0);
 }
"""
shader = rc.Shader(vert=VERT_SHADER, frag=FRAG_SHADER)
    
# Make Stimuli (Spheres)
reader = rc.WavefrontReader(rc.resources.obj_primitives)
circles = [reader.get_mesh("Circle", scale=0.07) for _ in range(1,nCircles+1)]
targets = [reader.get_mesh("Plane", scale=0.4)]

    
# Writing text during experiment(instructions...bla bla bla)
text = psychopy.visual.TextStim(win=win)

    
# ----------------------------------- Define Spheres Coordinates ----------------------------------------
    
    
# Define initial coordinates
    
def initial_coord():
    
    for circle in circles:

        circle.position.xy = np.random.uniform(-25, 25, size=2)
        z = np.random.uniform(near_z, far_z)

        circle.position.z = z
        circle.position.x *= z/far_z 
        circle.position.y *= z/far_z 

    for target in targets:

        target.position.xy = -10
        target.position.z = -50


    return (circles,targets)

initial_coord()    
    
GL.glEnable(GL.GL_CULL_FACE)
    
    
# ----------------------------------------- Animation -------------------------------------------------
    
clock.reset()                                               # reset clock 0 sec

# Start with a message before playing the animation
while clock.getTime() < pre_demo_duration_s:               
    text.text = pre_demo_msg
    text.draw()
    win.flip() 
    

for Nframes in range(700):                                  # (~ 12 sec)
    
    with shader:
      
        camera_z -= .1
    
        transformations['view_matrix'] = get_view_matrix(z=camera_z)
        transformations.send()
          
        

        for i,circle in enumerate(circles):
            
            #if i>5 : # change color to red during 6 frames
                #shader = rc.Shader(vert=VERT_SHADER, frag=FRAG_SHADER2)
                #sphere.draw() 
            #else:
                #shader = rc.Shader(vert=VERT_SHADER, frag=FRAG_SHADER)
            circle.draw()     
               
     
                # sphere.uniforms['diffuse_color'] = [1., 0., 0.]
                #GL.glColor3f (1.0, 0.0, 0.0)

            
    
# ------------- CHANGE COLOR HERE (1st try) ------------------

            # The goal is to change the color of only one sphere for approx. 100 ms in some trials

            #if Nframes in range(interv_color_chg,interv_color_chg+300) : # change color to red during 6 frames

                #sphere_mesh['diffuse']= (1,0,0,)            # NameError: name 'sphere_mesh' is not defined
                #sphere.uniforms['diffuse'] = (1,0,0,)        # No change of color, no error thrown
                #sphere.uniforms['diffuse_color'] = [1., 0., 0.] # No change of color, no error thrown
                

                
# --------------------------------------------------    
    
            # If a sphere is behind a camera, generate new sphere coordinates, with the z from the camera to z_far.
            # This way we keep a constant number of visible circles
    
            max_dist   = max(abs(circle.position.x), abs(circle.position.y))
            limit_dist = 25 * abs((circle.position.z-camera_z) / far_z)


            if circle.position.z >= camera_z or max_dist > limit_dist:

                # Generate new circles with z coordinates relative to the camera. 
                # That way the circles are in front of the camera
                z_rel = np.random.uniform(-30,far_z)#np.random.uniform(near_z,far_z) 
                circle.position.z = z_rel + camera_z

                # Generate and rescale x and y relative to the camera
                # The distance from the camera to the far plane is far_z and,
                # the distance to the sphere is sphere.position.z-camera_z. 
                # So the scale factor for x and y has to be (sphere.position.z-camera_z)/far_z

                circle.position.xy = np.random.uniform(-25, 25) * z_rel/far_z
                circle.position.y = np.random.uniform(-25, 25) * z_rel/far_z

        for i,target in enumerate(targets):
            if Nframes in range(interv_color_chg,interv_color_chg+100):
                target.draw()   

        # Get the back buffer frames
        #win.getMovieFrame(buffer='back')
    
    
    win.flip()

    
   # check events to break out of the loop!

    if len(event.getKeys())>0:
        break
    event.clearEvents()
    
    
# Save the frames into a movie with format mp4
#win.saveMovieFrames('optic_flow_circles.mp4')
        
win.close()