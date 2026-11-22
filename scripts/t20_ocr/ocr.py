import sys, json, numpy as np, pytesseract
from PIL import Image, ImageOps
img=Image.open(sys.argv[1]).convert('L')
xs=[72+85*k for k in range(35)]+[3046]
rows=[(229, 239), (293, 303), (325, 335), (357, 367), (389, 399), (421, 431), (485, 495), (517, 527), (549, 559), (613, 623), (645, 655), (677, 687), (709, 719), (741, 751), (773, 783), (805, 815), (869, 879), (901, 911), (933, 943), (965, 975), (997, 1007), (1029, 1039), (1093, 1103), (1125, 1135), (1157, 1167), (1189, 1199), (1221, 1231), (1285, 1295), (1317, 1327), (1349, 1359), (1381, 1391), (1413, 1423)]
scale=int(sys.argv[3]) if len(sys.argv)>3 else 4
out=[]
for (y0,y1) in rows:
    r=[]
    for c in range(35):
        cell=img.crop((xs[c]+2,y0-4,xs[c+1]-2,y1+4))
        a=np.array(cell)
        if (a<200).sum()<3: r.append(None); continue
        cell=cell.resize((cell.width*scale,cell.height*scale),Image.LANCZOS)
        cell=ImageOps.expand(cell,20,fill=255)
        t=pytesseract.image_to_string(cell,config='--psm 7 -c tessedit_char_whitelist=0123456789').strip()
        r.append(t)
    out.append(r)
json.dump(out,open(sys.argv[2],'w'))
