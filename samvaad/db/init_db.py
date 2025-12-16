from dotenv import load_dotenv
load_dotenv()

from samvaad.db.session import engine
from samvaad.db.models import Base

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    init_db()
