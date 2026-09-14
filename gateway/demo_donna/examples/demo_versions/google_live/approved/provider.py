"""Versao inicialmente aprovada do provedor Google."""

from donna_mcp.providers.google import GoogleProvider


class ActiveGoogleProvider(GoogleProvider):
    """A atualizacao inicial nao altera o comportamento do provedor."""

    name = "live-google"
