import os.path
import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .database import SessionLocal
from .models import Professor, EmailLog, Schedule, Section, Preference

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service(server_mode: bool = False):
    """Authenticates and returns the Gmail API service.

    Args:
        server_mode: When True, raises RuntimeError instead of launching the
                     interactive OAuth flow. Use this for background jobs or
                     headless server contexts where stdin is unavailable.
    """
    # Resolve absolute paths to keep auth working when executed from other dirs
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    token_path = os.path.join(BASE_DIR, 'token.json')
    creds_path = os.path.join(BASE_DIR, 'credentials.json')

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif server_mode:
            raise RuntimeError(
                "Gmail token is missing or expired. Run the app interactively "
                "once to complete the OAuth flow and regenerate token.json."
            )
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def send_preference_email(prof_id: int, semester: str, year: int) -> dict:
    """
    Drafts and sends a preference collection email to a specific professor.
    Embeds a custom header (X-Scheduler-Token) to track their reply.
    Logs the sent email to the database.
    """
    db = SessionLocal()

    try:
        service = get_gmail_service()
        # 1. Get the professor from the database
        prof = db.query(Professor).filter(Professor.id == prof_id).first()
        if not prof:
            return {"error": f"Professor with ID {prof_id} not found."}
        
        # 2. Get their schedule from last year (same semester)
        # For example, if we are scheduling Fall 2025, look at Fall 2024.
        last_semester = semester
        last_year = year - 1
        
        # We need to query the finalized schedule for the previous term
        last_schedule = db.query(Schedule).filter(
            Schedule.semester == last_semester,
            Schedule.year == last_year,
            Schedule.status == "Finalized"
        ).first()

        schedule_table_text = ""

        if last_schedule:
            # Get the sections assigned to this professor
            last_sections = db.query(Section).filter(
                Section.schedule_id == last_schedule.id,
                Section.professor_id == prof.id
            ).all()

            if last_sections:
                schedule_table_text += f"Your {last_semester} {last_year} Schedule (for reference):\n"
                schedule_table_text += "-"*50 + "\n"

                for sec in last_sections:
                    course_code = sec.course.code if sec.course else "Unknown Course"
                    course_name = sec.course.name if sec.course else "Unknown Title"
                    timeslot_label = sec.timeslot.label if sec.timeslot else "TBD"
                    schedule_table_text += f"{course_code} - {course_name} | {timeslot_label}\n"

                schedule_table_text += "-"*50 + "\n\n"
        
        # 3. Construct a plain-text email
        message = MIMEText(
            f"Dear {prof.name},\n\n"
            f"Please reply to this email with your teaching preferences for {semester.capitalize()} {year}.\n"
            f"Answer each of the following questions:\n\n"
            f"{schedule_table_text}"
            f"Courses you'd like to teach (IMPORTANT: provide both code and name, e.g. ECON 40970 Growth): \n"
            f"Courses you'd prefer not to teach (code and name): \n"
            f"How many sections you'd like: \n"
            f"Maximum sections you can take on: \n"
            f"Preferred days/times (e.g. MWF mornings, TR afternoons): \n"
            f"Days or times to avoid: \n"
            f"Back-to-back sections (prefer / avoid / no preference): \n"
            f"On leave or sabbatical this semester? (yes / no): \n"
            f"Anything else we should know: \n\n"
            f"Thanks,\n"
            f"TCU Econ Scheduling",
            "plain"
        )
        message['To'] = str(prof.email)
        message['Subject'] = f"Action Required: {semester} {year} Teaching Preferences"

        # 4. Add the custom header to track the reply
        token = f"PROF-{prof.id}-{semester}-{year}"
        message['X-Scheduler-Token'] = token

        # 5. Encode the message in base64 as Gmail API requires
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {
            'raw': encoded_message
        }
        
        # 6. Send the email
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        
        # 7. Log it in our database
        email_log = EmailLog(
            professor_id=prof.id,
            direction='sent',
            gmail_thread_id=sent_message.get('threadId'),
            subject=message['Subject'],
            status='sent'
        )
        db.add(email_log)
        db.commit()
        
        return {"status": "success", "message_id": sent_message.get('id'), "thread_id": sent_message.get('threadId')}
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

def _safe_decode(data: str) -> str:
    """Safely decode a base64url-encoded string to UTF-8 text.

    Normalizes missing '=' padding and replaces un-decodable bytes so that a
    single malformed part never aborts the entire email processing loop.
    """
    if not data:
        return ""
    try:
        padding = '=' * (-len(data) % 4)
        decoded_bytes = base64.urlsafe_b64decode(data + padding)
        return decoded_bytes.decode('utf-8', errors='replace')
    except Exception:
        return ""


def get_email_body(payload: dict) -> str:
    """Recursively extract the plain text body from a Gmail API payload."""
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                body += _safe_decode(part['body'].get('data', ''))
            elif 'parts' in part:
                body += get_email_body(part)
    elif payload.get('mimeType') == 'text/plain':
        body = _safe_decode(payload['body'].get('data', ''))
    return body

def poll_unread_replies(server_mode: bool = False) -> list:
    """
    Polls the Gmail inbox for unread replies, matches them to a professor,
    stores the raw email in the Preferences table, and marks the email as read.

    Args:
        server_mode: Passed to get_gmail_service(). When True, raises instead
                     of launching interactive OAuth (safe for background jobs).
    """
    db = SessionLocal()
    processed_replies = []

    try:
        service = get_gmail_service(server_mode=server_mode)

        # 1. Search for UNREAD preference-reply messages.
        # We only require UNREAD (not INBOX) so that threaded replies that Gmail
        # groups with the sent item aren't missed. The subject filter avoids
        # accidentally marking unrelated mail as read.
        messages: list = []
        list_kwargs: dict = {
            'userId': 'me',
            'labelIds': ['UNREAD'],
            'q': 'subject:"Action Required"',
        }
        results = service.users().messages().list(**list_kwargs).execute()
        while True:
            messages.extend(results.get('messages', []))
            page_token = results.get('nextPageToken')
            if not page_token:
                break
            results = service.users().messages().list(
                **list_kwargs, pageToken=page_token
            ).execute()

        print(f"[POLL] Found {len(messages)} unread message(s) matching query.")

        if not messages:
            return []

        for msg in messages:
            msg_id = msg['id']
            thread_id = msg['threadId']
            
            # Fetch the full message payload
            full_msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            payload = full_msg.get('payload', {})
            headers = payload.get('headers', [])

            # Extract Headers
            subject = ""
            sender_email = ""
            scheduler_token = None
            
            for header in headers:
                name = header['name'].lower()
                value = header['value']
                if name == 'subject':
                    subject = value
                elif name == 'from':
                    # Extract email from "Name <email@domain.com>" or "email@domain.com"
                    if '<' in value and '>' in value:
                        sender_email = value.split('<')[1].split('>')[0]
                    else:
                        sender_email = value
                elif name == 'x-scheduler-token':
                    scheduler_token = value

            # Extract the body
            body_text = get_email_body(payload)

            # 2. Identify the Professor and Semester/Year
            prof_id = None
            semester = None
            year = None

            # Strategy A: Use the custom X-Scheduler-Token if it survived the reply chain.
            # Validate against the sender's email to prevent anyone who knows the token
            # format from spoofing another professor's preferences.
            if scheduler_token and scheduler_token.startswith("PROF-"):
                try:
                    parts = scheduler_token.split('-')
                    token_prof_id = int(parts[1])
                    expected_prof = db.query(Professor).filter(Professor.id == token_prof_id).first()
                    if expected_prof and str(expected_prof.email).lower() == sender_email.lower():
                        prof_id = token_prof_id
                        semester = parts[2]
                        year = int(parts[3])
                except Exception:
                    pass
            
            # Strategy B: Fallback to matching the thread_id from our EmailLog
            if prof_id is None:
                sent_log = db.query(EmailLog).filter(
                    EmailLog.gmail_thread_id == thread_id, 
                    EmailLog.direction == 'sent'
                ).first()
                if sent_log:
                    prof_id = sent_log.professor_id
                    # We can parse semester/year from the subject: "Action Required: Fall 2025 Teaching Preferences"
                    try:
                        subj_parts = sent_log.subject.split("Action Required: ")[1].split(" Teaching")[0]
                        semester, year_str = subj_parts.split(" ")
                        year = int(year_str)
                    except Exception:
                        pass
            
            # If we couldn't definitively identify the professor/semester from the token or thread ID,
            # throw an error instead of guessing. The admin can manually assign it.
            if prof_id is None or semester is None or year is None:
                # Log the failed incoming email so the admin sees it in the dashboard.
                # Persist to DB BEFORE marking as read so that a commit failure doesn't
                # silently drop the message from the unread queue with no trace.
                failed_log = EmailLog(
                    professor_id=None,  # We don't know who it belongs to!
                    direction='received',
                    gmail_thread_id=thread_id,
                    subject=subject,
                    status='failed_match'
                )
                db.add(failed_log)
                db.commit()  # Commit DB changes before mutating Gmail so we don't lose the record on error

                # Mark as read so we don't infinitely process it
                service.users().messages().modify(
                    userId='me',
                    id=msg_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                
                processed_replies.append({
                    "error": "Failed to match email to a specific professor or semester.",
                    "subject": subject,
                    "sender": sender_email
                })
                continue

            # 3. Save the Preference and Log the Email
            if prof_id is not None and semester and year:
                # Check if a preference already exists (e.g. they replied twice).
                # If so, we can overwrite the raw email. The SYSTEM_PLAN says "Latest reply always wins".
                pref = db.query(Preference).filter(
                    Preference.professor_id == prof_id,
                    Preference.semester == semester,
                    Preference.year == year
                ).first()

                if not pref:
                    pref = Preference(
                        professor_id=prof_id,
                        semester=semester,
                        year=year,
                        raw_email=body_text
                    )
                    db.add(pref)
                else:
                    pref.raw_email = body_text
                    pref.admin_approved = False  # Reset approval since it's a new reply!

                # Log the incoming email
                in_log = EmailLog(
                    professor_id=prof_id,
                    direction='received',
                    gmail_thread_id=thread_id,
                    subject=subject,
                    status='processed'
                )
                db.add(in_log)
                db.commit()  # Persist preference + log before touching Gmail

                # 4. Remove the UNREAD label so we don't process it again
                service.users().messages().modify(
                    userId='me',
                    id=msg_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()

                processed_replies.append({
                    "professor_id": prof_id,
                    "subject": subject,
                    "semester": semester,
                    "year": year
                })
        
        return processed_replies

    except Exception as e:
        db.rollback()
        print(f"Error polling emails: {str(e)}")
        return []
    finally:
        db.close()

if __name__ == '__main__':
    # Test the service by fetching the user's email address
    service = get_gmail_service()
    profile = service.users().getProfile(userId='me').execute()
    print(f"Successfully authenticated as: {profile['emailAddress']}")