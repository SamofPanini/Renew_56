import json,sys
d=json.load(open(sys.argv[1]))
P="北京 天津 河北 山西 内蒙古 辽宁 吉林 黑龙江 上海 江苏 浙江 安徽 福建 江西 山东 河南 湖北 湖南 广东 广西 海南 重庆 四川 贵州 云南 西藏 陕西 甘肃 青海 宁夏 新疆".split()
v=lambda x:0 if x in (None,'') else int(x)
bad=0
for i,r in enumerate(d):
    # empty cell must be diagonal only
    s=sum(v(x) for x in r[1:])
    if s!=v(r[0]): bad+=1; print('row',i,(P[i-1] if i else '全国'),'diff',v(r[0])-s)
    if i>0:
        for c in range(3,34):
            if (r[c] is None)!=(c-3==i-1): print('empty mismatch',i,c,r[c])
for c in range(0,35):
    s=sum(v(d[i][c]) for i in range(1,32))
    if s!=v(d[0][c]): bad+=1; print('col',c,(P[c-3] if 3<=c<34 else c),'diff',v(d[0][c])-s)
print('bad',bad)
