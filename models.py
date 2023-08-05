from dbhelper import Base, Session
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship, backref
from datetime import datetime, date
import logging

log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
file_handler = logging.FileHandler("logs/app.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
# logger.info("Loging from models file")


class User(Base):
    __tablename__ = 'users'
    # name, email_id, college_name, chat_id, created_at
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email_id = Column(String(255), nullable=False, unique=True)
    phone_no = Column(String(13), nullable=False, unique=True)
    chat_id = Column(Integer, nullable=False, unique=True)
    college_name = Column(String(255))
    referral_code = Column(String(255))
    my_referral_id = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False)
    courses = relationship('Course', secondary='usercourses', viewonly=True)

    @classmethod
    def get_user(cls, session, id):
        return session.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_user_by_chatid(cls, session, chat_id):
        return session.query(cls).filter(cls.chat_id == chat_id).first()

    @classmethod
    def get_users_by_college_name(cls, session, college_name):
        return session.query(cls).filter(cls.college_name.like(f'%{college_name}%')).all()

    @classmethod
    def get_all_users_referred_by_code(cls, session, code):
        return session.query(cls).filter(cls.referral_code.like(f'%{code}%')).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_todays_users(cls, session):
        return session.query(cls).filter(func.DATE(cls.created_at) == date.today()).all()
        # return session.query(cls).filter(func.DATE(cls.created_at) == date.today())

    def update_name(self, session, name):
        self.name = name
        session.add(self)
        try:
            session.commit()
            return self
        except:
            session.rollback()
            return None

    def update_email(self, session, email):
        self.email_id = email
        session.add(self)
        try:
            session.commit()
            return self
        except:
            session.rollback()
            return None

    def update_phone(self, session, phone):
        self.phone_no = phone
        session.add(self)
        try:
            session.commit()
            return self
        except:
            session.rollback()
            return None

    def update_college(self, session, college_name):
        self.college_name = college_name
        session.add(self)
        try:
            session.commit()
            return self
        except:
            session.rollback()
            return None

    def __repr__(self):
        return f"<User. Id - {self.id}, Name = {self.name}, Email - {self.email_id}, Chat_id - {self.chat_id}, " \
               f"Phone No - {self.phone_no}, College Name = {self.college_name},  Referred By - {self.referral_code}, My Referral Code - {self.my_referral_id}, Created_at - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}>"


class Course(Base):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True, autoincrement=True)
    coursename = Column(String(255), nullable=False, unique=True)
    # users = relationship('UserCourse', back_populates='course')
    created_at = Column(DateTime, default=datetime.utcnow())
    users = relationship('User', secondary='usercourses', viewonly=True)
    certificates = relationship('Certificate', back_populates='course', lazy='dynamic')

    @classmethod
    def get_course(cls, session, id):
        return session.query(cls).filter(cls.id == id).first()

    @classmethod
    def create_course(cls, session, coursename):
        course = Course()
        course.coursename = coursename
        session.add(course)
        try:
            session.commit()
        except:
            print("Rolling back from `create_course`")
            session.rollback()
            return None
        return course

    def __repr__(self):
        return f"<Course: id {self.id}, coursename {self.coursename}>"


class UserCourse(Base):
    __tablename__ = 'usercourses'
    id = Column(Integer, unique=True, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    course_id = Column(Integer, ForeignKey('courses.id'))
    payment_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow())
    # user = relationship('User', back_populates='courses')
    # course = relationship('Course', back_populates='users')
    user = relationship('User', backref=backref('usercourses', cascade='all, delete-orphan', lazy='dynamic'))
    course = relationship('Course', backref=backref('usercourses', cascade='all, delete-orphan', lazy='dynamic'))

    learnings = relationship('Learning', back_populates='usercourse', lazy="dynamic")
    generaltalks = relationship('Generaltalk', back_populates='usercourse', lazy='dynamic')
    questions = relationship('Question', back_populates='usercourse', lazy='dynamic')
    interactions = relationship('Interaction', back_populates='usercourse', lazy='dynamic')
    certificate = relationship('Certificate', back_populates='usercourse', lazy='dynamic', uselist=True)  # one-one relationship
    # payment = relationship('Payment', back_populates='usercourse', lazy='dynamic', uselist=True)  # one-one relationship

    @classmethod
    def get_usercourse(cls, session, id):
        return session.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_usercourse_by_userid_and_courseid(cls, session, user_id, course_id):
        return session.query(cls).filter(cls.user_id == user_id).filter(cls.course_id == course_id).first()

    @classmethod
    def mark_as_payment_verified(cls, session, id):
        user = User.get_user(session=session, id=id)
        user.payment_verified_at = datetime.now()
        session.add(user)
        try:
            session.commit()
            return True
        except:
            logger.exception(f"Exception in mark_as_payment_verified for user id {id} ")
            print('Rolling back inside mark as payment verified')
            session.rollback()
            return False

    @classmethod
    def get_todays_usercourses(cls, session):
        return session.query(cls).filter(func.DATE(cls.created_at) == date.today()).all()

    def __repr__(self):
        return f"<UserCourse--> id: {self.id}, user_id: {self.user_id}, course_id: {self.course_id}, created_at: {self.created_at}>"


class Learning(Base):
    __tablename__ = 'learnings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    usercourse_id = Column(Integer, ForeignKey('usercourses.id'), nullable=False)
    level_number = Column(Integer)
    homework_link = Column(Text)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    usercourse = relationship('UserCourse')

    @classmethod
    def get_learning_by_user_and_level(cls, session, usercourse_id, level_no):
        return session.query(cls).filter(cls.usercourse_id == usercourse_id, cls.level_number == level_no).first()

    #
    # @classmethod
    # def get_last_finished_level_of_user(cls, session, usercourse_id):
    #     return session.query(cls).filter(cls.usercourse_id == usercourse_id, cls.finished_at is not None).all()

    @classmethod
    def update_learning_homework(cls, session, usercourse_id, level_no, homework_link, finished_at):
        learning = Learning.get_learning_by_user_and_level(session=session, usercourse_id=usercourse_id, level_no=level_no)
        learning.homework_link = homework_link
        learning.finished_at = finished_at
        session.add(learning)
        try:
            session.commit()
            logger.info(f'Homework updated --> {learning}')
        except:
            logger.exception(f"Exception in update_learning_homework for usercourse_id {usercourse_id}, level no - {level_no}, homework_link {homework_link} ")
            print('Rolling back inside update_learning_homework')
            session.rollback()

    def __repr__(self):
        return f"<Learning Table. Id - {self.id}, UserCourse id - {self.usercourse_id}, LevelNo - {self.level_number}, " \
               f"Homework Link - {self.homework_link}, Started_at - {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}, " \
               f"Finished_at - {self.finished_at.strftime('%Y-%m-%d %H:%M:%S') if self.finished_at else 'None' }>"


class Generaltalk(Base):
    __tablename__ = 'generaltalks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    usercourse_id = Column(Integer, ForeignKey('usercourses.id'), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    usercourse = relationship('UserCourse')

    @classmethod
    def get_last_three_messages_of_user(cls, session, usercourse_id):
        return session.query(cls).filter(cls.usercourse_id == usercourse_id).order_by(cls.created_at.desc()).limit(3).all()

    def __repr__(self):
        return f"Talk added - UserCourse id - {self.usercourse_id}, message - {self.message}, created_at - {self.created_at}"


class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    usercourse_id = Column(Integer, ForeignKey('usercourses.id'), nullable=False)
    question_text = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    answered_at = Column(DateTime, nullable=True)
    usercourse = relationship('UserCourse')

    @classmethod
    def get_question_by_id(cls, session, id):
        return session.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_last_three_questions_of_user(cls, session, usercourse_id):
        return session.query(cls).filter(cls.usercourse_id == usercourse_id).order_by(cls.created_at.desc()).limit(3).all()


    @classmethod
    def update_question_with_answer(cls, session, question_id, answer, answered_at):
        question = Question.get_question_by_id(session=session, id=question_id)
        question.answer = answer
        question.answered_at = answered_at
        session.add(question)
        try:
            session.commit()
            return True
        except:
            logger.exception(f"Exception in update_question_with_answer for question id {question_id} ")
            print('Rolling back inside update_question_with_answer')
            session.rollback()
            return False

    def __repr__(self):
        return f"Question added - UserCourse id - {self.usercourse_id}, message - {self.question_text}, created_at - {self.created_at}"


class Interaction(Base):
    __tablename__ = 'interactions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    command = Column(Text, nullable=False)
    usercourse_id = Column(Integer, ForeignKey('usercourses.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now())
    usercourse = relationship('UserCourse')

    @classmethod
    def get_interaction_by_id(cls, session, id):
        return session.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_all_interactions_by_user(cls, session, usercourse_id):
        return session.query(cls).filter(cls.usercourse_id == usercourse_id).all()

    @classmethod
    def get_todays_interactions(cls, session):
        return session.query(cls).filter(func.Date(cls.created_at) == datetime.today()).all()

    def __repr__(self):
        return f"Interaction: id - {self.id}, command - {self.command}, usercourse_id - {self.usercourse_id}, created_at - {self.created_at} "


class Certificate(Base):
    __tablename__ = 'certificates'
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=True, unique=True)
    usercourse_id = Column(Integer, ForeignKey('usercourses.id'), unique=True, nullable=False)   # unique=True mandatory for one-one
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    requested_at = Column(DateTime, nullable=False)
    generated_at = Column(DateTime, nullable=True)
    dump_requested_at = Column(Text, nullable=True)
    usercourse = relationship('UserCourse')
    course = relationship('Course')

    @classmethod
    def get_certificate_by_id(cls, session, id):
        return session.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_certificate_of_user(cls, session, usercourse_id):
        return session.query(cls).filter(cls.usercourse_id == usercourse_id).first()

    @classmethod
    def get_todays_certificates(cls, session):
        return session.query(cls).filter(func.Date(cls.created_at) == datetime.today()).all()

    def update_certificate_request(self, session, requested_at):
        self.requested_at = requested_at
        self.dump_requested_at = f"{self.dump_requested_at},,,{requested_at}"
        session.add(self)
        try:
            session.commit()
            return self
        except:
            session.rollback()
            return None

    def __repr__(self):
        return f"Certificate: id - {self.id}, filename - {self.filename}, usercourse_id - {self.usercourse_id}, requested_at - {self.requested_at}"

"""
class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    usercourse_id = Column(Integer, ForeignKey('usercourses.id'), unique=True, nullable=False)   # unique=True mandatory for one-one
    rzp_link_id = Column(String(255), nullable=False, unique=True)
    rzp_link_reference_id = Column(String(255), nullable=False, unique=True)
    rzp_link_short_url = Column(String(255), nullable=False, unique=True)
    amount = Column(Integer, nullable=False, unique=True)
    payment_made_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow())
    usercourse = relationship('UserCourse')

    def __repr__(self):
        return f"Payment Link Details: id - {self.id}, usercourse_id - {self.usercourse_id}, rzp_link_id - {self.rzp_link_id}, rzp_link_ref_id - {self.rzp_link_ref_id}, " \
               f"rzp_link_short_url - {self.rzp_link_short_url}, amount - {self.amount},created_at - {self.created_at}, payment_made_at - {self.payment_made_at}"
"""