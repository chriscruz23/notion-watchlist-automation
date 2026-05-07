import os

from dotenv import load_dotenv

from results_exceptions import NoEntriesFoundException
from utils import NotionHandler, TMDBHandler

# Load environment variables from .env file
load_dotenv()

# Constants
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")

# Language codes
# with open("utils/iso_639_1_languages.json", "r") as json_file:
#     iso_639_1_languages = json.load(json_file)

# Initialize Notion client and TMDB API
notion = NotionHandler(NOTION_API_KEY, DATABASE_ID)
tmdb = TMDBHandler(TMDB_API_KEY)

entries = notion.get_entries_to_update()

[
    entry["properties"]["Title"]["title"][0]["plain_text"].rstrip(";")
    for entry in entries
]


def update_notion_entries(
    notion_handler: NotionHandler, tmdb_handler: TMDBHandler, title: str | None = None
) -> None:
    """
    Update Notion entries with cleaned data from TMDb.

    :param notion_handler: Notion client
    :param tmdb_handler: TMDB client
    :param title: Optional title to search for
    """
    entries = notion_handler.get_entries_to_update(title=title)
    if not entries:
        raise NoEntriesFoundException("No entries found in Notion.")

    titles = [
        entry["properties"]["Title"]["title"][0]["plain_text"].rstrip(";")
        for entry in entries
    ]
    page_ids = [entry["id"] for entry in entries]

    results = tmdb_handler.search_media(titles)
    for i, page_id in enumerate(page_ids):
        title = titles[i]
        try:
            # Use the first result for now; a GUI could allow selection from search_results.
            tmdb_result = next(
                (result for result in results if result["title"] == title), None
            )
            if tmdb_result is None:
                print(f"No TMDb results found for title {title}.")
                continue
            media_type = tmdb_result.get("media_type")
            raw_data = tmdb_handler.fetch_media_details(tmdb_result)
            cleaned_data = tmdb_handler.clean_media_data(raw_data, media_type)
            notion_handler.update_page(page_id, cleaned_data)
        except ValueError as e:
            print(f"Failed to update page {page_id}: {e}")


update_notion_entries(notion, tmdb)
print(json.dumps(tmdb.test_clean_media_data(), indent=4))

search_results = tmdb.search_media("The Longest Yard")

if not search_results:
    raise ValueError("No TMDb results found for the title.")

# Use the first result for now; a GUI could allow selection from search_results.
tmdb_result = search_results[0]
media_type = tmdb_result.get("media_type")

# Fetch detailed data and clean it
raw_data = tmdb.fetch_media_details(tmdb_result)
cleaned_data = tmdb.clean_media_data(raw_data, media_type)
print(json.dumps(cleaned_data, indent=4))

# print(search_results)
