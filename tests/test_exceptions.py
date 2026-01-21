class TestExceptions:
    """Test exception handling."""

    def test_user_already_exists_exception(self):
        """Test UserAlreadyExistsException."""
        from app.exceptions import UserAlreadyExistsException

        exc = UserAlreadyExistsException()
        assert exc.status_code == 400
        assert "already exists" in exc.message

    def test_user_not_found_exception(self):
        """Test UserNotFoundException."""
        from app.exceptions import UserNotFoundException

        exc = UserNotFoundException()
        assert exc.status_code == 404
        assert "not found" in exc.message

    def test_credentials_exception(self):
        """Test CredentialsException."""
        from app.exceptions import CredentialsException

        exc = CredentialsException()
        assert exc.status_code == 401
        assert exc.headers is not None

    def test_document_not_found_exception(self):
        """Test DocumentNotFoundException."""
        from app.exceptions import DocumentNotFoundException

        exc = DocumentNotFoundException()
        assert exc.status_code == 404

    def test_requires_role_exception(self):
        """Test RequiresRoleException."""
        from app.exceptions import RequiresRoleException

        exc = RequiresRoleException("admin")
        assert exc.status_code == 403
        assert "admin" in exc.message

    def test_insufficient_scopes_exception(self):
        """Test InsufficientScopesException."""
        from app.exceptions import InsufficientScopesException

        exc = InsufficientScopesException(required_scopes=["admin"], provided_scopes=["read"])
        assert exc.status_code == 403
        assert exc.details is not None
