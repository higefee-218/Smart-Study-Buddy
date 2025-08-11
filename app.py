import streamlit as st
import google.generativeai as genai
import os
import datetime
import pickle
import sys
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# --- 1. Configure the Google Gemini API Key ---
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    st.error("Google API Key not found. Please set the GOOGLE_API_KEY environment variable.")
    st.stop()

# --- 2. Initialize the Generative Model ---
model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")

# --- 3. Google Calendar API Integration (Corrected Pathing) ---
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_events():
    creds = None
    # Check if we are running in a PyInstaller-packaged app
    if getattr(sys, 'frozen', False):
        # In a frozen app, use the bundled path
        bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
        token_path = os.path.join(bundle_dir, 'token.pickle')
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
    else:
        # In a normal Python script, use the standard path
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
    
    if not creds or not creds.valid:
        st.error("Authentication required. Please run the 'authenticate.py' script first.")
        st.stop()

    service = build('calendar', 'v3', credentials=creds)
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    end_of_week = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + 'Z'
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        timeMax=end_of_week,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    if not events:
        return "No upcoming events found for the next 7 days.", []
    
    events_list_str = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        summary = event.get('summary', 'No Title')
        events_list_str.append(f"- Event: {summary}, Start: {start}, End: {end}")
        
    return "Existing calendar events for the next 7 days:\n" + "\n".join(events_list_str), events

# --- 4. Streamlit App Interface ---
st.set_page_config(page_title="Context-Aware Study & Task Scheduler AI", layout="centered")

st.title("🗓️ Context-Aware Study & Task Scheduler AI")
st.markdown("I will create your weekly schedule, taking into account your existing calendar events!")

# --- Get calendar events at the start ---
events_text, _ = get_calendar_events()
st.session_state.calendar_events_text = events_text

st.info("Calendar events fetched successfully!")
st.markdown(st.session_state.calendar_events_text)

# --- Working Hours Input ---
st.subheader("Your Daily Working Hours")
col1, col2 = st.columns(2)
with col1:
    start_time = st.time_input("Start Time", value=datetime.time(8, 30))
with col2:
    end_time = st.time_input("End Time", value=datetime.time(17, 30))
lunch_break = st.checkbox("Include a 1-hour lunch break (12:00 PM - 1:00 PM)?", value=True)

# --- Task Input (Improved with Priority and Type) ---
st.subheader("Your Weekly Goals, Hours, Priority, and Type")
st.markdown("List each goal on a new line, followed by the estimated hours, a priority, and a task type.")
weekly_tasks_input = st.text_area(
    "Example:",
    height=250,
    value="""Finish Python Project: 8 hours: High: Deep Work
Write history essay: 5 hours: High: Deep Work
Study for Physics exam: 6 hours: Medium: Review
Review lecture notes: 3 hours: Low: Review"""
)

# --- Button to trigger the AI response ---
if st.button("Generate My Weekly Schedule"):
    if weekly_tasks_input:
        with st.spinner("Generating your personalized schedule..."):
            try:
                start_time_str = start_time.strftime("%I:%M %p")
                end_time_str = end_time.strftime("%I:%M %p")
                lunch_break_instruction = "with a one-hour lunch break from 12:00 PM to 1:00 PM" if lunch_break else ""
                
                full_prompt = f"""
                You are "Smart Scheduler AI", a highly skilled and helpful personal assistant for students. Your primary function is to help users manage their time effectively by creating a weekly study and task schedule.

                Your instructions are to:
                1.  Create a detailed, day-by-day schedule for the upcoming week.
                2.  Break down larger tasks into smaller, manageable chunks and assign them to specific time blocks.
                3.  **Crucially, you must schedule the new tasks around the existing appointments from the user's calendar.** Do not schedule anything during a pre-existing event. Instead, use the free time slots on that day to schedule the user's tasks.
                4.  **Prioritize the tasks based on their priority level ('High', 'Medium', 'Low'). Schedule 'High' priority tasks first.**
                5.  **Consider the task type when scheduling.** Try to schedule 'Deep Work' tasks during the user's most focused hours (e.g., the morning) and 'Review' or 'Admin' tasks later in the day.
                6.  Provide a short, encouraging summary of the week's plan.
                7.  Offer 3-5 personalized and actionable study tips based on the tasks.

                **Constraints & Context:**
                -   Your work hours are from {start_time_str} to {end_time_str} {lunch_break_instruction}.
                -   Here are the user's weekly goals and estimated hours:
                {weekly_tasks_input}
                -   Here are the existing appointments and events from the user's calendar:
                {st.session_state.calendar_events_text}

                Please generate the full response now, formatted clearly using Markdown.
                """
                response = model.generate_content(full_prompt)
                st.subheader("Your Personalized Weekly Plan:")
                st.markdown(response.text)

            except Exception as e:
                st.error(f"An error occurred: {e}")
                st.warning("Please check your inputs and try again.")
    else:
        st.warning("Please enter your weekly tasks and hours to generate a schedule!")

st.markdown("---")
st.caption("Powered by Google Gemini 1.5 Flash")