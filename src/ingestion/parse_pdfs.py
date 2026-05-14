import pdfplumber
import yaml
import json
from pathlib import Path
 
 
def load_registry(registry_path: str | Path) -> list[dict]:
    """
    Load the document registry YAML and return only in-scope documents.
    """
    registry_path = Path(registry_path)
    with open(registry_path) as f:
        raw = yaml.safe_load(f)
 
    in_scope = [doc for doc in raw["documents"] if doc.get("in_scope", False)]
    print(f"Registry loaded: {len(in_scope)} in-scope documents found.")
    return in_scope
 
 
def parse_pdf(doc_entry: dict, base_dir: str | Path) -> list[dict]:
    """
    Parse a single PDF using its registry entry for metadata.
 
    file_path in the registry is relative to base_dir (the project root).
    Returns a list of page objects, each containing:
        - text: raw extracted text for that page
        - metadata: all registry fields plus page_number and source_file
    """
    base_dir = Path(base_dir)
    pdf_path = base_dir / doc_entry["file_path"]
 
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
 
    # Build the metadata dict from the registry entry.
    # Optional fields (document_title, pds_version) are included as None if
    # blank — keeps the metadata schema consistent across all documents so
    # downstream filtering never has to handle missing keys.
    metadata_base = {
        "insurer": doc_entry["insurer"],
        "document_type": doc_entry.get("document_type"),
        "document_title": doc_entry.get("document_title") or None,
        "pds_version": doc_entry.get("pds_version") or None,
        "effective_date": str(doc_entry.get("effective_date")),
        "accessed_date": str(doc_entry.get("accessed_date")),
        "coverage_scope": doc_entry.get("coverage_scope"),
        "source_file": pdf_path.name,
    }
 
    pages = []
 
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
 
            # Skip pages with no extractable text (cover images, blank pages,
            # graphical pages). These would produce empty chunks downstream.
            if not text or not text.strip():
                continue
 
            page_obj = {
                "text": text.strip(),
                "metadata": {
                    **metadata_base,
                    # pdfplumber is 1-indexed here — matches physical page
                    # numbers in the printed document.
                    "page_number": page.page_number,
                },
            }
            pages.append(page_obj)
 
    return pages
 
 
def parse_all(registry_path: str | Path, base_dir: str | Path) -> list[dict]:
    """
    Parse all in-scope PDFs listed in the registry.
    Returns a flat list of page objects across all documents.
    """
    registry = load_registry(registry_path)
    all_pages = []
 
    for doc_entry in registry:
        insurer = doc_entry["insurer"]
        print(f"  Parsing {insurer}...")
        try:
            pages = parse_pdf(doc_entry, base_dir)
            print(f"    {len(pages)} pages extracted.")
            all_pages.extend(pages)
        except FileNotFoundError as e:
            print(f"    WARNING: {e} — skipping.")
 
    print(f"\nTotal pages extracted across all documents: {len(all_pages)}")
    return all_pages
 
 
# ---------------------------------------------------------------------------
# Test block
# Run against a single insurer by name to inspect output before processing
# the full corpus.
#
# Usage:
#   python parse_pdfs.py <path_to_registry.yaml> <project_root> [insurer_name]
#
# Examples:
#   python ./src/ingestion/parse_pdfs.py ./corpus/metadata/document_registry.yaml . NRMA
#   python ./src/ingestion/parse_pdfs.py ./corpus/metadata/document_registry.yaml .        # parses all
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
 
    if len(sys.argv) < 3:
        print("Usage: python parse_pdfs.py <registry.yaml> <project_root> [insurer]")
        sys.exit(1)
 
    registry_path = Path(sys.argv[1])
    base_dir = Path(sys.argv[2])
    target_insurer = sys.argv[3] if len(sys.argv) > 3 else None
 
    registry = load_registry(registry_path)
 
    if target_insurer:
        # Filter to the single requested insurer for inspection
        registry = [d for d in registry if d["insurer"] == target_insurer]
        if not registry:
            print(f"No in-scope document found for insurer: {target_insurer}")
            sys.exit(1)
 
    for doc_entry in registry:
        insurer = doc_entry["insurer"]
        print(f"\nParsing: {insurer}")
        print("-" * 60)
 
        pages = parse_pdf(doc_entry, base_dir)
        print(f"Total pages extracted: {len(pages)}\n")
 
        # Print first three pages for spot-checking text and metadata
        for page in pages[:3]:
            print(f"--- Page {page['metadata']['page_number']} ---")
            print(f"Metadata: {json.dumps(page['metadata'], indent=2)}")
            print(f"Text preview:\n{page['text'][:400]}")
            print()