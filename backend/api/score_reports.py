"""Score report import: pull the tables and graphs out of an uploaded Word/PDF file."""
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from services.score_report_extractor import ScoreReportError, extract_score_report

router = APIRouter()

MAX_UPLOAD_BYTES = 40 * 1024 * 1024
CHUNK = 1024 * 1024


@router.post("/extract")
async def extract(file: UploadFile = File(...)):
    """Return the tables and graphs found in a score report, in document order.

    Nothing is kept: score reports carry client identifiers, so the upload lives
    in a temp file only for the duration of the request. The caller sends back
    just the items the psychologist chose to include.
    """
    suffix = Path(file.filename or "").suffix.lower() or ".bin"
    handle, temp_name = tempfile.mkstemp(suffix=suffix, prefix="score_report_")
    temp_path = Path(temp_name)
    try:
        size = 0
        with os.fdopen(handle, "wb") as out:
            while True:
                chunk = await file.read(CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="That file is too large (limit 40 MB).")
                out.write(chunk)

        try:
            result = await run_in_threadpool(extract_score_report, temp_path, file.content_type)
        except ScoreReportError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:  # a corrupt/odd file shouldn't surface a stack trace
            raise HTTPException(
                status_code=400, detail="That score report couldn't be read. Try the Word version, or a PDF."
            ) from error
        return {"filename": file.filename, **result}
    finally:
        temp_path.unlink(missing_ok=True)
