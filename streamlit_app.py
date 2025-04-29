# streamlit_app.py

import streamlit as st
import sys
from datetime import date, time as dttime
import subprocess
import os

CATEGORY_TO_CLASSES = {
    "YOGA": [
        "V2: All Levels Vinyasa Flow",
        "V1: Alignment-Based Vinyasa",
        "V3: Dynamic Vinyasa + Advanced Postures",
        "V0 - Slow Flow",
        "V-HAB: Recovery",
        "HB: Hand Balancing",
        "Guided Meditation",
    ],
    "CYCLE": ["vBeats", "vRide", "Festival Ride"],
    "FITNESS": [
        "Total Body Strength 45",
        "Core 30",
        "Total Body Endurance 45",
        "Cardio Conditioning 30",
        "Kettlebell Strength",
    ],
    "AERIAL": [
        "Beginner Silks",
        "Advanced Beginner Silks",
        "Intermediate Silks",
        "Intermediate/Advanced Silks",
        "Hammock",
        "Introduction to Silks",
        "Circus Stretch (Ground Class)",
        "Open Workout (AB +)",
        "Choreography 1: Foundations (AB+)",
        "Choreography 2: Lab (Instructor Rec)",
    ],
    "PORCH AERIAL": [
        "Silks Conditioning",
        "Beginner Silks",
        "Introduction to Silks",
        "Hammock",
        "Choreography 1: Foundations (AB +)",
        "Advanced Beginner Silks",
    ],
    "CLIMBING": [
        "Holds and Directionality Technique Clinic",
        "Footwork & Balance-Led Decision Making Technique Clinic",
        "Bouldering Technique Fundamentals",
        "Bouldering 101",
    ],
    "KIDS CLIMBING": ["Kids Bouldering 101"],
}

def ensure_playwright():
    CACHE = os.path.expanduser("~/.cache/ms-playwright")
    if not os.path.isdir(CACHE):
        try:
            # single command with deps on Linux
            cmd = ["playwright", "install", "chromium"]
            with st.spinner("Installing Playwright browsers…"):
                subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            st.error("⚠️ Could not install Playwright browsers. You may see failures when booking.")
            st.write(f"`{e.cmd}` exited with code {e.returncode}")
            # do NOT st.stop() if you still want the rest of your UI to render

st.title("🧗‍♂️ Vital MBO")
ensure_playwright()

# — credentials —
st.sidebar.header("Mindbody Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

# — class selection —
st.header("Class Details")
gym_id = st.text_input("Gym ID", value="836167", help="e.g. '123456'")
category = st.selectbox("Category", list(CATEGORY_TO_CLASSES.keys()), value="AERIAL")
filtered_classes = CATEGORY_TO_CLASSES.get(category, [])
class_dropdown = st.selectbox(
    "Class Name",
    [f"{category} - {c}" for c in filtered_classes],
    value="Hammock"
)

# Other override text input
other_name = st.text_input(
    "Other Class Name (override)",
    help="Type here to override dropdown selection e.g. 'Yoga Flow'"
)

class_name = other_name.strip() if other_name.strip() else class_dropdown
class_date = st.date_input("Class Date", min_value=date.today(), format="MM/DD/YYYY")
class_time = st.time_input("Class Time", value=dttime(17, 15))

# — action button —
if st.button("Book Class"):
    if not (username and password and class_name and gym_id):
        st.error("Please fill in username, password, gym ID, and class name.")
    else:
        # format exactly as: --name="Yoga Flow" --day="April 16, 2025" --time="06:15 PM EDT"
        day_str  = class_date.strftime("%B %d, %Y")
        hour = class_time.hour % 12 or 12
        time_str = f"{hour}:{class_time.strftime('%M %p').lower()} EDT"

        cmd = [
             sys.executable,
             "book.py",
             "--name", class_name,
             "--day", day_str,
             "--time", time_str,
             "--id", gym_id,
             "--headless",
             "--proxy"
         ]

        # inject credentials into env
        env = os.environ.copy()
        env.update({"USERNAME": username, "PASSWORD": password})

        st.info(f"Running:\n`{cmd}`")

        st.subheader("Logs")
        log_placeholder = st.empty()
        logs = ""

        with st.spinner("Booking in progress…"):
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
            
            # read and display incrementally
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                logs += line
                # re-render our placeholder with the fresh content
                log_placeholder.code(logs, language="plain", line_numbers=True)

            proc.wait()

        if proc.returncode == 0:
            st.success("✅ Booking completed successfully!")
        else:
            st.error(f"❌ Booking failed (exit code {proc.returncode})")
