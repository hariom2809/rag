import logfire
from pypdf import PdfReader

def parse_pdf(file_path: str):
    with logfire.span("PDF Parser", filename=file_path):
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            logfire.info(f"PDF has {total_pages} pages")

            text_parts: list[str] = []
            blank_pages: list[int] = []

            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    text_parts.append(text)
                else:
                    blank_pages.append(i + 1)

            if blank_pages:
                logfire.info(f"⚠️ Pdf retured blank pages {blank_pages} - retrying with pyplumber")
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        for page_num in blank_pages:
                            page = pdf.pages[page_num - 1]
                            fallback_page = page.extract_text() or ""
                            if fallback_page.strip():
                                text_parts.append(fallback_page)
                except Exception as plumber_error:
                    logfire.warning(f"❌ PdfPlumber fallback Failed: {plumber_error}")

            full_text = "\n".join(text_parts)

            if not full_text.strip():
                logfire.warning(f"❌ No text extracted from {file_path}")
            else:
                logfire.info(f"✔️ Extracted {len(full_text)} from {file_path}")

            return full_text
        
        except Exception as e:
            logfire.error(f"❌ PDf Parsing Failed: {e}")
            raise e