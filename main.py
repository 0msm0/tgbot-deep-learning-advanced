import json
import os
import time
import pytz
import requests
import telegram.constants
from sqlalchemy import func
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.bot import BotCommand
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler
from dotenv import load_dotenv
import logging
from datetime import datetime, date
from models import User, Learning, Generaltalk, Question, Interaction, Certificate, UserCourse, Course
from dbhelper import engine, Session
from mail_templates import mail_body_for_question, mail_body_for_payment_proof, mail_body_for_certificate, mail_body_for_registration
from mail_sending_script import lets_send_that_mail
from content.course_content import course_content
from content.bot_commands import suggested_commands
from content.changelog import changelog_text
from content.outline import outline_text
from content.course_specific_variables import *
# from sqlalchemy import inspect
from requests.auth import HTTPBasicAuth


log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
file_handler = logging.FileHandler("logs/app.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
load_dotenv()

NAME, EMAILID, PHONENO, COLLEGE_NAME, REFERRAL_CODE = range(5)
ASK = range(1)
GET_PAYMENT_PROOF = range(1)
ASK_FOR_HW = range(1)
END = ConversationHandler.END
SELECTING_ACTION, SELECTED_NAME, SELECTED_EMAIL, SELECTED_PHONE, SELECTED_COLLEGE, WRONG_SELECTION = range(6)

# All timeouts
reg_timeout_time = 60
que_timeout_time = 60
payment_timeout_time = 300
homework_timeout_time = 60

# All text matters
# course_names = COURSE_NAMES
start_text = START_TEXT
payment_info = PAYMENT_INFO
ctoschool_courses_text = CTOSCHOOL_COURSES_TEXT
payment_proof_text = PAYMENT_PROOF_TEXT
send_question_text = SEND_QUESTION_TEXT
homework_instructions = HOMEWORK_INSTRUCTIONS
colablinkaccess_text = COLABLINKACCESS_TEXT
methodology_text = METHODOLOGY_TEXT
donation_text = DONATION_TEXT
discord_text = DISCORD_TEXT
telegramgroup_text = TELEGRAMGROUP_TEXT
community_text = COMMUNITY_TEXT
certificate_text_after_completion = CERTIFICATE_TEXT_AFTER_COMPLETION
jobroles_text = JOBROLES_TEXT
allcourse_text = ALLCOURSE_TEXT

# Imp values
token_name = TOKEN_NAME
TOKEN = os.environ.get(token_name)
SSL_CERT = SSL_PATH
THIS_COURSE_ID = THIS_COURSE_ID
THIS_COURSE_NAME = THIS_COURSE_NAME
LAST_LEVEL_OF_COURSE = LAST_LEVEL_OF_COURSE
PAID_LEVEL = PAID_LEVEL
certi_base_url = CERTI_BASE_URL
BOTOWNER_CHAT_ID = BOTOWNER_CHAT_ID
JOB_NAME = JOB_NAME
REPORT_TO_CHANNEL = REPORT_TO_CHANNEL


def logcommand(usercourse_obj, command, session):
    """ Command to log each command being used """
    uc = usercourse_obj
    if uc:
        interaction = Interaction(command=command, usercourse_id=uc.id, created_at=datetime.now())
        try:
            session.add(interaction)
        except:
            session.rollback()
            logger.exception(f"Exception saving Interaction - {interaction}")
        else:
            Session.commit()
            logger.info(f"----'{command}'----- - uid {uc.id}")


def logconversation(command_name, context, session):
    try:
        # user = context.user_data['user']
        uc = context.user_data['uc']
        if uc:
            logcommand(usercourse_obj=uc, command=command_name, session=session)
    except:
        logger.error(f"Some exception in LOGCOMMAND of {command_name}")


def start(update, context: CallbackContext):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        update.message.reply_text(start_text, disable_web_page_preview=True)
        user, uc = get_current_user_and_usercourse(chat_id, update, context, session)
        if uc:
            update.message.reply_text(f'Welcome back, {user.name.title()}')
            logcommand(usercourse_obj=user, command='/start', session=session)


def level_related_code(update, context, this_level):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id, update, context, session)
        THIS_LEVEL = this_level
        if not uc:
            return
        logcommand(usercourse_obj=uc, command=f"/part{this_level}", session=session)

        if THIS_LEVEL < PAID_LEVEL:
            subscription_status = True
        else:
            subscription_status = has_user_subscribed(uc)
            logger.info(f"Sub status for User {user.id}, {user.name}, {user.email_id} and UserCourse id {uc.id} is ---> {subscription_status}")
        if not subscription_status:
            update.message.reply_text(f"To access level {THIS_LEVEL}, you need to /unlock first.", parse_mode='HTML')
            return

        last_level_finished = get_last_finished_level_of_user(chat_id=chat_id, session=session)

        if THIS_LEVEL > last_level_finished + 1:
            # text for old command /partx_hw
            # update.message.reply_text(f'Finish level {last_level_finished + 1} first.\nSubmit homework with /part{last_level_finished + 1}_hw <i>your_colab_sheet_link</i> command!', parse_mode='HTML')
            update.message.reply_text(f'Finish level {last_level_finished + 1} by submitting homework with /part{last_level_finished + 1}hw command!', parse_mode='HTML')
            return

        # level_access = False
        if THIS_LEVEL == last_level_finished + 1:
            # level_access = True
            status = check_if_user_has_already_started_level(chat_id=chat_id, level_no=THIS_LEVEL, session=session)
            if status is False:
                update.message.reply_text(f"-----------LEVEL {THIS_LEVEL} BEGIN---------------", parse_mode='HTML')
                try:
                    save_learning(session=session, usercourse_id=uc.id, current_level=THIS_LEVEL, started_at=datetime.now())
                except:
                    logger.exception(f"Exception with save_learning. user_id {user.id}, current_level - {THIS_LEVEL}")
        # else:
        #     level_2_access = True

        # if level_2_access:
        lect_title = course_content[f'lecture{THIS_LEVEL}']['title']
        lect_description = course_content[f'lecture{THIS_LEVEL}']['description']
        lect_video_url = course_content[f'lecture{THIS_LEVEL}']['video_link']
        update.message.reply_text(f"<b>Title: </b>{lect_title}\n\n"
                                  f"<b>Brief: </b>{lect_description}\n\n"
                                  f"<b>Link: </b>{lect_video_url}", parse_mode='HTML')

        if THIS_LEVEL == LAST_LEVEL_OF_COURSE:
            update.message.reply_text('This is the last level of this course!')


def start_homework_conv(update, context, this_level):
    THIS_LEVEL = this_level
    curr_command = f"/part{THIS_LEVEL}hw"
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if not uc:
            return ConversationHandler.END
        logcommand(usercourse_obj=uc, command=f'{curr_command}', session=session)
        last_level_finished = get_last_finished_level_of_user(chat_id=chat_id, session=session)
        if THIS_LEVEL > last_level_finished + 1:
            update.message.reply_text(f"Finish part {last_level_finished + 1} first by submitting homework with /part{last_level_finished + 1}hw", parse_mode='HTML')
            return ConversationHandler.END
        new_level_status = check_if_user_has_already_started_level(chat_id=chat_id, level_no=THIS_LEVEL, session=session)
        if not new_level_status:
            update.message.reply_text(f"You need to <i>start</i> /part{THIS_LEVEL}, before submitting its homework!", parse_mode='HTML')
            return ConversationHandler.END

        update.message.reply_text(f'Share link of your colab notebook for part {THIS_LEVEL}\n'
                                  f'(The link needs to be publicly accessible, see /colablinkaccess for details)\n'
                                  f'(<i>/cancelsub to cancel</i>)\n\n'
                                  f'Submit link below...', parse_mode='HTML')
        chat_data = context.chat_data
        chat_data['level_for_hw'] = THIS_LEVEL
        logger.info(f"chat_data.get('level_for_hw') set to ---> {THIS_LEVEL}")
        return ASK_FOR_HW


def send_hw_link(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id, update, context, session)
        if not uc:
            return ConversationHandler.END
        chat_data = context.chat_data
        if not chat_data.get('level_for_hw'):
            logger.error(f"ERROR. Didn't receive level no for homework! This should not have happened")
            update.message.reply_text(f"Looks like there is a bug. Contact admin or try again!")
            return ConversationHandler.END
        THIS_LEVEL = chat_data['level_for_hw']
        curr_command = f"/part{THIS_LEVEL}hw"
        link = update.message.text.strip()
        logconversation(command_name=f'{curr_command} ---> link --> {link}', session=session, context=context)
        logger.info(f"{curr_command} ---> link --> {link}")
        if link.find('colab.research.google.com') == -1:
            update.message.reply_text(f"Homework needs to be submitted in a <b>colab notebook</b> only!\n"
                                      f"Share your colab link below.\n"
                                      f"(/cancelsub to cancel, /howtohomework for instructions)", parse_mode='HTML')
            return ASK_FOR_HW
        # IMP that this is called before actually updating the homework
        last_level_finished = get_last_finished_level_of_user(chat_id=chat_id, session=session)
        try:
            Learning.update_learning_homework(session=session, usercourse_id=uc.id, level_no=THIS_LEVEL, homework_link=link, finished_at=datetime.now())
            logger.info(f"{curr_command} ---> saved to db!")
        except:
            logger.exception(f"Error while update_learning_framework")
        if THIS_LEVEL == last_level_finished + 1:
            if THIS_LEVEL < LAST_LEVEL_OF_COURSE:
                update.message.reply_text(f'Awesome. You have finished part {THIS_LEVEL}.\n'
                                          f'You can start with /part{THIS_LEVEL + 1}', parse_mode='HTML')
                update.message.reply_text(f"-----------LEVEL {THIS_LEVEL} END---------------")
            elif THIS_LEVEL == LAST_LEVEL_OF_COURSE:
                update.message.reply_text(f'Awesome. You have finished part {THIS_LEVEL}.\n'
                                          f'-----------LEVEL {THIS_LEVEL} END---------------')

                update.message.reply_text('And with that, you have successfully completed the course. Congratulations!\n'
                                          'You can request for a /certificate now.')
        if THIS_LEVEL < last_level_finished + 1:
            update.message.reply_text(f'Your homework file is successfully updated. Use /myhomework to track your links.', parse_mode='HTML')
        logger.info(f'chat_data before deleting ---> {chat_data}')
        chat_data.clear()
        logger.info(f'chat_data after deleting ---> {chat_data}')
        return ConversationHandler.END


def cancelsub(update, context):
    with Session() as session:
        update.message.reply_text('Homework submission cancelled.')
        chat_data = context.chat_data
        THIS_LEVEL = 'NA'
        if chat_data.get('level_for_hw'):
            THIS_LEVEL = chat_data['level_for_hw']
        curr_command = f"/part{THIS_LEVEL}hw"
        logger.info(f"{curr_command} - cancelsub --> Homework link submission cancelled")
        logconversation(command_name=f'{curr_command}-> cancelsub', context=context, session=session)
        chat_data.clear()
        return ConversationHandler.END


def timeout_homework(update, context):
    with Session() as session:
        chat_data = context.chat_data
        THIS_LEVEL = 'NA'
        if chat_data.get('level_for_hw'):
            THIS_LEVEL = chat_data['level_for_hw']
        curr_command = f"/part{THIS_LEVEL}hw"
        update.message.reply_text(f'Timeout. Kindly {curr_command} again!.\n'
                                  f'(Timeout limit - {homework_timeout_time} sec)\n'
                                  f'i.e. paste the homework link within 30 sec after writing the command {curr_command}')
        logger.info(f"Timeout for {curr_command}")
        logconversation(command_name=f'{curr_command} -> timeout_homework', context=context, session=session)
        chat_data.clear()
        return ConversationHandler.END


def part1(update, context):
    level_related_code(update=update, context=context, this_level=1)


def part2(update, context):
    level_related_code(update=update, context=context, this_level=2)


def part3(update, context):
    level_related_code(update=update, context=context, this_level=3)


def part4(update, context):
    level_related_code(update=update, context=context, this_level=4)


def part5(update, context):
    level_related_code(update=update, context=context, this_level=5)


def part6(update, context):
    level_related_code(update=update, context=context, this_level=6)


def part7(update, context):
    level_related_code(update=update, context=context, this_level=7)


def part8(update, context):
    level_related_code(update=update, context=context, this_level=8)


def part9(update, context):
    level_related_code(update=update, context=context, this_level=9)


def part10(update, context):
    level_related_code(update=update, context=context, this_level=10)


def part11(update, context):
    level_related_code(update=update, context=context, this_level=11)


def part12(update, context):
    level_related_code(update=update, context=context, this_level=12)


def part13(update, context):
    level_related_code(update=update, context=context, this_level=13)


def part14(update, context):
    level_related_code(update=update, context=context, this_level=14)


def part15(update, context):
    level_related_code(update=update, context=context, this_level=15)


def part16(update, context):
    level_related_code(update=update, context=context, this_level=16)


def part17(update, context):
    level_related_code(update=update, context=context, this_level=17)


def part18(update, context):
    level_related_code(update=update, context=context, this_level=18)


def part19(update, context):
    level_related_code(update=update, context=context, this_level=19)


def part1hw(update, context):
    this_level = 1
    return start_homework_conv(update, context, this_level)


def part2hw(update, context):
    this_level = 2
    return start_homework_conv(update, context, this_level)


def part3hw(update, context):
    this_level = 3
    return start_homework_conv(update, context, this_level)


def part4hw(update, context):
    this_level = 4
    return start_homework_conv(update, context, this_level)


def part5hw(update, context):
    this_level = 5
    return start_homework_conv(update, context, this_level)


def part6hw(update, context):
    this_level = 6
    return start_homework_conv(update, context, this_level)


def part7hw(update, context):
    this_level = 7
    return start_homework_conv(update, context, this_level)


def part8hw(update, context):
    this_level = 8
    return start_homework_conv(update, context, this_level)


def part9hw(update, context):
    this_level = 9
    return start_homework_conv(update, context, this_level)


def part10hw(update, context):
    this_level = 10
    return start_homework_conv(update, context, this_level)


def part11hw(update, context):
    this_level = 11
    return start_homework_conv(update, context, this_level)


def part12hw(update, context):
    this_level = 12
    return start_homework_conv(update, context, this_level)


def part13hw(update, context):
    this_level = 13
    return start_homework_conv(update, context, this_level)


def part14hw(update, context):
    this_level = 14
    return start_homework_conv(update, context, this_level)


def part15hw(update, context):
    this_level = 15
    return start_homework_conv(update, context, this_level)


def part16hw(update, context):
    this_level = 16
    return start_homework_conv(update, context, this_level)


def part17hw(update, context):
    this_level = 17
    return start_homework_conv(update, context, this_level)


def part18hw(update, context):
    this_level = 18
    return start_homework_conv(update, context, this_level)


def part19hw(update, context):
    this_level = 19
    return start_homework_conv(update, context, this_level)


def methodology(update, context):
    update.message.reply_text(f"{methodology_text}", parse_mode='HTML')
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            logcommand(usercourse_obj=uc, command='/methodology', session=session)


def howtohomework(update, context):
    update.message.reply_text(homework_instructions, parse_mode='HTML', disable_web_page_preview=True)
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            logcommand(usercourse_obj=uc, command='/howtohomework', session=session)


def colablinkaccess(update, context):
    update.message.reply_text(colablinkaccess_text, parse_mode='HTML', disable_web_page_preview=True)
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            logcommand(usercourse_obj=uc, command='/colablinkaccess', session=session)


def donate(update, context):
    update.message.reply_text(donation_text, parse_mode='HTML', disable_web_page_preview=True)
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            logcommand(usercourse_obj=uc, command='/donate', session=session)


def discord(update, context):
    update.message.reply_text(discord_text, parse_mode='HTML', disable_web_page_preview=True)
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            logcommand(usercourse_obj=uc, command='/discord', session=session)


def telegramgroup(update, context):
    update.message.reply_text(telegramgroup_text, parse_mode='HTML', disable_web_page_preview=True)
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            logcommand(usercourse_obj=uc, command='/telegramgroup', session=session)


def community(update, context):
    update.message.reply_text(community_text, parse_mode='HTML', disable_web_page_preview=True)
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            logcommand(usercourse_obj=uc, command='/community', session=session)


def jobroles(update, context):
    update.message.reply_text(jobroles_text, parse_mode='HTML', disable_web_page_preview=True)
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            logcommand(usercourse_obj=uc, command='/jobroles', session=session)


def allcourses(update, context):
    update.message.reply_text(allcourse_text, parse_mode='HTML', disable_web_page_preview=True)
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            logcommand(usercourse_obj=uc, command='/jobroles', session=session)


def mycourses(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        nl = '\n'
        mycourses_text = [(c[0].coursename, dt_to_string(c[1].created_at)) for c in zip(user.courses, user.usercourses)]
        res = list(map(lambda x: ' - '.join(x), mycourses_text))
        if uc:
            update.message.reply_text(f"You have signed up for the following courses - \n\n"
                                      f"{nl.join(res)}", parse_mode='HTML', disable_web_page_preview=True)
            logcommand(usercourse_obj=uc, command='/jobroles', session=session)


def outline(update, context):
    text = ''
    # for key, val in outline_text.items():
    #     text += f"{key}. {val}\n"
    for key, val in course_content.items():
        text += f"{val['title']}\n"
    update.message.reply_text(text, parse_mode='HTML', disable_web_page_preview=True)
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            logcommand(usercourse_obj=uc, command='/jobroles', session=session)


def changelog(update, context):
    final_text = 'Changelog --->\n\n'
    nl = '\n\n'
    limit = 2
    if context.args:
        try:
            limit = int(context.args[0])
            logger.info(f'/changelog {limit}')
            if limit > 5:
                limit = 5
        except:
            limit = 2
    for log in changelog_text[:-limit-1:-1]:     # reverse the list, and get items as specified with limit value. Have to use -limit-1 to get values as mentioned in limit.
        final_text += f"Version - {log['version']}\n" \
                      f"Date - {log['date']}\n\n" \
                      f"{nl.join(log['changes'])}\n" \
                      f"--------------\n\n"
    update.message.reply_text(final_text, parse_mode='HTML', disable_web_page_preview=True)
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            logcommand(usercourse_obj=uc, command=f'/changelog {limit}', session=session)


def myhomework(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            logcommand(usercourse_obj=uc, command='/myhomework', session=session)
            for learning in uc.learnings:
                update.message.reply_text(f"Level - {learning.level_number}\n"
                                          f"Started on - {learning.started_at}\n"
                                          f"Submitted on - {learning.finished_at}\n"
                                          f"Homework Link - {learning.homework_link}\n", disable_web_page_preview=True)


def certificate(update, context: CallbackContext):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            logcommand(usercourse_obj=uc, command='/certificate', session=session)
            if uc.certificate.first():
                if uc.certificate.first().filename:
                    certi_link = f"{certi_base_url}{uc.certificate.first().filename}"
                    update.message.reply_text(f"Here is your certificate - {certi_link}\n"
                                              f"Download by right clicking on the image (long click if you are on phone) and click 'save image as' option.", disable_web_page_preview=True)
                    update.message.reply_text("For any questions, ask us on our /community. \n"
                                              "Check /courses to know about the next course you can take. You are one step closer to be a CTO. Keep it up!")
                    return
                else:
                    update.message.reply_text(f"Your certificate has been logged.\n\n"
                                              f"If you have paid the certificate fee already, you'll receive it within 24hrs. Try /certificate again after 24hrs.\n\n"
                                              f"If you haven't paid, use this link to request for certificate- {CERTIFICATE_PAYMENT_LINK}")
            else:
                last_level_completed = get_last_finished_level_of_user(chat_id=chat_id, session=session)
                if last_level_completed == LAST_LEVEL_OF_COURSE:
                    raise_certificate_request(uc=uc, session=session)
                    update.message.reply_text(certificate_text_after_completion)
                else:
                    update.message.reply_text(f'You need to complete till /part{LAST_LEVEL_OF_COURSE} to request the certificate.')
                if not uc.certificate.first():
                    return


def raise_certificate_request(uc, session):
    if not isinstance(uc, UserCourse):
        return
    if uc.certificate.count() < 1:
        certificate = Certificate(usercourse_id=uc.id, course_id=THIS_COURSE_ID, requested_at=datetime.now(), dump_requested_at=datetime.now())
        session.add(certificate)
        try:
            Session.commit()
            logger.info(f"Certificate Request Raised ---- {certificate}")
        except:
            session.rollback()
            logger.exception(f"Exception Raising Certificate Request - {certificate}")
    else:
        certificate = uc.certificate.first()
        certificate.update_certificate_request(session=session, requested_at=datetime.now())
        logger.info(f"Certificate Updated ---- {certificate}")
    send_certificate_mail_to_mentor(uc=uc)


def error(update, context: CallbackContext):
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    logger.error('Some error as mentioned above..', exc_info=True)


def register(update, context: CallbackContext):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = check_if_user_and_usercourse_exists(chat_id=chat_id, session=session)
        if not user:
            update.message.reply_text("Let's get you registerd. Please answer these 5 questions.\nYour name?")
            logger.info(f"/register ---> started")
            return NAME
        else:
            if not uc:
                update.message.reply_text(f"Looks like you are new to this course, but you have signed up for other courses by CTOschool - "
                                          f"{', '.join([c.coursename for c in user.courses])}.\n"
                                          f"Signing you up for the current course - {THIS_COURSE_NAME}")
                uc_new = bind_user_with_current_course(update=update, context=context, user=user)
                # send_email_to_old_user_for_enrolling_new_course
                if not uc_new:
                    update.message.reply_text('Something went wrong. Try /register again.')
                    logger.info(f"Couldn't bind user {user} for the course - {THIS_COURSE_ID}")
                    return ConversationHandler.END
                update.message.reply_text(f"Congrats! You are now enrolled to the new course - {THIS_COURSE_NAME}\m"
                                          f"You can start with /part1. Do join our /discord for any questions.")
                logcommand(usercourse_obj=uc_new, command='/register -> new in usercourse', session=session)
            else:
                update.message.reply_text(f"You are already registered and enrolled to this course.")
                logcommand(usercourse_obj=uc, command='/register -> old in usercourse', session=session)
            update.message.reply_text(f"Your registration details - "
                                      f"Name - {user.name}\n"
                                      f"Phone # - {user.phone_no}\n"
                                      f"Email Id - {user.email_id}\n"
                                      f"College/Company - {user.college_name}\n"
                                      f"Referral Code - {user.referral_code}\n"
                                      f"Courses Joined - {', '.join([c.coursename for c in user.courses])}")
            return ConversationHandler.END


def name(update: Update, context: CallbackContext):
    msg = update.message.text
    if len(msg) > 30:
        update.message.reply_text(f"Too long a name. It gotta be shorter!")
        logger.info(f"/register - name --> Long name : {msg}")
    update.message.reply_text(f"Glad to know you, {msg}")
    update.message.reply_text(f"Your email id?")
    user_data = context.user_data
    user_data['name'] = msg
    user_data['chat_id'] = update.effective_message.chat_id
    # print(user_data['name'], user_data['chat_id'])
    logger.info(f"/register - name --> {user_data['name']}")
    return EMAILID


def check_if_email_already_exists(email_id):
    with Session() as sess:
        res = sess.query(User).filter(User.email_id == email_id).first()
        return res


def email_id(update: Update, context: CallbackContext):
    email_id = update.message.text
    email_id = email_id.strip()

    old_email_flag = check_if_email_already_exists(email_id)
    if old_email_flag:
        update.message.reply_text(f"Email already in use.\nUse another one.")
        logger.info(f"/register - email --> ALREADY EXIST: {email_id}")
        return EMAILID
    user_data = context.user_data
    user_data['email_id'] = email_id
    # update.message.reply_text(f"Got your email id!")
    update.message.reply_text(f"Phone number? (with country code)")
    logger.info(f"/register - email --> {email_id}")
    return PHONENO


def wrong_email_id(update, context):
    logger.info(f"/register - email --> Rcvd wrong email  {update.message.text}")
    update.message.reply_text(f"Please enter correct emaild id.")
    return EMAILID


def check_if_phone_already_exists(phone_no):
    with Session() as sess:
        res = sess.query(User).filter(User.phone_no == phone_no).first()
        return res


def phone_no(update: Update, context: CallbackContext):
    phoneno = update.message.text
    phoneno = phoneno.strip()

    old_phone_flag = check_if_phone_already_exists(phoneno)
    if old_phone_flag:
        update.message.reply_text(f"Phone already in use.\nUse another one.")
        logger.info(f"/register - phone --> ALREADY EXIST: {phoneno}")
        return PHONENO

    user_data = context.user_data
    user_data['phoneno'] = phoneno
    # update.message.reply_text(f"Got your email id!")
    update.message.reply_text(f"Your college (or company)?")
    logger.info(f"/register - phoneno --> {phoneno}")
    return COLLEGE_NAME


def college_name(update: Update, context: CallbackContext):
    msg = update.message.text
    user_data = context.user_data
    user_data['college_name'] = msg
    update.message.reply_text(f"Lastly, do you have any referral code? Say /skipcode if not.")
    logger.info(f"/register - college name --> {user_data['college_name']}")
    return REFERRAL_CODE


def referral_code(update: Update, context: CallbackContext):
    referralcode = update.message.text
    referralcode = referralcode.strip()
    user_data = context.user_data
    user_data['referralcode'] = referralcode
    logger.info(f"/register - referralcode --> {user_data['referralcode']}")
    save_user(update, context)

    return ConversationHandler.END


def skipcode(update, context):
    update.message.reply_text('No worries.')
    user_data = context.user_data
    user_data['referralcode'] = 'NONE'
    logger.info(f"/register - referralcode --> (skipped) set to {user_data['referralcode']}")
    save_user(update, context)
    return ConversationHandler.END


def reg_cancel(update, context):
    update.message.reply_text('Byebye!')
    logger.info(f"/register - reg_cancel --> Reg cancelled some error.")
    return ConversationHandler.END


def timeout_reg(update, context):
    update.message.reply_text(f'Timeout. /register again.\n(Timeout limit - {reg_timeout_time} sec)')
    logger.info(f"Timeout for /register")


def myquestions(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if not uc:
            return
        all_questions = uc.questions.order_by(Question.created_at.desc()).all()
        if all_questions:
            update.message.reply_text(f"Questions you've asked")
            final_string = ''
            for question in all_questions:
                # final_string += f"{question.question_text}\n{question.created_at}"
                if not question.answer:
                    update.message.reply_text(f"{question.question_text} <i>({question.created_at})</i> \n", parse_mode='HTML')
                else:
                    update.message.reply_text(f"<b>Que: </b>{question.question_text} \n"
                                              f"<b>Ans: </b>{question.answer} \n"
                                              f"<i>(answered on {question.answered_at})</i>", parse_mode='HTML')
        else:
            update.message.reply_text("You haven't asked any questions yet..")


def question(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if not uc:
            return
        update.message.reply_text(send_question_text)
        logcommand(usercourse_obj=uc, command='/question', session=session)
        return ASK


def ask(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if not uc:
            return
        question_text = update.message.text
        que = Question(usercourse_id=uc.id, question_text=question_text, created_at=datetime.now())
        update.message.reply_text(f"Your question is sent. You'll receive the response on your registered email soon!\n")
        logger.info(f"/question - ask --> {question_text}")
        session.add(que)
        try:
            session.commit()
            logger.info(f"Question added to DB ---> {que}")
            send_question_mail_to_mentor(question_text, user, uc)
        except:
            logger.exception(f"Exception Saving Question within update {update} and error - {context.error}")
            session.rollback()
        logconversation(command_name='/question -> ask', context=context, session=session)
        return ConversationHandler.END


def questioncancel(update, context):
    with Session() as session:
        update.message.reply_text('Question cancelled!')
        logger.info(f"/question - questioncancel --> Question canelled somehow")
        logconversation(command_name='/question -> questioncancel', context=context, session=session)
        return ConversationHandler.END


def timeout_que(update, context):
    with Session() as session:
        update.message.reply_text(f'Timeout. Please /question again if you have any.\n(Timeout limit - {que_timeout_time} sec)')
        logger.info(f"Timeout for /question")
        logconversation(command_name='/question -> timeout_que', context=context, session=session)

"""
# Commenting this since paid plan is removed from the foundation course


def unlock(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            update.message.reply_text(f"Subscription Status - "
                                      f"{'Unpaid' if not uc.payment_verified_at else f'Paid (on {uc.payment_verified_at})'}\n\n")
            logcommand(usercourse_obj=uc, command='/unlock', session=session)
            if not uc.payment_verified_at:
                update.message.reply_text(payment_info)
                return GET_PAYMENT_PROOF



def payment_proof(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)

        received_payment_proof_text = update.message.text
        update.message.reply_text(payment_proof_text)
        logger.info(f"/unlock - payment_proof ---> {received_payment_proof_text}")
        send_payment_mail_to_mentor(received_payment_proof_text, user, uc)
        logconversation(command_name='/unlock -> payment_proof', context=context, session=session)
        return ConversationHandler.END


def goback(update, context):
    with Session() as session:
        update.message.reply_text('Operation cancelled!')
        logger.info(f"/unlock - goback ---> Some error")
        logconversation(command_name='/unlock -> goback', context=context, session=session)
        return ConversationHandler.END


def timeout_payment(update, context):
    with Session() as session:
        update.message.reply_text(f'Timeout. /unlock again to enter the menu.\n(Timeout limit - {payment_timeout_time} sec)')
        logger.info(f"Timeout for /timeout_unlock")
        logconversation(command_name='/unlock -> timeout_payment', context=context, session=session)

"""


def myreferrals(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            my_referral_id = user.my_referral_id
            students_referred = User.get_all_users_referred_by_code(session=session, code=my_referral_id)
            update.message.reply_text(f'Your referral id - {my_referral_id}\n'
                                      f'No of people you referred - {len(students_referred)}')
            for student in students_referred:
                update.message.reply_text(f"{student.name} - {student.created_at}")
            logcommand(usercourse_obj=uc, command='/myreferrals', session=session)


def send_question_mail_to_mentor(question_text, user, uc):
    body_text = f"Q: {question_text}\n" \
                f"User: {user}\n" \
                f"Course: {THIS_COURSE_ID}\n" \
                f"UserCourse: {uc}"
    msg = mail_body_for_question(body_text)
    logger.info(f"Sending mail ---> {msg}")
    lets_send_that_mail(msg=msg)
    logger.info('Main Sent!')


def send_payment_mail_to_mentor(payment_proof_text, user, uc):
    body_text = f"Sub: {payment_proof_text} - User: {user} - Course: {THIS_COURSE_ID}\n" \
                f"UserCourse - {uc}"
    msg = mail_body_for_payment_proof(body_text)
    logger.info(f"Sending mail ---")
    lets_send_that_mail(msg=msg)
    logger.info(f"Mail Sent!")


def send_certificate_mail_to_mentor(uc):
    learning_history = []
    for learning in uc.learnings:
        learning_history.append(learning)

    body_text = f"Certificate Request Received for user : {uc}\n" \
                f"User Learnings History: \n" \
                f"{learning_history}"
    msg = mail_body_for_certificate(body_text)
    logger.info(f"Sending mail ---> {msg}")
    lets_send_that_mail(msg=msg)
    logger.info(f"Mail Sent!")
    # prin(f"Mail sent - Certificate req with learning history - with the body ---> {msg}")


def generate_random_referral_id(chat_id):
    offset = 123123123
    temp = int(chat_id) + offset
    temp_str = f"{temp}"
    final_code = temp_str[::-1]
    return final_code


def save_user(update, context):
    user_data = context.user_data
    name = user_data['name']
    email_id = user_data['email_id']
    phoneno = user_data['phoneno']
    chat_id = user_data['chat_id']
    college_name = user_data['college_name']
    referralcode = user_data['referralcode']
    my_referral_id = generate_random_referral_id(chat_id)
    # current_level = user_data['current_level']
    created_at = datetime.now()

    user = User(name=name, email_id=email_id, phone_no=phoneno, chat_id=chat_id, college_name=college_name,
                referral_code=referralcode, my_referral_id=my_referral_id, created_at=created_at)
    with Session() as sess:
        sess.add(user)
        try:
            sess.commit()
        except:
            logger.exception(f"Got exception in save_user or send_mail after saving user. User name {name}, Email {email_id}, Phone no {phoneno}, College {college_name}, Referral - {referralcode}")
            sess.rollback()
        user_data.clear()
        logger.info(f'Created User - {user}')
        user = User.get_user_by_chatid(session=sess, chat_id=chat_id)
        uc = bind_user_with_current_course(update=update, context=context, user=user)
        if uc:
            update.message.reply_text(f"Awesome. You got registered with the following details!")
            user_creation_text = f"Name ---> {name}\n" \
                                 f"Email Id ---> {email_id}\n" \
                                 f"Phone No ---> {phoneno}\n" \
                                 f"College Name ---> {college_name}\n" \
                                 f"Referral Code ---> {referralcode}\n" \
                                 f"Course Name ----> {THIS_COURSE_NAME}"
            update.message.reply_text(user_creation_text)
            msg = mail_body_for_registration(body=user_creation_text, to_email=email_id)
            lets_send_that_mail(msg)
            logger.info(f"User details emailed to user!")
        else:
            logger.info('User created but some problem with binding')
            update.message.reply_text(f"User Created successfully. Try /register command again to view the details.")


def bind_user_with_current_course(update, context, user):
    if not isinstance(user, User):
        return None
    with Session() as session:
        # chat_id = update.effective_message.chat_id
        # user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        this_course = Course.get_course(session=session, id=THIS_COURSE_ID)
        logger.info(f'Binding user {user} with the course {this_course}')
        user.usercourses.append(UserCourse(course=this_course))
        session.add(user)
        try:
            session.commit()
            uc = user.usercourses.filter(UserCourse.course_id == this_course.id).first()
            logger.info(f'UserCourse created = {user}')
            return uc
        except:
            logger.exception(f"Got exception in bind_user_with_current_course. Course - {THIS_COURSE_ID}")
            session.rollback()
            return None


def save_learning(session, usercourse_id, current_level, started_at):
    user_learning = Learning(usercourse_id=usercourse_id, level_number=current_level, started_at=started_at)
    try:
        session.add(user_learning)
    except:
        session.rollback()
        logger.exception(f"Exception saving Learning - {user_learning}")
    else:
        Session.commit()
        logger.info(f"Learning Saved ---- {user_learning}")


def get_current_user(chat_id, update, context, session):
    user_data = context.user_data    # This is important, because everytime we call this function, we are storing user in user_data
    '''
    if user_data.get('user'):
        logger.info(f"Got user from local storage - {user_data['user']}")
        # ins = inspect(user_data.get('user'))
        # logger.info(f"Inspecting USER from storage ---> {ins.transient}, {ins.pending}, {ins.persistent}, {ins.detached}")
        # sess = Session.object_session(user_data.get('user'))
        # logger.info(f"User is from session -----{sess}")

        return user_data['user']
    '''
    # session = sqlalchemy.orm.scoped_session(Session)
    user = User.get_user_by_chatid(session=session, chat_id=chat_id)
        # logger.info(f"SSSSSSSSSS ---------- {s}")
        # ins = inspect(user)
        # logger.info(f"First inspection ---> {ins.detached}")
    if user:
        user_data['user'] = user
        # ins = inspect(user)
        # logger.info(f"Second inspection ---> {ins.detached}")
        logger.info(f"Got user from DB- {user_data['user']}")
        return user_data['user']
    else:
        logger.info(f"Could not find user. Sent /register message")
        update.message.reply_text(f"Hey hey, you need to /register first!")
        return None


def get_current_user_and_usercourse(chat_id, update, context, session):
    user_data = context.user_data    # This is important, because everytime we call this function, we are storing user in user_data
    user_temp = User.get_user_by_chatid(session=session, chat_id=chat_id)
    if not user_temp:
        logger.info(f"Could not find usercourse. Sent /register message")
        update.message.reply_text(f"Hey hey, you need to /register first!")
        return None, None
    user_data['user'] = user_temp
    # uc = user_temp.usercourses.filter(UserCourse.course_id == THIS_COURSE_ID).first()
    uc = session.query(UserCourse).filter(UserCourse.user_id == user_temp.id).filter(UserCourse.course_id == THIS_COURSE_ID).first()
    if uc:
        user_data['uc'] = uc
        logger.info(f"User and Usercourse found. User - {user_data['user']}\n"
                    f"And UserCourse - {user_data['uc']}")
        return user_data['user'], user_data['uc']
    else:
        logger.info('UserCourse is not availale. Creating now.')
        uc_new = bind_user_with_current_course(update=update, context=context, user=user_temp)
        if uc_new:
            logger.info(f'UserCourse created --> {uc_new}')
            user_data['uc'] = uc_new
            return user_data['user'], user_data['uc']
        else:
            logger.info(f'Error creating bind_user_with_current_course for user --> {user_temp}')
            return user_data['user'], None


def check_if_user_exists(chat_id, session):
    user = User.get_user_by_chatid(session=session, chat_id=chat_id)
    if user:
        return user
    else:
        return None


def check_if_user_and_usercourse_exists(chat_id, session):
    user = User.get_user_by_chatid(session=session, chat_id=chat_id)
    # print(user.courses)
    if not user:
        return None, None
    uc = user.usercourses.filter(UserCourse.course_id == THIS_COURSE_ID).first()
    # print(uc)
    if not uc:
        return user, None
    else:
        return user, uc


def check_if_user_has_already_started_level(chat_id, level_no, session):
    # print('check_if_user_has_already_started_level')
    # print(chat_id, level_no)
    logger.info(f"check_if_user_has_already_started_level. Chat id - {chat_id}, Level no - {level_no}")
    # user = check_if_user_exists(chat_id, session=session)
    user, uc = check_if_user_and_usercourse_exists(chat_id, session=session)
    user_level = uc.learnings.filter(Learning.level_number == level_no).first()
    logger.info(f"Result - {user_level}")
    # user_level = Learning.get_learning_by_user_and_level(session=session, chat_id=chat_id, level_no=level_no)
    # print(user_level)
    return True if user_level else False


def get_last_finished_level_of_user(chat_id, session):
    # last_finished_level = 2  # change it by actual last finished level
    logger.info('Inside get_last_finished_level_of_user ')
    user, uc = check_if_user_and_usercourse_exists(chat_id, session=session)
    count_user_learnings = uc.learnings.count()
    if count_user_learnings == 0:
        return 0
    user_level = uc.learnings.filter(Learning.finished_at != None).order_by(Learning.started_at.desc()).first()  # use != instead of IS NOT
    if not user_level:
        return 0
    last_finished_level = user_level.level_number
    logger.info(f"last finished level - {last_finished_level}")
    # print('last finished level', last_finished_level)
    return int(last_finished_level)


def get_current_level_of_user(chat_id, session):
    logger.info('Inside get_current_level_of_user')
    user, uc = check_if_user_and_usercourse_exists(chat_id, session=session)
    user_level = uc.learnings.filter(Learning.finished_at == None).order_by(Learning.started_at.desc()).first()
    if user_level:
        ongoing_level = user_level.level_number
        logger.info(f"Ongoing level - {ongoing_level}")
        return ongoing_level
    else:
        return None


def has_user_subscribed(uc):
    logger.info(f"Inside has_user_subscribed for {uc}")
    status = uc.payment_verified_at
    return status


def admin_check_user(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        if chat_id in BOTOWNER_CHAT_ID:
            if context.args:
                entered_id = context.args[0].strip()
                user_entered = User.get_user(id=entered_id, session=session)
                if user_entered:
                    uc = user_entered.usercourses.filter(UserCourse.course_id == THIS_COURSE_ID).first()
                    # uc = session.query(UserCourse).filter(UserCourse.user_id == user_entered.id).filter(UserCourse.course_id == THIS_COURSE_ID).first()
                    if uc:
                        update.message.reply_text(f"{user_entered}\n{uc}")
                        if uc.payment_verified_at:
                            update.message.reply_text(f"Subscription Verified on - {uc.payment_verified_at}")
                        else:
                            update.message.reply_text(f"Payment not made/verified.")
                        last_few_messages = uc.generaltalks.order_by(Generaltalk.created_at.desc()).limit(3).all()
                        for msg in last_few_messages:
                            update.message.reply_text(f"{msg.message} - {msg.created_at}\n")
                        people_referred = User.get_all_users_referred_by_code(code=user_entered.my_referral_id, session=session)
                        update.message.reply_text(f"Referred count - {len(people_referred)}")
                        for person in people_referred:
                            update.message.reply_text(f"{person.name} - {person.college_name} - {person.created_at}")
                    else:
                        update.message.reply_text(f"UserCourse does not exist for user - {user_entered}")
                else:
                    update.message.reply_text(f"No user found with this id.")
            else:
                update.message.reply_text('Pass user id in arg...')


def admin_check_user_learnings(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        if chat_id in BOTOWNER_CHAT_ID:
            if context.args:
                entered_id = context.args[0].strip()
                user_entered = User.get_user(id=entered_id, session=session)
                uc = user_entered.usercourses.filter(UserCourse.course_id == THIS_COURSE_ID).first()
                # uc = session.query(UserCourse).filter(UserCourse.user_id == user_entered.id).filter(UserCourse.course_id == THIS_COURSE_ID).first()
                update.message.reply_text(f"Learnings of the user ----> {user_entered}\n{uc}")
                if uc.learnings.count() > 0:
                    for learning in user_entered.learnings:
                        update.message.reply_text(f"{learning}")
                else:
                    update.message.reply_text(f"User has not started any lesson.")
            else:
                update.message.reply_text('Pass user id in arg...')


def admin_user_questions(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        if chat_id in BOTOWNER_CHAT_ID:
            if context.args:
                entered_id = context.args[0].strip()
                user_entered = User.get_user(id=entered_id, session=session)
                if not user_entered:
                    update.message.reply_text("User does not exist..")
                    return
                uc = user_entered.usercourses.filter(UserCourse.course_id == THIS_COURSE_ID).first()
                # uc = session.query(UserCourse).filter(UserCourse.user_id == user_entered.id).filter(UserCourse.course_id == THIS_COURSE_ID).first()
                if not uc:
                    update.message.reply_text(f"UserCourse does not exist for user - {user_entered}")
                    return
                update.message.reply_text(f"Questions of the user ----> {user_entered.id}, {user_entered.name}")
                if uc.questions.count() > 0:
                    for que in uc.questions:
                        update.message.reply_text(f"{que.id}. {que.question_text} - {que.created_at}")
                else:
                    update.message.reply_text(f"User has not asked any questions!")
            else:
                update.message.reply_text('Pass user id in arg...')


def admin_user_interactions(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        if chat_id in BOTOWNER_CHAT_ID:
            if context.args:
                entered_id = context.args[0].strip()
                user_entered = User.get_user(id=entered_id, session=session)
                uc = user_entered.usercourses.filter(UserCourse.course_id == THIS_COURSE_ID).first()
                # uc = session.query(UserCourse).filter(UserCourse.user_id == user_entered.id).filter(UserCourse.course_id == THIS_COURSE_ID).first()
                update.message.reply_text(f"Interactions of the user ---->  {user_entered.id}, {user_entered.name}")
                if uc.interactions.count() > 0:
                    for interaction in uc.interactions:
                        update.message.reply_text(f"{interaction.command} - {interaction.created_at}")
                else:
                    update.message.reply_text(f"User has not made any interaction.")
            else:
                update.message.reply_text('Pass user id in arg...')


def admin_mark_as_verified(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        if chat_id in BOTOWNER_CHAT_ID:
            if context.args:
                entered_id = context.args[0].strip()
                user = User.get_user(id=entered_id, session=session)
                uc = user.usercourses.filter(UserCourse.course_id == THIS_COURSE_ID).first()
                # uc = session.query(UserCourse).filter(UserCourse.user_id == user.id).filter(UserCourse.course_id == THIS_COURSE_ID).first()
                status = uc.mark_as_payment_verified(id=entered_id, session=session)
                if status is True:
                    logger.info(f"Marked this usercourse as verified --- {uc} at {uc.payment_verified_at}")
                    update.message.reply_text(f"Marked this user as verified.\n"
                                              f"{uc}")
                else:
                    logger.info(f'Something went wrong in marking user as verified - {uc}')
                    update.message.reply_text(f"Something went wrong in marking user as verified - {uc}")
            else:
                update.message.reply_text('Pass user id in arg...')


def admin_answer_question(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        if chat_id in BOTOWNER_CHAT_ID:
            if not context.args:
                update.message.reply_text("Pass the Question Id")
                return
            entered_id = context.args[0].strip()
            # print(entered_id)
            question = Question.get_question_by_id(session=session, id=entered_id)
            if not question:
                update.message.reply_text("No such question exists..")
                return
            if len(context.args) < 5:
                update.message.reply_text("This looks like very short answer..As a precaution I am not storing this as answer...")
                return
            ans = " ".join(context.args[1:])
            status = Question.update_question_with_answer(session=session, question_id=entered_id, answer=ans, answered_at=datetime.now())
            # print(status)
            # print(Question.get_question_by_id(session=session, id=entered_id))
            if status is True:
                logger.info(f"Answer submitted for question\n{question.id}. {question.question_text} ---> {ans}")
                update.message.reply_text(f"<b>Answer Submitted:</b> {ans}\n<b>For Question #</b>{question.id}. {question.question_text}", parse_mode='HTML')
            else:
                logger.info(f'Something went wrong in answering the question with id {question.id} - {question.question_text}')
                update.message.reply_text(f"Something went wrong in answering the question with id {question.id} - {question.question_text}")


def admin_rundown(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        if chat_id in BOTOWNER_CHAT_ID:
            with Session() as sess:
                total_users = sess.query(User).all()
                todays_users = User.get_todays_users(session=session)
                todays_usercourses = UserCourse.get_todays_usercourses(session=session)
                update.message.reply_text(f"--------- Total Users ---------\n {len(total_users)}")
                update.message.reply_text(f"--------- Today's Users ---------\n {todays_users}")
                update.message.reply_text(f"--------- Today's UserCourses ---------\n {todays_usercourses}")


def anyrandomcommand(update, context):
    with Session() as session:
        chat_id = update.message.chat_id
        msg = update.message.text
        user, uc = get_current_user_and_usercourse(chat_id, update, context, session=session)
        if not uc:
            return
        talk = Generaltalk(usercourse_id=uc.id, message=msg, created_at=datetime.now())
        session.add(talk)
        try:
            session.commit()
        except:
            logger.exception(f"Exception Saving GeneralTalk within update {update} and error - {context.error}")
            session.rollback()
        update.message.reply_text("This doesn't look like a valid command. To see list of all commands, just type / and scroll through the list!")
        logcommand(usercourse_obj=uc, command=msg, session=session)


def anyrandomtext(update, context):
    with Session() as session:
        chat_id = update.message.chat_id
        msg = update.message.text
        user, uc = get_current_user_and_usercourse(chat_id, update, context, session=session)
        if not uc:
            return
        talk = Generaltalk(usercourse_id=uc.id, message=msg, created_at=datetime.now())
        session.add(talk)
        try:
            session.commit()
        except:
            logger.exception(f"Exception Saving GeneralTalk within update {update} and error - {context.error}")
            session.rollback()
        update.message.reply_text("I'm not yet smart to understand general text (but I am learning day by day).\n"
                                  "For now I can only respond to commands that start with /")
        logcommand(usercourse_obj=uc, command=msg, session=session)


def editprofile(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            keyboard = [
                [
                    InlineKeyboardButton("Edit Name", callback_data='editname'),
                    InlineKeyboardButton("Edit Email", callback_data='editemail'),
                    InlineKeyboardButton("Edit Phone", callback_data='editphone'),
                    InlineKeyboardButton("Edit College", callback_data='editcollege'),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(f"Your profile details as follows -\n\n"
                                      f"Name - {user.name}\n"
                                      f"Email - {user.email_id}\n"
                                      f"Phone - {user.phone_no}\n"
                                      f"College - {user.college_name}\n\n"
                                      f"<i>(/canceledit to cancel)</i>", reply_markup=reply_markup, parse_mode='HTML')
            if uc:
                logcommand(usercourse_obj=uc, command='/editprofile', session=session)
            return SELECTING_ACTION


def editwhat(update: Update, context):
    with Session() as session:
        query = update.callback_query
        query.answer()
        if query.data == 'editname':
            # context.user_data['field'] = 'NAME'
            query.edit_message_text(text=f"Enter new name (/cancelthis to cancel)")
            logconversation(command_name=f"/editprofile --> Selected option - NAME", context=context, session=session)
            return SELECTED_NAME
        elif query.data =='editemail':
            # context.user_data['field'] = 'EMAIL'
            query.edit_message_text(text=f"Enter new email (/cancelthis to cancel)")
            logconversation(command_name=f"/editprofile --> Selected option - EMAIL", context=context, session=session)
            return SELECTED_EMAIL
        elif query.data =='editphone':
            # context.user_data['field'] = 'EMAIL'
            query.edit_message_text(text=f"Enter new phone no (/cancelthis to cancel)")
            logconversation(command_name=f"/editprofile --> Selected option - PHONE", context=context, session=session)
            return SELECTED_PHONE
        elif query.data =='editcollege':
            # context.user_data['field'] = 'EMAIL'
            query.edit_message_text(text=f"Enter new college name (/cancelthis to cancel)")
            logconversation(command_name=f"/editprofile --> Selected option - COLLEGE", context=context, session=session)
            return SELECTED_COLLEGE
        else:
            query.edit_message_text(text=f"Something is wrong. Try again later.")
            return ConversationHandler.END


def enter_new_name(update:Update, context: CallbackContext):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        msg = update.message.text
        if uc:
            edited_user = user.update_name(session=session, name=msg)
            update.message.reply_text(f"Your revised name -> {edited_user.name}")
            logconversation(command_name=f"/editprofile --> New name - {edited_user.name}", context=context, session=session)
        return END


def enter_new_email(update:Update, context: CallbackContext):
    with Session() as session:
        msg = update.message.text
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            if user.email_id == msg.strip():
                update.message.reply_text(f"New and old email are same. No changes made. (/editprofile again for any other changes)")
                return END
            is_old_email = check_if_email_already_exists(email_id=msg)
            if is_old_email:
                update.message.reply_text(f"This email already in use, try another one.")
                return SELECTED_EMAIL
            edited_user = user.update_email(session=session, email=msg)
            update.message.reply_text(f"Your revised emaild id -> {edited_user.email_id}")
            logconversation(command_name=f"/editprofile --> New email - {edited_user.email_id}", context=context, session=session)
        return END


def entered_wrong_new_email(update:Update, context: CallbackContext):
    with Session() as session:
        msg = update.message.text
        update.message.reply_text("That doesn't look like an email id. Enter valid email id. (/cancelthis to cancel)")
        logconversation(command_name=f"/editprofile --> Wrong email - {msg}", context=context, session=session)
        return SELECTED_EMAIL


def enter_new_phone(update:Update, context: CallbackContext):
    with Session() as session:
        msg = update.message.text
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        if uc:
            if user.phone_no == msg.strip():
                update.message.reply_text(f"New and old phone no are same. No changes made. (/editprofile again for any other changes)")
                return END
            is_existing_phone = check_if_phone_already_exists(phone_no=msg)
            if is_existing_phone:
                update.message.reply_text(f"This phone no is already in use, try another one.")
                return SELECTED_PHONE
            edited_user = user.update_phone(session=session, phone=msg)
            update.message.reply_text(f"Your revised phone no -> {edited_user.phone_no}")
            logconversation(command_name=f"/editprofile --> New phone no - {edited_user.phone_no}", context=context, session=session)
        return END


def enter_new_college(update:Update, context: CallbackContext):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user, uc = get_current_user_and_usercourse(chat_id=chat_id, update=update, context=context, session=session)
        msg = update.message.text
        if uc:
            edited_user = user.update_college(session=session, college_name=msg)
            update.message.reply_text(f"Your revised college name -> {edited_user.college_name}")
            logconversation(command_name=f"/editprofile --> New college name - {edited_user.college_name}", context=context, session=session)
        return END


def stop_nested(update, context):
    with Session() as session:
        update.message.reply_text('Editing Profile Canceled!')
        logconversation(command_name=f"/editprofile --> Stopped Nested", context=context, session=session)
        return END


def canceledit(update, context):
    with Session() as session:
        update.message.reply_text('Editing Cancelled')
        logconversation(command_name=f"/editprofile --> Cancelled Edit", context=context, session=session)
        return END


def set_bot_commands(updater):
    commands = [BotCommand(key, val) for key, val in dict(suggested_commands).items()]
    updater.bot.set_my_commands(commands)

# """
# DO NOT USE THIS SINCE COURSE ORDER IS DIFFERENT THAN THE ONE MENTIONED BELOW
# Make sure you read the instructions before enabling this
def one_time_fill_course_table():
    with Session() as session:
        # DONT UNCOMMENT THIS. Because they are saved to database once and for all. 
        # To add new course, just create one row, run once, and comment back. 
        Course.create_course(session=session, coursename='Python Advanced')
        Course.create_course(session=session, coursename='Machine Learning Basic')
        Course.create_course(session=session, coursename='Machine Learning Advanced')
        Course.create_course(session=session, coursename='NLP Basic')
        Course.create_course(session=session, coursename='NLP Advanced')
        Course.create_course(session=session, coursename='Computer Vision Basic')
        Course.create_course(session=session, coursename='Computer Vision Advanced')
        Course.create_course(session=session, coursename='Deep Learning Basic')
        Course.create_course(session=session, coursename='Deep Learning Advanced')
        Course.create_course(session=session, coursename='Devops Basic')
        Course.create_course(session=session, coursename='Devops Advanced')
        Course.create_course(session=session, coursename='Blockchain For All')
        Course.create_course(session=session, coursename='Web3 Basic')
        Course.create_course(session=session, coursename='Web3 Advanced')
        Course.create_course(session=session, coursename='AI 2023 For All')
        Course.create_course(session=session, coursename='AI Tools Basic')
        Course.create_course(session=session, coursename='AI Tools Advanced')
        Course.create_course(session=session, coursename='Mind Management')
# """

def dt_to_string(dt):
    return dt.strftime("%Y-%d-%m, %H:%M")


def send_long_message(context, msg):
    if len(msg) > 4096:
        for x in range(0, len(msg), 4096):
            context.bot.send_message(chat_id=REPORT_TO_CHANNEL, text=msg[x:x + 4096])
    else:
        context.bot.send_message(chat_id=REPORT_TO_CHANNEL, text=msg)


def job_today(context: CallbackContext):
    with Session() as session:
        # today_new_users = session.query(User).filter(func.date(User.created_at) == date.today()).all()
        for course in session.query(Course).all():
            today_new_users = course.usercourses.filter(func.date(UserCourse.created_at) == date.today()).all()
            today_new_users_names = [(uc.user.name, uc.user.college_name) for uc in today_new_users]
            final_str = f"{len(today_new_users)} New users for {course.coursename}\n\n" \
                        f"{today_new_users_names}"
            send_long_message(context, final_str)
            # context.bot.send_message(chat_id=REPORT_TO_CHANNEL, text=final_str)

            today_active_interactions = session.query(Interaction.usercourse_id).filter(func.date(Interaction.created_at) == date.today()).distinct().all()
            today_active_usercourses_for_course = [session.query(UserCourse).filter(UserCourse.id == interaction[0]).filter(UserCourse.course_id == course.id).first() for interaction in today_active_interactions]

            today_active_users_data = [(uc.user.name, uc.learnings.filter(func.date(Learning.started_at) == date.today()).all()) for uc in today_active_usercourses_for_course if uc is not None]
            final_str = f"{len(today_active_usercourses_for_course)} Active users for {course.coursename}\n\n" \
                        f"{today_active_users_data}"
            send_long_message(context, final_str)
            # context.bot.send_message(chat_id=REPORT_TO_CHANNEL, text=final_str)


def startjobforstats(update, context: CallbackContext):
    chat_id = update.effective_message.chat_id
    if chat_id in BOTOWNER_CHAT_ID:
        current_jobs = context.job_queue.get_jobs_by_name(JOB_NAME)
        if not current_jobs:
            sched_time = datetime(2023, 6, 12, 5, 00, 00)   # reporting time set to pm
            target_time = pytz.timezone('Asia/Kolkata').localize(sched_time)
            # context.job_queue.run_repeating(job_today, interval=5, first=2, context='myfoot', name=JOB_NAME)
            context.job_queue.run_daily(job_today, time=target_time, context='myfoot', name=JOB_NAME)
            context.bot.send_message(chat_id=chat_id, text=f"Job `{JOB_NAME}` started!")
        else:
            context.bot.send_message(chat_id=chat_id, text=f"Job `{JOB_NAME}` already running")


def stopjobforstats(update, context: CallbackContext):
    chat_id = update.effective_message.chat_id
    if chat_id in BOTOWNER_CHAT_ID:
        current_jobs = context.job_queue.get_jobs_by_name(JOB_NAME)
        if not current_jobs:
            context.bot.send_message(chat_id=chat_id, text=f"Job `{JOB_NAME}` does not exist!")
            return
        for job in current_jobs:
            job.schedule_removal()
            context.bot.send_message(chat_id=chat_id, text=f"Job `{JOB_NAME}` stopped!")

"""
## This function uses razorpay API and creates a ONE TIME payment link for the user whose data is passed in the payload. 
## Each url is unique and different for different user. 
def generate_razorpay_link(usercourse):
    print('generating payment link')
    rzp_key = os.environ.get('rzp_key')
    rzp_secret = os.environ.get('rzp_secret')
    print(rzp_key, rzp_secret)
    certi_cost = CERTI_COST
    rzp_ref_id = usercourse.user.my_referral_id
    rzp_payload_description = RZP_PAYLOAD_DESCRIPTION
    customer_name = usercourse.user.name
    customer_phone = usercourse.user.phone_no  # with prefix +91
    print(customer_name, customer_phone)
    if len(customer_name) < 8:
        customer_name = f"{customer_name} - {customer_name}"
    customer_name = customer_name[:14]
    if len(customer_phone) == 10:
        customer_phone = f"+91{customer_phone}"
    if len(customer_phone) == 12:
        customer_phone = f"+{customer_phone}"
    print(customer_name, customer_phone)

    auth = HTTPBasicAuth(rzp_key, rzp_secret)
    headers = {"Content-Type": "application/json"}
    rzp_link_url = 'https://api.razorpay.com/v1/payment_links/'
    payload = {
        'upi_link': "true",
        'amount': certi_cost,
        'currency': "INR",
        'reference_id': rzp_ref_id,
        'description': rzp_payload_description,
        "customer": {
            "name": customer_name,
            "contact": customer_phone,
        },
        'notify': {
            'sms': True
        },
    }
    try:
        res = requests.post(url=rzp_link_url, data=json.dumps(payload), headers=headers, auth=auth).json()
        print(res)
    except:
        logger.exception("Exception while creating payment link")
        return None
    else:
        rzp_link_id = res.get('id')
        rzp_link_reference_id = res.get('reference_id')
        rzp_link_short_url = res.get('short_url')
        amount = res.get('amount')
        payment = Payment(usercourse_id=usercourse.id, rzp_link_id=rzp_link_id, rzp_link_reference_id=rzp_link_reference_id, rzp_link_short_url=rzp_link_short_url, amount=amount, created_at=datetime.now())
        print('payment link saved - ,{payment}')
        with Session() as session:
            session.add(payment)
            try:
                session.commit()
                logger.info(f"Payment link created ----> {payment}")
            except:
                session.rollback()
                logger.exception(f"Problem creating payment link ----> {payment}")
        return payment

"""

# def test_razorpay_link():
#     """
#     We have to integrate Razorpay in this video.
#     Razorpay has an option to where we can create unique payment link for diffferetn users programmatically.
#     Our solution is to generate new link on razopay once user gives /certficate command, and then once the payment is done, update database accordingly.
#     Phase 1 - Generate razorpay link using their API
#     Phase 2 - Save the status of link in database. Modify user table to accommodate this new link (same link will be shared when user gives /certificate more than once. Until the payment is made
#     Phase 3 - Pay using the link and update database
#     Phase 4 - Call the function from /certificate (i.e. final integration)
#     """
#     # Create razorpay link programmatically
#     payment_link = generate_razorpay_link(usercourse)



if __name__ == '__main__':
    # test_razorpay_link()
    User.__table__.create(engine, checkfirst=True)
    Course.__table__.create(engine, checkfirst=True)
    UserCourse.__table__.create(engine, checkfirst=True)
    Learning.__table__.create(engine, checkfirst=True)
    Generaltalk.__table__.create(engine, checkfirst=True)
    Question.__table__.create(engine, checkfirst=True)
    Interaction.__table__.create(engine, checkfirst=True)
    Certificate.__table__.create(engine, checkfirst=True)
    one_time_fill_course_table()
    updater = Updater(token=TOKEN, use_context=True)
    set_bot_commands(updater)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('part1', part1))
    dp.add_handler(CommandHandler('part2', part2))
    dp.add_handler(CommandHandler('part3', part3))
    dp.add_handler(CommandHandler('part4', part4))
    dp.add_handler(CommandHandler('part5', part5))
    dp.add_handler(CommandHandler('part6', part6))
    dp.add_handler(CommandHandler('part7', part7))
    dp.add_handler(CommandHandler('part8', part8))
    dp.add_handler(CommandHandler('part9', part9))
    dp.add_handler(CommandHandler('part10', part10))
    dp.add_handler(CommandHandler('part11', part11))
    dp.add_handler(CommandHandler('part12', part12))
    dp.add_handler(CommandHandler('part13', part13))
    dp.add_handler(CommandHandler('part14', part14))
    dp.add_handler(CommandHandler('part15', part15))
    dp.add_handler(CommandHandler('part16', part16))
    dp.add_handler(CommandHandler('part17', part17))
    dp.add_handler(CommandHandler('part18', part18))
    dp.add_handler(CommandHandler('part19', part19))
    dp.add_handler(CommandHandler('methodology', methodology))
    dp.add_handler(CommandHandler('howtohomework', howtohomework))
    dp.add_handler(CommandHandler('colablinkaccess', colablinkaccess))
    # dp.add_handler(CommandHandler('test', test))

    dp.add_handler(CommandHandler('mycourses', mycourses))
    dp.add_handler(CommandHandler('myhomework', myhomework))
    dp.add_handler(CommandHandler('myquestions', myquestions))
    dp.add_handler(CommandHandler('certificate', certificate))
    dp.add_handler(CommandHandler('allcourses', allcourses))
    dp.add_handler(CommandHandler('jobroles', jobroles))
    dp.add_handler(CommandHandler('outline', outline))
    dp.add_handler(CommandHandler('donate', donate))
    dp.add_handler(CommandHandler('discord', discord))
    dp.add_handler(CommandHandler('telegramgroup', telegramgroup))
    dp.add_handler(CommandHandler('community', community))
    dp.add_handler(CommandHandler('changelog', changelog))

    dp.add_handler(CommandHandler('myreferrals', myreferrals))
    dp.add_handler(CommandHandler('admin_check_user', admin_check_user))
    dp.add_handler(CommandHandler('admin_check_user_learnings', admin_check_user_learnings))
    dp.add_handler(CommandHandler('admin_user_questions', admin_user_questions))
    dp.add_handler(CommandHandler('admin_user_interactions', admin_user_interactions))
    dp.add_handler(CommandHandler('admin_mark_as_verified', admin_mark_as_verified))
    dp.add_handler(CommandHandler('admin_rundown', admin_rundown))
    dp.add_handler(CommandHandler('admin_answer_question', admin_answer_question))
    # dp.add_handler(CommandHandler('admin_rundown', admin_rundown))
    dp.add_handler(CommandHandler('startjobforstats', startjobforstats))
    dp.add_handler(CommandHandler('stopjobforstats', stopjobforstats))

    dp.add_error_handler(error)

    reg_conv = ConversationHandler(
        entry_points=[CommandHandler('register', register)],
        states={
            NAME: [MessageHandler(Filters.text, name)],
            EMAILID: [MessageHandler(Filters.regex(r'^(\w|\.|\_|\-)+[@](\w|\_|\-|\.)+[.]\w{2,}$'), email_id),
                      MessageHandler(~Filters.regex(r'^(\w|\.|\_|\-)+[@](\w|\_|\-|\.)+[.]\w{2,}$'), wrong_email_id)],
            PHONENO: [MessageHandler(Filters.text, phone_no)],
            COLLEGE_NAME: [MessageHandler(Filters.text, college_name)],
            REFERRAL_CODE: [CommandHandler('skipcode', skipcode),
                            MessageHandler(Filters.text, referral_code)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_reg)]
        },
        fallbacks=[CommandHandler('reg_cancel', reg_cancel)],
        conversation_timeout=reg_timeout_time
    )
    que_conv = ConversationHandler(
        entry_points=[CommandHandler('question', question)],
        states={
            ASK: [CommandHandler('questioncancel', questioncancel),
                  MessageHandler(Filters.text and ~Filters.command, ask),
                  ],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_que)]
        },
        fallbacks=[CommandHandler('questioncancel', questioncancel)],
        conversation_timeout=que_timeout_time
    )

    # payment_conv = ConversationHandler(
    #     entry_points=[CommandHandler('unlock', unlock)],
    #     states={
    #         GET_PAYMENT_PROOF: [CommandHandler('goback', goback),
    #                             MessageHandler(Filters.text and ~Filters.command, payment_proof)],
    #         ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_payment)]
    #     },
    #     fallbacks=[CommandHandler('goback', goback)],
    #     conversation_timeout=payment_timeout_time
    # )

    edit_data_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(editwhat, pattern='^editname|editemail|editphone|editcollege$')],
        states={
            SELECTED_NAME: [MessageHandler(Filters.text and ~Filters.command, enter_new_name)],
            SELECTED_EMAIL: [MessageHandler(Filters.regex(r'^([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$'), enter_new_email),
                             MessageHandler(~Filters.regex(r'^([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$') and ~Filters.command, entered_wrong_new_email)],
            SELECTED_PHONE: [MessageHandler(Filters.text and ~Filters.command, enter_new_phone)],
            SELECTED_COLLEGE: [MessageHandler(Filters.text and ~Filters.command, enter_new_college)]
        },
        fallbacks=[CommandHandler('cancelthis', stop_nested)],
        map_to_parent={
            END: END
        }
    )
    editprofile_conv = ConversationHandler(
        entry_points=[CommandHandler('editprofile', editprofile)],
        states={
            SELECTING_ACTION: [edit_data_conv],
        },
        fallbacks=[CommandHandler('canceledit', canceledit)]
    )

    part1hw = ConversationHandler(
        entry_points=[CommandHandler('part1hw', part1hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part2hw = ConversationHandler(
        entry_points=[CommandHandler('part2hw', part2hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part3hw = ConversationHandler(
        entry_points=[CommandHandler('part3hw', part3hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part4hw = ConversationHandler(
        entry_points=[CommandHandler('part4hw', part4hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part5hw = ConversationHandler(
        entry_points=[CommandHandler('part5hw', part5hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part6hw = ConversationHandler(
        entry_points=[CommandHandler('part6hw', part6hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part7hw = ConversationHandler(
        entry_points=[CommandHandler('part7hw', part7hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part8hw = ConversationHandler(
        entry_points=[CommandHandler('part8hw', part8hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part9hw = ConversationHandler(
        entry_points=[CommandHandler('part9hw', part9hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part10hw = ConversationHandler(
        entry_points=[CommandHandler('part10hw', part10hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part11hw = ConversationHandler(
        entry_points=[CommandHandler('part11hw', part11hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part12hw = ConversationHandler(
        entry_points=[CommandHandler('part12hw', part12hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part13hw = ConversationHandler(
        entry_points=[CommandHandler('part13hw', part13hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part14hw = ConversationHandler(
        entry_points=[CommandHandler('part14hw', part14hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part15hw = ConversationHandler(
        entry_points=[CommandHandler('part15hw', part15hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part16hw = ConversationHandler(
        entry_points=[CommandHandler('part16hw', part16hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part17hw = ConversationHandler(
        entry_points=[CommandHandler('part17hw', part17hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part18hw = ConversationHandler(
        entry_points=[CommandHandler('part18hw', part18hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )
    part19hw = ConversationHandler(
        entry_points=[CommandHandler('part19hw', part19hw)],
        states={
            ASK_FOR_HW: [MessageHandler(Filters.text and ~Filters.command, send_hw_link)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_homework)]
        },
        fallbacks=[CommandHandler('cancelsub', cancelsub)],
        conversation_timeout=homework_timeout_time
    )

    dp.add_handler(editprofile_conv)
    dp.add_handler(reg_conv)
    dp.add_handler(que_conv)
    dp.add_handler(part1hw)
    dp.add_handler(part2hw)
    dp.add_handler(part3hw)
    dp.add_handler(part4hw)
    dp.add_handler(part5hw)
    dp.add_handler(part6hw)
    dp.add_handler(part7hw)
    dp.add_handler(part8hw)
    dp.add_handler(part9hw)
    dp.add_handler(part10hw)
    dp.add_handler(part11hw)
    dp.add_handler(part12hw)
    dp.add_handler(part13hw)
    dp.add_handler(part14hw)
    dp.add_handler(part15hw)
    dp.add_handler(part16hw)
    dp.add_handler(part17hw)
    dp.add_handler(part18hw)
    dp.add_handler(part19hw)
    # dp.add_handler(payment_conv)
    dp.add_handler(MessageHandler(Filters.command, anyrandomcommand))
    dp.add_handler(MessageHandler(Filters.text, anyrandomtext))

    # read MODE env variable, fall back to 'polling' when undefined
    mode = os.environ.get("MODE", "polling")
    if mode == 'webhook':
        live_server_url = os.environ.get("LIVE_SERVER_URL", "0.0.0.0")
        logger.info('inside WEBHOOK block')
        updater.start_webhook(listen="0.0.0.0", port=8443, url_path=f"{TOKEN}", webhook_url=f"{live_server_url}/{TOKEN}", cert=SSL_CERT)
        logging.info(updater.bot.get_webhook_info())
    else:
        logger.info('inside POLLING block')
        updater.start_polling()
        updater.idle()



