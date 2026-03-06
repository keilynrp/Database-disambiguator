import json
import logging
import os
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from backend.schema_registry import DomainSchema
from openai import OpenAI

logger = logging.getLogger(__name__)

# Try to get the client initialized
client = None
if os.environ.get("OPENAI_API_KEY"):
    client = OpenAI()

def _generate_system_prompt(domain: DomainSchema) -> str:
    """Generate a domain-aware prompt for the LLM based on the target schema."""
    
    attr_list = []
    for attr in domain.attributes:
        req_str = "Required" if attr.required else "Optional"
        attr_list.append(f"- '{attr.name}' ({attr.type}): {attr.label}. {req_str}")
        
    attributes_text = "\n".join(attr_list)
    
    sys_prompt = f"""You are UKIP Semantic Engine, a specialized AI for Semantic Disambiguation and Data Harmonization.
Your task is to take chaotic, raw JSON data and map it exactly into our strictly defined `{domain.name}` domain schema.

TARGET SCHEMA ATTRIBUTES:
{attributes_text}

RULES:
1. You must respond with valid JSON ONLY.
2. The root of your response MUST contain an "attributes" key with the mapped data, and a "confidence" float (0.0 to 1.0) indicating your mapping certainty.
3. Map any unstructured or synonym keys into our TARGET SCHEMA ATTRIBUTES exact names.
4. Try to correct subtle spelling errors, standardize casing (e.g., Title Case for names), and harmonize date formats (YYYY-MM-DD).
5. If a target attribute is required but cannot be confidently found or inferred from the data, leave it as null.
6. If the raw data contains useful attributes that do not map to the schema, nest them under a key called "extended_payload".
"""
    return sys_prompt

class DisambiguationResult(BaseModel):
    attributes: Dict[str, Any]
    confidence: float
    extended_payload: Optional[Dict[str, Any]] = Field(default_factory=dict)

def disambiguate_entity(raw_record: Dict[str, Any], domain: DomainSchema, api_key: str = None) -> DisambiguationResult:
    """
    Core function that calls the LLM. 
    Accepts raw un-normalized properties and attempts to harmonize them using the Domain Schema.
    """
    # Prefer explicitly passed API key (from frontend settings/header), fallback to env vars.
    active_client = OpenAI(api_key=api_key) if api_key else client
    
    # Fallback simulation logic if no API key is present
    if not active_client:
        logger.warning("No OpenAI API key found — returning simulated disambiguation.")
        # Simulated basic parsing just mapping known exact matches
        mapped = {}
        for attr in domain.attributes:
            mapped[attr.name] = raw_record.get(attr.name, None)
            
        return DisambiguationResult(
            attributes=mapped,
            confidence=0.5,
            extended_payload={"original": raw_record, "simulated": True}
        )
        
    system_prompt = _generate_system_prompt(domain)
    
    try:
        response = active_client.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cost-effective for data wrangling
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Harmonize this payload:\n{json.dumps(raw_record, indent=2)}"}
            ]
        )
        
        result_str = response.choices[0].message.content
        result_json = json.loads(result_str)
        
        return DisambiguationResult(
            attributes=result_json.get("attributes", {}),
            confidence=result_json.get("confidence", 0.0),
            extended_payload=result_json.get("extended_payload", {})
        )
        
    except Exception as e:
        logger.error("LLM disambiguation error: %s", e)
        return DisambiguationResult(attributes={}, confidence=0.0)

class CanonicalResolution(BaseModel):
    canonical_value: str
    reasoning: str

def resolve_canonical_name(field_name: str, variations: List[str], api_key: str = None) -> CanonicalResolution:
    """
    Given an entity attribute name and a list of lexical variations, uses the LLM to elect the single best
    canonical string (e.g., standardizing 'nike inc', 'NIKE', 'nkie' to 'Nike').
    """
    active_client = OpenAI(api_key=api_key) if api_key else client
    
    if not active_client:
        # Fallback to just taking the shortest capitalized one, or just the first if no API key
        best = variations[0] if variations else ""
        return CanonicalResolution(canonical_value=best, reasoning="Simulated selection (No LLM active).")
        
    prompt = f"""You are an expert Data Librarian and Lexicographer.
Given the attribute type '{field_name}' and a cluster of messy variations from our database, select the single most correct, canonical representation.
Rules:
1. Fix capitalization (Usually Title Case for brands/entities).
2. Remove illegal characters or trailing garbage.
3. If it's an acronym, capitalize it properly (e.g., 'ibm' -> 'IBM').
4. Reply ONLY in JSON format.

Variations to resolve:
{json.dumps(variations)}
"""

    try:
        response = active_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a master lexicographer outputting strictly valid JSON with keys: canonical_value, reasoning."},
                {"role": "user", "content": prompt}
            ]
        )
        data = json.loads(response.choices[0].message.content)
        return CanonicalResolution(
            canonical_value=data.get("canonical_value", variations[0] if variations else ""),
            reasoning=data.get("reasoning", "")
        )
    except Exception as e:
        logger.error("LLM canonical resolve error: %s", e)
        return CanonicalResolution(canonical_value=variations[0] if variations else "", reasoning=str(e))

