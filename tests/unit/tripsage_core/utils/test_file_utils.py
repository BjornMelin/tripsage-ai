"""
Unit tests for TripSage Core file utilities.

Tests file validation, path validation, type detection, size limits,
security scanning, and batch upload functionality.
"""

import hashlib
from io import BytesIO

from fastapi import UploadFile

from tripsage_core.utils.file_utils import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    FILE_TYPE_MAPPING,
    MAX_FILE_SIZE,
    MAX_FILES_PER_REQUEST,
    MAX_SESSION_SIZE,
    SUSPICIOUS_PATTERNS,
    ValidationResult,
    _detect_mime_type,
    _validate_file_content,
    _validate_filename,
    _validate_image_content,
    _validate_pdf_content,
    _validate_text_content,
    generate_safe_filename,
    validate_batch_upload,
    validate_file,
)


class TestValidationResult:
    """Test ValidationResult model."""

    def test_validation_result_success(self):
        """Test creating a successful validation result."""
        result = ValidationResult(
            is_valid=True,
            file_size=1024,
            detected_type="image/jpeg",
            file_hash="abc123",
        )
        assert result.is_valid is True
        assert result.error_message is None
        assert result.file_size == 1024
        assert result.detected_type == "image/jpeg"
        assert result.file_hash == "abc123"

    def test_validation_result_failure(self):
        """Test creating a failed validation result."""
        result = ValidationResult(
            is_valid=False,
            error_message="File too large",
            file_size=2048,
            detected_type="application/pdf",
        )
        assert result.is_valid is False
        assert result.error_message == "File too large"
        assert result.file_size == 2048
        assert result.detected_type == "application/pdf"
        assert result.file_hash is None


class TestFilenameValidation:
    """Test filename validation functionality."""

    def test_valid_filenames(self):
        """Test validation of valid filenames."""
        valid_files = [
            "document.pdf",
            "image.jpg",
            "data.csv",
            "archive.zip",
            "text_file.txt",
            "my-document.docx",
            "IMG_20231201_123456.jpeg",
        ]

        for filename in valid_files:
            is_valid, error = _validate_filename(filename)
            assert is_valid, f"Expected {filename} to be valid, got error: {error}"
            assert error is None

    def test_invalid_extensions(self):
        """Test validation of invalid file extensions."""
        invalid_files = [
            "malware.exe",
            "script.bat",
            "command.cmd",
            "screensaver.scr",
            "program.pif",
            "java_app.jar",
            "unknown.xyz",
        ]

        for filename in invalid_files:
            is_valid, error = _validate_filename(filename)
            assert not is_valid, f"Expected {filename} to be invalid"
            assert "extension" in error or "not allowed" in error

    def test_suspicious_patterns(self):
        """Test detection of suspicious patterns in filenames."""
        suspicious_files = [
            "../etc/passwd",
            "file\\with\\backslash",
            "file/with/slash",
            "file<with>brackets",
            'file"with"quotes',
            "file|with|pipes",
            "file?with?question",
            "file*with*asterisk",
            "file:with:colon",
        ]

        for filename in suspicious_files:
            is_valid, error = _validate_filename(filename)
            assert not is_valid, f"Expected {filename} to be flagged as suspicious"
            assert "suspicious pattern" in error

    def test_filename_too_long(self):
        """Test validation of overly long filenames."""
        long_filename = "a" * 300 + ".txt"
        is_valid, error = _validate_filename(long_filename)
        assert not is_valid
        assert "too long" in error

    def test_case_insensitive_extension_check(self):
        """Test that extension checking is case insensitive."""
        # Valid extensions in different cases
        valid_files = ["file.PDF", "image.JPG", "data.CSV", "doc.DOCX"]

        for filename in valid_files:
            is_valid, error = _validate_filename(filename)
            assert is_valid, f"Expected {filename} to be valid regardless of case"

    def test_case_insensitive_suspicious_patterns(self):
        """Test that suspicious pattern detection is case insensitive."""
        suspicious_files = ["file.EXE", "script.BAT", "malware.CMD"]

        for filename in suspicious_files:
            is_valid, error = _validate_filename(filename)
            assert not is_valid, f"Expected {filename} to be flagged regardless of case"


class TestMimeTypeDetection:
    """Test MIME type detection functionality."""

    def test_filename_based_detection(self):
        """Test MIME type detection based on filename."""
        test_cases = [
            ("document.pdf", b"", "application/pdf"),
            ("image.jpg", b"", "image/jpeg"),
            ("data.csv", b"", "text/csv"),
            ("text.txt", b"", "text/plain"),
            ("config.json", b"", "application/json"),
        ]

        for filename, content, expected in test_cases:
            detected = _detect_mime_type(filename, content)
            assert detected == expected, f"Expected {expected} for {filename}, got {detected}"

    def test_content_based_detection(self):
        """Test MIME type detection based on file content."""
        test_cases = [
            # JPEG
            ("unknown", b"\xff\xd8\xff", "image/jpeg"),
            # PNG
            ("unknown", b"\x89PNG\r\n\x1a\n", "image/png"),
            # GIF87a
            ("unknown", b"GIF87a", "image/gif"),
            # GIF89a
            ("unknown", b"GIF89a", "image/gif"),
            # PDF
            ("unknown", b"%PDF-1.4", "application/pdf"),
            # ZIP-based Office document
            (
                "document.docx",
                b"PK\x03\x04",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        ]

        for filename, content, expected in test_cases:
            detected = _detect_mime_type(filename, content)
            assert detected == expected, f"Expected {expected} for content, got {detected}"

    def test_unknown_type_fallback(self):
        """Test fallback for unknown file types."""
        detected = _detect_mime_type("unknown.xyz", b"\x00\x01\x02\x03")
        assert detected == "application/octet-stream"


class TestContentValidation:
    """Test file content validation functionality."""

    def test_image_content_validation(self):
        """Test image content validation."""
        # Valid JPEG
        is_valid, error = _validate_image_content(b"\xff\xd8\xff", "image/jpeg")
        assert is_valid
        assert error is None

        # Invalid JPEG
        is_valid, error = _validate_image_content(b"\x00\x01\x02", "image/jpeg")
        assert not is_valid
        assert "Invalid JPEG header" in error

        # Valid PNG
        is_valid, error = _validate_image_content(b"\x89PNG\r\n\x1a\n", "image/png")
        assert is_valid
        assert error is None

        # Invalid PNG
        is_valid, error = _validate_image_content(b"\x00\x01\x02", "image/png")
        assert not is_valid
        assert "Invalid PNG header" in error

        # Valid GIF
        is_valid, error = _validate_image_content(b"GIF87a", "image/gif")
        assert is_valid
        assert error is None

        # Invalid GIF
        is_valid, error = _validate_image_content(b"\x00\x01\x02", "image/gif")
        assert not is_valid
        assert "Invalid GIF header" in error

    def test_pdf_content_validation(self):
        """Test PDF content validation."""
        # Valid PDF
        pdf_content = b"%PDF-1.4\n...content...%%EOF"
        is_valid, error = _validate_pdf_content(pdf_content)
        assert is_valid
        assert error is None

        # Invalid PDF header
        is_valid, error = _validate_pdf_content(b"Not a PDF")
        assert not is_valid
        assert "Invalid PDF header" in error

        # Missing EOF marker
        is_valid, error = _validate_pdf_content(b"%PDF-1.4\nContent without EOF")
        assert not is_valid
        assert "missing EOF marker" in error

    def test_text_content_validation(self):
        """Test text content validation."""
        # Valid UTF-8 text
        valid_text = "Hello, 世界! 🌍".encode("utf-8")
        is_valid, error = _validate_text_content(valid_text)
        assert is_valid
        assert error is None

        # Invalid UTF-8
        invalid_text = b"\xff\xfe\x00\x01"  # Invalid UTF-8 sequence
        is_valid, error = _validate_text_content(invalid_text)
        assert not is_valid
        assert "not valid UTF-8" in error

    def test_content_validation_dispatch(self):
        """Test content validation dispatcher."""
        # Image content
        is_valid, error = _validate_file_content(b"\xff\xd8\xff", "image/jpeg")
        assert is_valid

        # PDF content
        is_valid, error = _validate_file_content(b"%PDF-1.4\n%%EOF", "application/pdf")
        assert is_valid

        # Text content
        is_valid, error = _validate_file_content(b"Hello, world!", "text/plain")
        assert is_valid

        # Unknown content type (should pass)
        is_valid, error = _validate_file_content(b"\x00\x01\x02", "application/unknown")
        assert is_valid
        assert error is None


class TestFileValidation:
    """Test main file validation functionality."""

    def create_upload_file(self, filename: str, content: bytes, content_type: str = None) -> UploadFile:
        """Helper to create UploadFile for testing."""
        file_obj = BytesIO(content)
        return UploadFile(
            filename=filename,
            file=file_obj,
            headers={"content-type": content_type} if content_type else {},
        )

    async def test_valid_file_upload(self):
        """Test validation of a valid file upload."""
        # Create a valid JPEG file
        jpeg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100
        file = self.create_upload_file("test.jpg", jpeg_content, "image/jpeg")

        result = await validate_file(file)
        assert result.is_valid
        assert result.error_message is None
        assert result.file_size == len(jpeg_content)
        assert result.detected_type == "image/jpeg"
        assert result.file_hash is not None

    async def test_empty_file_rejection(self):
        """Test rejection of empty files."""
        file = self.create_upload_file("empty.txt", b"")

        result = await validate_file(file)
        assert not result.is_valid
        assert "empty" in result.error_message
        assert result.file_size == 0

    async def test_oversized_file_rejection(self):
        """Test rejection of oversized files."""
        large_content = b"x" * (MAX_FILE_SIZE + 1)
        file = self.create_upload_file("large.txt", large_content)

        result = await validate_file(file, max_size=MAX_FILE_SIZE)
        assert not result.is_valid
        assert "exceeds maximum allowed size" in result.error_message
        assert result.file_size == len(large_content)

    async def test_missing_filename_rejection(self):
        """Test rejection of files without filename."""
        file = self.create_upload_file(None, b"content")

        result = await validate_file(file)
        assert not result.is_valid
        assert "Filename is required" in result.error_message

    async def test_invalid_file_type_rejection(self):
        """Test rejection of invalid file types."""
        exe_content = b"MZ" + b"\x00" * 100  # Fake exe header
        file = self.create_upload_file("malware.exe", exe_content)

        result = await validate_file(file)
        assert not result.is_valid
        assert "not allowed" in result.error_message

    async def test_mime_type_mismatch_rejection(self):
        """Test rejection when MIME type is not allowed."""
        # Create content that would be detected as unknown type
        unknown_content = b"\x00\x01\x02\x03" * 100
        file = self.create_upload_file("unknown.xyz", unknown_content)

        result = await validate_file(file)
        assert not result.is_valid
        assert "not allowed" in result.error_message

    async def test_content_validation_failure(self):
        """Test content validation failure."""
        # Create a file with PDF extension but invalid content
        invalid_pdf = b"Not a real PDF content"
        file = self.create_upload_file("fake.pdf", invalid_pdf)

        result = await validate_file(file)
        assert not result.is_valid
        assert "Invalid PDF header" in result.error_message

    async def test_custom_max_size(self):
        """Test validation with custom max size."""
        content = b"x" * 1000
        file = self.create_upload_file("test.txt", content)

        # Should pass with default size
        result = await validate_file(file)
        assert result.is_valid

        # Should fail with smaller custom size
        result = await validate_file(file, max_size=500)
        assert not result.is_valid
        assert "exceeds maximum allowed size" in result.error_message

    async def test_file_hash_generation(self):
        """Test that file hash is correctly generated."""
        content = b"test content for hashing"
        expected_hash = hashlib.sha256(content).hexdigest()
        file = self.create_upload_file("test.txt", content)

        result = await validate_file(file)
        assert result.is_valid
        assert result.file_hash == expected_hash


class TestBatchUploadValidation:
    """Test batch upload validation functionality."""

    def create_upload_file(self, filename: str, content: bytes) -> UploadFile:
        """Helper to create UploadFile for testing."""
        file_obj = BytesIO(content)
        return UploadFile(filename=filename, file=file_obj)

    async def test_empty_batch_rejection(self):
        """Test rejection of empty file batch."""
        result = await validate_batch_upload([])
        assert not result.is_valid
        assert "No files provided" in result.error_message
        assert result.file_size == 0

    async def test_valid_batch_upload(self):
        """Test validation of valid file batch."""
        files = [
            self.create_upload_file("file1.txt", b"content1"),
            self.create_upload_file("file2.jpg", b"\xff\xd8\xff" + b"x" * 100),
            self.create_upload_file("file3.pdf", b"%PDF-1.4\ncontent\n%%EOF"),
        ]

        result = await validate_batch_upload(files)
        assert result.is_valid
        assert result.error_message is None
        assert result.file_size > 0

    async def test_batch_size_limit_exceeded(self):
        """Test rejection when batch size limit is exceeded."""
        # Create files that exceed the batch size limit
        large_content = b"x" * (MAX_SESSION_SIZE // 2 + 1)
        files = [
            self.create_upload_file("large1.txt", large_content),
            self.create_upload_file("large2.txt", large_content),
        ]

        result = await validate_batch_upload(files, max_total_size=MAX_SESSION_SIZE)
        assert not result.is_valid
        assert "Total batch size" in result.error_message
        assert "exceeds maximum" in result.error_message

    async def test_batch_with_invalid_file(self):
        """Test rejection when batch contains invalid file."""
        files = [
            self.create_upload_file("valid.txt", b"valid content"),
            self.create_upload_file("invalid.exe", b"invalid content"),  # Invalid extension
        ]

        result = await validate_batch_upload(files)
        assert not result.is_valid
        assert "invalid.exe" in result.error_message

    async def test_batch_total_size_calculation(self):
        """Test that batch total size is calculated correctly."""
        content1 = b"x" * 100
        content2 = b"y" * 200
        content3 = b"z" * 300
        expected_total = 600

        files = [
            self.create_upload_file("file1.txt", content1),
            self.create_upload_file("file2.txt", content2),
            self.create_upload_file("file3.txt", content3),
        ]

        result = await validate_batch_upload(files)
        assert result.is_valid
        assert result.file_size == expected_total

    async def test_custom_batch_size_limit(self):
        """Test batch validation with custom size limit."""
        files = [
            self.create_upload_file("file1.txt", b"x" * 100),
            self.create_upload_file("file2.txt", b"y" * 100),
        ]

        # Should pass with default limit
        result = await validate_batch_upload(files)
        assert result.is_valid

        # Should fail with smaller custom limit
        result = await validate_batch_upload(files, max_total_size=150)
        assert not result.is_valid
        assert "exceeds maximum" in result.error_message


class TestSafeFilenameGeneration:
    """Test safe filename generation functionality."""

    def test_basic_filename_generation(self):
        """Test basic safe filename generation."""
        original = "test document.pdf"
        user_id = "user123"

        safe_name = generate_safe_filename(original, user_id)

        # Should contain user ID
        assert safe_name.startswith(user_id + "_")
        # Should preserve extension
        assert safe_name.endswith(".pdf")
        # Should contain hash component
        assert "_" in safe_name

    def test_filename_with_special_characters(self):
        """Test filename generation with special characters."""
        original = "my document with spaces & symbols!.txt"
        user_id = "user456"

        safe_name = generate_safe_filename(original, user_id)

        assert safe_name.startswith(user_id + "_")
        assert safe_name.endswith(".txt")
        # Should be a valid filename without special chars in the body
        assert " " not in safe_name
        assert "&" not in safe_name
        assert "!" not in safe_name

    def test_filename_deterministic_generation(self):
        """Test that same inputs produce same safe filename."""
        original = "test.jpg"
        user_id = "user789"

        safe_name1 = generate_safe_filename(original, user_id)
        safe_name2 = generate_safe_filename(original, user_id)

        assert safe_name1 == safe_name2

    def test_filename_uniqueness_across_users(self):
        """Test that different users get different safe filenames."""
        original = "document.pdf"

        safe_name1 = generate_safe_filename(original, "user1")
        safe_name2 = generate_safe_filename(original, "user2")

        assert safe_name1 != safe_name2
        assert safe_name1.startswith("user1_")
        assert safe_name2.startswith("user2_")

    def test_filename_uniqueness_across_originals(self):
        """Test that different original names get different safe filenames."""
        user_id = "user123"

        safe_name1 = generate_safe_filename("file1.txt", user_id)
        safe_name2 = generate_safe_filename("file2.txt", user_id)

        assert safe_name1 != safe_name2
        both_start_with_user_id = safe_name1.startswith(user_id + "_") and safe_name2.startswith(user_id + "_")
        assert both_start_with_user_id

    def test_extension_preservation(self):
        """Test that file extensions are properly preserved."""
        test_cases = [
            ("document.pdf", ".pdf"),
            ("image.JPEG", ".jpeg"),  # Should be lowercase
            ("data.CSV", ".csv"),
            ("archive.ZIP", ".zip"),
            ("no_extension", ""),
        ]

        for original, expected_ext in test_cases:
            safe_name = generate_safe_filename(original, "user123")
            assert safe_name.endswith(expected_ext), f"Expected {expected_ext} for {original}, got {safe_name}"

    def test_hash_component_length(self):
        """Test that hash component has expected length."""
        safe_name = generate_safe_filename("test.txt", "user123")

        # Remove user prefix and extension
        parts = safe_name[len("user123_") :].split(".")
        hash_part = parts[0]

        # Should be 8 characters (truncated MD5)
        assert len(hash_part) == 8
        assert hash_part.isalnum()


class TestConstants:
    """Test file utility constants."""

    def test_allowed_extensions(self):
        """Test that allowed extensions are properly defined."""
        assert isinstance(ALLOWED_EXTENSIONS, set)
        assert ".pdf" in ALLOWED_EXTENSIONS
        assert ".jpg" in ALLOWED_EXTENSIONS
        assert ".txt" in ALLOWED_EXTENSIONS
        assert ".exe" not in ALLOWED_EXTENSIONS

    def test_allowed_mime_types(self):
        """Test that allowed MIME types are properly defined."""
        assert isinstance(ALLOWED_MIME_TYPES, set)
        assert "application/pdf" in ALLOWED_MIME_TYPES
        assert "image/jpeg" in ALLOWED_MIME_TYPES
        assert "text/plain" in ALLOWED_MIME_TYPES
        assert "application/x-executable" not in ALLOWED_MIME_TYPES

    def test_file_type_mapping(self):
        """Test file type mapping constants."""
        assert isinstance(FILE_TYPE_MAPPING, dict)
        assert FILE_TYPE_MAPPING["image/jpeg"] == "image"
        assert FILE_TYPE_MAPPING["application/pdf"] == "document"
        assert FILE_TYPE_MAPPING["text/plain"] == "text"

    def test_size_limits(self):
        """Test size limit constants."""
        assert isinstance(MAX_FILE_SIZE, int)
        assert isinstance(MAX_FILES_PER_REQUEST, int)
        assert isinstance(MAX_SESSION_SIZE, int)
        assert MAX_FILE_SIZE > 0
        assert MAX_SESSION_SIZE >= MAX_FILE_SIZE

    def test_suspicious_patterns(self):
        """Test suspicious pattern constants."""
        assert isinstance(SUSPICIOUS_PATTERNS, set)
        assert ".." in SUSPICIOUS_PATTERNS
        assert ".exe" in SUSPICIOUS_PATTERNS
        assert "/" in SUSPICIOUS_PATTERNS
        assert "\\" in SUSPICIOUS_PATTERNS


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def create_upload_file(self, filename: str, content: bytes) -> UploadFile:
        """Helper to create UploadFile for testing."""
        file_obj = BytesIO(content)
        return UploadFile(filename=filename, file=file_obj)

    async def test_file_with_unicode_filename(self):
        """Test handling of unicode characters in filenames."""
        unicode_filename = "文档.txt"  # Chinese characters
        file = self.create_upload_file(unicode_filename, b"content")

        result = await validate_file(file)
        # Should handle unicode gracefully (either accept or reject consistently)
        assert isinstance(result.is_valid, bool)

    async def test_very_large_filename(self):
        """Test handling of extremely large filenames."""
        large_filename = "a" * 1000 + ".txt"
        file = self.create_upload_file(large_filename, b"content")

        result = await validate_file(file)
        assert not result.is_valid
        assert "too long" in result.error_message

    async def test_filename_with_null_bytes(self):
        """Test handling of filenames with null bytes."""
        null_filename = "test\x00.txt"
        file = self.create_upload_file(null_filename, b"content")

        result = await validate_file(file)
        # Should reject files with null bytes in filename
        assert not result.is_valid

    async def test_zero_byte_file_edge_case(self):
        """Test edge case of exactly zero-byte file."""
        file = self.create_upload_file("zero.txt", b"")

        result = await validate_file(file)
        assert not result.is_valid
        assert "empty" in result.error_message
        assert result.file_size == 0

    async def test_maximum_allowed_size_boundary(self):
        """Test files at exactly the maximum allowed size."""
        # File exactly at the limit
        content = b"x" * MAX_FILE_SIZE
        file = self.create_upload_file("boundary.txt", content)

        result = await validate_file(file)
        # Should be accepted (at limit, not over)
        assert result.is_valid
        assert result.file_size == MAX_FILE_SIZE

        # File one byte over the limit
        content_over = b"x" * (MAX_FILE_SIZE + 1)
        file_over = self.create_upload_file("over_boundary.txt", content_over)

        result_over = await validate_file(file_over)
        assert not result_over.is_valid
        assert "exceeds maximum" in result_over.error_message
