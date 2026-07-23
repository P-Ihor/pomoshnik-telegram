import os
import json
import time
import httpx
from mcp.server.fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import datetime

# Client ID provided by user
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_FILE = '/app/data/calendar_tokens.json'
DEVICE_CODE_FILE = '/app/data/calendar_device_codes.json'

def _load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def _save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f)

def get_calendar_auth_code() -> str:
    """
    Start the Google Calendar connection process.
    Returns the URL and the code the user needs to enter to authorize the bot.
    """
    user_id = "default"
    url = 'https://oauth2.googleapis.com/device/code'
    data = {
        'client_id': CLIENT_ID,
        'scope': ' '.join(SCOPES)
    }
    resp = httpx.post(url, data=data)
    if resp.status_code != 200:
        return f"Error getting auth code: {resp.text}"
    
    result = resp.json()
    
    codes = _load_json(DEVICE_CODE_FILE)
    codes[user_id] = {
        'device_code': result['device_code'],
        'expires_at': time.time() + result['expires_in']
    }
    _save_json(DEVICE_CODE_FILE, codes)
    
    return (f"Для подключения календаря перейдите по ссылке: {result['verification_url']}\n"
            f"И введите код: {result['user_code']}\n\n"
            f"После того как вы разрешите доступ на сайте, попросите меня 'проверить статус подключения календаря'.")

def verify_calendar_auth() -> str:
    """
    Check if the user has completed the Google Calendar connection.
    Use this after the user says they have entered the code on the Google website.
    """
    user_id = "default"
    codes = _load_json(DEVICE_CODE_FILE)
    if user_id not in codes:
        return "Нет активного запроса на подключение. Сначала начните процесс подключения (скажите 'подключи календарь')."
    
    device_code = codes[user_id]['device_code']
    
    url = 'https://oauth2.googleapis.com/token'
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'device_code': device_code,
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
    }
    
    resp = httpx.post(url, data=data)
    result = resp.json()
    
    if 'error' in result:
        if result['error'] == 'authorization_pending':
            return "Вы еще не подтвердили доступ на сайте. Пожалуйста, введите код по ссылке и попробуйте снова."
        else:
            return f"Ошибка авторизации: {result['error']}"
            
    tokens = _load_json(TOKEN_FILE)
    tokens[user_id] = {
        'token': result['access_token'],
        'refresh_token': result.get('refresh_token'),
        'token_uri': 'https://oauth2.googleapis.com/token',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scopes': SCOPES
    }
    _save_json(TOKEN_FILE, tokens)
    
    del codes[user_id]
    _save_json(DEVICE_CODE_FILE, codes)
    
    return "Календарь успешно подключен! Теперь вы можете просить меня добавлять или читать события."

def _get_credentials(user_id: str):
    tokens = _load_json(TOKEN_FILE)
    if user_id not in tokens:
        return None
    
    token_info = tokens[user_id]
    creds = Credentials(
        token=token_info['token'],
        refresh_token=token_info.get('refresh_token'),
        token_uri=token_info['token_uri'],
        client_id=token_info['client_id'],
        client_secret=token_info.get('client_secret'),
        scopes=token_info['scopes']
    )
    return creds

def add_calendar_event(summary: str, start_time: str, end_time: str, description: str = "", recurrence: list[str] = None) -> str:
    """
    Add an event to the user's Google Calendar.
    
    Args:
        summary: The title of the event
        start_time: Start time in ISO format with timezone (e.g. 2026-07-06T15:00:00+03:00). For full day events, use YYYY-MM-DD.
        end_time: End time in ISO format with timezone (e.g. 2026-07-06T16:00:00+03:00). For full day events, use YYYY-MM-DD.
        description: Optional description of the event
        recurrence: Optional list of RRULE strings for recurring events (e.g. ["RRULE:FREQ=YEARLY"])
    """
    user_id = "default"
    creds = _get_credentials(user_id)
    if not creds:
        return "Календарь не подключен. Пожалуйста, попросите меня подключить календарь."
        
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        # Check if dates are full day (YYYY-MM-DD) or datetime
        start_key = 'date' if len(start_time) == 10 else 'dateTime'
        end_key = 'date' if len(end_time) == 10 else 'dateTime'
        
        event = {
          'summary': summary,
          'description': description,
          'start': {
            start_key: start_time,
          },
          'end': {
            end_key: end_time,
          },
        }
        
        if recurrence:
            event['recurrence'] = recurrence
            
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Событие '{summary}' успешно добавлено! Ссылка: {event.get('htmlLink')}"
    except Exception as e:
        return f"Ошибка при добавлении события: {str(e)}"

def list_calendar_events(max_results: int = 10) -> str:
    """
    List upcoming events from the user's Google Calendar.
    
    Args:
        max_results: Maximum number of events to return (default 10)
    """
    user_id = "default"
    creds = _get_credentials(user_id)
    if not creds:
        return "Календарь не подключен. Пожалуйста, попросите меня подключить календарь."
        
    try:
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=max_results, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return 'Предстоящих событий не найдено.'

        res = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            res.append(f"- {start}: {event['summary']}")
        return "\n".join(res)
    except Exception as e:
        return f"Ошибка при получении событий: {str(e)}"

def register(mcp: FastMCP):
    mcp.tool()(get_calendar_auth_code)
    mcp.tool()(verify_calendar_auth)
    mcp.tool()(add_calendar_event)
    mcp.tool()(list_calendar_events)
