# streamlit_app.py

import streamlit as st
from datetime import date, time as dttime
import subprocess
import os

st.title("🧘 Mindbody Class Booker")

# — credentials —
st.sidebar.header("Mindbody Login")
username = st.sidebar.text_input("Username", type="default")
password = st.sidebar.text_input("Password", type="password")

# — class selection —
st.header("Class Details")
class_name = st.text_input("Class Name", help="e.g. 'Yoga Flow'")
class_date = st.date_input("Class Date", min_value=date.today(), help="Pick the day")
class_time = st.time_input("Class Time", value=dttime(6, 15), help="Choose the time (EDT)")

# — action button —
if st.button("Book Class"):
    # basic validation
    if not username or not password or not class_name:
        st.error("Please fill in your username, password, and class name.")
    else:
        # format arguments exactly as your main.py expects
        day_str = class_date.strftime("%B %d, %Y")      # "April 16, 2025"
        time_str = class_time.strftime("%I:%M %p") + " EDT"  # "06:15 PM EDT"

        cmd = [
            "python", "main.py",
            "--name", class_name,
            "--day", day_str,
            "--time", time_str
        ]

        # inject credentials into the subprocess env
        env = os.environ.copy()
        env["USERNAME"] = username
        env["PASSWORD"] = password

        st.info(f"Running:\n`{' '.join(cmd)}`")
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
        st.text_area("Output & Errors", value=result.stdout + "\n" + result.stderr, height=300)