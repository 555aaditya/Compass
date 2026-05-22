import os
import resend
from config_loader import CONFIG
import datetime

def send_digest(jobs):
    if not jobs:
        print("No jobs to send.")
        return
        
    api_key = os.getenv('RESEND_API_KEY')
    if not api_key:
        print("RESEND_API_KEY not found. Skipping email.")
        return
        
    resend.api_key = api_key
    
    strong_matches = [j for j in jobs if j.get('score', 0) >= 9]
    good_matches = [j for j in jobs if 6 <= j.get('score', 0) < 9]
    
    date_str = datetime.datetime.now().strftime("%b %d")
    subject = f"🚀 [{len(jobs)}] New Roles — {jobs[0]['company']} | {date_str}"
    
    html_content = f"<h2>🚀 {len(jobs)} New Roles</h2>"
    
    if strong_matches:
        html_content += "<h3>🔥 STRONG MATCHES</h3><ul>"
        for job in strong_matches:
            html_content += f"""
            <li>
                <strong>{job['company']}</strong> - {job['title']} <br>
                <em>{job['location']}</em> · Score: {job.get('score')}/10 <br>
                <a href="{job['url']}">View Role ↗</a>
                <p style="color: gray; font-size: 0.9em;">Reason: {job.get('reason')}</p>
            </li><br>
            """
        html_content += "</ul>"
        
    if good_matches:
        html_content += "<h3>✅ GOOD MATCHES</h3><ul>"
        for job in good_matches:
            html_content += f"""
            <li>
                <strong>{job['company']}</strong> - {job['title']} <br>
                <em>{job['location']}</em> · Score: {job.get('score')}/10 <br>
                <a href="{job['url']}">View Role ↗</a>
            </li><br>
            """
        html_content += "</ul>"
        
    html_content += f"<hr><p>Total sent: {len(jobs)} roles. Update preferences in config.yaml.</p>"
    
    recipient = CONFIG.get('email')
    
    try:
        r = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": recipient,
            "subject": subject,
            "html": html_content
        })
        print(f"Email sent successfully to {recipient}: {r}")
    except Exception as e:
        print(f"Error sending email: {e}")
