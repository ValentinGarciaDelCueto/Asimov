"""Google Drive client — OAuth user flow (Installed App)."""

from __future__ import annotations

import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
ROOT_FOLDER_NAME = "Resumenes UNO"


class DriveClient:
    def __init__(self, service):
        self._svc = service
        self._folder_cache: dict[str, str] = {}

    @classmethod
    def from_oauth(
        cls,
        credentials_json: Path,
        token_json: Path,
    ) -> "DriveClient":
        """
        Build a DriveClient using OAuth user credentials.
        On first run, opens a local browser window for the user to approve.
        Subsequent runs use the cached token.json.
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as e:
            raise ImportError(
                f"Dependencias de Drive no instaladas: {e}\n"
                "Ejecutá: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            ) from e

        creds = None

        if token_json.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_json), SCOPES)
            except Exception:
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds:
                if not credentials_json.exists():
                    raise FileNotFoundError(
                        f"No se encontró credentials.json en {credentials_json}\n"
                        "Descargalo desde GCP Console → APIs y servicios → Credenciales → "
                        "Crear credencial → ID de cliente OAuth → Desktop app"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_json), SCOPES)
                creds = flow.run_local_server(port=0)

            token_json.write_text(creds.to_json(), encoding="utf-8")
            logger.info(f"Token de Drive guardado en {token_json}")

        service = build("drive", "v3", credentials=creds)
        logger.info("Conectado a Google Drive")
        return cls(service)

    def ensure_root_folder(self, name: str = ROOT_FOLDER_NAME) -> str:
        """Find or create the root folder in Drive. Returns folder ID."""
        if name in self._folder_cache:
            return self._folder_cache[name]

        result = (
            self._svc.files()
            .list(
                q=f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id, name)",
                spaces="drive",
            )
            .execute()
        )
        files = result.get("files", [])
        if files:
            folder_id = files[0]["id"]
        else:
            meta = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            folder = self._svc.files().create(body=meta, fields="id").execute()
            folder_id = folder["id"]
            logger.info(f"Carpeta Drive creada: '{name}' (id={folder_id})")

        self._folder_cache[name] = folder_id
        return folder_id

    def ensure_subject_folder(self, parent_id: str, subject: str) -> str:
        """Find or create a subfolder for subject inside parent_id. Returns folder ID."""
        cache_key = f"{parent_id}/{subject}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        result = (
            self._svc.files()
            .list(
                q=(
                    f"name='{subject}' and "
                    f"mimeType='application/vnd.google-apps.folder' and "
                    f"'{parent_id}' in parents and trashed=false"
                ),
                fields="files(id, name)",
                spaces="drive",
            )
            .execute()
        )
        files = result.get("files", [])
        if files:
            folder_id = files[0]["id"]
        else:
            meta = {
                "name": subject,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }
            folder = self._svc.files().create(body=meta, fields="id").execute()
            folder_id = folder["id"]
            logger.info(f"Subcarpeta Drive creada: '{subject}'")

        self._folder_cache[cache_key] = folder_id
        return folder_id

    def file_exists(self, parent_id: str, name: str) -> str | None:
        """Return file ID if a file with this name exists in parent_id, else None."""
        result = (
            self._svc.files()
            .list(
                q=f"name='{name}' and '{parent_id}' in parents and trashed=false",
                fields="files(id)",
                spaces="drive",
            )
            .execute()
        )
        files = result.get("files", [])
        return files[0]["id"] if files else None

    def upload_markdown_as_doc(
        self,
        markdown: str,
        name: str,
        parent_id: str,
    ) -> str:
        """
        Upload markdown text as a Google Doc (Drive converts it automatically).
        Returns the created file's Drive ID.
        """
        from googleapiclient.http import MediaIoBaseUpload

        doc_name = name if name.endswith(".gdoc") else name
        # Strip .gdoc extension for Drive — it uses its own MIME type
        display_name = doc_name.removesuffix(".gdoc")

        existing_id = self.file_exists(parent_id, display_name)
        if existing_id:
            logger.info(f"Ya existe en Drive: '{display_name}' ({existing_id})")
            return existing_id

        media = MediaIoBaseUpload(
            io.BytesIO(markdown.encode("utf-8")),
            mimetype="text/markdown",
            resumable=False,
        )
        meta = {
            "name": display_name,
            "mimeType": "application/vnd.google-apps.document",
            "parents": [parent_id],
        }
        file = (
            self._svc.files()
            .create(body=meta, media_body=media, fields="id")
            .execute()
        )
        file_id = file["id"]
        logger.info(f"Subido a Drive: '{display_name}' ({file_id})")
        return file_id
