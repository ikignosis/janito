#!/usr/bin/env python3
"""
List OneDrive Files Tool - A class-based tool for listing files and folders in OneDrive.

This tool uses Microsoft Graph API to list files and folders in OneDrive.
Authentication is done using device code flow.
"""

import re
from typing import Any

from ...tooling import BaseTool
from ...tooling.decorator import tool


@tool(permissions="r")
class ListOneDriveFiles(BaseTool):
    """
    Tool for listing files and folders in OneDrive.

    Uses Microsoft Graph API to browse OneDrive storage.
    Requires authentication via device code flow.

    Required Secrets:
        - azure_client_id: Your Azure AD application client ID
        - azure_access_token: (auto-managed) Current access token
        - azure_refresh_token: (auto-managed) Refresh token

    Graph API Reference:
        https://docs.microsoft.com/en-us/graph/api/driveitem-listchildren

    Usage:
        # First authenticate:
        janito --set-secret azure_client_id=your-client-id
        janito --onedrive-auth

        # Then list files:
        janito --onedrive "List my Documents folder"
    """

    def _fetch_items(
        self, client, endpoint: str, params: dict, limit: int, folder_only: bool
    ) -> list:
        """Fetch items from Graph with pagination; returns the item list."""
        all_items = []
        next_link = None

        while True:
            if next_link:
                # Use next link for pagination
                response = client._make_request(
                    method="GET",
                    endpoint=next_link.replace(client.GRAPH_BASE_URL, ""),
                    timeout=30,
                )
            else:
                response = client._make_request(
                    method="GET", endpoint=endpoint, params=params, timeout=30
                )

            items = response.get("value", [])

            # Filter for folders only if requested
            if folder_only:
                items = [item for item in items if "folder" in item]

            all_items.extend(items)

            # Check for pagination
            next_link = response.get("@odata.nextLink")
            if not next_link or len(all_items) >= limit:
                break

        # Truncate if we got more than limit
        if len(all_items) > limit:
            all_items = all_items[:limit]
        return all_items

    @staticmethod
    def _format_item(item: dict) -> dict:
        """Format a drive item for cleaner output."""
        formatted = {
            "id": item.get("id"),
            "name": item.get("name"),
            "type": "folder" if item.get("folder") else "file",
            "size": item.get("size"),
            "created": item.get("createdDateTime"),
            "modified": item.get("lastModifiedDateTime"),
            "web_url": item.get("webUrl"),
        }

        if item.get("folder"):
            formatted["child_count"] = item.get("folder", {}).get("childCount")

        if item.get("file"):
            formatted["mime_type"] = item.get("file", {}).get("mimeType")

        if item.get("parentReference"):
            parent_path = item["parentReference"].get("path", "")
            # Handle both /me/drive/root: and /users/{userId}/drive/root: formats
            parent_path = parent_path.replace("/me/drive/root:", "")
            parent_path = re.sub(r"^/users/[^/]+/drive/root:", "", parent_path)
            formatted["parent_path"] = parent_path or "/"

        return formatted

    def run(
        self,
        path: str = "",
        limit: int = 50,
        order_by: str = "name",
        folder_only: bool = False,
    ) -> dict[str, Any]:
        """
        List files and folders in OneDrive.

        Args:
            path (str): Folder path to list (default: root folder)
                        Use format "folder/subfolder"
            limit (int): Maximum number of items to return (default: 50, max: 999)
            order_by (str): Sort order - "name", "name desc", "lastModifiedDateTime",
                           "lastModifiedDateTime desc", "size", "size desc" (default: "name")
            folder_only (bool): If True, only list folders (default: False)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'path': the folder path that was listed
                - 'items': list of file/folder dictionaries with metadata
                - 'total_count': number of items found
                - 'error': error message if operation failed (only present if success=False)
        """
        try:
            from .base_client import OneDriveBaseClient

            self.report_start(
                f"\ud83d\udcc1 Listing files in OneDrive path: {path or 'root'}"
            )

            client = OneDriveBaseClient()

            # Build the endpoint
            endpoint = client._get_drive_children_endpoint(path)

            # Build query parameters
            params = {
                "$top": min(limit, 999),
                "$orderby": order_by,
                "$select": "id,name,file,folder,size,createdDateTime,lastModifiedDateTime,webUrl,parentReference",
            }

            self.report_progress(" Fetching file list from Microsoft Graph...")

            all_items = self._fetch_items(client, endpoint, params, limit, folder_only)

            # Format items for cleaner output
            formatted_items = [self._format_item(item) for item in all_items]

            self.report_result(
                f"Found {len(formatted_items)} items in {path or 'root'}"
            )

            return {
                "success": True,
                "path": path or "/",
                "items": formatted_items,
                "total_count": len(formatted_items),
                "order_by": order_by,
            }

        except ValueError as e:
            self.report_error(str(e))
            return {"success": False, "error": str(e), "path": path or "/"}
        except Exception as e:
            self.report_error(f"Failed to list files: {e!s}")
            return {
                "success": False,
                "error": f"Failed to list files: {e!s}",
                "path": path or "/",
            }
