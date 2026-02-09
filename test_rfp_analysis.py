"""
Test script for orchestrated RFP analysis using the Woodgrove Bank RFP document.

This script:
1. Reads the Woodgrove Bank RFP PDF
2. Sends it to the orchestrated analysis endpoint
3. Displays the results from all three agents
"""

import requests
import json
from pathlib import Path

# Try to import PyPDF2 for PDF reading
try:
    import PyPDF2
    HAS_PDF_SUPPORT = True
except ImportError:
    HAS_PDF_SUPPORT = False
    print("⚠️  PyPDF2 not installed. Install with: pip install PyPDF2")


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    if not HAS_PDF_SUPPORT:
        raise ImportError("PyPDF2 is required. Install with: pip install PyPDF2")
    
    text_content = []
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        print(f"📄 Reading PDF: {Path(pdf_path).name}")
        print(f"   Pages: {len(pdf_reader.pages)}")
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            text = page.extract_text()
            text_content.append(text)
            print(f"   ✓ Extracted page {page_num}")
    
    return "\n\n".join(text_content)


def analyze_rfp(rfp_content: str, rfp_name: str, api_url: str = "http://localhost:8000") -> dict:
    """
    Send RFP to orchestrated analysis endpoint.
    
    Args:
        rfp_content: Full text content of the RFP
        rfp_name: Name/title of the RFP
        api_url: Base URL of the API (default: http://localhost:8000)
    
    Returns:
        Dictionary containing the analysis results
    """
    endpoint = f"{api_url}/api/rfp/analyze"
    
    payload = {
        "rfp_content": rfp_content,
        "rfp_name": rfp_name
    }
    
    print(f"\n{'='*60}")
    print(f"🚀 Sending RFP to orchestrated analysis endpoint...")
    print(f"{'='*60}")
    
    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minutes timeout for agent processing
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ ERROR: Cannot connect to {api_url}")
        print("   Make sure the backend server is running: python webapp/backend/api.py")
        raise
    except requests.exceptions.Timeout:
        print(f"\n❌ ERROR: Request timed out after 5 minutes")
        raise
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ ERROR: HTTP {response.status_code}")
        print(f"   {response.text}")
        raise


def display_results(results: dict):
    """Display the orchestrated analysis results in a formatted way."""
    print(f"\n{'='*60}")
    print(f"✅ ORCHESTRATED ANALYSIS COMPLETE")
    print(f"{'='*60}")
    
    print(f"\n📋 RFP: {results['rfp_name']}")
    
    print(f"\n{'─'*60}")
    print("📊 EXECUTIVE SUMMARY (rfp-summary-agent)")
    print(f"{'─'*60}")
    print(results['summary'])
    
    print(f"\n{'─'*60}")
    print("⚠️  RISK ASSESSMENT (rfp-risk-agent)")
    print(f"{'─'*60}")
    print(results['risks'])
    
    print(f"\n{'─'*60}")
    print("✓ COMPLIANCE ANALYSIS (rfp-compliance-agent)")
    print(f"{'─'*60}")
    print(results['compliance'])
    
    print(f"\n{'='*60}")
    print("💾 FULL REPORT")
    print(f"{'='*60}")
    print(results['full_report'])


def save_results(results: dict, output_file: str = "rfp_analysis_results.json"):
    """Save the analysis results to a JSON file."""
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Results saved to: {output_path.absolute()}")


def main():
    """Main function to test RFP analysis."""
    # Path to the Woodgrove Bank RFP PDF
    rfp_pdf_path = Path(__file__).parent / "woodgrove_bank_rfp_response_contoso_ltd.pdf"
    
    if not rfp_pdf_path.exists():
        print(f"❌ ERROR: RFP file not found: {rfp_pdf_path}")
        print("   Available RFP files:")
        for pdf_file in Path(__file__).parent.glob("*.pdf"):
            print(f"   - {pdf_file.name}")
        return
    
    try:
        # Step 1: Extract text from PDF
        print(f"\n{'='*60}")
        print("STEP 1: Extract RFP Content from PDF")
        print(f"{'='*60}")
        rfp_content = extract_text_from_pdf(str(rfp_pdf_path))
        print(f"✓ Extracted {len(rfp_content)} characters")
        
        # Step 2: Send to orchestrated analysis
        print(f"\n{'='*60}")
        print("STEP 2: Orchestrated Multi-Agent Analysis")
        print(f"{'='*60}")
        results = analyze_rfp(
            rfp_content=rfp_content,
            rfp_name="Woodgrove Bank RFP - Contoso Ltd Response"
        )
        
        # Step 3: Display results
        print(f"\n{'='*60}")
        print("STEP 3: Display Results")
        print(f"{'='*60}")
        display_results(results)
        
        # Step 4: Save results
        save_results(results, "woodgrove_rfp_analysis.json")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
