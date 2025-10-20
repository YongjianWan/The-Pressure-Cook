# Usage:
#   python3 scale_zones.py ../zones.json 1280 720 1920 1080 > ../zones.json
import json, sys

if len(sys.argv) != 6:
    print("用法: python3 scale_zones.py <zones.json> <原寬> <原高> <新寬> <新高>")
    print("例:   python3 scale_zones.py ../zones.json 1280 720 1920 1080 > ../zones.json")
    print("Usage: python3 scale_zones.py <zones.json> <old_w> <old_h> <new_w> <new_h>")
    print("Example: python3 scale_zones.py ../zones.json 1280 720 1920 1080 > ../zones.json")
    sys.exit(1)

path, ow, oh, nw, nh = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
sx, sy = nw/ow, nh/oh
with open(path,'r',encoding='utf-8') as f:
    zones = json.load(f)

for poly in zones:
    poly['pts'] = [[int(x*sx), int(y*sy)] for (x,y) in poly['pts']]

print(json.dumps(zones, ensure_ascii=False, indent=2))
