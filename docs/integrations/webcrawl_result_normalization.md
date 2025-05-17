# WebCrawl Result Normalization

This document describes the result normalization system implemented in the WebCrawl MCP to ensure consistent data structures, field naming, and confidence scoring across different data sources.

## Overview

The WebCrawl MCP can retrieve data from multiple sources (Crawl4AI, Playwright, WebSearchTool), each with potentially different output formats, field naming, and data structures. The result normalization system ensures that regardless of the source, the data returned to agents and other systems has a consistent structure, making it easier to consume and reducing the need for source-specific handling.

## Key Features

### 1. Consistent Data Structures

- Standardized field names across all sources
- Guaranteed presence of expected fields (with appropriate defaults if missing)
- Nested structure for metadata and source information
- Consistent date/time formatting

### 2. Source-Specific Confidence Scoring

- Confidence scores based on the reliability of the source
- Default confidence ranges:
  - Crawl4AI: 0.85 (high confidence for static content)
  - Playwright: 0.75 (medium-high confidence for dynamic content)
  - WebSearchTool: 0.65 (medium confidence for search results)
  - Unknown/Other: 0.50 (baseline confidence)

### 3. Content Enrichment

- Automatic summarization of long content
- Category detection based on content analysis
- Sentiment analysis for subjective content
- Missing field inference where appropriate

### 4. Metadata Tracking

- Source tracking for all data points
- Timestamp information for extraction and normalization
- Error handling and fallback indicators
- Processing history for audit and debugging

## Normalization Process

The normalization process happens in the request/response pipeline:

1. **Request Processing**: Handler receives request from agent/client
2. **Source Selection**: Intelligent source selector chooses appropriate source
3. **Data Retrieval**: Selected source retrieves raw data
4. **Normalization**: Raw data is passed through the normalizer
5. **Format Verification**: Output is validated against expected structure
6. **Response**: Normalized data is returned to the client

## Implementation Details

### Result Normalizer Class

The `ResultNormalizer` class in `src/mcp/webcrawl/utils/result_normalizer.py` is the core component responsible for normalization. It provides specialized methods for each type of data the WebCrawl MCP handles:

- `normalize_destination_results()`: For destination search results
- `normalize_events_results()`: For event listings
- `normalize_blog_results()`: For travel blog insights

### Integration Points

The normalizer is integrated at multiple points in the WebCrawl MCP:

1. **Handler Modules**: Each handler calls the normalizer before returning results
2. **Fallback Paths**: Normalization is applied to both primary and fallback source results
3. **Error Handling**: Even error responses are normalized for consistent client handling

### Example: Normalized Destination Results

```json
{
  "destination": "Barcelona, Spain",
  "topics": {
    "attractions": [
      {
        "title": "Sagrada Familia",
        "content": "The Sagrada Familia is a large unfinished Roman Catholic basilica...",
        "summary": "Antoni Gaudí's famous unfinished masterpiece basilica.",
        "source": "barcelona-tourism.com",
        "url": "https://www.barcelona-tourism.com/sagrada-familia",
        "image_url": "https://example.com/sagrada-familia.jpg",
        "category": "attraction",
        "confidence": 0.85,
        "metadata": {
          "source_type": "crawl4ai",
          "extraction_method": "crawl4ai",
          "extraction_timestamp": "2025-05-11T12:34:56.789Z",
          "normalized": true
        }
      }
    ],
    "transportation": [
      {
        "title": "Getting Around Barcelona",
        "content": "Barcelona has an excellent public transportation system...",
        "summary": "Barcelona offers comprehensive public transit options including metro, bus, and tram.",
        "source": "barcelona.com",
        "url": "https://www.barcelona.com/transportation",
        "image_url": "",
        "category": "transport",
        "confidence": 0.75,
        "metadata": {
          "source_type": "playwright",
          "extraction_method": "playwright",
          "extraction_timestamp": "2025-05-11T12:35:28.456Z",
          "normalized": true
        }
      }
    ]
  },
  "sources": [
    "barcelona-tourism.com",
    "barcelona.com",
    "visitbarcelona.com"
  ],
  "metadata": {
    "source": "crawl4ai",
    "normalization_timestamp": "2025-05-11T12:35:30.123Z",
    "original_timestamp": "2025-05-11T12:34:50.789Z",
    "confidence": 0.85
  }
}
```

### Example: Normalized Events Results

```json
{
  "destination": "London, UK",
  "date_range": {
    "start_date": "2025-06-01",
    "end_date": "2025-06-07"
  },
  "events": [
    {
      "name": "British Summer Time Festival",
      "description": "Annual music festival in Hyde Park featuring top artists...",
      "category": "music",
      "date": "2025-06-05",
      "time": "16:00",
      "venue": "Hyde Park",
      "address": "Hyde Park, London W2 2UH",
      "url": "https://www.bst-hydepark.com",
      "price_range": "£75-150",
      "image_url": "https://example.com/bst-festival.jpg",
      "source": "visitlondon.com",
      "confidence": 0.85,
      "metadata": {
        "source_type": "crawl4ai",
        "extraction_method": "crawl4ai",
        "extraction_timestamp": "2025-05-11T12:40:22.345Z",
        "normalized": true
      }
    }
  ],
  "event_count": 1,
  "categories": {
    "music": 1
  },
  "sources": [
    "visitlondon.com"
  ],
  "metadata": {
    "source": "crawl4ai",
    "normalization_timestamp": "2025-05-11T12:40:25.678Z",
    "original_timestamp": "2025-05-11T12:40:20.123Z",
    "confidence": 0.85
  }
}
```

## Content Enrichment Features

### Category Detection

The normalizer automatically detects categories based on content keywords:

- **Attraction**: museum, landmark, monument, gallery, park, etc.
- **Restaurant**: dining, cafe, food, cuisine, dishes, etc.
- **Hotel**: accommodation, lodging, resort, room, stay, etc.
- **Transport**: travel, bus, train, subway, taxi, etc.
- **Activity**: tour, experience, adventure, excursion, etc.
- **Shopping**: shop, store, market, mall, souvenirs, etc.

### Sentiment Analysis

For blog content and reviews, the normalizer performs basic sentiment analysis:

- **Positive**: great, excellent, recommend, amazing, etc.
- **Neutral**: informative, standard, average, etc.
- **Negative**: avoid, disappointing, expensive, crowded, etc.

### Automatic Summarization

Long content (>500 characters) is automatically summarized using:

- First 2-3 sentences extraction
- Key phrase identification
- Length-controlled output (typically 300 characters)

## Usage Examples

### Basic Normalization Flow

```python
from src.mcp.webcrawl.utils.result_normalizer import get_result_normalizer

# Get the normalizer singleton
normalizer = get_result_normalizer()

# Normalize results from a source
normalized_results = normalizer.normalize_destination_results(
    results=raw_results,
    source_type="crawl4ai"
)

# Return normalized results to client
return _format_response(normalized_results)
```

### Handling Fallbacks

```python
try:
    # Try primary source
    results = await primary_source.search_destination_info(...)
    
    # Normalize primary source results
    normalized_results = normalizer.normalize_destination_results(
        results=results,
        source_type="crawl4ai"
    )
    
    return _format_response(normalized_results)
except Exception:
    # Try fallback source
    fallback_results = await fallback_source.search_destination_info(...)
    
    # Normalize fallback source results
    normalized_fallback = normalizer.normalize_destination_results(
        results=fallback_results,
        source_type="playwright"
    )
    
    return _format_response(normalized_fallback)
```

## Benefits

1. **Consistency**: Agents can rely on consistent data structures regardless of the underlying source
2. **Completeness**: All expected fields are always present with appropriate defaults
3. **Confidence**: Source-specific confidence scoring helps with decision making
4. **Enrichment**: Automatic categorization, summarization, and sentiment analysis add value
5. **Metadata**: Comprehensive tracking of source information and processing history

## Future Enhancements

1. **Machine Learning Categorization**: Replace rule-based categorization with ML models
2. **Advanced Sentiment Analysis**: Use NLP for more accurate sentiment detection
3. **Content Deduplication**: Identify and merge duplicate content from different sources
4. **Content Verification**: Cross-reference information from multiple sources
5. **Dynamic Confidence Scoring**: Adjust confidence scores based on consistency checks
