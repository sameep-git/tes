import os.path
import base64
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .database import SessionLocal
from .models import Professor, EmailLog, Schedule, Section, Preference

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    """Authenticates and returns the Gmail API service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def send_preference_email(prof_id: int, semester: str, year: int) -> dict:
    """
    Drafts and sends a preference collection email to a specific professor.
    Embeds a custom header (X-Scheduler-Token) to track their reply.
    Logs the sent email to the database.
    """
    db = SessionLocal()
    service = get_gmail_service()
    
    try:
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

        schedule_table_html = ""
        schedule_table_text = ""

        if last_schedule:
            # Get the sections assigned to this professor
            last_sections = db.query(Section).filter(
                Section.schedule_id == last_schedule.id,
                Section.professor_id == prof.id
            ).all()

            if last_sections:
                schedule_table_html += f"<h3>Your {last_semester} {last_year} Schedule:</h3>"
                schedule_table_html += "<table border='1' cellpadding='5' style='border-collapse: collapse;'>"
                schedule_table_html += "<tr><th>Course</th><th>Title</th><th>Days & Times</th></tr>"
                
                schedule_table_text += f"Your {last_semester} {last_year} Schedule:\n"
                schedule_table_text += "-"*50 + "\n"
                
                for sec in last_sections:
                    course_code = sec.course.code if sec.course else "Unknown Course"
                    course_name = sec.course.name if sec.course else "Unknown Title"
                    timeslot_label = sec.timeslot.label if sec.timeslot else "TBD"
                    
                    schedule_table_html += f"<tr><td>{course_code}</td><td>{course_name}</td><td>{timeslot_label}</td></tr>"
                    schedule_table_text += f"{course_code} - {course_name} | {timeslot_label}\n"
                
                schedule_table_html += "</table><br>"
                schedule_table_text += "-"*50 + "\n\n"
        
        # 3. Construct the multipart email message
        message = MIMEMultipart("alternative")
        message['To'] = str(prof.email)
        message['Subject'] = f"Action Required: {semester} {year} Teaching Preferences"
        
        # Text version
        text_content = (
            f"Dear {prof.name},\n\n"
            f"It's time to collect teaching preferences for the {semester} {year} semester.\n\n"
            f"{schedule_table_text}"
            f"Please reply directly to this email with the courses and timeslots you would "
            f"prefer to teach.\n\n"
            f"Thank you,\n"
            f"TES System"
        )
        
        # HTML version
        html_content = f"""
        <html>
          <body>
            <p>Dear {prof.name},</p>
            <p>It's time to collect teaching preferences for the <b>{semester} {year}</b> semester.</p>
            {schedule_table_html}
            <p>Please reply directly to this email with the courses and timeslots you would prefer to teach.</p>
            <br>
            <p>Thank you,<br>TES System</p>
          </body>
        </html>
        """
        
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        message.attach(part1)
        message.attach(part2)

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

def get_email_body(payload: dict) -> str:
    """Recursively extract the plain text body from a Gmail API payload."""
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data', '')
                if data:
                    body += base64.urlsafe_b64decode(data).decode('utf-8')
            elif 'parts' in part:
                body += get_email_body(part)
    elif payload.get('mimeType') == 'text/plain':
        data = payload['body'].get('data', '')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8')
    return body

def poll_unread_replies() -> list:
    """
    Polls the Gmail inbox for unread replies, matches them to a professor,
    stores the raw email in the Preferences table, and marks the email as read.
    """
    db = SessionLocal()
    service = get_gmail_service()
    processed_replies = []

    try:
        # 1. Search for UNREAD messages in the INBOX
        results = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD']).execute()
        messages = results.get('messages', [])

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

            # Strategy A: Use the custom X-Scheduler-Token if it survived the reply chain
            if scheduler_token and scheduler_token.startswith("PROF-"):
                try:
                    parts = scheduler_token.split('-')
                    prof_id = int(parts[1])
                    semester = parts[2]
                    year = int(parts[3])
                except Exception:
                    pass
            
            # Strategy B: Fallback to matching the thread_id from our EmailLog
            if not prof_id:
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
            
            # Strategy C: Desperate fallback to matching the sender's email address
            if not prof_id:
                prof = db.query(Professor).filter(Professor.email == sender_email).first()
                if prof:
                    prof_id = prof.id
                    # If we got here, we don't know the exact semester, default to the upcoming Fall for testing
                    # (In a real app, we'd maybe flag this for admin review or infer from the current date)
                    semester = "Fall"
                    year = 2025

            # 3. Save the Preference and Log the Email
            if prof_id and semester and year:
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
                    pref.admin_approved = False # Reset approval since it's a new reply!

                # Log the incoming email
                in_log = EmailLog(
                    professor_id=prof_id,
                    direction='received',
                    gmail_thread_id=thread_id,
                    subject=subject,
                    status='processed'
                )
                db.add(in_log)

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
        
        db.commit()
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