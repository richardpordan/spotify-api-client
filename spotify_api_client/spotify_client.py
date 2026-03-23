"""Main Spotify API Client class."""

import time
from math import ceil

import httpx

from spotify_api_client.auth_client import SpotifyAuthClient
from spotify_api_client.logger_setup import setup_logger

HIT_LIMIT_CODE = 429

logger = setup_logger(__name__)


class RequestError(Exception):
    """Generic but expected error with a request."""

    pass


class RequestTypeNotImplementedError(Exception):
    """Type of request not implemented in package."""

    pass


class SpotifyClient:
    """Main Spotify API Client class."""

    def __init__(self):
        """Initialise, create auth backend client, set debug mode."""
        self.auth = SpotifyAuthClient()
        self.debug_mode = False

    def _httpx_request(
        self, type: str, base_url: str, params: dict[str, str] | None = None
    ) -> httpx.Response:
        """Request wrapper for all calls.

        Implements error handling, checks.

        Args:
            type (str): Types of request allowed and implemented.
            base_url (str): API endpoint URL.
            params (dict[str, str] | None, optional): Request parameters dict.
                Defaults to None.

        Raises:
            RequestTypeNotImplementedError: Request type not supported.
            RequestError: Generic but expected and gracefully handled
                exception with a request.

        Returns:
            httpx.Response: _description_

        """
        if type not in ["GET", "DELETE"]:
            raise RequestTypeNotImplementedError(
                "type must be one of GET or DELETE"
            )

        request = httpx.Request(
            type,
            base_url,
            headers={"Authorization": f"Bearer {self.auth.access_token}"},
            params=params,
        )

        if self.debug_mode:
            logger.info("Sending %s", request.url)

        with httpx.Client() as client:
            response = client.send(request)

        if response.status_code != httpx.codes.OK:
            if response.status_code == HIT_LIMIT_CODE:
                retry_after = int(response.headers.get("Retry-After", 1))
                error_message = (
                    f"{response.status_code}: {response.text}, "
                    f"retry after {retry_after}"
                )
            else:
                error_message = f"{response.status_code}: {response.text}"
            raise RequestError(error_message)

        return response

    def _get_request(
        self, base_url: str, params: dict[str, str] | None = None
    ) -> httpx.Response:
        """GET request wrapper.

        Args:
            base_url (str): API endpoint URL.
            params (dict[str, str] | None, optional): Request parameters dict.
                Defaults to None.

        Returns:
            httpx.Response: _description_

        """
        return self._httpx_request(
            type="GET",
            base_url=base_url,
            params=params,
        )

    def _del_request(
        self, base_url: str, params: dict[str, str] | None = None
    ) -> httpx.Response:
        """DELETE request wrapper.

        Args:
            base_url (str): API endpoint URL.
            params (dict[str, str] | None, optional): Request parameters dict.
                Defaults to None.

        Returns:
            httpx.Response: _description_

        """
        return self._httpx_request(
            type="DELETE",
            base_url=base_url,
            params=params,
        )

    def get_me(self) -> httpx.Response:
        """Get current user details.

        Returns:
            httpx.Response: JSON of response.

        """
        response = self._get_request(base_url="https://api.spotify.com/v1/me")

        return response.json()

    def get_sample_saved_tracks(self) -> httpx.Response:
        """Get a sample of saved tracks.

        Returns:
            httpx.Response: JSON of response.

        """
        response = self._get_request(
            base_url="https://api.spotify.com/v1/me/tracks",
        )

        return response.json()

    def get_saved_tracks(self) -> list[dict]:
        """Get all saved tracks in library of current user.

        Returns:
            list[dict]: List of saved tracks.

        """
        n_per_page = 50

        start_response = self.get_sample_saved_tracks()
        total_tracks = start_response["total"]
        max_requests = ceil(total_tracks / n_per_page)

        logger.info(
            "Getting total tracks: %s with max requests: %s",
            total_tracks,
            max_requests,
        )

        tracks = []
        request_url = "https://api.spotify.com/v1/me/tracks"
        params = {"limit": n_per_page, "offset": 0}

        for page_request in range(0, max_requests):
            if page_request != 0:
                time.sleep(1)
            logger.info("Reading page %s", page_request)
            response = self._get_request(base_url=request_url, params=params)
            data = response.json()
            tracks.extend(data["items"])
            request_url = data["next"]
            params = None

        return tracks

    def remove_saved_tracks(
        self, track_ids: list[str]
    ) -> list[httpx.Response.status_code]:
        """Remove the tracks with given ids from current user library.

        Remove up to 40 tracks per call via the /me/library endpoint,
            from the current users library.

        Args:
            track_ids (list[str]): List of ids. (Given by .get_save_tracks())

        Returns:
            list[httpx.Response.status_code]: List of status codes
                for each batch request.

        """
        n_per_page = 40
        responses = []
        for i in range(0, len(track_ids), n_per_page):
            if i != 0:
                time.sleep(1)
            logger.info("Deleting %s to %s", i, i + n_per_page)
            batch = track_ids[i : i + n_per_page]

            uris = ",".join(f"spotify:track:{track_id}" for track_id in batch)

            response = self._del_request(
                base_url="https://api.spotify.com/v1/me/library",
                params={"uris": uris},
            )

            responses.append(response.status_code)

        return responses
