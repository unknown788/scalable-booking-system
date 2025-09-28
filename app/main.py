
# app/main.py
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME}"}



# from fastapi import FastAPI #FastAPI is a class that inherits directly from Starlette.

# app = FastAPI()  # "instance" of the class FastAPI

# """
# Path" here refers to the last part of the URL starting from the first /.

# So, in a URL like:


# https://example.com/items/foo
# ...the path would be:


# /items/foo
# Info

# A "path" is also commonly called an "endpoint" or a "route".

# While building an API, the "path" is the main way to separate "concerns" and "resources".

# Operation¶
# "Operation" here refers to one of the HTTP "methods".

# Normally you use:

# POST: to create data.
# GET: to read data.
# PUT: to update data.
# DELETE: to delete data.


# """


# # path operation decorator The @app.get("/") tells FastAPI that the function right below is in charge of handling requests that go to:
# # the path /
# # using a get operation
# @app.get("/")  
# def index():  # path operation function
#     #It will be called by FastAPI whenever it receives a request to the URL "/" using a GET operation.
#     # In this case, it is an async function.

#     # You can return a dict, list, singular values as str, int, etc.
#     return {"message": "Jai Shree Hanuman"}




# """
# Recap¶
# Import FastAPI.
# Create an app instance.
# Write a path operation decorator using decorators like @app.get("/").
# Define a path operation function; for example, def root(): ....
# Run the development server using the command fastapi dev.
# """