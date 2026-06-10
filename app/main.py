from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import csv
from io import StringIO
from fastapi.responses import StreamingResponse
import os
from app.hash_utils import (
    generate_sha256,
    generate_content_hash
)
from app.services.pdf_service import extract_text_from_pdf
from app.services.address_extractor import extract_addresses
from app.services.address_service import (
    normalize_address,
    parse_address
)
from app.services.duplicate_detector import (
    calculate_similarity
)
from app.services.recommendation_service import (
    determine_recommendation
)

from app.database.db import (
    init_db,
    get_db,
    create_document,
    get_documents,
    get_document_by_id,
    get_document_by_sha256,
    create_address,
    get_address_by_normalized,
    create_address_document_link,
    get_addresses,
    get_addresses_count,
    get_address_by_id,
    soft_delete_address,
    get_pending_duplicate_candidates,
    get_all_addresses,
    create_duplicate_candidate,
    get_duplicate_candidate_by_id,
    mark_candidate_not_duplicate,
    merge_addresses,
    update_address,
    get_export_addresses,
    get_document_by_content_hash,
    get_total_documents,
    get_total_addresses,
    get_total_duplicates,
    get_unique_addresses,
    get_duplicate_addresses_count
)
from app.logger import logger
from pydantic import BaseModel
class AddressUpdateRequest(BaseModel):
    street: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None


class DuplicateResolveRequest(BaseModel):
    action: str
app = FastAPI(
    title="Address Registry System"
)

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def startup_event():
    init_db()
    logger.info("Database initialized")


@app.get("/")
def home():
    return FileResponse("templates/index.html")


@app.get("/documents")
def list_documents(
    db: Session = Depends(get_db)
):
    documents = get_documents(db)

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "size_bytes": doc.size_bytes,
            "status": doc.status,
            "failure_reason": doc.failure_reason,
            "uploaded_at": doc.uploaded_at
        }
        for doc in documents
    ]
@app.get("/statistics")
def get_statistics(
    db: Session = Depends(get_db)
):
    return {
        "documents": get_total_documents(db),
        "addresses": get_total_addresses(db),
        "duplicates": get_total_duplicates(db)
    }


@app.get("/stats")
def get_stats(
    db: Session = Depends(get_db)
):
    total_docs = get_total_documents(db)
    unique_addrs = get_unique_addresses(db)
    
    
    from sqlalchemy import text
    try:
        dup_files_rejected = db.execute(text("SELECT COUNT(*) FROM rejected_duplicates")).scalar() or 0
    except Exception:
        dup_files_rejected = 0
        
    dup_addrs_caught = get_duplicate_addresses_count(db)
    
    return {
        "total_documents": total_docs,
        "unique_addresses": unique_addrs,
        "duplicate_files_rejected": dup_files_rejected,
        "duplicate_addresses_caught": dup_addrs_caught
    }
@app.get("/documents/{document_id}")
def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    document = get_document_by_id(
        db,
        document_id
    )

    if not document:
        return {
            "message": "Document not found"
        }

    return {
        "id": document.id,
        "filename": document.filename,
        "size_bytes": document.size_bytes,
        "status": document.status,
        "failure_reason": document.failure_reason,
        "uploaded_at": document.uploaded_at
    }
@app.get("/addresses")
def list_addresses(
    limit: int = 20,
    offset: int = 0,
    search: str = None,
    city: str = None,
    state: str = None,
    zip_code: str = None,
    db: Session = Depends(get_db)
):
    addresses = get_addresses(
        db=db,
        limit=limit,
        offset=offset,
        search=search,
        city=city,
        state=state,
        zip_code=zip_code
    )

    total = get_addresses_count(
        db=db,
        search=search,
        city=city,
        state=state,
        zip_code=zip_code
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": address.id,
                "raw_text": address.raw_text,
                "normalized": address.normalized,
                "street": address.street,
                "city": address.city,
                "state": address.state,
                "zip": address.zip,
                "review_status": address.review_status
            }
            for address in addresses
        ]
    }
@app.get("/addresses/{address_id}")
def get_address(
    address_id: int,
    db: Session = Depends(get_db)
):
    address = get_address_by_id(
        db,
        address_id
    )

    if not address:
        return {
            "message": "Address not found"
        }

    return {
        "id": address.id,
        "raw_text": address.raw_text,
        "normalized": address.normalized,
        "street": address.street,
        "city": address.city,
        "state": address.state,
        "zip": address.zip,
        "review_status": address.review_status,
        "documents": [
            {
                "document_id": link.document.id,
                "filename": link.document.filename
            }
            for link in address.documents
        ]
    }
@app.delete("/addresses/{address_id}")
def delete_address(
    address_id: int,
    db: Session = Depends(get_db)
):
    address = soft_delete_address(
        db,
        address_id
    )

    if not address:
        return {
            "message": "Address not found"
        }

    return {
        "message": "Address soft deleted",
        "address_id": address.id
    }
@app.get("/duplicates")
def get_duplicates(
    db: Session = Depends(get_db)
):
    candidates = (
        get_pending_duplicate_candidates(
            db
        )
    )

    result = []
    for candidate in candidates:
        address1 = get_address_by_id(db, candidate.address1_id)
        address2 = get_address_by_id(db, candidate.address2_id)
        result.append({
            "id": candidate.id,
            "address1_id": candidate.address1_id,
            "address2_id": candidate.address2_id,
            "address1_text": address1.normalized if address1 else "",
            "address2_text": address2.normalized if address2 else "",
            "score": candidate.score,
            "status": candidate.status,
            "recommendation": candidate.recommendation
        })
    return result
@app.patch("/addresses/{address_id}")
def update_address_endpoint(
    address_id: int,
    request: AddressUpdateRequest,
    db: Session = Depends(get_db)
):
    address = update_address(
        db=db,
        address_id=address_id,
        street=request.street,
        city=request.city,
        state=request.state,
        zip_code=request.zip
    )

    if not address:
        return {
            "message": "Address not found"
        }

    return {
        "message": "Address updated",
        "address_id": address.id
    }
@app.post("/duplicates/{candidate_id}/resolve")
def resolve_duplicate(
    candidate_id: int,
    request: DuplicateResolveRequest,
    db: Session = Depends(get_db)
):
    candidate = get_duplicate_candidate_by_id(
        db,
        candidate_id
    )
    logger.info(f"Duplicate resolution action received: {request.action}")
    if not candidate:
        return {
            "message": "Candidate not found"
        }

    if request.action == "not_duplicate":

        mark_candidate_not_duplicate(
            db,
            candidate
        )

        return {
            "message": "Marked as not duplicate"
        }

    if request.action == "merge":

        merge_addresses(
            db,
            winner_id=candidate.address1_id,
            loser_id=candidate.address2_id
        )

        candidate.status = "merged"

        db.commit()

        return {
            "message": "Addresses merged"
        }

    return {
        "message": "Invalid action"
    }
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()

        if len(content) == 0:
            raise ValueError("Uploaded file is empty")

        file_hash = generate_sha256(content)
        logger.debug(f"Generated SHA256 hash: {file_hash}")

        existing_document = get_document_by_sha256(
            db,
            file_hash
        )

        if existing_document:
            logger.warning(
                f"Duplicate file rejected: {file.filename}"
            )
            db.execute(
                text("INSERT OR REPLACE INTO rejected_duplicates (sha256) VALUES (:sha256)"),
                {"sha256": file_hash}
            )
            db.commit()

            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Duplicate file",
                    "document_id": existing_document.id
                }
            )

        
        try:
            pdf_text = extract_text_from_pdf(content)
            if not pdf_text.strip():
                raise ValueError("No extractable text found in PDF")

            logger.info(
                f"Extracted text from {file.filename}"
            )
            content_hash = generate_content_hash(
                pdf_text
            )
            logger.info(
                f"CONTENT HASH: {content_hash}"
            )

            existing_content = get_document_by_content_hash(
                db,
                content_hash
            )
            logger.info(
                f"Checking content duplicate for: {file.filename}"
            )
            if existing_content:
                logger.warning(
                    f"Content duplicate detected: {file.filename}"
                )
                db.execute(
                    text("INSERT OR REPLACE INTO rejected_duplicates (sha256) VALUES (:sha256)"),
                    {"sha256": file_hash}
                )
                db.commit()

                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Content duplicate",
                        "document_id": existing_content.id
                    }
                )

            addresses_found = extract_addresses(
                pdf_text
            )
            if len(addresses_found) == 0:
                raise ValueError(
                    "No address found in document"
                )

        except HTTPException:
            
            raise
        except Exception as e:
            
            document = create_document(
                db=db,
                filename=file.filename,
                size_bytes=len(content),
                sha256=file_hash,
                status="failed",
                failure_reason=str(e)
            )
            logger.error(
                f"Upload failed: {file.filename} - {str(e)}"
            )
            return {
                "document_id": document.id,
                "status": "failed",
                "reason": str(e)
            }

        document = create_document(
            db=db,
            filename=file.filename,
            size_bytes=len(content),
            sha256=file_hash,
            content_hash=content_hash,
            status="processed"
        )

        processed_normalized = set()
        all_addresses = get_all_addresses(db)

        for raw_address in addresses_found:

            normalized = normalize_address(
                raw_address
            )

            if normalized in processed_normalized:
                logger.info(
                    f"Address already processed in this upload: {normalized}"
                )
                continue

            processed_normalized.add(normalized)

            existing_address = get_address_by_normalized(
                db,
                normalized
            )

            if existing_address:

                create_address_document_link(
                    db=db,
                    address_id=existing_address.id,
                    document_id=document.id
                )

                logger.info(
                    f"Existing address linked: {normalized}"
                )

                continue

            parsed = parse_address(
                raw_address
            )

            address = create_address(
                db=db,
                raw_text=raw_address,
                normalized=normalized,
                street=parsed["street"],
                city=parsed["city"],
                state=parsed["state"],
                zip_code=parsed["zip"]
            )

            for existing in all_addresses:

                if existing.id == address.id:
                    continue

                same_city = (
                    existing.city is not None and
                    address.city is not None and
                    existing.city.strip().upper() == address.city.strip().upper()
                )

                same_zip = (
                    existing.zip is not None and
                    address.zip is not None and
                    existing.zip.strip() == address.zip.strip()
                )

                if not (same_city or same_zip):
                    continue

                score = calculate_similarity(
                    existing.normalized,
                    address.normalized
                )

                if score >= 90:

                    recommendation = determine_recommendation(existing, address)
                    create_duplicate_candidate(
                        db=db,
                        address1_id=existing.id,
                        address2_id=address.id,
                        score=int(score),
                        recommendation=recommendation
                    )

                    logger.info(
                        f"Duplicate candidate found: "
                        f"{existing.id} <-> {address.id} "
                        f"score={score}"
                    )

            create_address_document_link(
                db=db,
                address_id=address.id,
                document_id=document.id
            )

            logger.info(
                f"New address stored: {normalized}"
            )

        logger.info(
            f"Document uploaded successfully: {file.filename}"
        )

        return {
            "document_id": document.id,
            "filename": document.filename,
            "status": document.status,
            "addresses_found": len(addresses_found)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Upload failed: {file.filename} - {str(e)}"
        )
        document = create_document(
            db=db,
            filename=file.filename,
            size_bytes=0,
            status="failed",
            failure_reason=str(e)
        )
        return {
            "document_id": document.id,
            "status": "failed",
            "reason": str(e)
        }
@app.get("/export")
def export_csv(
    search: str = None,
    city: str = None,
    state: str = None,
    zip_code: str = None,
    db: Session = Depends(get_db)
):
    addresses = get_export_addresses(
        db,
        search=search,
        city=city,
        state=state,
        zip_code=zip_code
    )

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow(
        [
            "id",
            "street",
            "city",
            "state",
            "zip",
            "normalized"
        ]
    )

    for address in addresses:

        writer.writerow(
            [
                address.id,
                address.street,
                address.city,
                address.state,
                address.zip,
                address.normalized
            ]
        )

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=addresses.csv"
        }
    )