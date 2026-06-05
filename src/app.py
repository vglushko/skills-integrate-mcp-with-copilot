"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
import sqlite3
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")

DB_PATH = current_dir / "activities.db"

DEFAULT_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
    }
}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS activities (
            name TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            schedule TEXT NOT NULL,
            max_participants INTEGER NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_name TEXT NOT NULL,
            email TEXT NOT NULL,
            UNIQUE(activity_name, email),
            FOREIGN KEY(activity_name) REFERENCES activities(name)
        )
        """
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_participants_activity_email ON participants(activity_name, email)"
    )
    conn.commit()

    cursor.execute("SELECT COUNT(1) FROM activities")
    if cursor.fetchone()[0] == 0:
        for name, details in DEFAULT_ACTIVITIES.items():
            cursor.execute(
                "INSERT INTO activities(name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                (name, details["description"], details["schedule"], details["max_participants"]),
            )
        conn.commit()
    conn.close()


def load_activities():
    conn = get_db_connection()
    cursor = conn.cursor()
    activities = {}
    activity_rows = cursor.execute("SELECT * FROM activities").fetchall()

    for row in activity_rows:
        participants = [
            participant["email"]
            for participant in cursor.execute(
                "SELECT email FROM participants WHERE activity_name = ?",
                (row["name"],),
            ).fetchall()
        ]

        activities[row["name"]] = {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": participants,
        }

    conn.close()
    return activities


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return load_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    conn = get_db_connection()
    cursor = conn.cursor()

    activity = cursor.execute(
        "SELECT * FROM activities WHERE name = ?", (activity_name,)
    ).fetchone()

    if activity is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Activity not found")

    participants = [
        participant["email"]
        for participant in cursor.execute(
            "SELECT email FROM participants WHERE activity_name = ?", (activity_name,)
        ).fetchall()
    ]

    if email in participants:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    if len(participants) >= activity["max_participants"]:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Activity is full"
        )

    cursor.execute(
        "INSERT INTO participants(activity_name, email) VALUES (?, ?)",
        (activity_name, email),
    )
    conn.commit()
    conn.close()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    conn = get_db_connection()
    cursor = conn.cursor()

    activity = cursor.execute(
        "SELECT * FROM activities WHERE name = ?", (activity_name,)
    ).fetchone()

    if activity is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Activity not found")

    participant = cursor.execute(
        "SELECT * FROM participants WHERE activity_name = ? AND email = ?",
        (activity_name, email),
    ).fetchone()

    if participant is None:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    cursor.execute(
        "DELETE FROM participants WHERE activity_name = ? AND email = ?",
        (activity_name, email),
    )
    conn.commit()
    conn.close()

    return {"message": f"Unregistered {email} from {activity_name}"}
