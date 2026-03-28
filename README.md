# spotify-api-client

> ***In development. Not maintained.***

Low-level DIY API client for Spotify.

Refer to [Web API | Spotify for Developers](https://developer.spotify.com/documentation/web-api).

## Features

Get and remove saved tracks from your Spotify.

## Usage

1. Create a spotify app with an arbitrary name. Save:

- Client id
- Client secret
- The chosen redirect uri (e.g. `http://127.0.0.1:8888/callback`)

2. Create a `.env` file in your current working directory with:

```
SPOTIFY_API_CLIENT_ID=<your_client_id>
SPOTIFY_API_CLIENT_SECRET=<your_client_secret>
SPOTIFY_API_REDIRECT_URI=<your_chosen_redirect_uri>
```

4. Install the project:

```bash
# Install a tag
uv pip install "git+https://github.com/richardpordan/spotify-api-client@main"
```

5. Example usage.

In the same directory where your `.env` file is or with the environment variables in (1) already loaded:

```py
from spotify_api_client.spotify_client import SpotifyClient


# Setup Client
sp_client = SpotifyClient()

# Initial auth
sp_client.auth.get_initial_tokens()

# Then to refresh the access token as required
sp_client.auth.refresh_access_token()

# Get a sample of saved tracks
sp_client.get_sample_saved_tracks()
```
