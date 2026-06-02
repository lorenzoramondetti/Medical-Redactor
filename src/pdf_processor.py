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

    def render_page_for_canvas(self, page_index, terms_to_highlight=None, max_width=1100):
        """
        Renders a page used for the Manual Redaction Canvas.
        Returns: (PIL Image, scale_factor, original_dimensions)
        """
        if not (0 <= page_index < len(self.doc)):
            return None, 1.0, (0, 0)

        page = self.doc[page_index]
        
        # 1. Get filtered rectangles for terms (Whole words only)
        all_terms_rects = []
        seen_rects = set()
        
        if terms_to_highlight:
            words = page.get_text("words") # (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            for term in terms_to_highlight:
                candidates = page.search_for(term)
                for rect in candidates:
                    if self._is_whole_word(rect, term, words):
                        # Deduplicate overlapping rectangles for the same word
                        # Round to 1 decimal place to handle slight floating point differences
                        rect_key = (round(rect.x0, 1), round(rect.y0, 1), round(rect.x1, 1), round(rect.y1, 1))
                        if rect_key not in seen_rects:
                            seen_rects.add(rect_key)
                            all_terms_rects.append({"rect": rect, "term": term})

        # Non disegniamo più i rettangoli rossi sull'immagine PNG!
        # In questo modo il Canvas frontend riceverà un'immagine pulita 
        # e userà le rects per disegnare oggetti interattivi e selezionabili.
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Resize for display
        original_width, original_height = pix.width, pix.height
        
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            scale_x = page.rect.width / max_width
            scale_y = page.rect.height / new_height
            
            return img, scale_x, scale_y, all_terms_rects
        else:
            scale_x = page.rect.width / img.width
            scale_y = page.rect.height / img.height
            return img, scale_x, scale_y, all_terms_rects

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
            
            # Qualsiasi intersezione è sufficiente per considerare la parola come "contesto"
            if w_rect.get_area() > 0 and intersection.get_area() > 0:
                 overlapping_words.append(w[4])
        
        if not overlapping_words:
            return False
            
        # Reconstruct the overlapping context (full strings of words found)
        context = " ".join(overlapping_words)
        
        # Validazione tramite Regex Boundary customizzata:
        # Invece di usare \b, che fallisce se il termine finisce o inizia con punteggiatura (es. "O."),
        # usiamo lookaround per assicurarci che non ci siano altre lettere/numeri adiacenti.
        pattern = r'(?i)(?<!\w)' + re.escape(term) + r'(?!\w)'
        return bool(re.search(pattern, context))

    def close(self):
        self.doc.close()
