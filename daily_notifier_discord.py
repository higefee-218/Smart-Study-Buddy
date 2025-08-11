# daily_notifier_discord.py

import os
import datetime
import pickle
import discord
from discord.ext import commands
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import google.generativeai as genai

# --- 1. Configure the Google Gemini API Key ---
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    print("Error: GOOGLE_API_KEY environment variable not set.")
    exit()

# --- 2. Discord Bot Configuration ---
# Replace with your Discord bot's token and the channel ID where you want messages sent.
DISCORD_BOT_TOKEN = ""  # Keep this token secret!
CHANNEL_ID = 1400717951228711046 # e.g., 123456789012345678

# --- 3. Google Calendar API Integration ---
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CREDENTIALS_FILE = 'credentials.json'

def get_calendar_events_today():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        print("Error: Authentication required. Run 'python authenticate.py' first.")
        return "Authentication required.", []

    service = build('calendar', 'v3', credentials=creds)
    start_of_day = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + datetime.timedelta(days=1)
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_of_day.isoformat() + 'Z',
        timeMax=end_of_day.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    if not events:
        return "No upcoming events found for today.", []
    
    events_list_str = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        summary = event.get('summary', 'No Title')
        events_list_str.append(f"- Event: {summary}, Start: {start}, End: {end}")
        
    return "\n".join(events_list_str), events


async def send_daily_plan():
    # Fetch today's schedule
    print("Fetching today's schedule...")
    today_events_str, _ = get_calendar_events_today()

    weekly_tasks_input = """Finish Python Project: 8 hours: High: Deep Work
Write history essay: 5 hours: High: Deep Work
Study for Physics exam: 6 hours: Medium: Review
Review lecture notes: 3 hours: Low: Review"""
    
    # Generate the Daily Plan with Gemini
    model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")
    
    prompt = f"""
    You are "Smart Scheduler AI", a highly skilled and helpful personal assistant for students. Your primary function is to create a focused, daily study and task schedule.

    Your instructions are to:
    1.  Create a detailed schedule for today, assigning tasks from the list below to available time blocks.
    2.  **Crucially, you must schedule the new tasks around the existing appointments for today.**
    3.  Provide a short, encouraging summary of the day's plan.
    
    **Constraints & Context:**
    -   Your work hours for today are from 8:30 AM to 5:30 PM, with a one-hour lunch break from 12:00 PM to 1:00 PM.
    -   Here are the user's weekly goals, hours, priority, and type:
    {weekly_tasks_input}
    -   Here are today's existing appointments from the user's calendar:
    {today_events_str}
    
    Please generate the full response now, formatted clearly using Markdown.
    """
    
    response = model.generate_content(prompt)
    daily_plan = response.text
    
    # Send the Plan via Discord
    # In daily_notifier_discord.py, find the 'send_daily_plan' function and replace it with this:

async def send_daily_plan():
    # Fetch today's schedule
    print("Fetching today's schedule...")
    today_events_str, _ = get_calendar_events_today()

    weekly_tasks_input = """Finish Python Project: 8 hours: High: Deep Work
Write history essay: 5 hours: High: Deep Work
Study for Physics exam: 6 hours: Medium: Review
Review lecture notes: 3 hours: Low: Review"""
    
    # Generate the Daily Plan with Gemini
    model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")
    
    prompt = f"""
    You are "Smart Scheduler AI", a highly skilled and helpful personal assistant for students. Your primary function is to create a focused, daily study and task schedule.

    Your instructions are to:
    1.  Create a detailed schedule for today, assigning tasks from the list below to available time blocks.
    2.  **Crucially, you must schedule the new tasks around the existing appointments for today.**
    3.  Provide a short, encouraging summary of the day's plan.
    
    **Constraints & Context:**
    -   Your work hours for today are from 8:30 AM to 5:30 PM, with a one-hour lunch break from 12:00 PM to 1:00 PM.
    -   Here are the user's weekly goals, hours, priority, and type:
    {weekly_tasks_input}
    -   Here are today's existing appointments from the user's calendar:
    {today_events_str}
    
    Please generate the full response now, formatted clearly using Markdown.
    """
    
    try:
        response = model.generate_content(prompt)
        daily_plan = response.text
    except Exception as e:
        # If the API call fails, we'll print the error and send a simple message
        print(f"Error calling Gemini API: {e}")
        daily_plan = "I'm sorry, I couldn't generate a schedule for you today. The AI is experiencing some technical difficulties."
    
    # Send the Plan via Discord
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
    
    @bot.event
    async def on_ready():
        print(f'{bot.user} has connected to Discord!')
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"📚 **Your Smart Study Buddy's Plan for {datetime.date.today().strftime('%A, %B %d')}**\n\n{daily_plan}")
        else:
            print(f"Error: Channel with ID {CHANNEL_ID} not found.")
        await bot.close()

    await bot.start(DISCORD_BOT_TOKEN)

# This part is a bit tricky to run, so we will create a simple runner
async def runner():
    await send_daily_plan()

if __name__ == '__main__':
    # You need to run this with an async function runner
    import asyncio
    asyncio.run(runner())