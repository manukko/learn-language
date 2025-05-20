import csv
import os
from typing import List
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, create_engine, text, Index
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, deferred, Mapped
import env
from sqlalchemy.dialects import postgresql
from datetime import datetime

DATABASE_URL = env.POSTGRES_DB_URL
engine = create_engine(
    DATABASE_URL, echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SUPPORTED_LANGUAGES = ["german", "italian"]
USER_LANGUAGE = "english" # TODO: expand with more user languages

class User(Base):
    """
    Represents a user of the application.

    Attributes:
        id (int): Primary key.
        username (str): Unique username of the user.
        email (str): Unique email address of the user.
        hashed_password (str): Hashed user password (deferred for lazy loading).
        created_at (datetime): Timestamp when the user was created.
        updated_at (datetime): Timestamp when the user was last updated.
        is_verified (bool): Whether the user's email is verified.
        games (List[Game]): Games associated with the user.
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False, default="default_user")
    email = Column(String, unique=True, index=True, nullable=False, default="default@default.default")
    hashed_password = deferred(Column(String, nullable=False, default="default_password"))
    created_at = Column(postgresql.TIMESTAMP, default=datetime.now, nullable=False)
    updated_at = Column(postgresql.TIMESTAMP, default=datetime.now, nullable=False)
    is_verified = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    games: Mapped[List["Game"]] = relationship("Game", cascade="all")

    def __repr__(self):
        return f"<User: username:{self.username}, id={self.id}>"

class Word(Base):
    """
    Represents a word in a specific language.

    Attributes:
        id (int): Primary key.
        text (str): The word text.
        language (str): The language of the word.
        associated_translations (List[WordTranslation]): List of word-to-word associations where current word figure as source word.
        associated_words (List[WordTranslation]): List of word-to-word associations where current word figure as translation.
    """
    __tablename__ = "words"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    text = Column(String, nullable=False)
    language = Column(String, nullable=False, index=True)
    associated_translations: Mapped[List["WordTranslation"]] = relationship("WordTranslation", foreign_keys="WordTranslation.word_id", back_populates="word", cascade="all")
    associated_words: Mapped[List["WordTranslation"]] = relationship("WordTranslation", foreign_keys="WordTranslation.translation_id", back_populates="translation", cascade="all")
    __table_args__ = (
        Index('ix_unique_language_text_word', 'language', 'text', unique=True),
    )

    def __repr__(self):
        return f"<Word: text:{self.text}, id={self.id}, translations={[word_translation.translation.text for word_translation in self.associated_translations]}>"

class WordTranslation(Base):
    """
    Association table mapping words to their translations.

    Attributes:
        id (int): Primary key.
        word_id (int): Foreign key to the Word.
        translation_id (int): Foreign key to the Translation.
        frequency (int): Frequency of usage or importance.
        word (Word): The source word.
        translation (Translation): The translated word.
    """
    __tablename__ = "word_translations"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    word_id = Column(Integer, ForeignKey("words.id", ondelete="CASCADE"))
    translation_id = Column(Integer, ForeignKey("words.id", ondelete="CASCADE"))
    frequency = Column(Integer, nullable=False, index=True)
    word: Mapped[Word] = relationship("Word", foreign_keys=[word_id], back_populates="associated_translations")
    translation: Mapped[Word]= relationship("Word", foreign_keys=[translation_id], back_populates="associated_words")

    def __repr__(self):
        return f"<WordTranslation: word:{self.word.text}, translation:{self.translation.text}, id={self.id}>"

class Game(Base):
    """
    Represents a game session for a user.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to the user who owns the game.
        is_active (bool): Whether the game is ongoing.
        language (str): Language used in the game.
        n_words_to_guess (int): Total number of words to guess.
        n_correct_answers (int): Number of correct answers given.
        n_vocabulary (int): Number of vocabulary words involved.
        words (List[GameWord]): Words associated with the game.
    """
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    is_active = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    language = Column(String, nullable=False)
    n_words_to_guess = Column(Integer, nullable=False)
    n_correct_answers = Column(Integer, nullable=False, default=0, server_default=text('0'))
    n_vocabulary = Column(Integer, nullable=False)
    words: Mapped[List["GameWord"]] = relationship("GameWord", back_populates="game", cascade="all")

    def __repr__(self):
        return (
            f"<Game: user_id:{self.user_id}, id={self.id}, "
            f"language={self.language}, n_words_left_to_guess={len(self.words)}>"
        )

class GameWord(Base):
    """
    Represents a word used in a specific game.

    Attributes:
        id (int): Primary key.
        game_id (int): Foreign key to the Game.
        word_id (int): Foreign key to the Word.
        game (Game): The associated game.
        word (Word): The associated word.
    """
    __tablename__ = "game_words"
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"))
    word_id = Column(Integer, ForeignKey("words.id", ondelete="CASCADE"))
    game: Mapped["Game"] = relationship("Game", back_populates="words")
    word: Mapped["Word"] = relationship("Word")

    def __repr__(self):
        return (
            f"<GameWord: id={self.id}, word={self.word.text}, "
            f"game_id:{self.game_id}, word_id:{self.word_id}>"
        )

class Stat(Base):
    """
    Tracks user performance on individual words.

    Attributes:
        id (int): Primary key.
        user_id (int): Foreign key to the user.
        word_id (int): Foreign key to the word.
        n_appearances (int): Number of times the word appeared.
        n_correct_answers (int): Number of times the user answered correctly.
        user (User): The associated user.
        word (Word): The associated word.
    """
    __tablename__ = "stats"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    word_id = Column(Integer, ForeignKey("words.id", ondelete="CASCADE"))
    n_appearances = Column(Integer, nullable=False)
    n_correct_answers = Column(Integer, nullable=False)
    user: Mapped[User] = relationship("User")
    word: Mapped[Word] = relationship("Word")

    def __repr__(self):
        return (
            f"<Stat: id={self.id}, username:{self.user.username}, word:{self.word.text}, "
            f"n_appearances:{self.n_appearances}, n_correct_answers:{self.n_correct_answers}>"
        )


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
                        word_text = row['Word']
                        word = db.query(Word).filter(Word.language == language).filter(Word.text == word_text).first()
                        if word is None:
                            word = Word(
                                text=word_text,
                                language=language
                            )
                            db.add(word)
                        translation_text = row['Translation']
                        translation = db.query(Word).filter(Word.language == USER_LANGUAGE).filter(Word.text == translation_text).first()
                        if translation is None:
                            translation = Word(
                                text=translation_text,
                                language=USER_LANGUAGE
                            )
                            db.add(translation)
                        db.commit()
                        db.refresh(word)
                        db.refresh(translation)
                        translation = WordTranslation(
                            word_id=word.id,
                            translation_id=translation.id,
                            frequency=int(row['Frequency'])
                        )
                        db.add(translation)
                        db.commit()
                print(f"Data imported successfully for language: {language}!")

if __name__=="__main__":
    init_db()