import turtle
import logging

def search(start):
    found = False
    
    logger.critical("AREA IS SEARCHING")
    
    t.goto(start, target_depth)

    for i in range(2):
        for j in range(100):
            t.forward(1)
            
            if (t.xcor() >= target_x_min and t.xcor() <= target_x_max) and (t.ycor() >= target_y_min and t.ycor() <= target_y_max):
                found = True
            
            else:
                pass
        
        t.left(90)
        
        for k in range(100):
            t.forward(1)
            
            if (t.xcor() >= target_x_min and t.xcor() <= target_x_max) and (t.ycor() >= target_y_min and t.ycor() <= target_y_max):
                found = True
            
            else:
                pass
            
        t.left(90)
    
    logger.critical("AREA SEARCHED")
    return found

logger = logging.getLogger("CALROV Yaz Autonomus Mission")

logger.critical("MISSION STARTED")
logger.critical("Mission Area Is Creating And Setting.")

t = turtle.Turtle()
t.shape('turtle')
t.speed(6)

form = turtle.Screen()
form.setup(800.0, 600.0)
form.title("AUTONOMUS MISSION")
form.bgcolor("lightblue")

start_position = (-150, 150)
target_position = (100, -150)
target_radius = 20
target_depth = -200

finish_circle_position = (target_position[0], target_position[1] + target_radius)

t.up()
t.goto(target_position[0], target_position[1])
t.down()
t.color('red', 'red')
t.begin_fill()
t.fillcolor('red')
t.circle(target_radius)
t.end_fill()
t.color(0, 0, 0)
t.up()
t.goto(start_position[0], start_position[1])

logger.critical("Mission Area Created And Setted.")
logger.critical("Mission Is Starting.")

t.speed(1)

# Dive

start = start_position[0]
logger.critical("DIVE STARTING")
t.goto(start, target_depth)
logger.critical("DIVE FINISHED")

# Search

target_x_max = target_position[0] + target_radius
target_x_min = target_position[0] - target_radius 
target_y_max = target_position[1] + target_radius
target_y_min = target_position[1] - target_radius

found = search(start)

# When target found

while found == False:
    logger.critical("TARGET NOT FOUND")
    t.goto(-100, target_depth)
    start += 50
    found = search(start)
    
if found == True:
    logger.critical("TARGET FOUND")
    t.goto(finish_circle_position[0], finish_circle_position[1])
    t.down()
    t.circle(40)
    t.up()
    
# Go to the start point

logger.critical("COMING BACK TO THE START POSITION")

t.goto(start_position[0], start_position[1])
t.left(90)

logger.critical("MISSION FINISHED")
turtle.delay(3000)
turtle.bye()

form.mainloop()