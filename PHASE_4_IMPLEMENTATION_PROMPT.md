# Phase 4: File Handling & Attachments - Implementation Prompt

## Context
You are implementing Phase 4 of the AI Chat Integration for TripSage. Phase 1 (Chat API Endpoint Enhancement and Session Management) was completed in PR #118 and PR #122. Phase 2 (Authentication & BYOK Integration) was completed in PR #123. Phase 3 (Testing Infrastructure & Dependencies) was completed in the current session with comprehensive testing solutions and zero linting errors. The chat interface is functional with proper authentication, and all MCP integrations are established.

## Your Task
Implement Phase 4: File Handling & Attachments as outlined in `tasks/TODO-INTEGRATION.md` (lines 156-180). This phase adds comprehensive file upload, processing, and AI analysis capabilities to enhance the travel planning experience with document intelligence.

## Tool Usage Instructions

### 1. Start with Research
```
- Use Read tool to examine: tasks/TODO-INTEGRATION.md (lines 156-180)
- Use Read tool to examine: frontend/src/app/api/chat/attachments/route.ts
- Use Read tool to examine: frontend/src/components/features/chat/message-input.tsx
- Use Read tool to examine: frontend/src/components/features/chat/messages/message-attachments.tsx
- Use Read tool to examine: tripsage/api/routers/chat.py
- Use Read tool to examine: tripsage/tools/ directory for file processing patterns
- Use Read tool to examine: docs/ for security and validation patterns
```

### 2. Create TODO List
```
Use TodoWrite tool to create a comprehensive task list based on Phase 4 requirements
```

### 3. Implementation Order
1. File Upload System (Section 4.1)
2. File Processing Pipeline (Section 4.2)
3. AI Analysis Integration (Section 4.3)
4. Security & Validation (Section 4.4)
5. Testing & Optimization (Section 4.5)

### 4. Key Files to Modify/Create
```
Backend:
- tripsage/api/routers/attachments.py (new - file upload endpoints)
- tripsage/services/file_processor.py (new - file processing service)
- tripsage/services/document_analyzer.py (new - AI document analysis)
- tripsage/models/attachments.py (new - file models)
- tripsage/utils/file_validation.py (new - security validation)

Frontend:
- frontend/src/app/api/chat/attachments/route.ts (enhance existing)
- frontend/src/components/features/chat/file-upload.tsx (new component)
- frontend/src/components/features/chat/messages/message-attachments.tsx (enhance)
- frontend/src/types/attachments.ts (new - file types)
- frontend/src/lib/file-utils.ts (new - file utilities)
```

### 5. Testing Approach
```
- Use Write tool to create: tests/api/test_file_upload.py
- Use Write tool to create: tests/services/test_document_analyzer.py
- Use Write tool to create: tests/integration/test_file_processing_flow.py
- Use Write tool to create: frontend/src/components/features/chat/__tests__/file-upload.test.tsx
- Run tests with: cd frontend && pnpm test
- Run backend tests with: cd /home/bjorn/repos/agents/openai/tripsage-ai && uv run pytest tests/api/ tests/services/
```

## Key Documentation References

### File Processing Architecture
- **File Storage**: Use configurable storage (S3/local filesystem)
- **Processing Pipeline**: Multi-stage document analysis and extraction
- **AI Integration**: OpenAI API for document analysis and information extraction
- **Security**: Comprehensive file validation, virus scanning, and sanitization

### Supported File Types
- **Documents**: PDF, DOC, DOCX, TXT (travel itineraries, bookings, passports)
- **Images**: JPG, PNG, WEBP (destination photos, screenshots, maps)
- **Data**: CSV, JSON (flight data, expense reports, travel logs)
- **Archives**: ZIP (travel document packages)

### Security Requirements
- File type whitelist enforcement (no executables)
- Size limits: 10MB per file, 50MB total per session
- Virus scanning before processing
- Content validation and sanitization
- Secure temporary storage with automatic cleanup
- User isolation (files only accessible to uploader)

## Phase 4 Checklist

### 4.1 Upload System Integration
- [ ] Create file upload API endpoints (`/api/v1/attachments`)
- [ ] Implement secure file storage with user isolation
- [ ] Add file validation and security scanning
- [ ] Create file metadata storage in database
- [ ] Implement temporary file cleanup system
- [ ] Add upload progress tracking and resumption

### 4.2 File Processing Pipeline
- [ ] Create document text extraction service
- [ ] Implement image analysis and OCR capabilities
- [ ] Add travel document recognition (tickets, passports, visas)
- [ ] Build structured data extraction from travel documents
- [ ] Create file format conversion utilities
- [ ] Implement batch processing for multiple files

### 4.3 AI Analysis Integration
- [ ] Integrate OpenAI API for document analysis
- [ ] Create travel-specific prompt templates for file analysis
- [ ] Extract relevant travel information (dates, locations, prices)
- [ ] Generate trip suggestions from uploaded content
- [ ] Implement context integration with chat conversations
- [ ] Add intelligent file categorization and tagging

### 4.4 Frontend File Management
- [ ] Enhance file upload component with drag-and-drop
- [ ] Add file preview and thumbnail generation
- [ ] Implement upload progress indicators
- [ ] Create file management interface (view, delete, re-analyze)
- [ ] Add file type validation feedback
- [ ] Implement file attachment display in chat messages

### 4.5 Security & Validation
- [ ] Implement comprehensive file type validation
- [ ] Add virus scanning integration (ClamAV or similar)
- [ ] Create secure file storage with encryption at rest
- [ ] Implement access control and user isolation
- [ ] Add file content sanitization
- [ ] Create audit logging for file operations

## Code Patterns to Follow

### File Upload API
```python
# In tripsage/api/routers/attachments.py
from fastapi import UploadFile, File, HTTPException, Depends
from tripsage.services.file_processor import FileProcessor
from tripsage.utils.file_validation import validate_file

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserDB = Depends(get_current_user),
    processor: FileProcessor = Depends(get_file_processor)
):
    """Upload and process a file attachment."""
    # Validate file
    validation_result = await validate_file(file)
    if not validation_result.is_valid:
        raise HTTPException(400, validation_result.error_message)
    
    # Process file
    result = await processor.process_file(file, current_user.id)
    
    return {
        "file_id": result.file_id,
        "analysis": result.analysis,
        "extracted_data": result.extracted_data
    }
```

### Document Analysis Service
```python
# In tripsage/services/document_analyzer.py
from openai import AsyncOpenAI
from typing import Dict, Any, Optional

class DocumentAnalyzer:
    """AI-powered document analysis for travel files."""
    
    async def analyze_travel_document(
        self, 
        file_content: str, 
        file_type: str
    ) -> Dict[str, Any]:
        """Analyze uploaded document for travel information."""
        
        prompt = self._get_analysis_prompt(file_type)
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": file_content}
            ],
            temperature=0.1
        )
        
        return self._parse_analysis_result(response)
    
    def _get_analysis_prompt(self, file_type: str) -> str:
        """Get travel-specific analysis prompt."""
        return f"""
        Analyze this {file_type} document for travel-related information.
        Extract and structure any:
        - Dates and times
        - Locations and addresses
        - Flight/hotel/rental information
        - Costs and pricing
        - Contact information
        - Important notes or requirements
        
        Return structured JSON with extracted data.
        """
```

### Frontend File Upload
```typescript
// In frontend/src/components/features/chat/file-upload.tsx
import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface FileUploadProps {
  onFileAnalyzed: (analysis: FileAnalysis) => void;
}

export function FileUpload({ onFileAnalyzed }: FileUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback(async (files: File[]) => {
    setUploading(true);
    
    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/v1/attachments/upload', {
          method: 'POST',
          body: formData,
          headers: {
            'Authorization': `Bearer ${getAuthToken()}`
          }
        });
        
        if (response.ok) {
          const result = await response.json();
          onFileAnalyzed(result);
        }
      } catch (error) {
        console.error('Upload failed:', error);
      }
    }
    
    setUploading(false);
  }, [onFileAnalyzed]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.jpg', '.jpeg', '.png', '.webp'],
      'text/*': ['.txt', '.csv']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: true
  });

  return (
    <div 
      {...getRootProps()} 
      className={`upload-zone ${isDragActive ? 'active' : ''}`}
    >
      <input {...getInputProps()} />
      {uploading ? (
        <UploadProgress progress={progress} />
      ) : (
        <UploadPrompt />
      )}
    </div>
  );
}
```

## Testing Requirements
- Unit tests for file validation and processing
- Integration tests for upload and analysis flow
- Security tests for file type and content validation
- Performance tests for large file handling
- E2E tests for complete file upload experience
- Error handling tests for malformed or malicious files

## Success Criteria
1. Secure file upload with comprehensive validation
2. AI-powered analysis extracts travel information accurately
3. File processing integrates seamlessly with chat interface
4. Upload progress and error handling work smoothly
5. File management (view, delete, re-analyze) functions correctly
6. Security measures prevent malicious file uploads
7. Performance remains acceptable for large files (<30s processing)
8. All tests pass with >90% coverage

## Important Notes
- Follow KISS principle - focus on essential file types first
- Use existing MCP patterns for external integrations
- Implement robust error handling and validation
- Ensure mobile-friendly file upload experience
- Plan for scalable file storage architecture
- Run `ruff check --fix` and `ruff format .` on Python files
- Run `npx biome lint --apply` and `npx biome format --write` on TypeScript files

## File Processing Strategy

### Supported Use Cases
1. **Travel Documents**: Boarding passes, hotel confirmations, rental agreements
2. **Planning Documents**: Itineraries, travel guides, research notes
3. **Financial Documents**: Receipts, expense reports, budget spreadsheets
4. **Identity Documents**: Passport scans, visa documents (secure handling)
5. **Media Files**: Destination photos, maps, screenshots

### Processing Pipeline
1. **Upload & Validation**: Secure file receipt and initial validation
2. **Content Extraction**: Text, image, or data extraction based on file type
3. **AI Analysis**: Intelligent parsing for travel-relevant information
4. **Structured Output**: Convert extracted data to standardized format
5. **Integration**: Merge results with chat context and trip planning
6. **Storage**: Secure long-term storage with user access controls

### Error Handling
- Graceful degradation for unsupported file types
- Clear error messages for validation failures
- Retry mechanisms for transient processing failures
- Fallback to manual processing when AI analysis fails
- Comprehensive logging for debugging and monitoring

## References
- Phase 1: PR #118 (Chat API) & PR #122 (Session Management)
- Phase 2: PR #123 (Authentication & BYOK)
- Phase 3: Current session (Testing Infrastructure)
- OpenAI API Documentation: https://platform.openai.com/docs/api-reference
- FastAPI File Uploads: https://fastapi.tiangolo.com/tutorial/request-files/
- React Dropzone: https://react-dropzone.js.org/

Start by reading the TODO-INTEGRATION.md file to understand Phase 4 scope, then create a comprehensive TODO list before beginning implementation. Focus on creating a secure, user-friendly file handling experience that enhances travel planning capabilities.