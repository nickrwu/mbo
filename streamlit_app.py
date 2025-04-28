# streamlit_app.py

import streamlit as st
from datetime import date, time as dttime
import subprocess
import os

os.system("sudo playwright install-deps")
os.system("playwright install")

st.title("🧘 Mindbody Class Booker")

# — credentials —
st.sidebar.header("Mindbody Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

# — class selection —
st.header("Class Details")
class_name = st.text_input("Class Name", help="e.g. 'Yoga Flow'")
class_date = st.date_input("Class Date", min_value=date.today())
class_time = st.time_input("Class Time", value=dttime(6, 15))

# — action button —
if st.button("Book Class"):
    if not (username and password and class_name):
        st.error("Please fill in username, password, and class name.")
    else:
        # format exactly as: --name="Yoga Flow" --day="April 16, 2025" --time="06:15 PM EDT"
        day_str  = class_date.strftime("%B %d, %Y")
        time_str = class_time.strftime("%I:%M %p") + " EDT"

        cmd = (
            f'python book.py '
            f'--name="{class_name}" '
            f'--day="{day_str}" '
            f'--time="{time_str}"'
        )

        # inject credentials into env
        env = os.environ.copy()
        env["USERNAME"] = username
        env["PASSWORD"] = password

        st.info(f"Running:\n`{cmd}`")
        with st.spinner("Booking in progress…"):
            result = subprocess.run(
                cmd,
                shell=True,
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