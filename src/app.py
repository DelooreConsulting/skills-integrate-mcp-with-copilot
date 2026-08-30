"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(Path(__file__).parent, "static")),
    name="static",
)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "student"


class LoginRequest(BaseModel):
    email: str
    password: str


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}

users = {
    "admin@mergington.edu": {
        "email": "admin@mergington.edu",
        "name": "School Administrator",
        "password_hash": hash_password("admin123"),
        "role": "system_admin",
    },
    "leader@mergington.edu": {
        "email": "leader@mergington.edu",
        "name": "Activity Leader",
        "password_hash": hash_password("leader123"),
        "role": "activity_admin",
    },
}

sessions = {}


def parse_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authentication header")

    return token


def get_current_user(authorization: str | None = Header(default=None)):
    token = parse_bearer_token(authorization)
    email = sessions.get(token)

    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = users.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def issue_session_token_for(email: str) -> str:
    for token, stored_email in sessions.items():
        if stored_email == email:
            return token
    token = secrets.token_urlsafe(32)
    sessions[token] = email
    return token


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/auth/register")
def register_user(payload: RegisterRequest):
    email = payload.email.lower().strip()
    if email in users:
        raise HTTPException(status_code=400, detail="User already exists")

    role = payload.role.lower().strip()
    if role not in {"student", "activity_admin", "system_admin"}:
        role = "student"

    user = {
        "email": email,
        "name": payload.name or email,
        "password_hash": hash_password(payload.password),
        "role": role,
    }
    users[email] = user

    token = issue_session_token_for(email)
    return {"token": token, "user": {"email": user["email"], "name": user["name"], "role": user["role"]}}


@app.post("/auth/login")
def login_user(payload: LoginRequest):
    email = payload.email.lower().strip()
    user = users.get(email)
    if not user or user["password_hash"] != hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = secrets.token_urlsafe(32)
    sessions[token] = email
    return {"token": token, "user": {"email": user["email"], "name": user["name"], "role": user["role"]}}


@app.post("/auth/logout")
def logout_user(authorization: str | None = Header(default=None)):
    token = parse_bearer_token(authorization)
    sessions.pop(token, None)
    return {"message": "Logged out"}


@app.get("/auth/me")
def me(current_user=Depends(get_current_user)):
    return current_user


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str | None = None,
    current_user=Depends(get_current_user),
):
    """Sign up a student for an activity."""
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    target_email = (email or current_user["email"]).lower().strip()
    if current_user["role"] == "student" and email and email.lower().strip() != current_user["email"]:
        raise HTTPException(
            status_code=403,
            detail="Students can only manage their own activity registrations",
        )

    if current_user["role"] == "student":
        target_email = current_user["email"]

    activity = activities[activity_name]
    if target_email in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(status_code=400, detail="Activity is full")

    activity["participants"].append(target_email)
    return {"message": f"Signed up {target_email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str | None = None,
    current_user=Depends(get_current_user),
):
    """Unregister a student from an activity."""
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    if current_user["role"] == "student":
        target_email = current_user["email"]
    else:
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        target_email = email.lower().strip()

    if current_user["role"] == "student" and email and email.lower().strip() != current_user["email"]:
        raise HTTPException(
            status_code=403,
            detail="Students can only manage their own activity registrations",
        )

    activity = activities[activity_name]
    if target_email not in activity["participants"]:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    activity["participants"].remove(target_email)
    return {"message": f"Unregistered {target_email} from {activity_name}"}
