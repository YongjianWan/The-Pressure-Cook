import cv2, json, numpy as np

WIN='ROI Calibrator'; zones=[]; current=[]; snap=None
def draw():
    if snap is None:
        return
    img=snap.copy()
    for z in zones:
        pts=np.array(z['pts'],np.int32)
        cv2.polylines(img,[pts],True,(0,255,0),2)
        M=pts.mean(axis=0).astype(int)
        cv2.putText(img,z['name'],tuple(M),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)
    if current:
        pts=np.array(current,np.int32); cv2.polylines(img,[pts],False,(0,200,255),2)
    cv2.imshow(WIN,img)

def on_mouse(e,x,y,flags,param):
    if e==cv2.EVENT_LBUTTONDOWN: current.append((x,y)); draw()
    elif e==cv2.EVENT_RBUTTONDOWN and len(current)>=3:
        name=input('ROI name (TABLE/TRAY/PLATE/...): ').strip() or f'ROI{len(zones)+1}'
        zones.append({'name':name,'pts':current.copy()}); current.clear(); draw()

cap=cv2.VideoCapture(0); ok,frame=cap.read(); cap.release()
if not ok: raise RuntimeError('Failed to read from camera')
snap=frame.copy(); cv2.namedWindow(WIN); cv2.setMouseCallback(WIN,on_mouse); draw()
print('Controls: left-click to add points, right-click/Enter to name ROI; U undo point; Z remove last ROI; S save; Q quit.')
while True:
    k=cv2.waitKey(20)&0xff
    if k in (27, ord('q')): break
    if k==ord('u') and current: current.pop(); draw()
    if k==ord('z') and zones: zones.pop(); draw()
    if k==ord('s'):
        with open('zones.json','w',encoding='utf-8') as f: json.dump(zones,f,ensure_ascii=False,indent=2)
        print('Saved zones.json')
cv2.destroyAllWindows()
