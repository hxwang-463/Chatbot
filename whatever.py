

init = 0
fly = 1


def abc():
    global fly
    fly = 2
    return fly


p = abc()
print(p==fly)
