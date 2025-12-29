from core import setup
from sqlalchemy.orm import Session


class CreateDBSession:
    def __init__(self):
        self.db_factory = setup.DatabaseSetup().get_session()
        self.session = None

    def __enter__(self) -> Session:
        self.session = self.db_factory()
        return self.session

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.session:
            if exc_type is not None:
                self.session.rollback()
            self.session.close()
