# APU Timetable Calendar

A Flask application that scrapes the APU (Asia Pacific University) timetable website and generates an ICS calendar feed that can be subscribed to from any calendar application.

## Features

- 📅 Automatic timetable scraping from APU's website
- 🔄 Converts timetable data into calendar events
- 📱 Mobile-friendly calendar view with intuitive UI
- 🎨 Ability to customize subject names (instead of course codes)
- 📲 Provides an ICS feed URL that can be subscribed to from any calendar app
- ⏰ Automatic updates at configurable times

## Screenshot

![screenshot](https://github.com/user-attachments/assets/6ccd20b7-f67b-47ee-a913-25736311d3f1)

## Prerequisites

- Python 3.7+
- Flask
- BeautifulSoup4
- ics
- pytz
- requests

## Installation

1. Clone this repository
   ```bash
   git clone https://github.com/yourusername/apu-timetable-calendar.git
   cd apu-timetable-calendar
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your intake and group
   ```bash
   # Edit config.json with your intake code and group
   {
     "intake": "YOUR_INTAKE_CODE",
     "group": "YOUR_GROUP",
     "weeks_ahead": 4,
     "updates_per_day": ["08:00", "16:00"]
   }
   ```

4. Run the application
   ```bash
   python app.py
   ```

5. Open http://localhost:5000 in your browser

## Docker Installation

You can also run this application using Docker:

```bash
docker build -t apu-timetable-calendar .
docker run -p 5000:5000 apu-timetable-calendar
```

## Configuration

### config.json

- `intake`: Your intake code (e.g., "APUFEFREI2501")
- `group`: Your group (e.g., "G1")
- `weeks_ahead`: How many weeks to fetch in advance
- `updates_per_day`: Times of day to refresh the calendar data

### subject_mapping.json

This file maps course codes to friendly names. For example:

```json
{
  "CX007-2.5-3-JAV-L-1": "Java Programming (Lecture)",
  "CX007-2.5-3-JAV-LAB-1": "Java Programming (Lab)"
}
```

## Usage

1. Once the server is running, go to http://localhost:5000
2. You'll see a calendar with your timetable and a subscription URL
3. Add the subscription URL to your preferred calendar application
4. The calendar will automatically update according to your configuration

### Adding to Calendar Apps

#### Google Calendar
1. Go to Google Calendar
2. Click the "+" next to "Other calendars" 
3. Select "From URL"
4. Paste your calendar URL and click "Add calendar"

#### Apple Calendar
1. Go to File > New Calendar Subscription
2. Paste your calendar URL
3. Set auto-refresh and other options as desired

#### Outlook
1. Go to Calendar view
2. Right-click on "Other calendars"
3. Select "Add calendar" > "From Internet"
4. Paste your calendar URL

## Acknowledgements
- APU for providing the timetable data for free
