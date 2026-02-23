"""
generate_diagrams.py
--------------------
Standalone script to produce all engineering-page PNG diagrams.
Run with the project venv:
    /path/to/.venv/bin/python3 proof/generate_diagrams.py

Design principles
• DPI = 300  →  ~3600 px wide images, crystal-clear at any web size
• Minimum font size = 13 pt (most labels 14-16 pt)
• Large, well-spaced boxes — nothing overlapping
• All coordinates hand-tuned for each diagram
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
DPI = 300

# ─── Colour palette ───────────────────────────────────────────────────────────
BG        = '#0F0F1A'
SURFACE   = '#1A1A2E'
SURFACE2  = '#16213E'
VIOLET    = '#7C3AED'
VIOLET_LT = '#A78BFA'
GOLD      = '#F59E0B'
GOLD_LT   = '#FCD34D'
CYAN      = '#06B6D4'
GREEN     = '#10B981'
RED       = '#EF4444'
PINK      = '#EC4899'
TEXT      = '#E2E8F0'
TEXT_DIM  = '#94A3B8'
BORDER    = '#334155'

SAVE_KW = dict(dpi=DPI, bbox_inches='tight', facecolor=BG, edgecolor='none')

plt.rcParams.update({
    'figure.facecolor': BG,
    'axes.facecolor'  : BG,
    'text.color'      : TEXT,
    'font.family'     : ['DejaVu Sans'],
    'font.size'       : 14,
})

def save(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, **SAVE_KW)
    plt.close(fig)
    print(f'  [OK]  {name}')

def rbox(ax, x, y, w, h, fc, ec, lw=1.5, r=0.2, alpha=0.92, zorder=3):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f'round,pad=0.04,rounding_size={r}',
        facecolor=fc, edgecolor=ec, linewidth=lw, alpha=alpha, zorder=zorder))

def ctext(ax, cx, cy, txt, fs=14, color=TEXT, bold=False, italic=False, zorder=5, **kw):
    ax.text(cx, cy, txt, ha='center', va='center',
            fontsize=fs, color=color,
            fontweight='bold' if bold else 'normal',
            fontstyle='italic' if italic else 'normal',
            zorder=zorder, **kw)

def ltext(ax, x, y, txt, fs=14, color=TEXT, bold=False, zorder=5):
    ax.text(x, y, txt, ha='left', va='center',
            fontsize=fs, color=color,
            fontweight='bold' if bold else 'normal',
            zorder=zorder)

def arr(ax, x1, y1, x2, y2, color=TEXT_DIM, lw=1.8, label='', ls='solid', rad=0.0):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                connectionstyle=f'arc3,rad={rad}',
                                linestyle=ls), zorder=2)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my+0.12, label, ha='center', va='bottom',
                fontsize=12, color=color, zorder=6,
                bbox=dict(boxstyle='round,pad=0.15', facecolor=BG, edgecolor='none', alpha=0.85))

# ═══════════════════════════════════════════════════════════════════════════════
# 1 · SYSTEM ARCHITECTURE DIAGRAM
# ═══════════════════════════════════════════════════════════════════════════════
def make_architecture():
    FW, FH = 34, 22
    fig, ax = plt.subplots(figsize=(FW, FH))
    ax.set_xlim(0, FW); ax.set_ylim(0, FH); ax.axis('off')
    fig.patch.set_facecolor(BG)

    # Layer bands (y_bottom, y_top, fill, label)
    bands = [
        (18.5, 22.0, '#06B6D410', 'CLIENT LAYER'),
        (14.0, 18.4, '#7C3AED12', 'FRONTEND LAYER'),
        ( 8.5, 13.9, '#7C3AED22', 'API LAYER'),
        ( 3.2,  8.4, '#10B98118', 'DATA LAYER'),
        ( 0.3,  3.1, '#EC489918', 'ASYNC LAYER'),
    ]
    for yb, yt, fc, lbl in bands:
        ax.add_patch(plt.Rectangle((0.6, yb), FW-1.2, yt-yb,
                                   facecolor=fc, edgecolor=BORDER, linewidth=0.5, zorder=0))
        ax.text(0.9, (yb+yt)/2, lbl, va='center', ha='left',
                fontsize=10, color=TEXT_DIM, fontweight='bold', rotation=90, alpha=0.7)

    # ── Client ──────────────────────────────────────────────────────
    rbox(ax, 11, 19.3, 12, 1.5, SURFACE2, CYAN, lw=2)
    ctext(ax, 17, 20.35, '[www]  Browser / End User', fs=16, color=CYAN, bold=True)
    ctext(ax, 17, 19.75, 'booking.404by.me', fs=13, color=TEXT_DIM)

    # ── Legend (top right) ──────────────────────────────────────────
    legend = [(CYAN,'Frontend'),(VIOLET_LT,'API'),(GREEN,'Database'),
              (GOLD,'Redis'),(PINK,'Async'),(RED,'DB Lock')]
    for i,(c,lbl) in enumerate(legend):
        lx = 22 + i*2.0
        ax.add_patch(plt.Rectangle((lx, 21.1), 0.35, 0.28, facecolor=c, zorder=5))
        ax.text(lx+0.5, 21.24, lbl, va='center', fontsize=11, color=TEXT_DIM)

    # ── Next.js Frontend block ──────────────────────────────────────
    rbox(ax, 7, 16.2, 20, 1.2, '#1E3A5F', CYAN, lw=2)
    ctext(ax, 17, 17.0, 'Next.js 15  —  Frontend',           fs=16, color=CYAN, bold=True)
    ctext(ax, 17, 16.5, 'App Router · TypeScript · Tailwind CSS  |  :3000', fs=13, color=TEXT_DIM)

    pages = [('/events',8.0),('/events/[id]',11.0),('/bookings/my',14.0),('/organizer',17.0),('/login /signup',20.5)]
    for lbl, px in pages:
        rbox(ax, px-1.6, 14.5, 3.2, 0.8, '#0F2744', CYAN, r=0.15)
        ctext(ax, px, 14.9, lbl, fs=12, color=CYAN)
    ctext(ax, 17, 14.1, 'Pages', fs=12, color=TEXT_DIM)

    # ── FastAPI block ───────────────────────────────────────────────
    rbox(ax, 6, 11.5, 22, 1.2, '#2D1B69', VIOLET_LT, lw=2)
    ctext(ax, 17, 12.3, 'FastAPI 0.116  +  Uvicorn',          fs=16, color=VIOLET_LT, bold=True)
    ctext(ax, 17, 11.8, '/api/v1  ·  JWT Bearer Auth  ·  Pydantic v2  |  :8000', fs=13, color=TEXT_DIM)

    routes = [('/auth',7.5),('/users',10.0),('/events',12.5),('/bookings',15.0),('/organizer',17.5),('/metrics',20.5)]
    for lbl, rx in routes:
        rbox(ax, rx-1.7, 9.9, 3.4, 0.7, '#1E0F47', VIOLET_LT, r=0.12)
        ctext(ax, rx, 10.25, lbl, fs=12, color=VIOLET_LT)
    ctext(ax, 17, 9.5, 'Endpoints', fs=12, color=TEXT_DIM)

    svcs = [('BookingService', 8.2), ('EventService', 14.0), ('CacheService', 20.5)]
    for lbl, sx in svcs:
        rbox(ax, sx-2.6, 8.5, 5.2, 0.8, '#3D1F7A', VIOLET_LT, r=0.18)
        ctext(ax, sx, 8.9, lbl, fs=13, color=VIOLET_LT, bold=True)
    ctext(ax, 17, 8.1, 'Service Layer', fs=12, color=TEXT_DIM)

    # ── PostgreSQL ──────────────────────────────────────────────────
    rbox(ax, 2.5, 5.6, 14.5, 1.5, '#0F3D2A', GREEN, lw=2)
    ctext(ax, 9.75, 6.65, '[pg]  PostgreSQL 15', fs=16, color=GREEN, bold=True)
    ctext(ax, 9.75, 6.1, 'pool_size=20  ·  max_overflow=10  |  :5434→5432', fs=13, color=TEXT_DIM)

    tables = ['User','Venue','Seat','Event','Booking','Ticket [!]']
    for i,t in enumerate(tables):
        is_t = '[!]' in t
        rbox(ax, 3.0+i*2.4, 4.4, 2.2, 0.8,
             '#0A2B1E' if not is_t else '#2A0A0A',
             GREEN if not is_t else RED, r=0.1)
        ctext(ax, 4.1+i*2.4, 4.8, t, fs=12,
              color=GREEN if not is_t else RED)
    ctext(ax, 9.75, 3.9, 'UNIQUE(event_id, seat_id)  →  prevents double-booking at DB level',
          fs=12, color=RED, italic=True)

    # ── Redis ────────────────────────────────────────────────────────
    rbox(ax, 19.0, 5.6, 13.5, 1.5, '#3D1A0A', GOLD, lw=2)
    ctext(ax, 25.75, 6.65, '[!]  Redis 7', fs=16, color=GOLD, bold=True)
    ctext(ax, 25.75, 6.1, 'TTL=300s  ·  max_connections=20  |  :6380→6379', fs=13, color=TEXT_DIM)

    rkeys = ['availability:{id}','cache_hits','cache_misses','hit_total_ms','db_total_ms']
    for i,k in enumerate(rkeys):
        rbox(ax, 19.5+i*2.55, 4.4, 2.4, 0.8, '#2A1000', GOLD_LT, r=0.1)
        ctext(ax, 20.7+i*2.55, 4.8, k, fs=11, color=GOLD_LT)
    ctext(ax, 25.75, 3.9, 'metrics:* keys via INCR  ·  event-driven invalidation on booking',
          fs=12, color=GOLD_LT, italic=True)

    # ── Async layer ──────────────────────────────────────────────────
    rbox(ax, 2.5,  0.6, 9.5, 1.9, '#3D0A0A', '#FF6B6B', lw=2)
    ctext(ax, 7.25, 1.75, '[mq]  RabbitMQ 3.13', fs=15, color='#FF6B6B', bold=True)
    ctext(ax, 7.25, 1.2, 'AMQP  |  :5672  ·  Mgmt :15672', fs=13, color=TEXT_DIM)

    rbox(ax, 13.0, 0.6, 9.5, 1.9, '#2A1A00', GOLD, lw=2)
    ctext(ax, 17.75, 1.75, '⚙  Celery Worker', fs=15, color=GOLD, bold=True)
    ctext(ax, 17.75, 1.2, 'send_booking_confirmation  ·  acks_late=True', fs=13, color=TEXT_DIM)

    rbox(ax, 23.5, 0.6, 9.5, 1.9, '#0A1F3D', CYAN, lw=2)
    ctext(ax, 28.25, 1.75, '[mail]  Mailpit', fs=15, color=CYAN, bold=True)
    ctext(ax, 28.25, 1.2, 'SMTP :1025  ·  Web UI :8025', fs=13, color=TEXT_DIM)

    # ── Arrows ───────────────────────────────────────────────────────
    arr(ax, 17, 19.3,  17, 17.4,  CYAN,      label='HTTPS')
    arr(ax, 17, 16.2,  17, 12.7,  VIOLET_LT, label='REST /api/v1')
    arr(ax, 17, 11.5,  17, 10.62, VIOLET_LT)
    arr(ax, 17, 9.9,   17, 9.30,  VIOLET_LT)
    arr(ax, 8.2, 8.5,  8.5, 7.12, GREEN,  label='SQLAlchemy')
    arr(ax, 14.0, 8.5, 10.5, 7.12, GREEN, label='SELECT')
    arr(ax, 17.5, 8.5, 23.5, 7.12, GOLD,  label='GET/SET TTL=300s')
    arr(ax, 20.5, 8.5, 26.5, 7.12, GOLD,  label='INCR')
    arr(ax, 8.2, 8.5,  7.25, 2.5,  PINK,  label='AMQP .delay()')
    arr(ax, 12.0, 1.5, 13.0, 1.5,  PINK,  label='consume')
    arr(ax, 22.5, 1.5, 23.5, 1.5,  CYAN,  label='SMTP')

    ax.set_title('Scalable Booking System — System Architecture',
                 fontsize=22, color=TEXT, fontweight='bold', pad=14)
    plt.tight_layout(pad=0.5)
    save(fig, 'architecture_diagram.png')


# ═══════════════════════════════════════════════════════════════════════════════
# 2 · BOOKING REQUEST FLOW (SWIMLANE)
# ═══════════════════════════════════════════════════════════════════════════════
def make_swimlane():
    FW, FH = 36, 20
    fig, ax = plt.subplots(figsize=(FW, FH))
    ax.set_xlim(0, FW); ax.set_ylim(0, FH); ax.axis('off')
    fig.patch.set_facecolor(BG)

    # Lanes (yb, yt, fill, label, label_color)
    lanes = [
        (16.5, 20.0, '#7C3AED12', '[web]  Client',              VIOLET_LT),
        (13.0, 16.4, '#06B6D415', '[nx]  Next.js',              CYAN),
        ( 8.8, 12.9, '#7C3AED22', '[api]  FastAPI',              VIOLET_LT),
        ( 4.5,  8.7, '#10B98115', '[pg]  PostgreSQL',           GREEN),
        ( 2.0,  4.4, '#F59E0B12', '[!]  Redis',                GOLD),
        ( 0.0,  1.9, '#EC489915', '[mail]  Celery / RabbitMQ / Mailpit', PINK),
    ]
    for yb, yt, fc, lbl, lc in lanes:
        ax.add_patch(plt.Rectangle((0, yb), FW, yt-yb,
                                   facecolor=fc, edgecolor=BORDER, linewidth=0.5, zorder=0))
        ax.text(0.3, (yb+yt)/2, lbl, va='center', ha='left',
                fontsize=12, color=lc, fontweight='bold')

    # Celery lane detail
    ax.text(6, 0.95, '→  acks_late=True  ·  AMQP queue  ·  send_booking_confirmation.delay(booking_id, email)',
            va='center', ha='left', fontsize=11, color=TEXT_DIM, fontstyle='italic')

    # Step boxes: (cx, cy, title, subtitle, bg, edge_color)
    BW, BH = 3.5, 1.3
    steps = [
        ( 3.5, 18.2, 'User clicks\n"Book Seats"',
          '',
          '#1E3A5F', CYAN),
        ( 7.5, 14.7, 'bookingService.ts',
          'POST /api/v1/bookings\nAuthorization: Bearer <JWT>',
          '#1A1F4A', CYAN),
        (11.5, 10.8, 'Dependency Injection',
          'get_current_user()\ndecodes JWT → user_id',
          '#2D1B69', VIOLET_LT),
        (16.0, 10.8, 'BookingService',
          'create_new_booking(\n  db, booking_in, user_id)',
          '#2D1B69', VIOLET_LT),
        (20.5,  6.6, 'BEGIN\nTRANSACTION',
          'INSERT INTO booking\nflush() → booking.id',
          '#0F3D2A', GREEN),
        (25.0,  6.6, 'INSERT INTO ticket',
          'event_id, seat_id\n[!] UniqueConstraint check',
          '#1A0A0A', RED),
        (29.5,  6.6, 'COMMIT [OK]',
          'Transaction committed\ndata durable on disk',
          '#0F3D2A', GREEN),
        (29.5,  3.2, 'DEL availability:{id}',
          'Cache invalidated\nnext read hits DB',
          '#3D1A0A', GOLD),
        (33.5,  6.6, 'Celery .delay(\n  booking_id, email)',
          '',
          '#2A1A00', GOLD),
        (25.0,  3.2, 'ROLLBACK',
          'IntegrityError caught\ndb.rollback()',
          '#3D0A0A', RED),
        (33.5,  3.2, 'HTTP 409 Conflict',
          '"seat already booked"',
          '#3D0A0A', RED),
        (33.5, 10.8, 'HTTP 200 OK',
          'BookingRead schema\nJSON response',
          '#0F3D2A', GREEN),
    ]
    for cx, cy, title, sub, bg, ec in steps:
        rbox(ax, cx-BW/2, cy-BH/2, BW, BH, bg, ec, lw=1.5, r=0.2)
        if sub:
            ctext(ax, cx, cy+0.22, title, fs=12, color=ec, bold=True)
            ctext(ax, cx, cy-0.30, sub,   fs=10.5, color=TEXT_DIM)
        else:
            ctext(ax, cx, cy, title, fs=12, color=ec, bold=True)

    # Step numbers
    nums  = ['(1)','(2)','(3)','(4)','(5)','(6)','(7)','(8)','(9)']
    ncxcy = [(3.5,18.2),(7.5,14.7),(11.5,10.8),(16.0,10.8),(20.5,6.6),
             (25.0,6.6),(29.5,6.6),(29.5,3.2),(33.5,6.6)]
    for n,(cx,cy) in zip(nums,ncxcy):
        ax.text(cx-BW/2-0.1, cy+BH/2+0.1, n, fontsize=13, color=GOLD_LT,
                fontweight='bold', va='bottom', ha='right', zorder=6)

    # Flow arrows
    flows = [
        ( 3.5, 18.2-BH/2, 7.5,  14.7+BH/2, CYAN,     'POST /bookings\n+ JWT token'),
        ( 7.5, 14.7-BH/2, 11.5, 10.8+BH/2, VIOLET_LT,'HTTP request'),
        (11.5+BW/2, 10.8, 16.0-BW/2, 10.8,  VIOLET_LT,'user_id'),
        (16.0+BW/2, 10.8, 20.5-BW/2, 6.6+BH/2, GREEN,'db.add/flush'),
        (20.5+BW/2, 6.6,  25.0-BW/2, 6.6,       GREEN,''),
        (25.0+BW/2, 6.6,  29.5-BW/2, 6.6,       GREEN,'[OK] no conflict'),
        (29.5,  6.6-BH/2, 29.5, 3.2+BH/2,        GOLD,'invalidate cache'),
        (29.5+BW/2, 6.6,  33.5-BW/2, 6.6,        GOLD,'Celery .delay()'),
        (33.5,  6.6+BH/2, 33.5, 10.8-BH/2,        GREEN,'HTTP 200'),
        (25.0,  6.6-BH/2, 25.0, 3.2+BH/2,         RED,'[X] IntegrityError'),
        (25.0+BW/2, 3.2,  33.5-BW/2, 3.2,          RED,'HTTP 409'),
    ]
    for x1,y1,x2,y2,c,lbl in flows:
        arr(ax,x1,y1,x2,y2,c,label=lbl,lw=1.6)

    # Async dashed line to celery lane
    ax.annotate('', xy=(33.5, 1.85), xytext=(33.5, 3.2-BH/2),
                arrowprops=dict(arrowstyle='->', color=PINK, lw=1.8, linestyle='dashed'), zorder=2)
    ax.text(33.8, 2.5, 'async\nemail', ha='left', fontsize=11, color=PINK)

    ax.set_title('Booking Request — End-to-End Flow  (Happy Path [OK]  +  Conflict Path [X])',
                 fontsize=20, color=TEXT, fontweight='bold', pad=12)
    plt.tight_layout(pad=0.5)
    save(fig, 'request_flow_swimlane.png')


# ═══════════════════════════════════════════════════════════════════════════════
# 3a · LLD CLASS DIAGRAM
# ═══════════════════════════════════════════════════════════════════════════════
def make_lld():
    FW, FH = 36, 24
    fig, ax = plt.subplots(figsize=(FW, FH))
    ax.set_xlim(0, FW); ax.set_ylim(0, FH); ax.axis('off')
    fig.patch.set_facecolor(BG)

    ROW_H = 0.42
    HDR_H = 0.80

    def uml(ax, cx, cy_top, name, stereo, attrs, methods, ec, hc, w=5.5):
        n_attr = len(attrs)
        n_meth = len(methods)
        stereo_h = 0.32 if stereo else 0
        attr_h   = n_attr * ROW_H + 0.18
        meth_h   = n_meth * ROW_H + 0.18
        total_h  = HDR_H + stereo_h + attr_h + meth_h
        left = cx - w/2

        # shadow
        ax.add_patch(FancyBboxPatch((left+0.1, cy_top-total_h-0.1), w, total_h,
                     boxstyle='round,pad=0.04,rounding_size=0.2',
                     facecolor='#000000', alpha=0.30, zorder=2))
        # outer
        ax.add_patch(FancyBboxPatch((left, cy_top-total_h), w, total_h,
                     boxstyle='round,pad=0.04,rounding_size=0.2',
                     facecolor=SURFACE, edgecolor=ec, linewidth=2.0, zorder=3))
        # header
        ax.add_patch(FancyBboxPatch((left+0.04, cy_top-HDR_H-stereo_h), w-0.08, HDR_H+stereo_h,
                     boxstyle='round,pad=0.02,rounding_size=0.15',
                     facecolor=hc, edgecolor='none', alpha=0.90, zorder=4))
        if stereo:
            ax.text(cx, cy_top-0.22, f'<<{stereo}>>', ha='center', va='center',
                    fontsize=11, color='white', alpha=0.7, fontstyle='italic', zorder=5)
        ax.text(cx, cy_top-HDR_H/2-stereo_h+(0.06 if stereo else 0),
                name, ha='center', va='center',
                fontsize=15, color='white', fontweight='bold', zorder=5)

        sep1 = cy_top - HDR_H - stereo_h
        ax.plot([left+0.12, left+w-0.12], [sep1, sep1], color=ec, lw=1.0, alpha=0.5, zorder=4)

        for i,(vis,typ,aname) in enumerate(attrs):
            ay = sep1 - 0.14 - (i+0.5)*ROW_H
            vc = GOLD if vis=='+' else PINK if vis=='#' else TEXT_DIM
            ax.text(left+0.18, ay, vis,   ha='left', va='center', fontsize=11, color=vc, fontweight='bold', zorder=5)
            ax.text(left+0.42, ay, aname, ha='left', va='center', fontsize=11, color=TEXT, zorder=5)
            ax.text(left+w-0.16, ay, f': {typ}', ha='right', va='center',
                    fontsize=10, color=TEXT_DIM, fontstyle='italic', zorder=5)

        sep2 = sep1 - attr_h
        ax.plot([left+0.12, left+w-0.12], [sep2, sep2], color=ec, lw=1.0, alpha=0.5, zorder=4)

        for i,(vis,mname,params,ret) in enumerate(methods):
            my = sep2 - 0.14 - (i+0.5)*ROW_H
            vc = GOLD if vis=='+' else PINK if vis=='#' else TEXT_DIM
            ax.text(left+0.18, my, vis, ha='left', va='center', fontsize=11, color=vc, fontweight='bold', zorder=5)
            ax.text(left+0.42, my, f'{mname}({params})', ha='left', va='center',
                    fontsize=11, color=CYAN, zorder=5)
            if ret:
                ax.text(left+w-0.16, my, f': {ret}', ha='right', va='center',
                        fontsize=10, color=TEXT_DIM, fontstyle='italic', zorder=5)
        return cy_top - total_h  # bottom y

    # Class data
    user_a  = [('+','int','id'),('+','str','email'),('+','str','full_name'),
               ('-','str','hashed_password'),('+','bool','is_active'),('+','UserRole','role')]
    user_m  = [('+','verify_password','plain: str','bool'),('+','__repr__','','str')]

    venue_a = [('+','int','id'),('+','str','name'),('+','int','rows'),('+','int','cols')]
    venue_m = [('+','total_seats','','int')]

    seat_a  = [('+','int','id'),('+','str','row'),('+','int','number'),('+','int','venue_id [FK]')]
    seat_m  = [('+','label','','str')]

    event_a = [('+','int','id'),('+','str','name'),('+','str','description'),
               ('+','datetime','event_time'),('+','EventType','event_type'),
               ('+','int','venue_id [FK]'),('+','int','organizer_id [FK]')]
    event_m = [('+','is_future','','bool'),('+','available_seats','db: Session','list[Seat]')]

    booking_a = [('+','int','id'),('+','datetime','booking_time'),
                 ('+','BookingStatus','status'),('+','int','user_id [FK]')]
    booking_m = [('+','cancel','','None'),('+','total_price','','Decimal'),('+','__repr__','','str')]

    ticket_a = [('+','int','id'),('+','Decimal','price'),('+','int','booking_id [FK]'),
                ('+','int','event_id [FK] UC'),('+','int','seat_id [FK] UC')]
    ticket_m = [('+','__repr__','','str')]

    bsvc_a  = [('#','Session','db'),('#','Redis','cache')]
    bsvc_m  = [('+','create_new_booking','db, booking_in, user_id','Booking'),
               ('+','get_my_bookings','db, user_id','list[Booking]'),
               ('#','_invalidate_cache','event_id: int','None'),
               ('#','_publish_email_task','booking_id, email','None')]

    W = 5.5
    # Row 1: y=23
    b_user  = uml(ax,  4.0, 23.0, 'User',    'entity', user_a,  user_m,  '#6D28D9','#7C3AED', W)
    b_venue = uml(ax, 11.5, 23.0, 'Venue',   'entity', venue_a, venue_m, '#0284C7','#0369A1', W)
    b_seat  = uml(ax, 19.0, 21.0, 'Seat',    'entity', seat_a,  seat_m,  '#059669','#047857', W)

    # Row 2: y=14
    b_event   = uml(ax, 11.5, 13.5, 'Event',   'entity', event_a,   event_m,   '#D97706','#B45309', W)
    b_booking = uml(ax,  4.0, 12.0, 'Booking', 'entity', booking_a, booking_m, '#6D28D9','#7C3AED', W)
    b_ticket  = uml(ax, 19.0, 13.5, 'Ticket',  'entity', ticket_a,  ticket_m,  '#DC2626','#991B1B', W)

    # Row 3: BookingService
    b_bsvc    = uml(ax,  6.5,  5.5, 'BookingService','service', bsvc_a, bsvc_m, '#7C3AED','#5B21B6', W+1.0)

    # Enums (right column)
    enums = [
        ('UserRole',     ['customer','organizer'],                '#6D28D9', 23.0),
        ('EventType',    ['movie','concert','meetup'],             '#D97706', 20.5),
        ('BookingStatus',['pending','confirmed','cancelled'],      '#DC2626', 17.5),
    ]
    ex = 28.5
    for ename, vals, ec, ey_top in enums:
        eh = len(vals)*0.42 + 1.0
        ax.add_patch(FancyBboxPatch((ex-2.6, ey_top-eh), 5.2, eh,
                     boxstyle='round,pad=0.06,rounding_size=0.15',
                     facecolor=SURFACE, edgecolor=ec, linewidth=1.6, zorder=3))
        ax.text(ex, ey_top-0.35, f'<<enum>>  {ename}', ha='center', va='center',
                fontsize=12, color=ec, fontweight='bold', zorder=4)
        ax.plot([ex-2.2,ex+2.2],[ey_top-0.62,ey_top-0.62], color=ec, lw=0.8, alpha=0.5)
        for j,v in enumerate(vals):
            ax.text(ex, ey_top-0.95-j*0.42, v, ha='center', va='center',
                    fontsize=11, color=TEXT_DIM, zorder=4)

    # Constraint box
    uc_cx, uc_cy, uc_w, uc_h = 28.5, 11.0, 6.0, 1.8
    ax.add_patch(FancyBboxPatch((uc_cx-uc_w/2, uc_cy-uc_h/2), uc_w, uc_h,
                 boxstyle='round,pad=0.12,rounding_size=0.22',
                 facecolor='#1A0808', edgecolor=RED, linewidth=2.5, zorder=5))
    ax.text(uc_cx, uc_cy+0.35, '[!]  CONSTRAINT', ha='center', va='center',
            fontsize=14, color=RED, fontweight='bold', zorder=6)
    ax.text(uc_cx, uc_cy-0.10, 'UNIQUE(event_id, seat_id)', ha='center', va='center',
            fontsize=13, color=GOLD_LT, zorder=6, fontfamily='monospace')
    ax.text(uc_cx, uc_cy-0.55, 'prevents double-booking', ha='center', va='center',
            fontsize=12, color=TEXT_DIM, fontstyle='italic', zorder=6)
    ticket_right = 19.0 + W/2
    ax.annotate('', xy=(ticket_right+0.08, 11.0),
                xytext=(uc_cx-uc_w/2-0.08, uc_cy),
                arrowprops=dict(arrowstyle='<-', color=RED, lw=2.2), zorder=5)

    # Relationships
    def rel(x1,y1,x2,y2,lbl,c,rad=0.0,ls='solid'):
        ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
                    arrowprops=dict(arrowstyle='->', color=c, lw=1.8,
                                    connectionstyle=f'arc3,rad={rad}',
                                    linestyle=ls), zorder=2)
        if lbl:
            mx,my=(x1+x2)/2,(y1+y2)/2
            ax.text(mx+0.12, my, lbl, ha='left', va='center', fontsize=10, color=c, zorder=6,
                    bbox=dict(boxstyle='round,pad=0.15', facecolor=BG, edgecolor='none', alpha=0.9))

    rel( 4.0,   b_user,   4.0,  12.0,     '1..* has',        '#6D28D9')
    rel( 5.5,   16.8,     9.5,  12.5,     'organizes',       '#6D28D9', rad=0.1)
    rel(11.5,   b_venue,  11.5, 13.5,     '1..* hosts',      '#0284C7')
    rel(13.8,   21.2,     17.2, 21.0,     '1..* seats',      '#0284C7')
    rel( 4.0,   b_booking, 17.0, 9.0,     '1..* <<compose>>',RED, rad=0.0)
    rel(13.8,   10.5,     17.2, 10.5,     'event_id',        '#D97706')
    rel(19.0,   b_seat,   19.0, 13.5,     'seat_id',         '#059669')
    rel( 5.0,    5.0,      1.5,  9.5,     '<<uses>>',        VIOLET_LT, rad=0.2, ls='dashed')
    rel( 8.0,    5.5,     11.5, b_event-0.1, '<<reads>>',    VIOLET_LT, rad=0.3, ls='dashed')

    # Visibility legend
    for i,(sym,c,lbl) in enumerate([('+',GOLD,'public'),('#',PINK,'protected'),('-',TEXT_DIM,'private')]):
        ax.text(0.5+i*4.0, 1.2, f'{sym}  {lbl}', ha='left', va='center', fontsize=13, color=c)
    ax.text(0.5, 0.65, 'Visibility:',   ha='left', va='center', fontsize=12, color=TEXT_DIM)
    ax.text(16, 0.65, 'Solid = association/composition    Dashed = dependency/use',
            ha='center', va='center', fontsize=12, color=TEXT_DIM, fontstyle='italic')

    ax.set_title('Low-Level Design — Class Diagram (UML)',
                 fontsize=22, color=TEXT, fontweight='bold', pad=12)
    plt.tight_layout(pad=0.5)
    save(fig, 'lld_class_diagram.png')


# ═══════════════════════════════════════════════════════════════════════════════
# 3b · ERD
# ═══════════════════════════════════════════════════════════════════════════════
def make_erd():
    FW, FH = 32, 18
    fig, ax = plt.subplots(figsize=(FW, FH))
    ax.set_xlim(0, FW); ax.set_ylim(0, FH); ax.axis('off')
    fig.patch.set_facecolor(BG)

    RH = 0.48

    def entity(ax, cx, cy_top, title, fields, ec, hc, w=4.8):
        n = len(fields)
        total_h = 0.68 + n*RH + 0.16
        left = cx - w/2
        ax.add_patch(FancyBboxPatch((left, cy_top-total_h), w, total_h,
                     boxstyle='round,pad=0.04,rounding_size=0.2',
                     facecolor=SURFACE, edgecolor=ec, linewidth=2.2, zorder=3))
        ax.add_patch(FancyBboxPatch((left, cy_top-0.64), w, 0.62,
                     boxstyle='round,pad=0.01,rounding_size=0.15',
                     facecolor=hc, edgecolor='none', alpha=0.92, zorder=4))
        ax.text(cx, cy_top-0.33, title, ha='center', va='center',
                fontsize=14, color='white', fontweight='bold', zorder=5)
        ax.plot([left+0.08, left+w-0.08], [cy_top-0.66, cy_top-0.66],
                color=ec, lw=1.0, alpha=0.5, zorder=4)
        for i,(ftype,fname,note) in enumerate(fields):
            fy = cy_top - 0.66 - (i+0.55)*RH
            tc = GOLD if ftype in ('PK','FK') else TEXT_DIM
            ax.text(left+0.18, fy, ftype, ha='left', va='center',
                    fontsize=11, color=tc, fontfamily='monospace', zorder=5)
            ax.text(left+0.85, fy, fname, ha='left', va='center',
                    fontsize=12, color=TEXT, zorder=5)
            if note:
                ax.text(left+w-0.14, fy, note, ha='right', va='center',
                        fontsize=10, color=RED if 'UC' in note else TEXT_DIM,
                        fontstyle='italic', zorder=5)
        return cy_top - total_h

    user_f    = [('PK','id','Integer'),('str','email','unique'),('str','full_name',''),
                 ('str','hashed_password',''),('bool','is_active','default=True'),('enum','role','customer|organizer')]
    venue_f   = [('PK','id','Integer'),('str','name','unique'),('int','rows',''),('int','cols','')]
    seat_f    = [('PK','id','Integer'),('str','row','e.g. "A"'),
                 ('int','number','e.g. 1..cols'),('FK','venue_id','→ Venue')]
    event_f   = [('PK','id','Integer'),('str','name',''),('str','description',''),
                 ('dt','event_time','tz-aware'),('enum','event_type','movie|concert|meetup'),
                 ('FK','venue_id','→ Venue'),('FK','organizer_id','→ User')]
    booking_f = [('PK','id','Integer'),('dt','booking_time','now()'),
                 ('enum','status','pending|confirmed|cancelled'),('FK','user_id','→ User')]
    ticket_f  = [('PK','id','Integer'),('dec','price','Numeric(10,2)'),
                 ('FK','booking_id','→ Booking'),
                 ('FK','event_id','→ Event  [UC]'),('FK','seat_id','→ Seat  [UC]')]

    b_user  = entity(ax,  3.5, 17.2, '[user]  User',    user_f,    '#5B21B6','#6D28D9')
    b_venue = entity(ax, 10.5, 17.2, '[venue]  Venue',   venue_f,   '#0369A1','#0284C7')
    b_seat  = entity(ax, 17.5, 17.2, '[seat]  Seat',    seat_f,    '#047857','#059669')
    b_bk    = entity(ax,  3.5,  9.0, '[book]  Booking', booking_f, '#5B21B6','#6D28D9')
    b_evt   = entity(ax, 11.5, 11.5, '[event]  Event',   event_f,   '#B45309','#D97706')
    b_tkt   = entity(ax, 19.5, 13.0, '[ticket]  Ticket',  ticket_f,  '#991B1B','#DC2626', w=5.2)

    # UC callout
    ax.text(19.5, 4.5, '[!] UniqueConstraint\n(event_id, seat_id)',
            ha='center', va='center', fontsize=13, color=RED, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.45', facecolor='#1A0808', edgecolor=RED, linewidth=2.2))
    ax.annotate('', xy=(19.5, b_tkt+0.1), xytext=(19.5, 5.5),
                arrowprops=dict(arrowstyle='->', color=RED, lw=2.2))

    # Arrows
    rels = [
        ( 3.5, b_user,     3.5,  9.0,  '1:N  has bookings',  '#5B21B6'),
        (10.5, b_venue,   10.5, 11.5,  '1:N  hosts events',  '#0369A1'),
        (10.5, 16.2,      17.5, 16.6,  '1:N  has seats',     '#0369A1'),
        (17.5, b_seat,    19.5, 13.0,  '→ seat_id',          '#047857'),
        (11.5,  9.5,      19.5, 12.0,  '→ event_id',         '#B45309'),
        ( 3.5,  7.2,      19.5, 12.0,  '1:N  booking→tickets','#5B21B6'),
        ( 3.5, 16.2,      11.5, 12.4,  '→ organizer_id',     '#5B21B6'),
    ]
    for x1,y1,x2,y2,lbl,c in rels:
        ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
                    arrowprops=dict(arrowstyle='->', color=c, lw=1.8,
                                    connectionstyle='arc3,rad=0.15'), zorder=2)
        mx,my=(x1+x2)/2,(y1+y2)/2
        ax.text(mx, my, lbl, ha='center', va='center', fontsize=11, color=c,
                bbox=dict(boxstyle='round,pad=0.14', facecolor=BG, edgecolor='none', alpha=0.88))

    ax.set_title('Entity Relationship Diagram  —  6 DB Models',
                 fontsize=22, color=TEXT, fontweight='bold', pad=12)
    ax.text(16, 0.55, '(!)  Ticket.UniqueConstraint(event_id, seat_id) = database-level lock that '
            'prevents double-booking across all concurrent requests — no application mutex needed.',
            ha='center', va='center', fontsize=12, color=TEXT_DIM, fontstyle='italic')
    plt.tight_layout(pad=0.5)
    save(fig, 'erd_diagram.png')


# ═══════════════════════════════════════════════════════════════════════════════
# 4 · TECH STACK + DOCKER SERVICE MAP
# ═══════════════════════════════════════════════════════════════════════════════
def make_stack():
    FW, FH = 34, 15
    fig, axes = plt.subplots(1, 2, figsize=(FW, FH))
    fig.patch.set_facecolor(BG)

    # LEFT: Stack layers
    ax = axes[0]
    ax.set_facecolor(BG); ax.axis('off')
    ax.set_xlim(0, 15); ax.set_ylim(0, 14)

    layers = [
        (12.2, 1.8, '#1E3A5F', CYAN,      'CLIENT LAYER',
         ['Next.js 15  (App Router)', 'TypeScript', 'Tailwind CSS', 'Dark Luxury Theme']),
        (10.1, 1.8, '#2D1B69', VIOLET_LT, 'API LAYER',
         ['FastAPI 0.116  +  Uvicorn', 'Pydantic v2  (validation)', 'JWT Bearer Auth', 'Loguru (structured logs)']),
        ( 8.0, 1.8, '#0F3D2A', GREEN,     'DATA LAYER',
         ['PostgreSQL 15', 'SQLAlchemy 2.0  (ORM)', 'Alembic  (migrations)', 'pool_size=20 / max_overflow=10']),
        ( 5.9, 1.8, '#3D1A0A', GOLD,      'CACHE LAYER',
         ['Redis 7', 'TTL = 300s', 'max_connections=20', 'Atomic INCR counters']),
        ( 3.8, 1.8, '#3D0A0A', '#FF6B6B', 'ASYNC LAYER',
         ['RabbitMQ 3.13  (AMQP broker)', 'Celery 5.4  (task queue)', 'acks_late=True', 'Mailpit  (dev SMTP)']),
        ( 1.7, 1.8, '#1A1A2E', TEXT_DIM,  'INFRA LAYER',
         ['Docker Compose  (7 services)', 'Health checks  (depends_on)', 'pytest 8.3  +  Locust 2.32', 'booking.404by.me']),
    ]
    for y0, h, bg, tc, name, items in layers:
        ax.add_patch(FancyBboxPatch((0.4, y0), 14.2, h,
                     boxstyle='round,pad=0.06,rounding_size=0.22',
                     facecolor=bg, edgecolor=tc, linewidth=1.8, alpha=0.92, zorder=2))
        ax.text(0.75, y0+h-0.35, name, ha='left', va='center',
                fontsize=12, color=tc, fontweight='bold', zorder=3)
        for j, item in enumerate(items):
            ax.text(0.9+j*3.45, y0+0.55, f'• {item}', ha='left', va='center',
                    fontsize=11, color=TEXT_DIM, zorder=3)
    ax.set_title('Technology Stack  (top → bottom = client → infra)',
                 fontsize=16, color=TEXT, fontweight='bold')

    # RIGHT: Docker service table
    ax2 = axes[1]
    ax2.set_facecolor(BG); ax2.axis('off')
    ax2.set_xlim(0, 17); ax2.set_ylim(0, 14)

    svcs = [
        ('[api]  backend',            '8000→8000', 'FastAPI + Uvicorn',             VIOLET_LT, 'depends: db, redis, rabbitmq'),
        ('[pg]  db',                 '5434→5432', 'PostgreSQL 15 (main)',           GREEN,     'volumes: postgres_data'),
        ('[test]  test_db',            '5433→5432', 'PostgreSQL 15 (isolated)',       GREEN,     'separate from prod DB'),
        ('[!]  redis',              '6380→6379', 'Redis 7 — cache + metrics',      GOLD,      'healthcheck: redis-cli ping'),
        ('[mq]  rabbitmq',           '5672,15672','RabbitMQ 3.13 — AMQP',          '#FF6B6B', 'mgmt UI :15672'),
        ('[mail]  mailpit',            '8025,1025', 'Dev SMTP — Mailpit',             CYAN,      'web UI :8025'),
        ('⚙  notification_worker', '—',         'Celery Worker',                  GOLD,      'depends: rabbitmq, backend'),
    ]

    ax2.text(8.5, 13.5, 'Docker Compose Service Map', ha='center', va='center',
             fontsize=17, color=TEXT, fontweight='bold')
    ax2.text(8.5, 12.95, '7 services · all running · health-checked',
             ha='center', va='center', fontsize=12, color=TEXT_DIM, fontstyle='italic')

    cols  = ['Service', 'Host Ports', 'Description', 'Dependencies / Notes']
    col_x = [0.2, 4.0, 6.2, 11.5]
    col_w = [3.6, 2.0, 5.1,  5.2]

    for cx, cw, col in zip(col_x, col_w, cols):
        ax2.add_patch(plt.Rectangle((cx, 12.1), cw-0.14, 0.65,
                                    facecolor='#2D1B69', edgecolor=VIOLET_LT, linewidth=0.9))
        ax2.text(cx+(cw-0.14)/2, 12.43, col, ha='center', va='center',
                 fontsize=12, color=VIOLET_LT, fontweight='bold')

    for i,(name,ports,desc,tc,deps) in enumerate(svcs):
        ry = 11.55 - i*1.48
        rbg = '#1A1A2E' if i%2==0 else '#16213E'
        for cx, cw in zip(col_x, col_w):
            ax2.add_patch(plt.Rectangle((cx, ry-0.58), cw-0.14, 1.15,
                          facecolor=rbg, edgecolor=BORDER, linewidth=0.5))
        row_data   = [name, ports, desc, deps]
        row_colors = [tc, TEXT, TEXT_DIM, TEXT_DIM]
        row_sizes  = [11.5, 11, 11, 10.5]
        for cx, cw, val, vc, vs in zip(col_x, col_w, row_data, row_colors, row_sizes):
            ax2.text(cx+0.18, ry, val, ha='left', va='center',
                     fontsize=vs, color=vc, fontweight='bold' if val==name else 'normal')

    plt.tight_layout(pad=0.5)
    save(fig, 'stack_and_services.png')


# ═══════════════════════════════════════════════════════════════════════════════
# 5 · DESIGN DECISIONS
# ═══════════════════════════════════════════════════════════════════════════════
def make_decisions():
    FW, FH = 34, 20
    fig, ax = plt.subplots(figsize=(FW, FH))
    ax.set_xlim(0, FW); ax.set_ylim(0, FH); ax.axis('off')
    fig.patch.set_facecolor(BG)

    decisions = [
        {
            'title':  '1. PostgreSQL UniqueConstraint\nvs Redis SETNX vs Pessimistic Lock',
            'chosen': 'UniqueConstraint(event_id, seat_id)',
            'why': [
                '[OK] Enforced atomically by the DB engine — no application-level code can bypass it',
                '[OK] Works with multiple API replicas behind a load balancer',
                '[OK] No TTL expiry risk (Redis SETNX can leak locks on crash)',
                '[OK] Zero extra infra — just a SQL constraint',
                '[X] Trades lower throughput for correctness — acceptable for ticket sales',
            ],
            'color': RED,      'x': 0.8, 'y': 19.2, 'w': 15.8, 'h': 5.2,
        },
        {
            'title':  '2. Redis Cache TTL=300s\nvs No Cache vs Memcached',
            'chosen': 'Redis 7  ·  TTL=300s  ·  Event-driven invalidation',
            'why': [
                '[OK] Availability reads are 16.6× faster than DB queries',
                '[OK] On booking, cache for that event is immediately invalidated',
                '[OK] Redis supports pub/sub, Lua scripts, counters — future features',
                '[OK] TTL=300s: 5-min stale acceptable; shorter = more DB pressure',
                '[X] Cache-aside: first read after invalidation always hits DB (cold start)',
            ],
            'color': GOLD,     'x': 17.4, 'y': 19.2, 'w': 15.8, 'h': 5.2,
        },
        {
            'title':  '3. Celery + RabbitMQ\nvs Synchronous Email vs Redis Queue',
            'chosen': 'Celery 5.4  +  RabbitMQ  +  acks_late=True',
            'why': [
                '[OK] Email is NOT on the critical path — user gets HTTP 200 in ~5ms',
                '[OK] acks_late=True: if worker crashes mid-send, message requeued (at-least-once)',
                '[OK] RabbitMQ decouples producer (API) from consumer (worker)',
                '[OK] Synchronous email would add 200-500ms per booking request',
                '[X] Operational complexity: 2 extra services (rabbitmq + worker)',
            ],
            'color': PINK,     'x': 0.8, 'y': 13.5, 'w': 15.8, 'h': 5.2,
        },
        {
            'title':  '4. SQLAlchemy pool_size=20\nvs Default (5) vs PgBouncer',
            'chosen': 'pool_size=20  ·  max_overflow=10  ·  pool_timeout=30s',
            'why': [
                '[OK] Concurrency test: 50 goroutines × 3 queries = 150 simultaneous DB ops',
                '[OK] Default pool_size=5 would queue 145 connections → timeout errors',
                '[OK] max_overflow=10 handles burst (80 Locust users)',
                '[OK] pool_recycle=1800 prevents stale connections from PG idle timeout',
                '[X] Higher pool_size uses more memory; use PgBouncer at scale',
            ],
            'color': GREEN,    'x': 17.4, 'y': 13.5, 'w': 15.8, 'h': 5.2,
        },
        {
            'title':  '5. FastAPI + Uvicorn  vs Django + Gunicorn  vs Express.js',
            'chosen': 'FastAPI 0.116  +  Uvicorn  +  async-capable',
            'why': [
                '[OK] Native async I/O — one Uvicorn worker handles thousands of concurrent connections',
                '[OK] Pydantic v2 validation — 5-17× faster than v1, zero boilerplate',
                '[OK] Auto-generated OpenAPI docs at /docs — essential for dev collaboration',
                '[OK] Dependency Injection for DB session + JWT auth — clean, testable',
                '[X] SQLAlchemy sync sessions block the event loop — future: AsyncSession',
            ],
            'color': VIOLET_LT,'x': 0.8, 'y': 7.8, 'w': 32.4, 'h': 5.2,
        },
    ]

    for d in decisions:
        cx = d['x'] + d['w']/2
        c  = d['color']
        ax.add_patch(FancyBboxPatch((d['x'], d['y']-d['h']), d['w'], d['h'],
                     boxstyle='round,pad=0.07,rounding_size=0.25',
                     facecolor=SURFACE, edgecolor=c, linewidth=2.0, alpha=0.92, zorder=2))
        ax.add_patch(FancyBboxPatch((d['x']+0.08, d['y']-1.0), d['w']-0.16, 0.95,
                     boxstyle='round,pad=0.03,rounding_size=0.15',
                     facecolor=c, edgecolor='none', alpha=0.88, zorder=3))
        ax.text(cx, d['y']-0.52, d['title'], ha='center', va='center',
                fontsize=13, color='white', fontweight='bold', zorder=4)
        ax.text(d['x']+0.22, d['y']-1.28,
                f'Chosen:  {d["chosen"]}',
                ha='left', va='center', fontsize=12, color=c, fontstyle='italic', zorder=4)
        for i, item in enumerate(d['why']):
            iy = d['y'] - 1.72 - i * 0.60
            tc = GREEN if item.startswith('[OK]') else RED
            ax.text(d['x']+0.22, iy, item, ha='left', va='center',
                    fontsize=12, color=tc, zorder=4)

    ax.set_title('Architecture Design Decisions — Trade-offs & Rationale',
                 fontsize=22, color=TEXT, fontweight='bold', pad=12)
    plt.tight_layout(pad=0.5)
    save(fig, 'design_decisions.png')


# ═══════════════════════════════════════════════════════════════════════════════
# 6 · CONCURRENCY TIMELINE + METRICS
# ═══════════════════════════════════════════════════════════════════════════════
def make_concurrency():
    FW, FH = 32, 15
    fig, axes = plt.subplots(1, 2, figsize=(FW, FH))
    fig.patch.set_facecolor(BG)

    # LEFT: Race condition timeline
    ax = axes[0]
    ax.set_facecolor(BG); ax.axis('off')
    ax.set_xlim(0, 14); ax.set_ylim(0, 14)

    ax.add_patch(plt.Rectangle((0.8, 0.4), 5.0, 13.0, facecolor='#1A0F3A',
                                edgecolor=VIOLET_LT, linewidth=1.8, alpha=0.5))
    ax.add_patch(plt.Rectangle((7.8, 0.4), 5.0, 13.0, facecolor='#1A0F3A',
                                edgecolor=PINK, linewidth=1.8, alpha=0.5))

    ax.text(3.3, 13.8, 'Transaction A', ha='center', fontsize=15, color=VIOLET_LT, fontweight='bold')
    ax.text(3.3, 13.3, '(User 1 — wins)', ha='center', fontsize=12, color=TEXT_DIM)
    ax.text(10.3, 13.8, 'Transaction B', ha='center', fontsize=15, color=PINK, fontweight='bold')
    ax.text(10.3, 13.3, '(User 2 — loses)', ha='center', fontsize=12, color=TEXT_DIM)

    for y in np.arange(0.6, 13.2, 0.4):
        ax.axhline(y, color=BORDER, lw=0.3, alpha=0.3)

    steps_a = [
        (12.5, VIOLET_LT, 'BEGIN'),
        (11.2, VIOLET_LT, 'INSERT booking → id=42'),
        ( 9.8, VIOLET_LT, 'INSERT ticket\n(event_id=1, seat_id=5)'),
        ( 7.9, GREEN,     'COMMIT [OK]'),
        ( 6.6, GREEN,     'cache DEL availability:1'),
        ( 5.3, GREEN,     'Celery .delay(42, email_a)'),
        ( 4.0, GREEN,     'HTTP 200 → User 1'),
    ]
    for y, c, txt in steps_a:
        ax.add_patch(FancyBboxPatch((0.9, y-0.48), 4.8, 0.85,
                     boxstyle='round,pad=0.04,rounding_size=0.14',
                     facecolor='#1E0F47' if c==VIOLET_LT else '#0F2D1A',
                     edgecolor=c, linewidth=1.3, alpha=0.92))
        ax.text(3.3, y, txt, ha='center', va='center', fontsize=11, color=c)

    steps_b = [
        (12.1, PINK, 'BEGIN  (20ms later)'),
        (10.8, PINK, 'INSERT booking → id=43'),
        ( 9.4, PINK, 'INSERT ticket\n(event_id=1, seat_id=5) ← SAME'),
        ( 7.5, RED,  '[!!] IntegrityError\n_event_seat_uc violated'),
        ( 6.2, RED,  'ROLLBACK'),
        ( 4.9, RED,  'booking id=43 deleted'),
        ( 3.6, RED,  'HTTP 409 → User 2'),
    ]
    for y, c, txt in steps_b:
        ax.add_patch(FancyBboxPatch((7.9, y-0.48), 4.8, 0.85,
                     boxstyle='round,pad=0.04,rounding_size=0.14',
                     facecolor='#1A0F3A' if c==PINK else '#2A0808',
                     edgecolor=c, linewidth=1.3, alpha=0.92))
        ax.text(10.3, y, txt, ha='center', va='center', fontsize=11, color=c)

    ax.annotate('', xy=(7.8, 8.65), xytext=(5.7, 8.65),
                arrowprops=dict(arrowstyle='<->', color=RED, lw=2.2))
    ax.text(6.75, 9.1, 'DB locks\nconflict here', ha='center', va='center',
            fontsize=11, color=RED, fontweight='bold')

    ax.set_title('Race Condition Timeline\n(50 concurrent users, 1 seat)',
                 fontsize=15, color=TEXT, fontweight='bold')

    # RIGHT: Metric cards
    ax2 = axes[1]
    ax2.set_facecolor(BG); ax2.axis('off')
    ax2.set_xlim(0, 16); ax2.set_ylim(0, 14)

    ax2.text(8, 13.5, 'Measured System Metrics', ha='center', va='center',
             fontsize=18, color=TEXT, fontweight='bold')
    ax2.text(8, 12.9, 'From live Locust + concurrency test + /api/v1/metrics',
             ha='center', va='center', fontsize=12, color=TEXT_DIM, fontstyle='italic')

    cards = [
        ('16.6×',  'Cache Speedup',        'avg_cache=1.6ms vs avg_db=26.6ms',  GOLD),
        ('62.5%',  'Cache Hit Rate',        '295 hits / 472 total requests',     GREEN),
        ('37 RPS', 'Peak Throughput',       '80 concurrent users — Locust test', VIOLET_LT),
        ('<1%',    'Error Rate',            'Under sustained 80-user load',      GREEN),
        ('1 / 50', 'Concurrency Result',    '49 × HTTP 409  ·  1 × HTTP 200',   CYAN),
        ('~16s',   'Concurrency Test Time', '50 users, asyncio.gather race',     TEXT_DIM),
        ('20',     'DB Connection Pool',    'pool_size=20 + max_overflow=10',    GREEN),
        ('300s',   'Cache TTL',             'event-driven invalidation on book', GOLD),
    ]

    CW, CH = 6.0, 2.6
    for i,(val,title,detail,c) in enumerate(cards):
        row = i // 2
        col = i % 2
        cx = 3.2 + col * 7.2
        cy = 11.8 - row * 3.0
        ax2.add_patch(FancyBboxPatch((cx-CW/2, cy-CH), CW, CH,
                      boxstyle='round,pad=0.07,rounding_size=0.24',
                      facecolor=SURFACE, edgecolor=c, linewidth=2.0, alpha=0.92))
        ax2.text(cx, cy-0.75,  val,    ha='center', va='center', fontsize=32, color=c, fontweight='bold')
        ax2.text(cx, cy-1.65,  title,  ha='center', va='center', fontsize=13, color=TEXT, fontweight='bold')
        ax2.text(cx, cy-2.20,  detail, ha='center', va='center', fontsize=11, color=TEXT_DIM)

    ax2.set_title('System Performance Summary', fontsize=16, color=TEXT, fontweight='bold')
    plt.tight_layout(pad=0.5)
    save(fig, 'concurrency_mechanism.png')


# ═══════════════════════════════════════════════════════════════════════════════
# 7 · SCALING ROADMAP
# ═══════════════════════════════════════════════════════════════════════════════
def make_scaling():
    FW, FH = 32, 14
    fig, ax = plt.subplots(figsize=(FW, FH))
    ax.set_xlim(0, FW); ax.set_ylim(0, FH); ax.axis('off')
    fig.patch.set_facecolor(BG)

    ax.set_title('Scaling Roadmap — Current → Production → Hyperscale',
                 fontsize=22, color=TEXT, fontweight='bold', pad=14)

    stages = [
        {
            'x': 4.0, 'label': '[box] Current\n(Docker Compose)',
            'cap': '~100 concurrent users', 'color': VIOLET,
            'items': ['1× FastAPI (Uvicorn)','1× PostgreSQL','1× Redis','1× RabbitMQ',
                      '1× Celery worker','pool_size=20','No load balancer','Single host'],
        },
        {
            'x': 14.0, 'label': '[api] Production\n(Kubernetes / ECS)',
            'cap': '~10k concurrent users', 'color': GOLD,
            'items': ['N× FastAPI replicas','Nginx / ALB load balancer','RDS PostgreSQL (Multi-AZ)',
                      'ElastiCache Redis (cluster)','N× Celery workers','PgBouncer (connection pooler)',
                      'Horizontal pod autoscaling','CDN for static assets'],
        },
        {
            'x': 26.5, 'label': '[!] Hyperscale\n(Event-Driven Architecture)',
            'cap': '~100k concurrent users', 'color': CYAN,
            'items': ['Redis SETNX pre-reservation','DB sharding by venue_id',
                      'Read replicas for availability','Kafka instead of RabbitMQ',
                      'CQRS (separate read/write)','WebSocket seat-map updates',
                      'Circuit breakers (Hystrix)','Distributed tracing (Jaeger)'],
        },
    ]

    HW = 5.0  # half-width
    for s in stages:
        cx, c = s['x'], s['color']
        ax.add_patch(FancyBboxPatch((cx-HW, 0.5), HW*2, 12.5,
                     boxstyle='round,pad=0.12,rounding_size=0.30',
                     facecolor=SURFACE, edgecolor=c, linewidth=2.5, alpha=0.92))
        ax.add_patch(FancyBboxPatch((cx-HW+0.1, 11.3), HW*2-0.2, 1.5,
                     boxstyle='round,pad=0.04,rounding_size=0.20',
                     facecolor=c, edgecolor='none', alpha=0.88))
        ax.text(cx, 12.1, s['label'], ha='center', va='center',
                fontsize=14, color='white', fontweight='bold')
        ax.text(cx, 10.9, s['cap'], ha='center', va='center',
                fontsize=12, color=c, fontstyle='italic')
        ax.plot([cx-HW+0.4, cx+HW-0.4], [10.55, 10.55], color=c, lw=1.0, alpha=0.45)
        for i, item in enumerate(s['items']):
            iy = 10.0 - i * 1.12
            ax.text(cx-HW+0.35, iy, '•', ha='left', va='center', fontsize=14, color=c)
            ax.text(cx-HW+0.75, iy, item, ha='left', va='center', fontsize=12, color=TEXT_DIM)

    # Arrows between stages
    for xa, xb, c, lbl in [(4.0+HW, 14.0-HW, GOLD,'scale\nout'),
                            (14.0+HW, 26.5-HW, CYAN,'decouple\n& shard')]:
        ax.annotate('', xy=(xb, 6.5), xytext=(xa, 6.5),
                    arrowprops=dict(arrowstyle='->', color=c, lw=4.0, mutation_scale=24))
        ax.text((xa+xb)/2, 7.1, lbl, ha='center', fontsize=12, color=c)

    # "You are here" badge
    ax.add_patch(FancyBboxPatch((0.6, 0.18), 7.0, 0.45,
                 boxstyle='round,pad=0.04,rounding_size=0.12',
                 facecolor='#0F3D2A', edgecolor=GREEN, linewidth=1.5))
    ax.text(4.1, 0.40, '* YOU ARE HERE — fully running in Docker Compose',
            ha='center', va='center', fontsize=12, color=GREEN)

    plt.tight_layout(pad=0.5)
    save(fig, 'scaling_roadmap.png')


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print(f'Generating diagrams at DPI={DPI} into {OUT_DIR}/')
    make_architecture()
    make_swimlane()
    make_lld()
    make_erd()
    make_stack()
    make_decisions()
    make_concurrency()
    make_scaling()
    print('\nAll done [OK]')
