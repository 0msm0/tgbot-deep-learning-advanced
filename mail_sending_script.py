import os
import smtplib
import logging
EMAIL = os.environ.get('CTOSCHOOL_DL_EMAIL_ADDRESS')
PWD = os.environ.get('CTOSCHOOL_DL_EMAIL_PASSWORD')

log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
file_handler = logging.FileHandler("logs/app.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def lets_send_that_mail(msg):
    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        try:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(user=EMAIL, password=PWD)
            # smtp.sendmail(from_addr=EMAIL, to_addrs=EMAIL, msg=msg)
            smtp.send_message(msg=msg)
            logger.info(f"Mail sent to {EMAIL}\ncontent = {msg}")
        except:
            logger.exception(f"Exception in sending mail to {EMAIL}\ncontent = {msg}")
