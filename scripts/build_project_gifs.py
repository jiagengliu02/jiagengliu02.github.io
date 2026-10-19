#!/usr/bin/env python3
"""Build the homepage's 11 short project animations from documented sources.

Requires Python 3, Pillow, ffmpeg and ffprobe.
Usage: python scripts/build_project_gifs.py --cache /tmp/project-gif-sources
Missing official assets are downloaded into the cache; originals stay unchanged.
Source URLs, excerpts and animation types are recorded in img/gifs/sources.json.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'img' / 'gifs'
W, H, FPS, FRAMES = 400, 272, 10, 48
INK, MUTED, BLUE = '#182b45', '#607086', '#326de6'
FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')


def font(size, bold=False):
    try:
        return ImageFont.truetype(str(FONT_DIR / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')), size)
    except OSError:
        return ImageFont.load_default(size=size)


VIDEOS = [
    dict(id='autoagent0', title='AutoAgent0', file='auto-main.mp4',
         url='https://jiagengliu02.github.io/AutoAgent0/assets/videos/AutoAgent0_demo.mp4',
         start=46, duration=9.6, crop='crop=1260:610:90:400',
         caption='Verified obstacle bypass · 2x'),
    dict(id='esi-bench', title='ESI-Bench', file='esi-pick.mov',
         url='https://esi-bench.github.io/static/vids/qualitative/pick_up.mov',
         start=0, duration=2.4, caption='Robot manipulation: pick up · 0.5x'),
    dict(id='av-phys-bench', title='AV-Phys-Bench', file='av-coin.mp4',
         url='https://huggingface.co/datasets/ZijunCui/AV-Phys-Bench/resolve/main/videos/Seedance-2.0/C1-1-01.mp4',
         start=0.5, duration=4.8, caption='Seedance 2.0 · spinning coin · silent'),
    dict(id='edit3r', title='Edit3r', file='edit3r.mp4',
         url='https://edit3r.github.io/edit3r/static/videos/example1.mp4',
         start=0.2, duration=4.8, crop='crop=1032:512:137:336',
         caption='Original → edited: decorate for a party'),
    dict(id='virtual-community', title='Virtual Community', file='virtual-community.mp4',
         url='https://virtual-community-ai.github.io/_astro/traffic_demo.DEFnM9xd.mp4',
         start=17, duration=4.8, crop='crop=1920:920:0:160',
         caption='City-scale traffic simulation'),
    dict(id='mindjourney', title='MindJourney', file='mindjourney-swmsvc1.m4v',
         url='https://umass-embodied-agi.github.io/MindJourney/static/videos/SWMSVC_1.m4v',
         start=1, duration=5.12, crop='crop=456:286:490:190',
         fps=25, smooth=True, loop_blend_seconds=0.32,
         caption='Controllable world-model navigation demo · natural speed, motion interpolation'),
    dict(id='architect', title='ARCHITECT', file='architect-restaurant.mp4',
         url='https://wangyian-me.github.io/Architect/static/videos/restaurant.mp4',
         start=0, duration=4.8, caption='Generated 3D scene: restaurant'),
    dict(id='rila', title='RILA', file='rila.mp4',
         url='https://rila-savn.github.io/RILA/images/demo.mp4',
         start=10, duration=5.12, crop='crop=500:225:260:175',
         fps=25, smooth=True, loop_blend_seconds=0.32,
         caption='Audio-visual navigation: map + agent view · motion interpolation'),
]


def asset(cache, name, url):
    path = cache / name
    if not path.exists():
        with urllib.request.urlopen(url, timeout=90) as response:
            path.write_bytes(response.read())
    return path


def encode(name, frames, fps=FPS):
    # A single palette prevents color flicker between frames.
    with tempfile.TemporaryDirectory(prefix='project-gif-') as temp:
        temp = Path(temp)
        for i, frame in enumerate(frames):
            frame.save(temp / f'{i:03}.png')
        subprocess.run([
            'ffmpeg', '-v', 'error', '-y', '-threads', '1',
            '-framerate', str(fps), '-i', str(temp / '%03d.png'),
            '-filter_complex_threads', '1', '-filter_complex',
            '[0:v]scale=320:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:reserve_transparent=1[p];'
            '[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle',
            '-loop', '0', str(OUT / f'{name}.gif'),
        ], check=True)
    print(f'{name}: {(OUT / (name + ".gif")).stat().st_size / 1024:.0f} KiB', flush=True)


def video_frames(spec, cache):
    source = asset(cache, spec['file'], spec['url'])
    fps = spec.get('fps', FPS)
    blend_count = round(spec.get('loop_blend_seconds', 0) * fps)
    frame_count = round(4.8 * fps) + blend_count
    output_seconds = frame_count / fps
    filters = [f'setpts=(PTS-STARTPTS)*{output_seconds / spec["duration"]}']
    if spec.get('crop'):
        filters.append(spec['crop'])
    # Preserve the footage's own aspect ratio: no title bars or letterboxing.
    filters += ['scale=320:-1:flags=lanczos', 'setsar=1']
    if spec.get('smooth'):
        # Navigation demos repeat simulation steps; interpolate across those holds.
        filters += ['fps=5', f'minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none']
    else:
        filters.append(f'fps={fps}')
    with tempfile.TemporaryDirectory(prefix='project-frames-') as temp:
        subprocess.run([
            'ffmpeg', '-v', 'error', '-threads', '1', '-ss', str(spec['start']), '-i', str(source),
            '-an', '-vf', ','.join(filters), '-frames:v', str(frame_count),
            '-threads', '1', str(Path(temp) / '%03d.png'),
        ], check=True)
        paths = sorted(Path(temp).glob('*.png'))
        if len(paths) != frame_count:
            raise ValueError(f'Incomplete excerpt: {spec["id"]}')
        frames = [Image.open(path).convert('RGB') for path in paths]
    if blend_count:
        # Wrap the last short segment onto the opening, keeping forward motion.
        tail = [Image.blend(frames[-blend_count+i], frames[i], (i+1)/blend_count)
                for i in range(blend_count)]
        frames = frames[blend_count:-blend_count] + tail
    return frames, hashlib.sha256(source.read_bytes()).hexdigest()


def lsm_frames():
    """Schematic of the paper's four stages, not a model execution trace."""
    frames = []
    labels = ['Observe', 'Store memory', 'Imagine views', 'Update & reason']
    for i in range(FRAMES):
        stage = i // 12
        im = Image.new('RGB', (W, H), 'white')
        d = ImageDraw.Draw(im)
        for j, label in enumerate(labels):
            x = 8 + j * 98
            d.rounded_rectangle((x, 35, x+91, 61), 6, fill=BLUE if stage == j else '#edf2f9')
            d.text((x+5, 43), label, font=font(10, stage == j), fill='white' if stage == j else MUTED)
        # A minimal room map supplies persistent spatial memory.
        d.rounded_rectangle((13, 74, 193, 226), 8, fill='#f1f6fc', outline='#c9d7e8', width=2)
        d.text((23, 82), 'BEV memory', font=font(13, True), fill=INK)
        d.rectangle((30, 112, 73, 133), fill='#8db4e6')
        d.rectangle((120, 168, 175, 190), fill='#bda4de')
        d.text((31, 137), 'table', font=font(11), fill=MUTED)
        d.text((130, 195), 'sofa', font=font(11), fill=MUTED)
        # Camera changes pose only in the imagination stage.
        progress = max(0, min(1, (i-24)/11))
        x, y = 55 + 46 * progress, 198 - 44 * progress
        d.polygon([(x,y),(x-8,y+15),(x+8,y+15)], fill=BLUE)
        if stage >= 2:
            d.line([(55,207),(101,163)], fill=BLUE, width=2)
            d.arc((x-20,y-22,x+20,y+18), 210, 330, fill=BLUE, width=2)
        d.text((219, 82), 'Scene graph', font=font(13, True), fill=INK)
        nodes = [(243,131,'table','#8db4e6'), (346,131,'sofa','#bda4de'), (295,198,'agent','#8ecdb4')]
        if stage >= 1:
            for a,b in [(0,1),(0,2),(1,2)]:
                d.line([nodes[a][:2],nodes[b][:2]], fill='#a9b8ca', width=2)
        for j,(nx,ny,label,color) in enumerate(nodes):
            if stage == 0 and j == 1:
                continue
            d.ellipse((nx-17,ny-17,nx+17,ny+17), fill=color)
            d.text((nx-16,ny+20),label,font=font(11),fill=INK)
        if stage == 3:
            d.rounded_rectangle((222, 67, 378, 79), 4, fill='#ccebdd')
            d.text((227, 68), 'Evidence → memory update', font=font(9), fill='#226647')
        frames.append(im.crop((8, 35, 393, 234)))
    return frames


def cmcr_frames(cache):
    paths = [asset(cache, f'cmcr-{i}.jpg', f'https://c-mcr.github.io/C-MCR/a2i/images/audio1_ours{i}.jpg') for i in range(3)]
    frames = []
    for i in range(FRAMES):
        selected = i // 16
        im = Image.new('RGB', (360, 120), 'white')
        d = ImageDraw.Draw(im)
        for j,path in enumerate(paths):
            x = 120*j
            tile = ImageOps.fit(Image.open(path).convert('RGB'), (120, 120))
            im.paste(tile, (x, 0))
            if j == selected:
                d.rectangle((x,0,x+119,119),outline=BLUE,width=3)
        frames.append(im)
    return frames


def word_frames():
    original = Image.open(ROOT / 'img' / 'pub3.jpg').convert('RGB')
    boxes = [(365,772,512,920),(519,772,667,920),(674,772,821,920)]
    panels = [ImageOps.fit(original.crop(box),(320,320),method=Image.Resampling.LANCZOS) for box in boxes]
    return [panels[i // 16].copy() for i in range(FRAMES)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path(tempfile.gettempdir())/'project-gif-sources')
    args=parser.parse_args()
    args.cache.mkdir(parents=True,exist_ok=True)
    OUT.mkdir(parents=True,exist_ok=True)
    for binary in ['ffmpeg','ffprobe']:
        if not shutil.which(binary):
            raise SystemExit(f'Missing executable: {binary}')
    records=[]
    for spec in VIDEOS:
        frames, sha=video_frames(spec,args.cache)
        encode(spec['id'],frames,fps=spec.get('fps',FPS))
        records.append(dict(spec,kind='official-video-excerpt',source_sha256=sha))
    for name,frames,record in [
        ('lsm-vlm',lsm_frames(),dict(kind='method-schematic',source='files/lsm-vlm.pdf',note='Illustration of the method; not a recorded inference run. Demo URL returned 404.')),
        ('c-mcr',cmcr_frames(args.cache),dict(kind='official-result-sequence',source='https://c-mcr.github.io/C-MCR/',images=[f'https://c-mcr.github.io/C-MCR/a2i/images/audio1_ours{i}.jpg' for i in range(3)],note='Fireworks audio query, top three official retrieved images. GIF has no audio.')),
        ('worddiffuser',word_frames(),dict(kind='paper-result-sequence',source='img/pub3.jpg',paper='files/WordDiffuser.pdf',note='Three published stages; transitions are a presentation, not intermediate diffusion samples.')),
    ]:
        encode(name,frames)
        records.append(dict(id=name,**record))
    for record in records:
        with Image.open(OUT / f'{record["id"]}.gif') as image:
            record['width'], record['height'] = image.size
    (OUT/'sources.json').write_text(json.dumps(dict(width=320,duration_seconds=4.8,fps=FPS,loop=True,presentation='Content only; native aspect ratios, no added captions or padding.',projects=records),indent=2)+'\n')


if __name__ == '__main__':
    main()
