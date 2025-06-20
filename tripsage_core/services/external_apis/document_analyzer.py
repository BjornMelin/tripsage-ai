"""
AI-powered document analysis service for travel-related document processing
with TripSage Core integration.

This service analyzes uploaded documents to extract travel-relevant information
using AI models while following KISS principles and Core integration patterns.
"""

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import CoreExternalAPIError as CoreAPIError
from tripsage_core.exceptions.exceptions import CoreServiceError

# Import models from existing location (could be moved to Core later)
from tripsage_core.models.attachments import (
    DocumentAnalysisResult,
    FileType,
)


class DocumentAnalyzerError(CoreAPIError):
    """Exception raised for document analyzer errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="DOCUMENT_ANALYZER_ERROR",
            service="DocumentAnalyzer",
            details={"original_error": str(original_error) if original_error else None},
        )
        self.original_error = original_error


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
    Service for AI-powered analysis of travel documents with Core integration.

    Processes various document types to extract travel-relevant information
    using appropriate extraction methods based on file type.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize document analyzer.

        Args:
            settings: Core application settings
        """
        self.settings = settings or get_settings()
        self._connected = False

        # Get AI configuration from settings
        self.ai_enabled = getattr(self.settings, "document_analyzer_ai_enabled", False)
        self.max_text_length = getattr(
            self.settings, "document_analyzer_max_text_length", 50000
        )
        self.max_concurrent_analyses = getattr(
            self.settings, "document_analyzer_max_concurrent", 3
        )

        # OCR settings
        self.ocr_enabled = getattr(
            self.settings, "document_analyzer_ocr_enabled", False
        )
        self.pdf_extraction_enabled = getattr(
            self.settings, "document_analyzer_pdf_enabled", False
        )

        # Rate limiting
        self._analysis_semaphore = asyncio.Semaphore(self.max_concurrent_analyses)

        # TODO: Initialize AI client when AI service is ready
        self.ai_client = None

        # Analysis templates for different document types
        self.analysis_templates = {
            "travel_itinerary": {
                "prompt": "Extract travel itinerary information including "
                "destinations, dates, accommodations, and activities.",
                "fields": ["destinations", "dates", "accommodations", "activities"],
            },
            "booking_confirmation": {
                "prompt": "Extract booking details including confirmation "
                "numbers, dates, locations, and contact information.",
                "fields": ["booking_reference", "dates", "location", "contact_info"],
            },
            "travel_document": {
                "prompt": "Extract travel document information including "
                "passport details, visa information, and validity dates.",
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

    async def connect(self) -> None:
        """Initialize the document analyzer service."""
        if self._connected:
            return

        try:
            # TODO: Initialize AI client when available
            # if self.ai_enabled:
            #     self.ai_client = await get_ai_client()

            self._connected = True

        except Exception as e:
            raise CoreServiceError(
                message=f"Failed to connect document analyzer: {str(e)}",
                code="CONNECTION_FAILED",
                service="DocumentAnalyzer",
                details={"error": str(e)},
            ) from e

    async def disconnect(self) -> None:
        """Clean up resources."""
        self.ai_client = None
        self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure service is connected."""
        if not self._connected:
            await self.connect()

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

        Raises:
            DocumentAnalyzerError: When analysis fails
        """
        await self.ensure_connected()

        start_time = datetime.now(timezone.utc)

        async with self._analysis_semaphore:
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
                    (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                )

                # Extract travel-specific information
                travel_info = self._extract_travel_information(
                    analysis_results, extracted_text
                )

                return DocumentAnalysisResult(
                    file_id=context.file_id,
                    analysis_type=analysis_type,
                    extracted_text=extracted_text[:5000]
                    if extracted_text
                    else None,  # Limit text for storage
                    key_information=analysis_results,
                    travel_relevance=travel_info.dict() if travel_info else None,
                    confidence_score=self._calculate_confidence_score(analysis_results),
                    processing_time_ms=processing_time,
                )

            except Exception as e:
                processing_time = int(
                    (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                )

                raise DocumentAnalyzerError(
                    f"Document analysis failed for {context.file_id}: {str(e)}",
                    original_error=e,
                ) from e

    async def _extract_text_content(self, context: AnalysisContext) -> Optional[str]:
        """
        Extract text content from file based on type.

        Args:
            context: Analysis context

        Returns:
            Extracted text content or None

        Raises:
            DocumentAnalyzerError: When text extraction fails
        """
        try:
            if context.mime_type == "text/plain":
                return await self._extract_text_from_text_file(context.file_path)
            elif context.mime_type == "application/pdf":
                if self.pdf_extraction_enabled:
                    return await self._extract_text_from_pdf(context.file_path)
                else:
                    return (
                        f"PDF text extraction disabled in settings for "
                        f"{context.file_path.name}"
                    )
            elif context.mime_type == "application/json":
                return await self._extract_text_from_json(context.file_path)
            elif context.mime_type == "text/csv":
                return await self._extract_text_from_csv(context.file_path)
            elif context.mime_type.startswith("image/"):
                if self.ocr_enabled:
                    return await self._extract_text_from_image(context.file_path)
                else:
                    return (
                        f"OCR text extraction disabled in settings for "
                        f"{context.file_path.name}"
                    )
            elif "officedocument" in context.mime_type:
                # TODO: Implement Office document parsing when needed
                return await self._extract_text_from_office_doc(context.file_path)
            else:
                return None

        except Exception as e:
            raise DocumentAnalyzerError(
                f"Text extraction failed for {context.file_id}: {str(e)}",
                original_error=e,
            ) from e

    async def _extract_text_from_text_file(self, file_path: Path) -> str:
        """Extract text from plain text file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if len(content) > self.max_text_length:
                    content = content[: self.max_text_length]
                return content
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, "r", encoding="latin-1") as f:
                content = f.read()
                if len(content) > self.max_text_length:
                    content = content[: self.max_text_length]
                return content

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
            content = json.dumps(data, indent=2)
            if len(content) > self.max_text_length:
                content = content[: self.max_text_length]
            return content

    async def _extract_text_from_csv(self, file_path: Path) -> str:
        """Extract text from CSV file."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if len(content) > self.max_text_length:
                content = content[: self.max_text_length]
            return content

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
        # TODO: Implement AI analysis using Core AI service when available
        # For now, return structured placeholder with enhanced analysis

        template = self.analysis_templates.get(
            analysis_type, self.analysis_templates["general"]
        )

        # Enhanced analysis with better entity extraction
        entities = self._extract_basic_entities(text)
        keywords = self._find_travel_keywords(text)

        # Calculate text statistics
        text_stats = {
            "word_count": len(text.split()),
            "character_count": len(text),
            "sentence_count": len(text.split(".")),
            "paragraph_count": len(text.split("\n\n")),
        }

        # Mock analysis with Core integration
        mock_analysis = {
            "analysis_type": analysis_type,
            "template_used": template["prompt"],
            "text_stats": text_stats,
            "user_context": user_context,
            "extracted_entities": entities,
            "travel_keywords": keywords,
            "status": "mock_analysis_with_core",
            "ai_enabled": self.ai_enabled,
            "settings_source": "core_app_settings",
        }

        return mock_analysis

    def _extract_basic_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract basic entities from text using enhanced pattern matching.

        This is an enhanced implementation that can be further improved with
        proper NLP libraries when needed.
        """
        entities = {
            "dates": [],
            "locations": [],
            "emails": [],
            "phone_numbers": [],
            "currency_amounts": [],
            "confirmation_numbers": [],
            "flight_numbers": [],
        }

        # Enhanced date patterns
        date_patterns = [
            r"\d{1,2}/\d{1,2}/\d{4}",  # MM/DD/YYYY
            r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
            r"\b\w+ \d{1,2}, \d{4}\b",  # Month DD, YYYY
            r"\d{1,2}-\d{1,2}-\d{4}",  # DD-MM-YYYY
            r"\d{1,2}\.\d{1,2}\.\d{4}",  # DD.MM.YYYY
        ]

        for pattern in date_patterns:
            entities["dates"].extend(re.findall(pattern, text))

        # Email pattern
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        entities["emails"] = re.findall(email_pattern, text)

        # Enhanced phone patterns
        phone_patterns = [
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # US format
            r"\+\d{1,3}[-.\s]?\d{1,14}\b",  # International format
            r"\(\d{3}\)\s?\d{3}[-.]?\d{4}\b",  # (xxx) xxx-xxxx
        ]

        for pattern in phone_patterns:
            entities["phone_numbers"].extend(re.findall(pattern, text))

        # Enhanced currency patterns
        currency_patterns = [
            r"\$\d+(?:,\d{3})*(?:\.\d{2})?",  # USD
            r"€\d+(?:,\d{3})*(?:\.\d{2})?",  # EUR
            r"£\d+(?:,\d{3})*(?:\.\d{2})?",  # GBP
            r"\d+(?:,\d{3})*(?:\.\d{2})?\s*USD",  # USD suffix
        ]

        for pattern in currency_patterns:
            entities["currency_amounts"].extend(re.findall(pattern, text))

        # Confirmation number patterns
        confirmation_patterns = [
            r"\b[A-Z]{2}\d{4,6}\b",  # Airline style
            r"\b\d{6,10}\b",  # Numeric confirmations
            r"\b[A-Z0-9]{6,12}\b",  # Mixed alphanumeric
        ]

        for pattern in confirmation_patterns:
            entities["confirmation_numbers"].extend(re.findall(pattern, text))

        # Flight number patterns
        flight_pattern = r"\b[A-Z]{2,3}\s?\d{1,4}\b"
        entities["flight_numbers"] = re.findall(flight_pattern, text)

        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))

        return entities

    def _find_travel_keywords(self, text: str) -> List[str]:
        """Find travel-related keywords in text with enhanced matching."""
        travel_keywords = {
            # Transportation
            "flight",
            "airline",
            "airport",
            "departure",
            "arrival",
            "boarding",
            "gate",
            "terminal",
            "seat",
            "baggage",
            "luggage",
            "check-in",
            # Accommodation
            "hotel",
            "accommodation",
            "booking",
            "reservation",
            "room",
            "suite",
            "checkout",
            "lobby",
            "concierge",
            # Travel planning
            "destination",
            "travel",
            "trip",
            "vacation",
            "holiday",
            "tour",
            "itinerary",
            "schedule",
            "agenda",
            "activities",
            "sightseeing",
            # Documents
            "passport",
            "visa",
            "ticket",
            "confirmation",
            "boarding pass",
            "receipt",
            "invoice",
            "voucher",
            # Locations
            "city",
            "country",
            "address",
            "location",
            "coordinates",
            # Time
            "date",
            "time",
            "duration",
            "calendar",
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
            # Extract entities from enhanced analysis
            entities = analysis_results.get("extracted_entities", {})
            keywords = analysis_results.get("travel_keywords", [])

            # Build travel information structure
            travel_info = TravelInformation()

            # Extract destinations (enhanced logic)
            if "locations" in entities:
                travel_info.destinations = entities["locations"]

            # Extract dates
            if "dates" in entities:
                travel_info.dates = entities["dates"]

            # Extract flight information
            if "flight_numbers" in entities:
                flights = []
                for flight_num in entities["flight_numbers"]:
                    flights.append({"flight_number": flight_num, "type": "flight"})
                travel_info.flights = flights

            # Extract budget information
            if "currency_amounts" in entities:
                amounts = entities["currency_amounts"]
                if amounts:
                    travel_info.budget_info = {
                        "mentioned_amounts": amounts,
                        "currency": "USD",  # Default assumption
                        "total_estimates": len(amounts),
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

            # Add activities based on keywords and context
            activity_keywords = [
                kw
                for kw in keywords
                if kw
                in ["vacation", "holiday", "trip", "tour", "sightseeing", "activities"]
            ]
            travel_info.activities = activity_keywords

            # Add accommodation information based on keywords
            if any(
                kw in keywords for kw in ["hotel", "accommodation", "room", "suite"]
            ):
                if "confirmation_numbers" in entities:
                    accommodations = []
                    for conf_num in entities["confirmation_numbers"]:
                        accommodations.append(
                            {"confirmation_number": conf_num, "type": "accommodation"}
                        )
                    travel_info.accommodations = accommodations

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
        # Enhanced confidence calculation
        score = 0.0

        # Base score for successful analysis
        if "error" not in analysis_results:
            score += 0.2

        # Score based on extracted entities
        entities = analysis_results.get("extracted_entities", {})
        entity_count = sum(len(v) for v in entities.values())
        score += min(0.4, entity_count * 0.03)

        # Score based on travel keywords
        keywords = analysis_results.get("travel_keywords", [])
        score += min(0.3, len(keywords) * 0.04)

        # Score based on text statistics
        text_stats = analysis_results.get("text_stats", {})
        word_count = text_stats.get("word_count", 0)
        if word_count > 50:
            score += 0.1  # Bonus for substantial content

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

        Raises:
            DocumentAnalyzerError: When batch analysis setup fails
        """
        await self.ensure_connected()

        if not contexts:
            return []

        try:
            # Process documents concurrently for better performance
            tasks = [
                self.analyze_document(context, analysis_type) for context in contexts
            ]
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

        except Exception as e:
            raise DocumentAnalyzerError(
                f"Batch document analysis failed: {str(e)}", original_error=e
            ) from e

    async def analyze_travel_document(
        self, context: AnalysisContext, document_type: str = "general"
    ) -> DocumentAnalysisResult:
        """
        Analyze travel-specific document with enhanced extraction.

        Args:
            context: Analysis context
            document_type: Type of travel document (itinerary, booking, passport, etc.)

        Returns:
            DocumentAnalysisResult with travel-focused analysis
        """
        # Map document types to analysis types
        analysis_type_mapping = {
            "itinerary": "travel_itinerary",
            "booking": "booking_confirmation",
            "passport": "travel_document",
            "visa": "travel_document",
            "ticket": "booking_confirmation",
        }

        analysis_type = analysis_type_mapping.get(document_type, "general")
        return await self.analyze_document(context, analysis_type)

    async def health_check(self) -> bool:
        """
        Perform a health check to verify the service is working.

        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            await self.ensure_connected()

            # Test basic functionality
            analysis_types = await self.get_supported_analysis_types()
            return len(analysis_types) > 0
        except Exception:
            return False

    async def close(self) -> None:
        """Close the service and clean up resources."""
        await self.disconnect()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Global service instance
_document_analyzer: Optional[DocumentAnalyzer] = None


async def get_document_analyzer() -> DocumentAnalyzer:
    """
    Get the global document analyzer instance.

    Returns:
        DocumentAnalyzer instance
    """
    global _document_analyzer

    if _document_analyzer is None:
        _document_analyzer = DocumentAnalyzer()
        await _document_analyzer.connect()

    return _document_analyzer


async def close_document_analyzer() -> None:
    """Close the global document analyzer instance."""
    global _document_analyzer

    if _document_analyzer:
        await _document_analyzer.close()
        _document_analyzer = None


__all__ = [
    "DocumentAnalyzer",
    "DocumentAnalyzerError",
    "AnalysisContext",
    "TravelInformation",
    "get_document_analyzer",
    "close_document_analyzer",
]
