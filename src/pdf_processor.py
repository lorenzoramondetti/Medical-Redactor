import fitz  # PyMuPDF
import re
from io import BytesIO
from PIL import Image
from utils import logger

class PDFProcessor:
    def __init__(self, file_bytes):
        self.doc = fitz.open(stream=file_bytes, filetype="pdf")

    def get_page_count(self):
        return len(self.doc)

    def extract_text(self, page_index):
        if 0 <= page_index < len(self.doc):
            return self.doc[page_index].get_text()
        return ""

    def render_page_for_canvas(self, page_index, terms_to_highlight=None, max_width=800):
        """
        Renders a page used for the Manual Redaction Canvas.
        Returns: (PIL Image, scale_factor, original_dimensions)
        """
        if not (0 <= page_index < len(self.doc)):
            return None, 1.0, (0, 0)

        page = self.doc[page_index]
        
        # 1. Get filtered rectangles for terms (Whole words only)
        all_terms_rects = []
        if terms_to_highlight:
            words = page.get_text("words") # (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            for term in terms_to_highlight:
                candidates = page.search_for(term)
                for rect in candidates:
                    if self._is_whole_word(rect, term, words):
                        all_terms_rects.append(rect)

        # Create a temporary PDF page to draw text highlights (simulating redaction view)
        # We don't want to modify the actual doc yet.
        temp_doc = fitz.open()
        temp_page = temp_doc.new_page(width=page.rect.width, height=page.rect.height)
        temp_page.show_pdf_page(temp_page.rect, self.doc, page_index)
        
        # Highlight terms (Preview Only)
        if all_terms_rects:
            shape = temp_page.new_shape()
            for rect in all_terms_rects:
                # Red semi-transparent rect
                shape.draw_rect(rect)
                shape.finish(color=(1, 0, 0), fill=(1, 0, 0), fill_opacity=0.3)
            shape.commit()

        # Render high quality
        pix = temp_page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Resize for display
        original_width, original_height = pix.width, pix.height
        
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # The canvas pixels are different from PDF points
            # We need the scale from Canvas Pixels -> PDF Points
            # PDF Points width = page.rect.width
            # Canvas width = max_width
            scale_x = page.rect.width / max_width
            scale_y = page.rect.height / new_height
            
            return img, scale_x, scale_y
        else:
            scale_x = page.rect.width / img.width
            scale_y = page.rect.height / img.height
            return img, scale_x, scale_y

    def save_redacted_pdf(self, redaction_map, manual_rects_map):
        """
        Applies redactions irreversibly.
        :param redaction_map: {page_index: [list of terms]}
        :param manual_rects_map: {page_index: [[x0,y0,x1,y1], ...]} # Note: handled per-file logic in main, but here we expect a map for this specific doc
        """
        # We work on a copy or the current doc? Let's assume we modify self.doc or a copy.
        # Ideally, reload from bytes to be fresh if called multiple times, but here usually called once at end.
        
        for i in range(len(self.doc)):
            page = self.doc[i]
            
            # 1. Text Redactions
            if i in redaction_map:
                terms = redaction_map[i]
                words = page.get_text("words")
                for term in terms:
                    candidates = page.search_for(term)
                    for rect in candidates:
                        if self._is_whole_word(rect, term, words):
                            page.add_redact_annot(rect, fill=(0, 0, 0))
            
            # 2. Manual Redactions (Rectangles)
            # Manual rects might be applied to ALL pages or Specific pages. 
            # The Logic in main decides which rects go where. 
            # Here we expect `manual_rects_map` to be fully resolved: {page_idx: [rects...]}
            if i in manual_rects_map:
                pages_rects = manual_rects_map[i]
                for r in pages_rects:
                    rect = fitz.Rect(r)
                    page.add_redact_annot(rect, fill=(0, 0, 0))
            
            # Apply and scrub
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE) 
        
        # Initialize output buffer
        out_buffer = BytesIO()
        
        # Save with garbage collection and deflate to minimize size and remove history
        self.doc.save(out_buffer, garbage=4, deflate=True)
        return out_buffer.getvalue()

    def _is_whole_word(self, rect, term, page_words):
        """
        Validates if a found rectangle corresponds to a whole word (or sequence of words).
        Prevents partial matches like 'Rossi' inside 'Prossimo'.
        """
        def normalize(text):
            # Lowercase and replace non-alphanumeric with spaces, then collapse
            clean = re.sub(r'[^a-z0-9]', ' ', text.lower())
            return " ".join(clean.split())

        term_norm = normalize(term)
        
        # Find all words that significantly overlap with the candidate rectangle
        # Important: Use '&' operator to avoid in-place modification of rect
        overlapping_words = []
        for w in page_words:
            w_rect = fitz.Rect(w[:4])
            intersection = rect & w_rect
            
            # Check if the match covers most of the individual WORD's area (90%)
            if w_rect.get_area() > 0 and (intersection.get_area() / w_rect.get_area()) > 0.9:
                 overlapping_words.append(w[4])
        
        if not overlapping_words:
            return False
            
        # Reconstruct the overlapping context (full strings of words found)
        context_norm = normalize(" ".join(overlapping_words))
        
        # A match is valid if the normalized term is effectively a full word match
        # against the normalized context.
        return term_norm == context_norm or term_norm in context_norm or context_norm in term_norm

    def close(self):
        self.doc.close()
