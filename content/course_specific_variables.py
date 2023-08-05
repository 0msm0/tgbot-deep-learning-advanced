from content.all_courses_metainfo import COURSES_DETAILS, COURSES_NAMES

CURRENT_COURSE_SHORTCODE = 'dla'
PAID_LEVEL = 20
TOKEN_NAME = 'DL_ADVANCED_TELEGRAM_TOKEN'
SSL_PATH = 'ssl-certi/dlbasic-tgbot-ssl.pem'

LAST_LEVEL_OF_COURSE = COURSES_DETAILS[CURRENT_COURSE_SHORTCODE]['levels']
THIS_COURSE_ID = COURSES_DETAILS[CURRENT_COURSE_SHORTCODE]['course_id']
course_slug = COURSES_DETAILS[CURRENT_COURSE_SHORTCODE]['course_slug']
THIS_COURSE_NAME = COURSES_DETAILS[CURRENT_COURSE_SHORTCODE]['course_name']

CERTI_BASE_URL = f"https://ctoschool.live/{course_slug}/certificate/"
BOTOWNER_CHAT_ID = [1748983631]
CERTI_COST_STR = '₹ 360'
CERTIFICATE_PAYMENT_LINK = 'https://rzp.io/l/3jn5r7lgi'

START_TEXT = "Welcome to the Deep Learning Basic course by CTOschool.\nSince you are here, I assume that you have completed Python Foundation and Advanced course.\n" \
             "This course is full of practical and hands-on knowledge on Deep Learning.\n You'll see the true power of DL here. \n\nCheck /methodology before you start. \n\nJoin /community to meet others taking this course." \

# RZP_PAYLOAD_DESCRIPTION = 'Payment for Python Foundation Certificate'
# RZP_PAYLOAD_CERTI_COST = 36000

REGISTRATION_EMAIL_SUBJECT_TEXT = f'Welcome To {THIS_COURSE_NAME} by CTOschool'
REGISTRATION_EMAIL_BODY_TEXT = f'This course is a Powerhouse packed with tons of practical, hands-on python knowledge.\n' \
                                f'On completion, you are almost ready to apply for positions such as Backend Engineer, Full Stack Developer etc..\n' \
                                f'We suggest you finish the Complete cto-track offered by CTOschool before applying for jobs.\n\n'

CERTIFICATE_TEXT_AFTER_COMPLETION = f"Congratulations for completing the course. This is a big win for you and a big milestone in your career building. You can start with the next course in cto-track.\n\n" \
                                    f"While CTOschool couses are completely free and the certificates are paid. That's how we can afford to keep the courses free.\n\n" \
                                    f"Certificate fee - {CERTI_COST_STR}\n" \
                                    f"Payment link - {CERTIFICATE_PAYMENT_LINK}\n" \
                                    f"You'll receive certificate over the email within 24hrs after making the payment. \n" \
                                    f"CTOschool certificates are unique. They come preloaded with Proof Of Coding, which helps interviewer track and verify your coding skills, bringing you one step closer to cracking the interview!\n\n" \
                                    f"Certificate or not, feel free to take up the new course. Hop on to /discord and continue your journey to the CTO with new team!" \

PAYMENT_INFO = "Fees - 360\nGpay/Phonepe - 9819012630\nUPI - 9819012630@sbi\n\n" \
               "Once paid, forward the sms/receipt below and access shall be granted to you in some time.\n\n" \
               "(/goback if you haven't paid.\n/whybuyme if you still have doubts)\n" \


CTOSCHOOL_COURSES_TEXT = f"Check out the info at https://ctoschool.live/ctotrack"

PAYMENT_PROOF_TEXT = f"Mailing your receipt to the admin..\n\n" \
                     f"You'll be granted access once it is verified. It won't take long.\n"

SEND_QUESTION_TEXT = f"Ask your question here, one of our mentors shall reply you soon.\n" \
                     f"Type /questioncancel to quit."

HOMEWORK_INSTRUCTIONS = f"1. Go to Colab website - https://colab.research.google.com/\n" \
                        f"2. File -> New Notebook\n" \
                        f"3. Give it a name in the format <i>your email - original sheet name</i>\n" \
                        f"4. Type each program as given in the original notebook and execute it (if you want to copy paste, you might as well stop taking this course. TYPING is an important part of our methodology)\n" \
                        f"5. Make your notebook PUBLICLY ACCESSIBLE by using SHARE option in colab (see /colablinkaccess)\n" \
                        f"6. Copy url\n" \
                        f"7. Use /part1hw command and it'll ask you for homework link. Paste the link."

COLABLINKACCESS_TEXT = f"Follow these instructions to make your colab file publicly accessible\n" \
                  f"1. Open colab file & click on SHARE button on TOP RIGHT\n" \
                  f"2. Select option - 'Anyone With The Link'\n" \
                  f"3. Copy the link (give 'Viewer' level access)\n\n" \
                  f"Note - If you are on <b>phone</b>, go to browser settings and click on 'Desktop Site' option then follow the above steps."

METHODOLOGY_TEXT = f"Our methodology is simple. <b><u>Learning by Doing, Programming by Typing</u></b>\n" \
                   f"Don't copy paste, but actually type so the muscle memory gets trained.\n\n" \
                   f"Few Imp Points - \n" \
                   f" - Start the course with /part1\n" \
                   f" - Explore other commands by simply typing / \n" \
                   f" - Use telegram on computer (preferred)\n" \
                   f" - No need of any software installation\n" \
                   f" - Get a certificate after finishing all {LAST_LEVEL_OF_COURSE} levels\n" \
                   f" - If you don't understand something, ask the mentors/colleagues on our open /discord community or /telegramgroup community\n" \
                   f" - Course can be completed within 1 to 5 days\n" \
                   f" - Check out /howtohomework for homework instructions\n" \
                   f" - Rest the bot will guide you step by step\n\n" \
                   f"Congratulations for taking the first step. All the best." \

DONATION_TEXT = f"Kindly consider donating some amount if you found this course to be useful. <i>(Min donation INR 5)</>\n\n" \
                f"Benefits - \n" \
                f"<b>a. Get equal amount of discount in the next course</b>\n" \
                f"<b>b. Access to a special community on discord</b>\n\n" \
                f"Donation link - https://rzp.io/l/n6ZzjdV"

DISCORD_TEXT = f"Meet the community of students taking the same course - https://discord.gg/n3p9jGKRRX\n(If you are not on discord yet, you should!)"
TELEGRAMGROUP_TEXT = f"Telegram group for all participants of this course - https://t.me/pythonfoundation\n"
COMMUNITY_TEXT = f"Telegram group  - https://t.me/ctoschool\nDiscord group - https://discord.gg/n3p9jGKRRX"


JOBROLES_TEXT = 'Completing the entire cto-track enables you to apply for the following roles in IT industry.\n\n' \
                '<b>Software Developer</b>\n<b>Backend Developer</b>\n<b>Python Developer</b>\n<b>Devops Engineer</b>\n' \
                '<b>Full Stack Developer</b>\n<b>Machine Learning Engineer</b>\n<b>Data Scientist</b>\n' \
                '<b>Blockchain Developer</b>\n<b>Startup CTO</b>\n\n' \
                'And many such similar roles.'
ALLCOURSE_TEXT = 'CTOschool aims to create holistic techology professionals and hence the curriculum is designed in such a way that the candidate can acquire all the skills that a potential (startup) CTO candidate requires!\n\n' \
                 '1. Python Foundation\n' \
                 '2. Python Advanced\n' \
                 '3. Machine Learning Foundation\n' \
                 '4. Deep Learning with NLP\n' \
                 '5. Devops\n' \
                 '6. Deep Learning with CV\n' \
                 '7. Blockchain 101\n' \
                 '8. Blockchain 102\n\n' \
                 'Check out https://ctoschool.live/ctotrack for more details. Join /discord to access the community of fellow CTO aspirants!'


REPORT_TO_CHANNEL = '@Zlstatschannelllll'
JOB_NAME='sendstatstoadminchannel'