from fastapi import APIRouter, status

from app.schemas import DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document():
    pass


@router.get("/", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
def get_user_documents():
    pass


@router.get("/{id}", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
def get_document():
    pass


@router.put("/{id}", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def update_document():
    pass


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document():
    pass
