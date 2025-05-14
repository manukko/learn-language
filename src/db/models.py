import csv
import os
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, create_engine, text, Index
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, deferred
import env
from sqlalchemy.dialects import postgresql
from datetime import datetime

DATABASE_URL = env.POSTGRES_DB_URL
engine = create_engine(
    # DATABASE_URL, connect_args={"check_same_thread": False}, echo=True # for sqlite
    DATABASE_URL, echo=False # for postgres
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SUPPORTED_LANGUAGES = ["german", "italian"]


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
    source_word = Column(String, nullable=False)
    language = Column(String, nullable=False, index=True)
    frequency = Column(Integer, nullable=False)
    translations = relationship("WordTranslation", back_populates="word", cascade="all")
    __table_args__ = (
        Index('ix_unique_language_frequency', 'language', 'frequency', unique=True),
        Index('ix_unique_language_word', 'language', 'source_word', unique=True)
    )

class WordTranslation(Base):
    __tablename__ = "word_translations"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    word_id = Column(Integer, ForeignKey("words.id", ondelete="CASCADE"))
    translation = Column(String, nullable=False)
    word = relationship("Word", back_populates="translations")

class Game(Base):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    is_active = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    language = Column(String, nullable=False)
    n_words_to_guess = Column(Integer, nullable=False)
    n_correct_answers = Column(Integer, nullable=False, default=0, server_default=text('0'))
    n_vocabulary = Column(Integer, nullable=False)
    words = relationship("GameWords", back_populates="game", cascade="all")


class GameWords(Base):
    __tablename__ = "game_words"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"))
    word_id = Column(Integer, ForeignKey("words.id", ondelete="CASCADE"))
    game = relationship("Game", back_populates="words")
    word = relationship("Word")


class Stat(Base):
    __tablename__ = "stats"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    word_id = Column(Integer, ForeignKey("words.id", ondelete="CASCADE"))
    n_appearances = Column(Integer, nullable=False)
    n_correct_answers = Column(Integer, nullable=False)
    user = relationship("User")
    word = relationship("Word")

def init_db():
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    import_csvs_to_db()
    print("Database is ready.")

def import_csvs_to_db(db=SessionLocal()):
        for language in SUPPORTED_LANGUAGES:
            result = db.query(Word).filter(Word.language == language).limit(1).first()
            if not result:
                print(f"No words present in Word table for language {language}: importing words from csvs...")
                csv_file = f"{os.path.dirname(os.path.abspath(__file__))}/csv/{language}.csv"
                with open(csv_file, mode='r', encoding='utf-8') as file:
                    csv_reader = csv.DictReader(file)
                    for row in csv_reader:
                        source_word = row['Word']
                        word = db.query(Word).filter(Word.source_word == source_word).first()
                        if word is None:
                            word = Word(
                                source_word=source_word,
                                language=language,
                                frequency=int(row['Frequency'])
                            )
                        db.add(word)
                        db.commit()
                        db.refresh(word)
                        translation = WordTranslation(
                            translation=row['Translation'],
                            word_id=word.id
                        )
                        db.add(translation)
                        db.commit()
                print(f"Data imported successfully for language: {language}!")

if __name__=="__main__":
    init_db()