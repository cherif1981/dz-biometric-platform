from app.repositories.document_repository import DocumentRepository


class DocumentService:
    def __init__(self, repo: DocumentRepository):
        self.repo = repo

    def create(self, **kwargs):
        return self.repo.create(**kwargs)