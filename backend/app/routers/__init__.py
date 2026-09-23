"""Register every router here. A new feature = a new module in this folder + one line below."""
from . import auth, exercises, health, lifts

all_routers = [
    health.router,
    auth.router,
    exercises.router,
    lifts.router,
]
