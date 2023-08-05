from sqlalchemy import create_engine
# from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
# from models import User, Learning
from dotenv import load_dotenv
import os
load_dotenv()

db_host = os.environ.get('db_host')
db_user = os.environ.get('db_user')
db_password = os.environ.get('db_password')
db_name = os.environ.get('db_name')
# db_port = os.environ.get('db_port')


dbmode = os.environ.get("DBMODE", "sqlite")
if dbmode == 'mysql':
    db_url = f"mysql://{db_user}:{db_password}@{db_host}/{db_name}"
    engine = create_engine(f"{db_url}", pool_recycle=60)
else:
    engine = create_engine('sqlite:///test.db', echo=False)
    # with engine.connect() as con:
        # stmt = text("""ALTER TABLE QUESTIONS ADD COLUMN 'answer' 'text';""")
        # stmt = text("""ALTER TABLE questions ADD COLUMN answered_at datetime AFTER created_at;""")
        # con.execute(stmt)
        # q = con.execute("""SELECT * FROM QUESTIONS""")
        # quest = q.fetchall()
        # print(quest)


# sessionmkr = sessionmaker(bind=engine)
# session = sessionmkr()
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)
Base = declarative_base()
