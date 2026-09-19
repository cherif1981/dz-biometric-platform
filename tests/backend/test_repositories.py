from app.repositories.document_repository import DocumentRepository
from app.repositories.user_repository import UserRepository


def test_user_repository_create_and_get(db):
    repo = UserRepository(db)
    u = repo.create(email="a@b.c", hashed_password="x")
    assert u.id is not None
    assert repo.get_by_email("a@b.c").id == u.id
    assert repo.get_by_email("missing@b.c") is None


def test_document_repository_create(db):
    repo = DocumentRepository(db)
    d = repo.create(filename="card.jpg", nin="123456789012345678")
    assert d.id is not None
    assert repo.get(d.id).filename == "card.jpg"