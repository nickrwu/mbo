# streamlit_app.py

import streamlit as st
import sys
from datetime import date, time as dttime
import subprocess
import os

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
    

st.title("🧘 Mindbody Class Booker")
ensure_playwright()

# — credentials —
st.sidebar.header("Mindbody Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

# — class selection —
st.header("Class Details")
gym_id = st.text_input("Gym ID", value="836167", help="e.g. '123456'")
class_name = st.text_input("Class Name", help="e.g. 'Yoga Flow'")
class_date = st.date_input("Class Date", min_value=date.today())
class_time = st.time_input("Class Time", value=dttime(6, 15))

# — action button —
if st.button("Book Class"):
    if not (username and password and class_name and gym_id):
        st.error("Please fill in username, password, gym ID, and class name.")
    else:
        # format exactly as: --name="Yoga Flow" --day="April 16, 2025" --time="06:15 PM EDT"
        day_str  = class_date.strftime("%B %d, %Y")
        time_str = class_time.strftime("%I:%M %p") + " EDT"

        cmd = [
             sys.executable,
             "book.py",
             "--name", class_name,
             "--day", day_str,
             "--time", time_str,
             "--id", gym_id,
             "--headless"
         ]

        # inject credentials into env
        env = os.environ.copy()
        env.update({"USERNAME": username, "PASSWORD": password})

        st.info(f"Running:\n`{cmd}`")
        with st.spinner("Booking in progress…"):
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env
            )

        if result.returncode == 0:
            st.success("✅ Booking completed successfully!")
        else:
            st.error(f"❌ Booking failed (exit code {result.returncode})")

        st.subheader("Logs")
        st.text_area(
            "Output & Errors",
            value=result.stdout + "\n" + result.stderr,
            height=300
        )
