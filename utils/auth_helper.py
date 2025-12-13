
def get_auth_headers(token: str) -> dict:
    """Create authorization header from token."""
    return {"Authorization": f"Bearer {token}"}