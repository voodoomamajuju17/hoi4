"""Distancia de color CIEDE2000 (sRGB/D65), para las pruebas de la paleta del mapa (2026-11-15)."""
import math, re, itertools, yaml, sys
def lab(rgb):
    def f(c):
        c/=255; return ((c+0.055)/1.055)**2.4 if c>0.04045 else c/12.92
    r,g,b=map(f,rgb)
    x=(r*0.4124+g*0.3576+b*0.1805)/0.95047; y=r*0.2126+g*0.7152+b*0.0722; z=(r*0.0193+g*0.1192+b*0.9505)/1.08883
    g_=lambda t: t**(1/3) if t>0.008856 else 7.787*t+16/116
    return 116*g_(y)-16, 500*(g_(x)-g_(y)), 200*(g_(y)-g_(z))
def de(c1,c2):
    L1,a1,b1=lab(c1);L2,a2,b2=lab(c2)
    C1=math.hypot(a1,b1);C2=math.hypot(a2,b2);Cb=(C1+C2)/2
    G=0.5*(1-math.sqrt(Cb**7/(Cb**7+25**7)));a1p=a1*(1+G);a2p=a2*(1+G)
    C1p=math.hypot(a1p,b1);C2p=math.hypot(a2p,b2)
    h1=math.degrees(math.atan2(b1,a1p))%360;h2=math.degrees(math.atan2(b2,a2p))%360
    dL=L2-L1;dC=C2p-C1p
    dh=h2-h1
    if C1p*C2p==0: dh=0
    elif dh>180: dh-=360
    elif dh<-180: dh+=360
    dH=2*math.sqrt(C1p*C2p)*math.sin(math.radians(dh/2))
    Lb=(L1+L2)/2;Cbp=(C1p+C2p)/2
    if C1p*C2p==0: hb=h1+h2
    elif abs(h1-h2)<=180: hb=(h1+h2)/2
    elif h1+h2<360: hb=(h1+h2+360)/2
    else: hb=(h1+h2-360)/2
    T=1-0.17*math.cos(math.radians(hb-30))+0.24*math.cos(math.radians(2*hb))+0.32*math.cos(math.radians(3*hb+6))-0.20*math.cos(math.radians(4*hb-63))
    dt=30*math.exp(-((hb-275)/25)**2);RC=2*math.sqrt(Cbp**7/(Cbp**7+25**7))
    SL=1+0.015*(Lb-50)**2/math.sqrt(20+(Lb-50)**2);SC=1+0.045*Cbp;SH=1+0.015*Cbp*T;RT=-math.sin(math.radians(2*dt))*RC
    return math.sqrt((dL/SL)**2+(dC/SC)**2+(dH/SH)**2+RT*(dC/SC)*(dH/SH))
