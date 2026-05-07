import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from notion_client import AsyncClient

# logger = logging.getLogger(__name__)


class NotionMovieProcessor:
    """Interact with the Notion API to fetch and update media entries."""

    def __init__(self, database_id: Optional[str] = None) -> None:
        """
        Initialize Notion client.

        :param api_key: The Notion API key.
        :param database_id: The ID of the database to interact with.
        """
        load_dotenv()

        notion_token = os.getenv("NOTION_TOKEN")
        if not notion_token:
            raise ValueError("NOTION_API_KEY environment variable is required.")
        try:
            self.notion = AsyncClient(auth=notion_token)
            self.database_id = database_id or os.getenv("DATABASE_ID")
        except ValueError as e:
            raise ValueError("Invalid Notion API key.") from e

    # TODO catch database_id and client not found exceptions
    def get_entries_to_update(
        self, title: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch entries with titles ending in semicolon, or for the given title."""

        query = {
            "database_id": self.database_id,
            "filter": {"property": "Title", "title": {"ends_with": ";"}},
        }

        if title:
            query["filter"]["title"] = {"equals": title}

        try:
            # Any is to silence pylance(reportAttributeAccessIssue) error
            response: Any = self.notion.databases.query(**query)
            return response.get("results", [])
        except Exception:
            # logger.error(f"Error querying database for entries: {e}", exc_info=True)
            return []

    # def update_page(self, page_id: str, data: Dict[str, Any]) -> None:
    #     """Update page properties with cleaned data."""

    #     self.client.pages.update(page_id=page_id, properties=data)

    #     # Set the icon and cover images
    #     self.client.pages.update(
    #         page_id=page_id,
    #         icon={"type": "external", "external": {"url": data.get("poster_path")}},
    #     )
    #     self.client.pages.update(
    #         page_id=page_id,
    #         cover={"type": "external", "external": {"url": data.get("backdrop_path")}},
    #     )
