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
         start=46, duration=9.6, crop='crop=1280:640:80:390',
         caption='Verified obstacle bypass · 2x'),
    dict(id='esi-bench', title='ESI-Bench', file='esi-bench.mp4',
         url='https://esi-bench.github.io/static/vids/qualitative/pour_down.mp4',
         start=0, duration=4.8, caption='Embodied interaction: pour down'),
    dict(id='av-phys-bench', title='AV-Phys-Bench', file='av-coin.mp4',
         url='https://huggingface.co/datasets/ZijunCui/AV-Phys-Bench/resolve/main/videos/Seedance-2.0/C1-1-01.mp4',
         start=0.5, duration=4.8, caption='Seedance 2.0 · spinning coin · silent'),
    dict(id='edit3r', title='Edit3r', file='edit3r.mp4',
         url='https://edit3r.github.io/edit3r/static/videos/example1.mp4',
         start=0.2, duration=4.8, crop='crop=1032:590:137:336',
         caption='Original → edited: decorate for a party'),
    dict(id='virtual-community', title='Virtual Community', file='virtual-community.mp4',
         url='https://virtual-community-ai.github.io/_astro/traffic_demo.DEFnM9xd.mp4',
         start=17, duration=4.8, crop='crop=1920:920:0:160',
         caption='City-scale traffic simulation'),
    dict(id='mindjourney', title='MindJourney', file='mindjourney.mp4',
         url='https://umass-embodied-agi.github.io/MindJourney/static/videos/traj_expansion.mov',
         start=0, duration=8, caption='World-model trajectory expansion · 1.67x'),
    dict(id='architect', title='ARCHITECT', file='architect-restaurant.mp4',
         url='https://wangyian-me.github.io/Architect/static/videos/restaurant.mp4',
         start=0, duration=4.8, caption='Generated 3D scene: restaurant'),
    dict(id='rila', title='RILA', file='rila.mp4',
         url='https://rila-savn.github.io/RILA/images/demo.mp4',
         start=10, duration=4.8, crop='crop=520:245:260:175',
         caption='Audio-visual navigation: map + agent view'),
]


def asset(cache, name, url):
    path = cache / name
    if not path.exists():
        with urllib.request.urlopen(url, timeout=90) as response:
            path.write_bytes(response.read())
    return path


def base(title, caption):
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)
    d.text((12, 6), title, font=font(15, True), fill=INK)
    d.text((12, 253), caption, font=font(12), fill=MUTED)
    return im


def encode(name, frames):
    # A single palette prevents color flicker between frames.
    with tempfile.TemporaryDirectory(prefix='project-gif-') as temp:
        temp = Path(temp)
        for i, frame in enumerate(frames):
            frame.save(temp / f'{i:03}.png')
        subprocess.run([
            'ffmpeg', '-v', 'error', '-y', '-threads', '1',
            '-framerate', str(FPS), '-i', str(temp / '%03d.png'),
            '-filter_complex_threads', '1', '-filter_complex',
            '[0:v]scale=320:218:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:reserve_transparent=1[p];'
            '[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle',
            '-loop', '0', str(OUT / f'{name}.gif'),
        ], check=True)
    print(f'{name}: {(OUT / (name + ".gif")).stat().st_size / 1024:.0f} KiB', flush=True)


def video_frames(spec, cache):
    source = asset(cache, spec['file'], spec['url'])
    filters = [f'setpts=(PTS-STARTPTS)*{4.8 / spec["duration"]}']
    if spec.get('crop'):
        filters.append(spec['crop'])
    filters += ['fps=10', 'scale=400:220:force_original_aspect_ratio=decrease:flags=lanczos',
                'pad=400:220:(ow-iw)/2:(oh-ih)/2:white', 'setsar=1']
    result = subprocess.run([
        'ffmpeg', '-v', 'error', '-threads', '1', '-ss', str(spec['start']), '-i', str(source),
        '-an', '-vf', ','.join(filters), '-frames:v', str(FRAMES),
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-threads', '1', 'pipe:1',
    ], check=True, stdout=subprocess.PIPE)
    frame_bytes = 400 * 220 * 3
    if len(result.stdout) != FRAMES * frame_bytes:
        raise ValueError(f'Incomplete excerpt: {spec["id"]}')
    frames = []
    for i in range(FRAMES):
        im = base(spec['title'], spec['caption'])
        im.paste(Image.frombytes('RGB', (400, 220), result.stdout[i*frame_bytes:(i+1)*frame_bytes]), (0, 28))
        frames.append(im)
    return frames, hashlib.sha256(source.read_bytes()).hexdigest()


def lsm_frames():
    """Schematic of the paper's four stages, not a model execution trace."""
    frames = []
    labels = ['Observe', 'Store memory', 'Imagine views', 'Update & reason']
    for i in range(FRAMES):
        stage = i // 12
        im = base('LSM-VLM', 'Method schematic · perception / memory loop')
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
        frames.append(im)
    return frames


def cmcr_frames(cache):
    paths = [asset(cache, f'cmcr-{i}.jpg', f'https://c-mcr.github.io/C-MCR/a2i/images/audio1_ours{i}.jpg') for i in range(3)]
    frames = []
    for i in range(FRAMES):
        selected = i // 16
        im = base('C-MCR', 'Official retrieval results · silent preview')
        d = ImageDraw.Draw(im)
        d.text((14, 40), 'Audio query: fireworks', font=font(16, True), fill=INK)
        d.text((14, 65), 'Audio → shared space → images', font=font(13), fill=MUTED)
        # Progress is a presentation cue, not a fabricated audio waveform.
        d.rounded_rectangle((14, 91, 386, 97), 3, fill='#e5ecf7')
        d.rounded_rectangle((14, 91, 15 + int(371*(i+1)/FRAMES), 97), 3, fill=BLUE)
        for j,path in enumerate(paths):
            x = 14 + 127*j
            tile = ImageOps.fit(Image.open(path).convert('RGB'), (116, 116))
            im.paste(tile, (x, 112))
            if j == selected:
                d.rectangle((x-2,110,x+117,229),outline=BLUE,width=3)
            d.text((x+33,232), f'Rank {j+1}', font=font(11), fill=BLUE if j==selected else MUTED)
        frames.append(im)
    return frames


def word_frames():
    original = Image.open(ROOT / 'img' / 'pub3.jpg').convert('RGB')
    boxes = [(365,772,512,920),(519,772,667,920),(674,772,821,920)]
    panels = [ImageOps.fit(original.crop(box),(170,170),method=Image.Resampling.LANCZOS) for box in boxes]
    frames = []
    labels = ['Oracle glyph','Shape optimized','Style enhanced']
    for i in range(FRAMES):
        stage = i // 16
        im = base('WordDiffuser', 'Paper example · three-stage result sequence')
        d = ImageDraw.Draw(im)
        im.paste(panels[stage], (16,65))
        d.text((16, 38), 'Glyph → meaning', font=font(15,True), fill=INK)
        for j,label in enumerate(labels):
            y=85+j*52
            d.ellipse((210,y,232,y+22),fill=BLUE if j==stage else '#e5ecf7')
            d.text((217,y+4),str(j+1),font=font(11),fill='white' if j==stage else MUTED)
            d.text((242,y+4),label,font=font(13,j==stage),fill=INK if j==stage else MUTED)
            if j<2:
                d.line((221,y+26,221,y+46),fill='#c9d7e8',width=2)
        frames.append(im)
    return frames


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
        encode(spec['id'],frames)
        records.append(dict(spec,kind='official-video-excerpt',source_sha256=sha))
    for name,frames,record in [
        ('lsm-vlm',lsm_frames(),dict(kind='method-schematic',source='files/lsm-vlm.pdf',note='Illustration of the method; not a recorded inference run. Demo URL returned 404.')),
        ('c-mcr',cmcr_frames(args.cache),dict(kind='official-result-sequence',source='https://c-mcr.github.io/C-MCR/',images=[f'https://c-mcr.github.io/C-MCR/a2i/images/audio1_ours{i}.jpg' for i in range(3)],note='Fireworks audio query, top three official retrieved images. GIF has no audio.')),
        ('worddiffuser',word_frames(),dict(kind='paper-result-sequence',source='img/pub3.jpg',paper='files/WordDiffuser.pdf',note='Three published stages; transitions are a presentation, not intermediate diffusion samples.')),
    ]:
        encode(name,frames)
        records.append(dict(id=name,**record))
    (OUT/'sources.json').write_text(json.dumps(dict(width=320,height=218,duration_seconds=4.8,fps=FPS,loop=True,projects=records),indent=2)+'\n')


if __name__ == '__main__':
    main()
