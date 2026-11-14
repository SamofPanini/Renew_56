import json
from collections import Counter
D=[json.load(open(f'work/ocr{s}.json')) for s in (3,4,5,6)]
R,C=32,35
v=lambda x:0 if x in (None,'') else int(x)
cand=[[Counter(d[i][c] for d in D) for c in range(C)] for i in range(R)]
G=[[cand[i][c].most_common(1)[0][0] for c in range(C)] for i in range(R)]
def rowdiff(i): return v(G[i][0])-sum(v(x) for x in G[i][1:])
def coldiff(c): return v(G[0][c])-sum(v(G[i][c]) for i in range(1,R))
changed=True; it=0
while changed and it<50:
    changed=False; it+=1
    br=[i for i in range(R) if rowdiff(i)]; bc=[c for c in range(C) if coldiff(c)]
    for i in br:
        for c in bc:
            rd,cd=rowdiff(i),coldiff(c)
            if not rd or not cd: continue
            for alt in cand[i][c]:
                if alt==G[i][c]: continue
                delta=v(alt)-v(G[i][c])
                # cell in data region (i>0, c>0) affects row-sum (subtract) & col-sum
                if i>0 and c>0 and delta==rd and delta==cd: G[i][c]=alt; changed=True; print('fix',i,c,alt)
                # total col c==0 cell or total row i==0 cell
br=[(i,rowdiff(i)) for i in range(R) if rowdiff(i)]; bc=[(c,coldiff(c)) for c in range(C) if coldiff(c)]
print('rows',br); print('cols',bc)
json.dump(G,open('work/G.json','w'))
