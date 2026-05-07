import json
import logging
from typing import List

import requests

# import TMDB_API
import tmdbsimple
from tmdbsimple import TV, Movies, Search

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),  # Logs to console
        logging.FileHandler("logs/notion.log"),  # Logs to a file
    ],
)

# Initialize a logger for the module
logger = logging.getLogger(__name__)


class TMDBHandler:
    def __init__(self, api_key: str | None) -> None:
        """
        Initialize the TMDBHandler with the given API key.

        :param api_key: The API key to use for the TMDb API.
        :raises ValueError: If the API key is invalid.
        """
        tmdbsimple.API_KEY = api_key

        try:
            test_search = Search()
            test_search.multi(query=19995)
            logger.info("TMDBHandler initialized successfully.")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to TMDb API: {e}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Invalid API key provided for TMDBHandler: {api_key}")
            raise ValueError(
                f"Invalid API key provided for TMDBHandler: {api_key}"
            ) from e

    def search_media(self, title: str | List[str]):
        """
        Search TMDb for a given title, which could be a movie or TV show.
        Returns a list of search results.
        """
        try:
            search = Search()
            response = search.multi(query=title)
            results = response.get("results", [])
            if not results:
                logger.warning(f"No results found for title: '{title}'")
            else:
                logger.info(f"Found {len(results)} result(s) for title: '{title}'")
            return results
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error searching for title '{title}': {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.error(f"Error searching for title '{title}': {e}", exc_info=True)
            raise

    # FIXME This only works with movies right now
    def fetch_media_details(self, tmdb_result):
        """
        Fetch detailed data for a specific media item, whether it's a movie or TV show.
        """
        try:
            media_type = tmdb_result.get("media_type")
            media_id = tmdb_result.get("id")

            if media_type == "movie":
                media = Movies(media_id)
            elif media_type == "tv":
                media = TV(media_id)
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

            raw_data = media.info(
                append_to_response=["watch/providers,credits,release_dates,videos"]
            )
            logger.info(f"Fetched details for {media_type} with ID {media_id}")
            return raw_data

        except ValueError:
            logger.error(f"Error with media type: {media_type}", exc_info=True)
        except AttributeError:
            logger.error(f"Error with tmdb result: {tmdb_result}", exc_info=True)
            raise
        except Exception:
            logger.error(f"Error fetching info for media ID {media_id}", exc_info=True)
            raise

    @staticmethod
    def _get_watch_providers(data, country_code="US"):
        providers = (
            data.get("watch/providers", {}).get("results", {}).get(country_code, {})
        )

        streaming = []
        watch_free = []

        # Extract provider names from 'flatrate' and 'buy' if they exist
        if "flatrate" in providers:
            streaming = [
                {"name": item["provider_name"]} for item in providers["flatrate"]
            ]

        if "free" in providers:
            watch_free = [{"name": item["provider_name"]} for item in providers["free"]]

        return {"streaming": streaming, "watch_free": watch_free}

    def clean_media_data(self, tmdb_data, media_type):
        # Extract and format desired TMDb fields

        if media_type == "movie":
            # Media type
            tmdb_data["type"] = media_type.capitalize()

            # TMDB rating
            if tmdb_data.get("vote_average"):
                tmdb_data["tmdb_rating"] = round(tmdb_data.pop("vote_average"), 1)

            # Directors, producers, and main actors
            for key in tmdb_data["credits"]:
                if key == "crew":  # Directors and producers are here
                    for member in tmdb_data["credits"][key]:
                        if member["job"] == "Director":
                            tmdb_data.setdefault("directors", []).append(member["name"])
                        elif member["job"] == "Producer":
                            tmdb_data.setdefault("producers", []).append(member["name"])
                elif key == "cast":  # Actors are here
                    for member in tmdb_data["credits"][key]:
                        if (
                            member["known_for_department"] == "Acting"
                            and "(uncredited)" not in member["character"]
                        ):  # Find only well-known actors
                            tmdb_data.setdefault("cast", []).append(
                                {
                                    "name": member["name"],
                                    "popularity": member["popularity"],
                                }
                            )

            tmdb_data["directors"] = ", ".join(tmdb_data.get("directors"))
            tmdb_data["producers"] = ", ".join(tmdb_data.get("producers"))
            # Sort actors from most popular to least
            tmdb_data["cast"] = [
                d["name"]
                for d in sorted(
                    tmdb_data["cast"], key=lambda x: x["popularity"], reverse=True
                )
            ]
            tmdb_data["cast"] = ", ".join(tmdb_data.get("cast")[:15])

            # Genres
            tmdb_data["genres"] = [
                {"name": genre["name"]} for genre in tmdb_data.get("genres", [])
            ]

            # # Streaming providers
            # for provider in (
            #     tmdb_data.get("watch/providers", {})
            #     .get("results", {})
            #     .get("US", {})
            #     .get("flatrate", [])
            # ):
            #     if provider:
            #         tmdb_data["streaming"] = [
            #             {"name": provider["provider_name"]}
            #             for provider in tmdb_data.get("watch/providers", {})
            #             .get("results", {})
            #             .get("US", {})
            #             .get("flatrate", [])
            #         ]

            # # Watch free
            # for provider in (
            #     tmdb_data.get("watch/providers", {})
            #     .get("results", {})
            #     .get("US", {})
            #     .get("free", [])
            # ):
            #     if provider:
            #         tmdb_data["watch_free"] = [
            #             {"name": provider["provider_name"]}
            #             for provider in tmdb_data.get("watch/providers", {})
            #             .get("results", {})
            #             .get("US", {})
            #             .get("free", [])
            #         ]

            # Official trailer
            # TODO Prioritize official trailers

            trailers = []
            for trailer in tmdb_data["videos"]["results"]:
                if (
                    trailer["type"] == "Trailer"
                    and trailer["site"] == "YouTube"
                    and trailer["iso_3166_1"] == "US"
                ):
                    trailers.append(trailer)

            if trailers:
                tmdb_data["trailer_url"] = (
                    f"https://www.youtube.com/watch?v={max(trailers, key=lambda x: x['size'])['key']}"
                )
            else:
                tmdb_data["trailer_url"] = None

            # IMDB page
            tmdb_data["imdb_url"] = (
                f"https://www.imdb.com/title/{tmdb_data.get('imdb_id')}/"
                if tmdb_data.get("imdb_id")
                else None
            )

            # Country of origin
            # TODO change origin country to full country name
            tmdb_data["origin_country"] = (
                tmdb_data.get("origin_country")[0]
                if tmdb_data.get("origin_country")
                else None
            )

            # Content rating
            if tmdb_data.get("release_dates"):
                for result in tmdb_data["release_dates"]["results"]:
                    if result["iso_3166_1"] == "US":
                        for date in result["release_dates"]:
                            if date["type"] == 1:
                                tmdb_data["content_rating"] = date["certification"]

            # # Episode count
            # tmdb_data['episodes'] = tmdb_data.pop('number_of_episodes', None)

            # # Season count
            # tmdb_data['seasons'] = tmdb_data.pop('number_of_seasons', None)

            # Writer
            # "Writer": {"rich_text": [{"text": {"content": data.get("writer")}}]},

            # Last episode
            # "Last Episode": {"rich_text": [{"text": {"content": data.get("last_episode")}}]},

            # Upcoming episode
            # "Upcoming Episode": {"rich_text": [{"text": {"content": data.get("upcoming_episode")}}]},

            # Last air date
            # "Last Air Date": {"date": {"start": data.get("last_air_date")}},

            # Next air date
            # "Next Air Date": {"date": {"start": data.get("next_air_date")}},

            # Production status
            # tmdb_data["status"] = tmdb_data.pop("status", None)

            # Original language
            # FIXME use tmdb's internal languages instead
            # tmdb_data['original_language'] = iso_639_1_languages[tmdb_data.get('original_language', '')]

            # Original title
            tmdb_data["original_title"] = (
                tmdb_data.get("original_title")
                if tmdb_data.get("original_title", "") != tmdb_data.get("title")
                else None
            )

            # Backdrop and poster paths
            base_url = "https://image.tmdb.org/t/p/original"
            if tmdb_data.get("poster_path"):
                tmdb_data["poster_path"] = base_url + tmdb_data["poster_path"]
            if tmdb_data.get("backdrop_path"):
                tmdb_data["backdrop_path"] = base_url + tmdb_data["backdrop_path"]

        elif media_type == "tv":
            pass

        return self._filter_tmdb_data(tmdb_data, keep_nulls=True)

    @staticmethod
    def _filter_tmdb_data(tmdb_data, keep_nulls=False):
        # 22 keys
        allowed_keys = [
            "title",
            "type",
            "tagline",
            "tmdb_rating",
            "directors",
            "producers",
            "genres",
            "runtime",
            "streaming",
            "watch_free",
            "trailer_url",
            "imdb_url",
            "overview",
            "release_date",
            "cast",
            "origin_country",
            "content_rating",
            "poster_path",
            "status",
            "original_language",
            "original_title",
            "backdrop_path",
        ]
        for key in list(tmdb_data.keys()):
            if not keep_nulls and tmdb_data[key] is None:
                del tmdb_data[key]
            elif key not in allowed_keys:
                del tmdb_data[key]
        return tmdb_data

    def get_cleaned_media_data(self, title: str):
        """
        Searches for media by title and returns cleaned data of the first result.
        """
        search_results = self.search_media(title)

        if not search_results:
            raise ValueError("No TMDb results found for the title.")

        # Use the first result for now; a GUI could allow selection from search_results.
        tmdb_result = search_results[0]
        media_type = tmdb_result.get("media_type")

        # Fetch detailed data and clean it
        raw_data = self.fetch_media_details(tmdb_result)
        cleaned_data = self.clean_media_data(raw_data, media_type)

        print(search_results)

        # return cleaned_data

    def test_clean_media_data(self):
        with open("scratch/the_dark_knight.json", "r") as f:
            tmdb_data = json.load(f)

        # Assuming you want to test with "movie" media type
        media_type = "movie"

        cleaned_data = self.clean_media_data(tmdb_data, media_type)

        # You can add assertions or print statements here to verify the output
        return cleaned_data
