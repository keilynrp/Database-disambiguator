import time
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from backend import models
from backend.adapters.enrichment.openalex import OpenAlexAdapter

adapter = OpenAlexAdapter()

def enrich_single_record(db: Session, product: models.RawProduct) -> models.RawProduct:
    """
    Synchronously enriches a single record by title or DOI.
    """
    if not product.product_name and not product.model:
        return product
        
    query = product.product_name or product.model
    if not query:
        return product
        
    try:
        # We try to search by title
        results = adapter.search_by_title(query, limit=1)
        if results and len(results) > 0:
            enriched_data = results[0]
            product.enrichment_doi = enriched_data.doi
            product.enrichment_citation_count = enriched_data.citation_count
            product.enrichment_concepts = ", ".join(enriched_data.concepts) if enriched_data.concepts else None
            product.enrichment_source = enriched_data.source_api
            product.enrichment_status = "completed"
        else:
            product.enrichment_status = "failed"
            product.enrichment_source = "OpenAlex"
            
    except Exception as e:
        product.enrichment_status = "failed"
        
    db.commit()
    return product

async def background_enrichment_worker(db_generator):
    """
    Background worker that runs slowly to avoid rate limit bans.
    Pulls records where enrichment_status == 'pending'.
    """
    # Wait a bit before starting so server can boot
    await asyncio.sleep(5)
    
    while True:
        try:
            db = next(db_generator)
            # Find one pending record
            product = db.query(models.RawProduct).filter(
                models.RawProduct.enrichment_status == "pending"
            ).first()
            
            if product:
                enrich_single_record(db, product)
                db.close()
                # Polite rate limiting (e.g. 1 process per 2 seconds)
                await asyncio.sleep(2)
            else:
                db.close()
                # If no pending records, sleep for a while
                await asyncio.sleep(10)
        except Exception as e:
            # Sleep on error before retrying
            await asyncio.sleep(10)

def trigger_enrichment_bulk(db: Session, skip: int = 0, limit: int = 100):
    """
    Marks a batch of products as 'pending' so the background worker picks them up.
    """
    products = db.query(models.RawProduct).filter(
        models.RawProduct.enrichment_status.in_(["none", "failed"])
    ).offset(skip).limit(limit).all()
    
    count = 0
    for p in products:
        p.enrichment_status = "pending"
        count += 1
        
    db.commit()
    return count
