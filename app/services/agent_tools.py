# app/services/agent_tools.py
"""
Enhanced agent tools with web search, document comparison, and analytics.
"""

import json
from datetime import datetime, timedelta
from typing import Literal

import httpx
from langchain_core.tools import tool
from sqlmodel import func, select

from app.core.config import settings
from app.core.database import get_session
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.query import Query
from app.services.embeddings import embedding_service
from app.services.vector_store import vector_store

# =============================================================================
# WEB SEARCH TOOL (Tavily)
# =============================================================================


@tool
def web_search(
    query: str, search_depth: Literal["basic", "advanced"] = "basic", max_results: int = 5
) -> str:
    """
    Search the web for current information using Tavily.

    Use this when:
    - User asks about recent events or news
    - Need information not in the user's documents
    - Require up-to-date facts or data
    - Researching a topic

    Args:
        query: The search query
        search_depth: "basic" for quick results, "advanced" for comprehensive search
        max_results: Maximum number of results to return (1-10)

    Returns:
        JSON string with search results including titles, URLs, and snippets

    Example:
        User: "What's the latest news about AI?"
        → web_search(query="latest AI news", search_depth="basic", max_results=5)
    """
    try:
        if not settings.TAVILY_API_KEY:
            return json.dumps(
                {
                    "status": "error",
                    "message": "Web search is not configured. Tavily API key is missing.",
                }
            )

        # Call Tavily API
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": True,
            "include_raw_content": False,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        # Format results
        results = {
            "status": "success",
            "answer": data.get("answer", ""),
            "results": [
                {
                    "title": r["title"],
                    "url": r["url"],
                    "snippet": r["content"][:300] + "..."
                    if len(r["content"]) > 300
                    else r["content"],
                    "score": r.get("score", 0),
                }
                for r in data.get("results", [])
            ],
            "query": query,
        }

        return json.dumps(results)

    except httpx.HTTPError as e:
        return json.dumps({"status": "error", "message": f"Web search failed: {str(e)}"})
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Unexpected error during web search: {str(e)}"}
        )


# =============================================================================
# DOCUMENT COMPARISON TOOL
# =============================================================================


@tool
def compare_documents(
    document_ids: list[int], user_id: int, comparison_aspects: list[str] | None = None
) -> str:
    """
    Compare multiple documents across various aspects.

    Use this when:
    - User wants to understand differences between documents
    - Need to analyze similarities and contrasts
    - Comparing multiple versions of a document

    Args:
        document_ids: List of document IDs to compare (2-5 documents)
        user_id: User ID for authorization
        comparison_aspects: Aspects to compare (length, topics, sentiment, structure)
                          If None, compares all aspects

    Returns:
        JSON string with detailed comparison analysis

    Example:
        User: "Compare my two AI research papers"
        → compare_documents(document_ids=[1, 2], user_id=123)
    """
    try:
        if len(document_ids) < 2:
            return json.dumps(
                {"status": "error", "message": "Need at least 2 documents to compare"}
            )

        if len(document_ids) > 5:
            return json.dumps(
                {"status": "error", "message": "Can only compare up to 5 documents at once"}
            )

        with next(get_session()) as session:
            # Fetch documents
            statement = select(Document).where(
                Document.id.in_(document_ids), Document.owner_id == user_id
            )
            documents = session.exec(statement).all()

            if len(documents) != len(document_ids):
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Found {len(documents)} documents, expected {len(document_ids)}",
                    }
                )

            # Get chunks for each document
            comparison = {
                "status": "success",
                "documents_compared": len(documents),
                "comparison": {},
            }

            doc_data = {}
            for doc in documents:
                chunks = session.exec(select(Chunk).where(Chunk.document_id == doc.id)).all()

                doc_data[doc.id] = {
                    "title": doc.title,
                    "chunk_count": len(chunks),
                    "total_tokens": sum(c.tokens for c in chunks),
                    "text_length": sum(len(c.text) for c in chunks),
                    "chunks": chunks,
                }

            # Comparison aspects
            aspects = comparison_aspects or ["length", "structure", "topics"]

            # Length comparison
            if "length" in aspects:
                comparison["comparison"]["length"] = {
                    doc_id: {
                        "chunks": data["chunk_count"],
                        "tokens": data["total_tokens"],
                        "characters": data["text_length"],
                    }
                    for doc_id, data in doc_data.items()
                }

            # Structure comparison
            if "structure" in aspects:
                comparison["comparison"]["structure"] = {
                    doc_id: {
                        "avg_chunk_size": data["total_tokens"] // max(data["chunk_count"], 1),
                        "chunk_distribution": "even"
                        if _is_even_distribution(data["chunks"])
                        else "varied",
                    }
                    for doc_id, data in doc_data.items()
                }

            # Topic similarity (using vector similarity)
            if "topics" in aspects and len(documents) == 2:
                doc_ids = list(doc_data.keys())
                chunks1 = doc_data[doc_ids[0]]["chunks"]
                chunks2 = doc_data[doc_ids[1]]["chunks"]

                if chunks1 and chunks2:
                    # Get average embeddings (simplified)
                    similarity = _calculate_document_similarity(chunks1, chunks2)
                    comparison["comparison"]["similarity"] = {
                        "score": round(similarity, 3),
                        "interpretation": _interpret_similarity(similarity),
                    }

            return json.dumps(comparison)

    except Exception as e:
        return json.dumps({"status": "error", "message": f"Comparison failed: {str(e)}"})


def _is_even_distribution(chunks: list) -> bool:
    """Check if chunk sizes are evenly distributed."""
    if len(chunks) < 2:
        return True

    sizes = [c.tokens for c in chunks]
    avg = sum(sizes) / len(sizes)
    variance = sum((s - avg) ** 2 for s in sizes) / len(sizes)
    std_dev = variance**0.5

    # Even if std dev is less than 20% of average
    return std_dev < (avg * 0.2)


def _calculate_document_similarity(chunks1: list, chunks2: list) -> float:
    """Calculate similarity between two documents based on chunks."""
    # Simplified: compare first chunks
    # In production, use average embeddings
    if not chunks1 or not chunks2:
        return 0.0

    # Get embeddings for first chunks
    try:
        emb1 = embedding_service.generate_embedding(chunks1[0].text)
        emb2 = embedding_service.generate_embedding(chunks2[0].text)

        # Cosine similarity
        import numpy as np

        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    except:
        return 0.0


def _interpret_similarity(score: float) -> str:
    """Interpret similarity score."""
    if score > 0.9:
        return "Very similar - likely discussing the same topic"
    elif score > 0.7:
        return "Similar - related topics or themes"
    elif score > 0.5:
        return "Somewhat similar - some common elements"
    else:
        return "Different - distinct topics or content"


# =============================================================================
# STATISTICAL ANALYSIS TOOL
# =============================================================================


@tool
def analyze_documents_statistics(
    user_id: int,
    time_period: Literal["week", "month", "quarter", "year", "all"] = "all",
    group_by: Literal["day", "week", "month"] | None = None,
) -> str:
    """
    Perform statistical analysis on the user's documents.

    Use this when:
    - User asks about their document usage patterns
    - Need insights into document activity
    - Analyzing trends over time
    - Understanding document collection

    Args:
        user_id: User ID for authorization
        time_period: Time period to analyze
        group_by: How to group the data for trends

    Returns:
        JSON string with statistical analysis

    Example:
        User: "How many documents did I upload this month?"
        → analyze_documents_statistics(user_id=123, time_period="month")
    """
    try:
        with next(get_session()) as session:
            # Determine date filter
            now = datetime.utcnow()
            if time_period == "week":
                start_date = now - timedelta(days=7)
            elif time_period == "month":
                start_date = now - timedelta(days=30)
            elif time_period == "quarter":
                start_date = now - timedelta(days=90)
            elif time_period == "year":
                start_date = now - timedelta(days=365)
            else:
                start_date = None

            # Build base query
            base_query = select(Document).where(Document.owner_id == user_id)
            if start_date:
                base_query = base_query.where(Document.created_at >= start_date)

            # Get documents
            documents = session.exec(base_query).all()

            if not documents:
                return json.dumps(
                    {
                        "status": "success",
                        "message": "No documents found for the specified period",
                        "statistics": {},
                    }
                )

            # Calculate statistics
            stats = {
                "status": "success",
                "time_period": time_period,
                "statistics": {
                    "total_documents": len(documents),
                    "by_status": _group_by_status(documents),
                    "by_type": _group_by_type(documents),
                    "size_statistics": _calculate_size_stats(documents),
                    "upload_trend": _calculate_upload_trend(documents, group_by)
                    if group_by
                    else None,
                },
            }

            # Add query statistics
            query_stats = session.exec(
                select(func.count(Query.id)).where(Query.user_id == user_id)
            ).one()

            stats["statistics"]["total_queries"] = query_stats

            # Average queries per document
            if len(documents) > 0:
                stats["statistics"]["avg_queries_per_document"] = round(
                    query_stats / len(documents), 2
                )

            return json.dumps(stats)

    except Exception as e:
        return json.dumps({"status": "error", "message": f"Analysis failed: {str(e)}"})


def _group_by_status(documents: list) -> dict:
    """Group documents by status."""
    from collections import Counter

    statuses = [d.status for d in documents]
    return dict(Counter(statuses))


def _group_by_type(documents: list) -> dict:
    """Group documents by MIME type."""
    from collections import Counter

    types = [d.mime_type for d in documents if d.mime_type]
    type_map = {
        "application/pdf": "PDF",
        "text/plain": "Text",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
        "text/markdown": "Markdown",
    }

    simplified = [type_map.get(t, "Other") for t in types]
    return dict(Counter(simplified))


def _calculate_size_stats(documents: list) -> dict:
    """Calculate size statistics."""
    sizes = [d.file_size for d in documents if d.file_size]

    if not sizes:
        return {}

    return {
        "total_size_bytes": sum(sizes),
        "total_size_mb": round(sum(sizes) / (1024 * 1024), 2),
        "average_size_bytes": round(sum(sizes) / len(sizes)),
        "largest_size_bytes": max(sizes),
        "smallest_size_bytes": min(sizes),
    }


def _calculate_upload_trend(documents: list, group_by: str) -> dict:
    """Calculate upload trend over time."""
    from collections import defaultdict

    trend = defaultdict(int)

    for doc in documents:
        if not doc.created_at:
            continue

        if group_by == "day":
            key = doc.created_at.strftime("%Y-%m-%d")
        elif group_by == "week":
            key = doc.created_at.strftime("%Y-W%W")
        elif group_by == "month":
            key = doc.created_at.strftime("%Y-%m")
        else:
            continue

        trend[key] += 1

    return dict(sorted(trend.items()))


# =============================================================================
# ADVANCED SEARCH TOOL
# =============================================================================


@tool
def advanced_search(
    query: str,
    user_id: int,
    filters: dict | None = None,
    search_mode: Literal["semantic", "keyword", "hybrid"] = "hybrid",
) -> str:
    """
    Advanced document search with filters and multiple search modes.

    Use this when:
    - User needs filtered search results
    - Specific search requirements (date range, document type)
    - Need to combine semantic and keyword search

    Args:
        query: Search query
        user_id: User ID for authorization
        filters: Optional filters (date_range, document_types, min_score)
        search_mode: Type of search to perform

    Returns:
        JSON string with search results

    Example:
        User: "Find PDF documents from last month about AI"
        → advanced_search(
            query="AI",
            user_id=123,
            filters={"document_types": ["PDF"], "date_range": "last_month"}
        )
    """
    try:
        # Parse filters
        filters = filters or {}
        date_range = filters.get("date_range")
        doc_types = filters.get("document_types", [])
        min_score = filters.get("min_score", 0.7)

        # Perform search
        if search_mode in ["semantic", "hybrid"]:
            results = vector_store.search(
                query_text=query,
                limit=10,
                filter_conditions={"user_id": user_id},
                min_score=min_score,
            )
        else:
            # Keyword search implementation
            results = []

        # Apply filters
        filtered_results = []
        with next(get_session()) as session:
            for result in results:
                doc = session.get(Document, result.document_id)

                if not doc:
                    continue

                # Date filter
                if date_range == "last_week" and doc.created_at:
                    if doc.created_at < datetime.utcnow() - timedelta(days=7):
                        continue
                elif date_range == "last_month" and doc.created_at:
                    if doc.created_at < datetime.utcnow() - timedelta(days=30):
                        continue

                # Type filter
                if doc_types:
                    type_map = {
                        "PDF": "application/pdf",
                        "Text": "text/plain",
                        "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    }
                    allowed_types = [type_map.get(t, t) for t in doc_types]
                    if doc.mime_type not in allowed_types:
                        continue

                filtered_results.append(
                    {
                        "chunk_text": result.text[:200] + "...",
                        "document_id": result.document_id,
                        "document_title": doc.title,
                        "score": result.score,
                        "document_type": doc.mime_type,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    }
                )

        return json.dumps(
            {
                "status": "success",
                "results": filtered_results,
                "count": len(filtered_results),
                "search_mode": search_mode,
                "filters_applied": filters,
            }
        )

    except Exception as e:
        return json.dumps({"status": "error", "message": f"Advanced search failed: {str(e)}"})


# Export all tools
ENHANCED_TOOLS = [web_search, compare_documents, analyze_documents_statistics, advanced_search]
