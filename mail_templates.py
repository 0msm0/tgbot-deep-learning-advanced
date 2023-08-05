from mail_sending_script import lets_send_that_mail
from email.message import EmailMessage
import os
from content.course_specific_variables import REGISTRATION_EMAIL_SUBJECT_TEXT, REGISTRATION_EMAIL_BODY_TEXT
# import smtplib

EMAIL = os.environ.get('CTOSCHOOL_DL_EMAIL_ADDRESS')
PWD = os.environ.get('CTOSCHOOL_DL_EMAIL_PASSWORD')


def mail_body_for_question(body):
    msg = EmailMessage()
    msg['From'] = EMAIL
    msg['To'] = EMAIL
    msg['Subject'] = 'Got Question'
    msg.set_content(body)
    return msg


def mail_body_for_payment_proof(body):
    msg = EmailMessage()
    msg['From'] = EMAIL
    msg['To'] = EMAIL
    msg['Subject'] = 'Got Payment Proof'
    msg.set_content(body)
    return msg


def mail_body_for_registration(body, to_email):
    msg = EmailMessage()
    msg['From'] = EMAIL
    msg['To'] = to_email
    msg['Subject'] = REGISTRATION_EMAIL_SUBJECT_TEXT
    welcome_message = f"{REGISTRATION_EMAIL_BODY_TEXT}" \
                      f'Your registration details as follows - \n' \
                      f'{body}\n\n' \
                      f'-\n' \
                      f'Regards,\n' \
                      f'Team CTOschool'
    print(f'Sending registration mail to - {to_email}')
    msg.set_content(welcome_message)
    return msg


def mail_body_for_certificate(body):
    msg = EmailMessage()
    msg['From'] = EMAIL
    msg['To'] = EMAIL
    msg['Subject'] = 'Got Certificate Request'
    msg.set_content(body)
    return msg


# def testmail(msg):
#     with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
#         smtp.ehlo()
#         smtp.starttls()
#         smtp.ehlo()
#         smtp.login(user=EMAIL, password=PWD)
#         smtp.send_message(msg)
#         # smtp.sendmail(msg=msg)