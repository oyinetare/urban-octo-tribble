from abc import ABC, abstractmethod

from fastapi import UploadFile


class FileValidator(ABC):
    def __init__(self):
        self.next_validator: FileValidator | None = None

    def set_next(self, validator: "FileValidator"):
        self.next_validator = validator
        return validator

    async def validate(self, file: UploadFile) -> tuple[bool, str]:
        result, message = await self._validate(file)

        if not result:
            return False, message

        if self.next_validator:
            return await self.next_validator.validate(file)

        return True, "Valid"

    @abstractmethod
    async def _validate(self, file: UploadFile) -> tuple[bool, str]:
        pass


class FileSizeValidator(FileValidator):
    def __init__(self, max_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__()
        self.max_size = max_size

    async def _validate(self, file: UploadFile) -> tuple[bool, str]:
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(0)  # Reset

        if size > self.max_size:
            return False, f"File too large. Max: {self.max_size} bytes"
        return True, "Size OK"


class FileTypeValidator(FileValidator):
    def __init__(self, allowed_types: list[str]):
        super().__init__()
        self.allowed_types = allowed_types

    async def _validate(self, file: UploadFile) -> tuple[bool, str]:
        if file.content_type not in self.allowed_types:
            return False, f"Invalid file type. Allowed: {self.allowed_types}"
        return True, "Type OK"


class FileNameValidator(FileValidator):
    async def _validate(self, file: UploadFile) -> tuple[bool, str]:
        if not file.filename or len(file.filename) > 255:
            return False, "Invalid filename"
        return True, "Filename OK"


# Build validation chain
validator = FileSizeValidator(max_size=10 * 1024 * 1024)
validator.set_next(
    FileTypeValidator(
        [
            "application/pdf",
            "text/plain",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
    )
).set_next(FileNameValidator())
