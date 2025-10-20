# make_aruco_duplex.py - A4 duplex identical graphics (page 2 can rotate 180 degrees and apply offset compensation)
# Requirement: pip install opencv-contrib-python reportlab
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import black
import cv2, numpy as np

# ========= Configurable Parameters =========
IDS        = [1, 2, 3]   # merged_code_cam uses IDs 1/2/3
SIZE_MM    = 50          # Marker edge length (mm)
BORDERBITS = 1
DPI        = 300
MARGIN_MM  = 15          # Margin around all sides (mm)
GAP_MM     = 12          # Spacing between markers (mm)
FONT_SIZE  = 10
OUT_DIR    = "aruco_out"
PDF_NAME   = f"aruco_4x4_50_IDs_{'_'.join(map(str,IDS))}_{SIZE_MM}mm_A4_duplex.pdf"

# Duplex alignment controls (use these when the two sides misalign):
BACK_ROTATE_180 = False   # Set True if your printer flips on the short edge; long-edge flips usually stay False
BACK_OFFSET_MM_X = 1.0    # Horizontal offset of page 2 relative to page 1 (+ right / - left)
BACK_OFFSET_MM_Y = 2.0    # Vertical offset of page 2 relative to page 1 (+ up / - down)

# ========= Generate ArUco Markers =========
try:
    import cv2.aruco as aruco
except Exception as e:
    raise RuntimeError("cv2.aruco not found; install with: pip install opencv-contrib-python") from e

aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

def gen_marker_img(marker_id: int, px: int, border_bits: int = 1) -> np.ndarray:
    if hasattr(aruco, "generateImageMarker"):
        return aruco.generateImageMarker(aruco_dict, marker_id, px, borderBits=border_bits)
    img = np.full((px, px), 255, np.uint8)
    aruco.drawMarker(aruco_dict, marker_id, px, img, borderBits=border_bits)
    return img

def mm2px(mm_val, dpi=DPI):
    return int(round(mm_val / 25.4 * dpi))

def draw_crop_marks(c: canvas.Canvas, x, y, w, h, len_mm=6, inset_mm=0):
    L = len_mm * mm
    I = inset_mm * mm
    c.setLineWidth(0.3)
    # Bottom left
    c.line(x - I, y, x - I + L, y)
    c.line(x, y - I, x, y - I + L)
    # Bottom right
    c.line(x + w + I - L, y, x + w + I, y)
    c.line(x + w, y - I, x + w, y - I + L)
    # Top left
    c.line(x - I, y + h, x - I + L, y + h)
    c.line(x, y + h + I - L, x, y + h + I)
    # Top right
    c.line(x + w + I - L, y + h, x + w + I, y + h)
    c.line(x + w, y + h + I - L, x + w, y + h + I)

def draw_center_marks(c: canvas.Canvas, page_w, page_h):
    c.setLineWidth(0.3)
    c.setStrokeColor(black)
    # Short centerline markers (front/back alignment reference)
    c.line(page_w/2 - 5*mm, 10*mm, page_w/2 + 5*mm, 10*mm)
    c.line(page_w/2 - 5*mm, page_h - 10*mm, page_w/2 + 5*mm, page_h - 10*mm)
    c.line(10*mm, page_h/2 - 5*mm, 10*mm, page_h/2 + 5*mm)
    c.line(page_w - 10*mm, page_h/2 - 5*mm, page_w - 10*mm, page_h/2 + 5*mm)

def build_layout(c: canvas.Canvas, png_paths, size_mm, margin_mm, gap_mm):
    page_w, page_h = A4
    box = size_mm * mm
    margin = margin_mm * mm
    gap = gap_mm * mm

    draw_center_marks(c, page_w, page_h)

    x = margin
    y = page_h - margin - box

    for mid, path in png_paths:
        # Marker image
        c.drawImage(path, x, y, width=box, height=box, preserveAspectRatio=True, mask='auto')
        # Label
        c.setFont("Helvetica", FONT_SIZE)
        c.drawCentredString(x + box/2, y - 4*mm, f"DICT_4X4_50  ID {mid}  ({size_mm}mm)")
        # Crop marks
        draw_crop_marks(c, x, y, box, box)

        x += box + gap
        if x + box > page_w - margin:  # Wrap to next row
            x = margin
            y -= (box + gap + 8*mm)
            if y < margin + box:
                c.showPage()
                draw_center_marks(c, page_w, page_h)
                y = page_h - margin - box

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # 1) Generate PNG (includes a 10% quiet zone)
    px = mm2px(SIZE_MM, DPI)
    pad = int(px * 0.10)
    png_paths = []
    for mid in IDS:
        marker = gen_marker_img(mid, px, border_bits=BORDERBITS)
        canvas_img = np.full((px + 2*pad, px + 2*pad), 255, np.uint8)
        canvas_img[pad:pad+px, pad:pad+px] = marker
        p = os.path.join(OUT_DIR, f"aruco_4x4_50_id{mid}_{SIZE_MM}mm_{DPI}dpi.png")
        cv2.imwrite(p, canvas_img)
        png_paths.append((mid, p))

    # 2) Create duplex PDF: both pages identical, with optional rotation/offset on page 2
    page_w, page_h = A4
    pdf_path = os.path.join(OUT_DIR, PDF_NAME)
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setTitle("ArUco 4x4_50 duplex same content")

    # Page 1 (front as-is)
    build_layout(c, png_paths, SIZE_MM, MARGIN_MM, GAP_MM)
    c.showPage()

    # Page 2 (same graphics; optional 180-degree rotation and offset compensation)
    if BACK_ROTATE_180:
        c.translate(page_w, page_h)
        c.rotate(180)
    if BACK_OFFSET_MM_X or BACK_OFFSET_MM_Y:
        c.translate(BACK_OFFSET_MM_X * mm, BACK_OFFSET_MM_Y * mm)

    build_layout(c, png_paths, SIZE_MM, MARGIN_MM, GAP_MM)
    c.showPage()

    c.save()
    print("[OK] Output:", pdf_path)
    print("Print suggestion: A4, 100% scale, duplex (long-edge or short-edge flip per your setting), no auto scaling.")

if __name__ == "__main__":
    main()
