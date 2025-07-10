import turtle

t = turtle.Turtle()
t.shape('turtle')
t.speed(6)

form = turtle.Screen()
form.setup(800.0, 600.0)
form.title("AUTONOMUS MISSION")
form.bgcolor("lightblue")

start_position = (-200, 150)
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

# Dive

t.goto(0, target_depth)

# Search

found = False

target_x_max = target_position[0] + target_radius
target_x_min = target_position[0] - target_radius 
target_y_max = target_position[1] + target_radius
target_y_min = target_position[1] - target_radius

for i in range(2):
    for j in range(100):
        t.forward(1)
        
        if j >= target_x_min or j <= target_x_max:
            found = True
            
        else:
            pass

    t.left(90)

    for k in range(100):
        t.forward(1)
        
        if k >= target_y_min or k <= target_y_max:
            found = True
            
        else:
            pass

    t.left(90)

# When target found

if found == True:
    t.goto(finish_circle_position[0], finish_circle_position[1])
    t.down()
    t.circle(40)
    t.up()

# Go to the start point

t.goto(start_position[0], start_position[1])
t.left(90)

form.mainloop()