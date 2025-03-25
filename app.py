from flask import Flask, render_template, request, Response, jsonify
from bs4 import BeautifulSoup
import requests
from ics import Calendar, Event
import datetime
import pytz
import json
import os
import logging
import time
from threading import Thread

app = Flask(__name__)

# Configuration
CONFIG_FILE = os.environ.get('CONFIG_FILE', 'config.json')
SUBJECT_MAPPING_FILE = os.environ.get(
    'SUBJECT_MAPPING_FILE', 'subject_mapping.json')
CACHE_DURATION = int(os.environ.get('CACHE_DURATION', 3600)
                     )  # Default cache: 1 hour
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Set up logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('apu_calendar')

# Global cache
timetable_cache = {
    'events': [],
    'last_updated': None
}


def load_config():
    """Load configuration from file or create default if it doesn't exist."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(
                f"Error parsing {CONFIG_FILE}. Using default configuration.")

    # Default configuration
    default_config = {
        'intake': 'APUFEFREI2501',
        'group': 'G1',
        'weeks_ahead': 4,
        'updates_per_day': ['08:00', '16:00']
    }

    # Save default config if the file doesn't exist
    if not os.path.exists(CONFIG_FILE):
        save_config(default_config)

    return default_config


def load_subject_mapping():
    """Load subject mapping from file or create empty if it doesn't exist."""
    if os.path.exists(SUBJECT_MAPPING_FILE):
        try:
            with open(SUBJECT_MAPPING_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(
                f"Error parsing {SUBJECT_MAPPING_FILE}. Using empty mapping.")

    return {}


def save_config(config):
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved successfully")
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")


def save_subject_mapping(mapping):
    """Save subject mapping to file."""
    try:
        with open(SUBJECT_MAPPING_FILE, 'w') as f:
            json.dump(mapping, f, indent=2)
        logger.info("Subject mapping saved successfully")
    except Exception as e:
        logger.error(f"Error saving subject mapping: {e}")


def get_future_mondays(weeks_ahead):
    """Get a list of future Mondays for the specified number of weeks ahead."""
    today = datetime.datetime.now()
    current_monday = today - datetime.timedelta(days=today.weekday())
    mondays = []

    for i in range(weeks_ahead):
        monday = current_monday + datetime.timedelta(weeks=i)
        mondays.append(monday.strftime('%Y-%m-%d'))

    return mondays


def fetch_timetable(week, intake, group):
    """Fetch timetable from APU's website."""
    url = f"https://api.apiit.edu.my/timetable-print/index.php?Week={week}&Intake={intake}&Intake_Group={group}&print_request=print_tt"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # Raise an error for bad responses
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error fetching timetable for week {week}: {e}")
        return None


def get_pretty_subject_name(code, mapping):
    """Get a user-friendly subject name from the mapping or return the code if not found."""
    return mapping.get(code, code)


def parse_timetable(html, subject_mapping):
    """Parse timetable HTML and extract events."""
    if not html:
        return []

    events = []
    soup = BeautifulSoup(html, 'html.parser')

    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) == 6:
            try:
                date = cells[0].text.strip()
                time_range = cells[1].text.strip()
                classroom = cells[2].text.strip()
                location = cells[3].text.strip()
                subject_code = cells[4].text.strip()
                lecturer = cells[5].text.strip()

                # Use the subject mapping
                subject_name = get_pretty_subject_name(
                    subject_code, subject_mapping)

                # Parse the date
                date_obj = datetime.datetime.strptime(date, '%a, %d-%b-%Y')

                # Parse time range
                start_time, end_time = time_range.split('-')

                # Create ISO format datetime strings
                start_datetime = f"{date_obj.strftime('%Y-%m-%d')}T{start_time.strip()}"
                end_datetime = f"{date_obj.strftime('%Y-%m-%d')}T{end_time.strip()}"

                events.append({
                    'start': start_datetime,
                    'end': end_datetime,
                    'subject': subject_name,
                    'location': f"{classroom}, {location}",
                    'description': f"Course Code: {subject_code}\nLecturer: {lecturer}"
                })

                logger.debug(
                    f"Created event: {subject_name} from {start_datetime} to {end_datetime}")

            except Exception as e:
                logger.error(f"Error parsing row: {e}")
                continue

    return events


def generate_ics(events):
    """Generate an ICS calendar file from the events."""
    cal = Calendar()
    kl_tz = pytz.timezone('Asia/Kuala_Lumpur')

    for event_data in events:
        event = Event()
        try:
            # Parse the ISO format datetime strings
            start = datetime.datetime.strptime(
                event_data['start'], '%Y-%m-%dT%H:%M')
            end = datetime.datetime.strptime(
                event_data['end'], '%Y-%m-%dT%H:%M')

            start = kl_tz.localize(start)
            end = kl_tz.localize(end)

            event.name = event_data['subject']
            event.begin = start
            event.end = end
            event.location = event_data['location']
            event.description = event_data['description']
            cal.events.add(event)
        except Exception as e:
            logger.error(f"Error generating calendar event: {e}")

    return cal


def update_cache():
    """Update the timetable cache."""
    config = load_config()
    subject_mapping = load_subject_mapping()
    all_events = []

    try:
        mondays = get_future_mondays(config['weeks_ahead'])

        for monday in mondays:
            html = fetch_timetable(monday, config['intake'], config['group'])
            if html:
                events = parse_timetable(html, subject_mapping)
                all_events.extend(events)

        timetable_cache['events'] = all_events
        timetable_cache['last_updated'] = datetime.datetime.now()

        logger.info(f"Cache updated with {len(all_events)} events")
    except Exception as e:
        logger.error(f"Error updating cache: {e}")


def background_updater():
    """Background thread to update the cache periodically."""
    while True:
        # First update
        update_cache()

        # Check if we need to update at specific times
        config = load_config()

        while True:
            now = datetime.datetime.now()
            # Check if cache needs to be refreshed based on cache duration
            if (timetable_cache['last_updated'] is None or
                    (now - timetable_cache['last_updated']).total_seconds() > CACHE_DURATION):
                update_cache()

            # Check for scheduled updates
            current_time = now.strftime('%H:%M')
            if current_time in config['updates_per_day']:
                update_cache()

            # Sleep for a minute before checking again
            time.sleep(60)


@app.route('/')
def index():
    """Render the home page."""
    config = load_config()
    return render_template('index.html', config=config)


@app.route('/calendar_view')
def calendar_view():
    """Render the calendar view page."""
    # Use cached events if available
    if timetable_cache['events'] and timetable_cache['last_updated']:
        cache_age = (datetime.datetime.now() -
                     timetable_cache['last_updated']).total_seconds()

        if cache_age < CACHE_DURATION:
            logger.info(f"Using cached events (age: {cache_age:.2f}s)")
            return render_template('calendar.html', events=timetable_cache['events'])

    # If no valid cache, refresh it
    update_cache()
    return render_template('calendar.html', events=timetable_cache['events'])


@app.route('/subject_mapping', methods=['GET', 'PUT'])
def subject_mapping_endpoint():
    """API endpoint to get or update subject mappings."""
    if request.method == 'GET':
        mapping = load_subject_mapping()
        return jsonify(mapping)
    elif request.method == 'PUT':
        try:
            new_mapping = request.json
            save_subject_mapping(new_mapping)
            # Update cache since mapping changed
            update_cache()
            return {'status': 'success'}
        except Exception as e:
            logger.error(f"Error updating subject mapping: {e}")
            return {'status': 'error', 'message': str(e)}, 400


@app.route('/update_config', methods=['POST'])
def update_config_endpoint():
    """API endpoint to update configuration."""
    try:
        config = load_config()
        config['intake'] = request.form['intake']
        config['group'] = request.form['group']
        config['weeks_ahead'] = int(request.form['weeks_ahead'])
        updates = request.form['updates_per_day'].split(',')
        config['updates_per_day'] = [time.strip() for time in updates]
        save_config(config)

        # Update cache since config changed
        update_cache()

        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        return {'status': 'error', 'message': str(e)}, 400


@app.route('/calendar.ics')
def calendar_endpoint():
    """Provide the calendar as an ICS file."""
    # Use cached events if available and fresh
    if timetable_cache['events'] and timetable_cache['last_updated']:
        cache_age = (datetime.datetime.now() -
                     timetable_cache['last_updated']).total_seconds()

        if cache_age < CACHE_DURATION:
            logger.info(f"Using cached events for ICS (age: {cache_age:.2f}s)")
            cal = generate_ics(timetable_cache['events'])
            response = Response(str(cal), mimetype='text/calendar')
            response.headers['Content-Disposition'] = 'inline'
            return response

    # If no valid cache, refresh it
    update_cache()

    cal = generate_ics(timetable_cache['events'])
    response = Response(str(cal), mimetype='text/calendar')
    response.headers['Content-Disposition'] = 'inline'
    return response


@app.route('/status')
def status():
    """Return status information about the application."""
    return {
        'status': 'running',
        'last_cache_update': timetable_cache['last_updated'].isoformat() if timetable_cache['last_updated'] else None,
        'event_count': len(timetable_cache['events']),
        'version': '1.0.0'
    }


if __name__ == '__main__':
    # Start background thread for cache updates
    updater_thread = Thread(target=background_updater, daemon=True)
    updater_thread.start()

    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))

    # Run app
    app.run(host='0.0.0.0', port=port, debug=os.environ.get(
        'FLASK_DEBUG', 'False').lower() == 'true')
