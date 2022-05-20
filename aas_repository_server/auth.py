"""
This module implements the Authentication Model for the cTrack Server.

Users are stored in the `users.dat` file. Please use the given functions to modify users
"""
import flask
from functools import wraps  # To create the authorization decorator
import jwt
from typing import Dict
import werkzeug.security
import os
import secrets
import configparser

config = configparser.ConfigParser()
config.read([
    os.path.join(os.path.dirname(__file__), "config.ini"),
    os.path.join(os.path.dirname(__file__), "config.ini.default")
])
USER_FILE = config["AUTHENTICATION"]["USER_FILE"]


SECRET_KEY = secrets.token_hex(64)


def load_user_file() -> Dict[str, str]:
    users: Dict[str, str] = {}
    with open(os.path.join(os.path.dirname(__file__), "users.dat"), "r") as file:
        data = file.read().rstrip("\n").split("\n")
        for i in data:
            try:
                usr, psw = i.split(", ")
                users[usr] = psw
            except ValueError:
                pass
    return users


def save_user_file():
    with open(os.path.join(os.path.dirname(__file__), "users.dat"), "w") as file:
        for usr, psw in USERS.items():
            file.write(usr + ", " + psw + "\n")
        file.close()


USERS: Dict[str, str] = load_user_file()


def add_user(username: str, password: str):
    """
    Add a User to the Users list

    :param username:
    :param password:
    """
    hashed_password: str = werkzeug.security.generate_password_hash(password, method="sha256")
    USERS[username] = hashed_password


def remove_user(username: str):
    """
    Remove an user from the Users list

    :param username:
    """
    USERS.pop(username)


def get_password_hash(username: str) -> str:
    """
    Get the password hash to check a user's password

    :param username:
    :return:
    """
    return USERS.get(username)


def check_if_user_exists(username: str) -> bool:
    """
    Checks if the given username exists

    :param username:
    :return: True, if exists
    """
    if USERS.get(username) is None:
        return False
    return True


def cli_add_user():
    """
    CLI-Helper tool that makes it easy to add a user.
    """
    print("CLI-User Adding Tool")
    print("Enter the username and password to be added to the available users")
    usr = input("Username:        ")
    psw = input("Password:        ")
    psw2 = input("Repeat Password: ")
    if psw != psw2:
        print("Passwords don't match, please try again.")
    print("\nIs this correct?")
    print("Username: ", usr)
    print("Password: ", psw)
    b = input("Is this correct? [y/N]: ")
    if b.lower() == "y":
        add_user(usr, psw)
        save_user_file()
        print("Saved new User.")
    else:
        print("Exiting without saving")


def token_required(f):
    """
    This creates the @token_required decorator, making it easy to use JWT authentication for any path I like by
    simply putting this decorator in front of it.

    The JWT received with the request (in the "x-access-tokens" header) is checked and the username of the sender is
    extracted. If the token is valid (otherwise `jwt.decode` raises a `DecodeError`) and the user exists, the current
    user is then passed to the function below the decorator for logging purposes.
    """
    @wraps(f)
    def decorator(*args, **kwargs):
        token = flask.request.headers.get("x-access-tokens")
        if not token:
            return flask.make_response("Unauthorized - Valid token is missing", 401)
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = data["name"]
            if current_user is None:
                return flask.make_response("Unauthorized - Invalid User", 401)
            return f(current_user, *args, **kwargs)
        except (jwt.DecodeError, jwt.ExpiredSignatureError):
            return flask.make_response("Unauthorized - Invalid Token", 401)
    return decorator


if __name__ == '__main__':
    print(USER_FILE)
    cli_add_user()
