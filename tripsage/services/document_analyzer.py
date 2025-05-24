"""
AI-powered document analysis service for travel-related document processing.

This service analyzes uploaded documents to extract travel-relevant information
using AI models while following KISS principles.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from tripsage.models.attachments import (
    DocumentAnalysisResult,
    FileType,
)


class AnalysisContext(BaseModel):
    """Context for document analysis."""

    file_id: str = Field(..., description="File identifier")
    file_path: Path = Field(..., description="Path to file on disk")
    mime_type: str = Field(..., description="MIME type of file")
    file_type: FileType = Field(..., description="Categorized file type")
    user_context: Optional[str] = Field(None, description="User-provided context")


class TravelInformation(BaseModel):
    """Extracted travel-related information."""

    destinations: List[str] = Field(
        default_factory=list, description="Mentioned destinations"
    )
    dates: List[str] = Field(default_factory=list, description="Travel dates")
    accommodations: List[Dict[str, str]] = Field(
        default_factory=list, description="Accommodation details"
    )
    flights: List[Dict[str, str]] = Field(
        default_factory=list, description="Flight information"
    )
    activities: List[str] = Field(
        default_factory=list, description="Planned activities"
    )
    budget_info: Optional[Dict[str, Any]] = Field(
        None, description="Budget-related information"
    )
    contact_info: List[Dict[str, str]] = Field(
        default_factory=list, description="Important contact information"
    )


class DocumentAnalyzer:
    """
    Service for AI-powered analysis of travel documents.

    Processes various document types to extract travel-relevant information
    using appropriate extraction methods based on file type.
    """

    def __init__(self):
        """Initialize document analyzer."""
        # TODO: Initialize AI client when AI service is ready
        self.ai_client = None

        # Analysis templates for different document types
        self.analysis_templates = {
            "travel_itinerary": {
                "prompt": (
                    "Extract travel itinerary information including destinations, "
                    "dates, accommodations, and activities."
                ),
                "fields": ["destinations", "dates", "accommodations", "activities"],
            },
            "booking_confirmation": {
                "prompt": (
                    "Extract booking details including confirmation numbers, dates, "
                    "locations, and contact information."
                ),
                "fields": ["booking_reference", "dates", "location", "contact_info"],
            },
            "travel_document": {
                "prompt": (
                    "Extract travel document information including passport details, "
                    "and visa information, and validity dates."
                ),
                "fields": [
                    "document_type",
                    "document_number",
                    "validity_dates",
                    "issuing_authority",
                ],
            },
            "general": {
                "prompt": "Extract any travel-related information from this document.",
                "fields": ["travel_relevance", "key_information"],
            },
        }

    async def analyze_document(
        self, context: AnalysisContext, analysis_type: str = "general"
    ) -> DocumentAnalysisResult:
        """
        Analyze a document and extract travel-relevant information.

        Args:
            context: Analysis context with file information
            analysis_type: Type of analysis to perform

        Returns:
            DocumentAnalysisResult with extracted information
        """
        start_time = datetime.utcnow()

        try:
            # Extract text content based on file type
            extracted_text = await self._extract_text_content(context)

            # Perform AI analysis
            if extracted_text:
                analysis_results = await self._analyze_text_with_ai(
                    extracted_text, analysis_type, context.user_context
                )
            else:
                analysis_results = {"error": "No text content could be extracted"}

            # Calculate processing time
            processing_time = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            # Extract travel-specific information
            travel_info = self._extract_travel_information(
                analysis_results, extracted_text
            )

            return DocumentAnalysisResult(
                file_id=context.file_id,
                analysis_type=analysis_type,
                extracted_text=(
                    extracted_text[:5000] if extracted_text else None
                ),  # Limit text for storage
                key_information=analysis_results,
                travel_relevance=travel_info.dict() if travel_info else None,
                confidence_score=self._calculate_confidence_score(analysis_results),
                processing_time_ms=processing_time,
            )

        except Exception as e:
            processing_time = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            return DocumentAnalysisResult(
                file_id=context.file_id,
                analysis_type=analysis_type,
                extracted_text=None,
                key_information={"error": str(e)},
                travel_relevance=None,
                confidence_score=0.0,
                processing_time_ms=processing_time,
            )

    async def _extract_text_content(self, context: AnalysisContext) -> Optional[str]:
        """
        Extract text content from file based on type.

        Args:
            context: Analysis context

        Returns:
            Extracted text content or None
        """
        try:
            if context.mime_type == "text/plain":
                return await self._extract_text_from_text_file(context.file_path)
            elif context.mime_type == "application/pdf":
                return await self._extract_text_from_pdf(context.file_path)
            elif context.mime_type == "application/json":
                return await self._extract_text_from_json(context.file_path)
            elif context.mime_type == "text/csv":
                return await self._extract_text_from_csv(context.file_path)
            elif context.mime_type.startswith("image/"):
                # TODO: Implement OCR for images when needed
                return await self._extract_text_from_image(context.file_path)
            elif "officedocument" in context.mime_type:
                # TODO: Implement Office document parsing when needed
                return await self._extract_text_from_office_doc(context.file_path)
            else:
                return None

        except Exception as e:
            # Log error and return None
            print(f"Text extraction failed for {context.file_id}: {str(e)}")
            return None

    async def _extract_text_from_text_file(self, file_path: Path) -> str:
        """Extract text from plain text file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    async def _extract_text_from_pdf(self, file_path: Path) -> Optional[str]:
        """
        Extract text from PDF file.

        TODO: Implement PDF text extraction using PyPDF2 or similar
        when needed. For now, return placeholder.
        """
        # Placeholder implementation
        return f"PDF text extraction not yet implemented for {file_path.name}"

    async def _extract_text_from_json(self, file_path: Path) -> str:
        """Extract text from JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return json.dumps(data, indent=2)

    async def _extract_text_from_csv(self, file_path: Path) -> str:
        """Extract text from CSV file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    async def _extract_text_from_image(self, file_path: Path) -> Optional[str]:
        """
        Extract text from image using OCR.

        TODO: Implement OCR using pytesseract or cloud OCR service
        when needed. For now, return placeholder.
        """
        # Placeholder implementation
        return f"OCR text extraction not yet implemented for {file_path.name}"

    async def _extract_text_from_office_doc(self, file_path: Path) -> Optional[str]:
        """
        Extract text from Office documents.

        TODO: Implement Office document parsing using python-docx, openpyxl
        when needed. For now, return placeholder.
        """
        # Placeholder implementation
        return (
            f"Office document text extraction not yet implemented for {file_path.name}"
        )

    async def _analyze_text_with_ai(
        self, text: str, analysis_type: str, user_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze extracted text using AI.

        Args:
            text: Extracted text content
            analysis_type: Type of analysis to perform
            user_context: Optional user-provided context

        Returns:
            Analysis results dictionary
        """
        # TODO: Implement AI analysis using OpenAI or other AI service
        # when AI integration is ready. For now, return structured placeholder.

        template = self.analysis_templates.get(
            analysis_type, self.analysis_templates["general"]
        )

        # Placeholder analysis - replace with actual AI call
        mock_analysis = {
            "analysis_type": analysis_type,
            "template_used": template["prompt"],
            "text_length": len(text),
            "user_context": user_context,
            "extracted_entities": self._extract_basic_entities(text),
            "travel_keywords": self._find_travel_keywords(text),
            "status": "mock_analysis",
        }

        return mock_analysis

    def _extract_basic_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract basic entities from text using simple pattern matching.

        This is a placeholder implementation that can be enhanced with
        proper NLP libraries when needed.
        """
        entities = {
            "dates": [],
            "locations": [],
            "emails": [],
            "phone_numbers": [],
            "currency_amounts": [],
        }

        # Simple regex patterns for common entities
        import re

        # Date patterns (simple)
        date_patterns = [
            r"\d{1,2}/\d{1,2}/\d{4}",
            r"\d{4}-\d{2}-\d{2}",
            r"\b\w+ \d{1,2}, \d{4}\b",
        ]

        for pattern in date_patterns:
            entities["dates"].extend(re.findall(pattern, text))

        # Email pattern
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        entities["emails"] = re.findall(email_pattern, text)

        # Phone pattern (simple)
        phone_pattern = r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
        entities["phone_numbers"] = re.findall(phone_pattern, text)

        # Currency pattern
        currency_pattern = r"\$\d+(?:,\d{3})*(?:\.\d{2})?"
        entities["currency_amounts"] = re.findall(currency_pattern, text)

        return entities

    def _find_travel_keywords(self, text: str) -> List[str]:
        """Find travel-related keywords in text."""
        travel_keywords = {
            "flight",
            "airline",
            "airport",
            "departure",
            "arrival",
            "hotel",
            "accommodation",
            "booking",
            "reservation",
            "destination",
            "travel",
            "trip",
            "vacation",
            "holiday",
            "passport",
            "visa",
            "itinerary",
            "ticket",
            "confirmation",
            "check-in",
            "checkout",
            "baggage",
            "luggage",
        }

        text_lower = text.lower()
        found_keywords = []

        for keyword in travel_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)

        return found_keywords

    def _extract_travel_information(
        self, analysis_results: Dict[str, Any], text: str
    ) -> Optional[TravelInformation]:
        """
        Extract structured travel information from analysis results.

        Args:
            analysis_results: AI analysis results
            text: Original text content

        Returns:
            Structured travel information
        """
        try:
            # Extract entities from basic analysis
            entities = analysis_results.get("extracted_entities", {})
            keywords = analysis_results.get("travel_keywords", [])

            # Build travel information structure
            travel_info = TravelInformation()

            # Extract destinations (placeholder logic)
            if "locations" in entities:
                travel_info.destinations = entities["locations"]

            # Extract dates
            if "dates" in entities:
                travel_info.dates = entities["dates"]

            # Extract budget information
            if "currency_amounts" in entities:
                amounts = entities["currency_amounts"]
                if amounts:
                    travel_info.budget_info = {
                        "mentioned_amounts": amounts,
                        "currency": "USD",  # Default assumption
                    }

            # Extract contact information
            contacts = []
            if "emails" in entities:
                for email in entities["emails"]:
                    contacts.append({"type": "email", "value": email})

            if "phone_numbers" in entities:
                for phone in entities["phone_numbers"]:
                    contacts.append({"type": "phone", "value": phone})

            travel_info.contact_info = contacts

            # Add activities based on keywords
            activity_keywords = [
                kw for kw in keywords if kw in ["vacation", "holiday", "trip"]
            ]
            travel_info.activities = activity_keywords

            return travel_info

        except Exception:
            return None

    def _calculate_confidence_score(self, analysis_results: Dict[str, Any]) -> float:
        """
        Calculate confidence score for analysis results.

        Args:
            analysis_results: Analysis results dictionary

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Simple confidence calculation based on available data
        score = 0.0

        # Base score for successful analysis
        if "error" not in analysis_results:
            score += 0.3

        # Score based on extracted entities
        entities = analysis_results.get("extracted_entities", {})
        entity_count = sum(len(v) for v in entities.values())
        score += min(0.4, entity_count * 0.05)

        # Score based on travel keywords
        keywords = analysis_results.get("travel_keywords", [])
        score += min(0.3, len(keywords) * 0.05)

        return min(1.0, score)

    async def get_supported_analysis_types(self) -> List[str]:
        """
        Get list of supported analysis types.

        Returns:
            List of supported analysis type names
        """
        return list(self.analysis_templates.keys())

    async def batch_analyze_documents(
        self, contexts: List[AnalysisContext], analysis_type: str = "general"
    ) -> List[DocumentAnalysisResult]:
        """
        Analyze multiple documents in batch.

        Args:
            contexts: List of analysis contexts
            analysis_type: Type of analysis to perform

        Returns:
            List of analysis results
        """
        # Process documents concurrently for better performance
        tasks = [self.analyze_document(context, analysis_type) for context in contexts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = DocumentAnalysisResult(
                    file_id=contexts[i].file_id,
                    analysis_type=analysis_type,
                    extracted_text=None,
                    key_information={"error": str(result)},
                    travel_relevance=None,
                    confidence_score=0.0,
                    processing_time_ms=0,
                )
                final_results.append(error_result)
            else:
                final_results.append(result)

        return final_results


# Dependency injection function for FastAPI
def get_document_analyzer() -> DocumentAnalyzer:
    """
    Get DocumentAnalyzer instance for dependency injection.

    Returns:
        DocumentAnalyzer instance
    """
    return DocumentAnalyzer()
