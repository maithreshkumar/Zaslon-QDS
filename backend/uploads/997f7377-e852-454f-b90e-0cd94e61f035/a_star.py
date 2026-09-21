from heapq import *

g={'A':{'B':1,'C':4},'B':{'D':2},'C':{'D':1},'D':{}}
h={'A':3,'B':2,'C':1,'D':0}

q=[(h['A'],0,'A',[])]
while q:
    f,c,n,p=heappop(q)
    if n=='D':
        print(p+[n],c); break
    for x,w in g[n].items():
        nc=c+w
        heappush(q,(nc+h[x],nc,x,p+[n]))