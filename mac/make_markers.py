import cv2, os
from cv2 import aruco

OUT="markers"  # 輸出資料夾 / Output folder
os.makedirs(OUT, exist_ok=True)

DICT = aruco.DICT_5X5_100   # 如沿用舊紙可改 aruco.DICT_4X4_50 / Use aruco.DICT_4X4_50 for old paper
IDS  = [10,11,20,21,30,31,32,33,40,50]  # 你要輸出的 ID / IDs to generate
SIZE = 600  # 圖片邊長像素（600px 約可印 25~50mm，視 DPI 調整）/ Image size in pixels (600px prints about 25~50mm, adjust by DPI)

d = aruco.getPredefinedDictionary(DICT)
for mid in IDS:
    img = aruco.generateImageMarker(d, mid, SIZE)
    cv2.imwrite(os.path.join(OUT, f"aruco_{mid}.png"), img)
print(f"Output {len(IDS)} images to {OUT}/. Please print at 300DPI and keep the white border.")
