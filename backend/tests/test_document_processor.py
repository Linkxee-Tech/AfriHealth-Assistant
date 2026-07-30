from backend.core.document_processor import DocumentProcessor


def test_text_document_processing_and_chunking():
    result = DocumentProcessor().process_document(b"Fever and malaria guidance.\n" * 20, "notes.txt")
    assert result["raw_text"]
    assert result["chunks"]
    assert all(item["text"] for item in result["chunks"])
