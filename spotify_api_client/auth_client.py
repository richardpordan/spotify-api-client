"""Handles API authentication."""

import base64
import hashlib
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from secrets import choice
from string import ascii_uppercase
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from dotenv import load_dotenv

from spotify_api_client.logger_setup import setup_logger

logger = setup_logger(__name__)

load_dotenv()


class MissingEnvVarsError(Exception):
    """Required env vars not found."""

    pass


class ExpiredOrNoRefreshTokenError(Exception):
    """Valid refresh token not found."""

    pass


class SpotifyAuthClient:
    """Handles API authentication."""

    SCOPE = (
        "user-read-private "
        "user-read-email "
        "user-library-read "
        "user-library-modify "
        "user-follow-read "
        "user-follow-modify "
        "playlist-read-private "
        "playlist-modify-private "
        "playlist-modify-public"
    )

    def __init__(self):
        """Initialise, read credentials and setup."""
        self._read_credentials()
        self.authorization_code = None
        self.refresh_token = None
        self.access_token = None

    def _read_credentials(self):
        """Read Spotify app credentials from env vars."""
        self.client_id = os.getenv("SPOTIFY_API_CLIENT_ID", None)
        self.client_secret = os.getenv("SPOTIFY_API_CLIENT_SECRET", None)
        self.redirect_uri = os.getenv("SPOTIFY_API_REDIRECT_URI", None)

        if (
            self.client_id is None
            or self.client_secret is None
            or self.redirect_uri is None
        ):
            raise MissingEnvVarsError(
                """One of the following environment variables is missing:
                SPOTIFY_API_CLIENT_ID
                SPOTIFY_API_CLIENT_SECRET
                SPOTIFY_API_REDIRECT_URI
                """
            )

        self.credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

    def _generate_random_string(self, length: int = 16) -> str:
        """Generate random string on given length.

        Args:
            length (int, optional): Length of string to generate.
                Defaults to 16.

        Returns:
            str: Random string.

        """
        return "".join(choice(ascii_uppercase) for i in range(length))

    def _refresh_token_path(self) -> Path:
        """Return the path of the refresh token.

        Returns:
            Path: Path of the refresh token.

        """
        cache_dir = Path.home() / ".spotify_api_client"
        cache_dir.mkdir(exist_ok=True, parents=True)

        filename = hashlib.sha256(self.client_id.encode()).hexdigest()

        return cache_dir / filename

    def _save_refresh_token(self) -> None:
        """Write the refresh token."""
        token_path = self._refresh_token_path()
        with token_path.open(mode="w") as f:
            f.write(self.refresh_token)

        logger.info("Saving refresh token to %s", token_path)

    def _load_refresh_token(self) -> str:
        """Load cached refresh token.

        Raises:
            ExpiredOrNoRefreshTokenError: Refresh token not found.

        Returns:
            str : API refresh token.

        """
        token_path = self._refresh_token_path()

        logger.info("Loading refresh token from %s", token_path)

        if not token_path.is_file:
            raise ExpiredOrNoRefreshTokenError(
                "Valid refresh token not found. call .get_initial_tokens()."
            )
        with token_path.open(mode="r") as f:
            return f.read().strip()

    def get_authorization_code(self):
        """Get authorization code from API."""
        auth_params = {
            "response_type": "code",
            "client_id": self.client_id,
            "scope": self.SCOPE,
            "redirect_uri": self.redirect_uri,
            "state": self._generate_random_string(),
        }
        url = (
            f"https://accounts.spotify.com/authorize?{urlencode(auth_params)}"
        )
        webbrowser.open(url)

        client = self

        class AuthCallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                query = parse_qs(urlparse(self.path).query)
                client.authorization_code = query.get("code", [None])[0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(
                    b"Authorization complete. You can close this tab."
                )

        server = HTTPServer(("localhost", 8888), AuthCallbackHandler)
        server.handle_request()

    def get_initial_tokens(self) -> httpx.Response.status_code:
        """After authorization, gets the initial refresh and access tokens.

        Returns:
            httpx.Response.status_code: Request response status code.

        """
        if self.authorization_code is None:
            self.get_authorization_code()

        response = httpx.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Authorization": f"Basic {self.credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": self.authorization_code,
                "redirect_uri": self.redirect_uri,
            },
        )

        tokens = response.json()
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]

        self._save_refresh_token()

        return response.status_code

    def refresh_access_token(self) -> httpx.Response.status_code:
        """Refresh the access token using the refresh token.

        Returns:
            httpx.Response.status_code: Request response status code.

        """
        self.refresh_token = self._load_refresh_token()

        response = httpx.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Authorization": f"Basic {self.credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )

        self.access_token = response.json()["access_token"]

        return response.status_code
