import csv
import os
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, create_engine, text, Index, UniqueConstraint
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, deferred
import env
from sqlalchemy.dialects import postgresql
from datetime import datetime

DATABASE_URL = env.POSTGRES_DB_URL
engine = create_engine(
    # DATABASE_URL, connect_args={"check_same_thread": False}, echo=True # for sqlite
    DATABASE_URL, echo=True # for postgres
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SUPPORTED_LANGUAGES = ["german", ]


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False, default="default_user")
    email = Column(String, unique=True, index=True, nullable=False, default="default@default.default")
    hashed_password = deferred(Column(String, nullable=False, default="default_password"))
    created_at = Column(postgresql.TIMESTAMP, default=datetime.now, nullable=False)
    updated_at = Column(postgresql.TIMESTAMP, default=datetime.now, nullable=False)
    is_verified = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    games = relationship("Game", cascade="all")
    # stats = relationship("Stat", back_populates="owner", cascade="all")

class Word(Base):
    __tablename__ = "words"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    translation = Column(String, nullable=False)
    language = Column(String, nullable=False, index=True)
    frequency = Column(Integer, nullable=False)
    __table_args__ = (
        Index('ix_unique_language_frequency', 'language', 'frequency', unique=True),
        Index('ix_unique_language_name', 'language', 'name', unique=True),
        UniqueConstraint('language', 'name', name='unique_language_name'),
    )

class Game(Base):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    is_active = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    language = Column(String, nullable=False)
    total_words_to_guess = Column(Integer, nullable=False)
    correct_words = Column(Integer, nullable=False, default=0, server_default=text('0'))
    vocabulary_size = Column(Integer, nullable=False)
    words = relationship("GameWords", back_populates="game", cascade="all")


class GameWords(Base):
    __tablename__ = "game_words"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"))
    word_id = Column(Integer, ForeignKey("words.id", ondelete="CASCADE"))
    game = relationship("Game", back_populates="words")
    word = relationship("Word")


""" class Stat(Base):
    __tablename__ = "stats"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(postgresql.TIMESTAMP, default=datetime.now, nullable=False)
    owner = relationship("User", back_populates="stats") """


def init_db():
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    import_csvs_to_db()
    print("Database is ready.")

def import_csvs_to_db(session=SessionLocal()):
    result = session.query(Word).limit(1).first()
    if not result:
        print("No words present in Word table: importing words from csvs...")
        for language in SUPPORTED_LANGUAGES:
            csv_file = f"{os.path.dirname(os.path.abspath(__file__))}/csv/{language}.csv"
            with open(csv_file, mode='r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    word_translation = Word(
                        name=row['Word'],
                        translation=row['Translation'],
                        language=language,
                        frequency=int(row['Frequency'])
                    )
                    session.add(word_translation)
        session.commit()
        print("Data imported successfully!")

if __name__=="__main__":
    init_db()