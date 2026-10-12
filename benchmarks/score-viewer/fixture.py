"""Self-authored structured score -> common vector layout -> PDF/images/SVG+HTML.

Not a production engraver: deliberately covers monophonic treble, quarter/eighth
notes, four 4/4 bars per system and Vietnamese syllabic lyrics.
"""
import hashlib
import html
import json
from pathlib import Path
import platform
import time

import PIL
from PIL import Image, ImageChops, ImageStat
import pymupdf
import reportlab
import fontTools
from fontTools import subset
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
W, H = 760, 1060


def structured_score():
    # Four beats in every bar, 20 notes per system, 6 systems per page.
    melodies = [[0, 2, 4, 5, 4], [2, 3, 4, 2, 1], [0, 1, 2, 4, 3], [2, 1, 0, 1, 0]]
    lyrics = ['Bình minh lên qua đồi xanh lòng ta vui đón ánh sáng dịu êm trong ngày mới đầy hy vọng',
              'Tiếng chim ngân bên dòng sông cùng nhau đi giữa nắng ấm bàn tay giữ tình thương mãi bền lâu',
              'Gió mang theo câu chào thân từ nơi xa gửi tiếng hát dịu dàng đến bạn tôi giữa trời trong',
              'Hãy yêu thêm từng ngày qua và nâng niu những ước muốn bình yên dưới vòm xanh sáng ngời lên']
    pages = []
    for p in range(4):
        systems = []
        for s in range(6):
            words = lyrics[(p+s) % 4].split()
            notes = []
            for bar in range(4):
                for i, beats in enumerate((1, .5, .5, 1, 1)):
                    step = melodies[(p+s+bar) % 4][i]
                    notes.append({'pitch': ('C4', 'D4', 'E4', 'F4', 'G4', 'A4')[step],
                                  'diatonicStep': step, 'beats': beats, 'bar': bar+1,
                                  'lyric': words[(bar*5+i) % len(words)]})
            systems.append({'meter': '4/4', 'clef': 'treble', 'notes': notes})
        pages.append({'number': p+1, 'systems': systems})
    return {'id': 'audiotp:self-authored:morning-study:v1', 'title': 'Bình minh - Khúc tập đọc nhạc',
            'locale': 'vi', 'rights': 'Self-authored synthetic melody and lyrics; reusable for AudioTP benchmark. Not BookVN/WATV.',
            'pages': pages}


def layout(score, page):
    shapes, texts = [], []
    def line(x1,y1,x2,y2,width=1): shapes.append({'type':'line','x1':x1,'y1':y1,'x2':x2,'y2':y2,'width':width})
    def ellipse(x,y,rx,ry): shapes.append({'type':'ellipse','x':x,'y':y,'rx':rx,'ry':ry})
    def text(x,y,value,size=12): texts.append({'x':x,'y':y,'text':str(value),'size':size})
    text(52, 54, score['title'], 25)
    text(52, 83, 'Nhạc và lời tự soạn • 4/4 • Đô trưởng • Tempo = 88', 13)
    text(52, 109, 'Fixture nghiên cứu AudioTP - không phải bài ca thờ phượng từ nguồn bên ngoài', 10)
    for system, data in enumerate(page['systems']):
        top = 155 + system * 140
        for i in range(5): line(52,top+i*8,708,top+i*8,.8)
        # A geometric treble-clef study mark, independent of music glyph fonts.
        ellipse(65,top+24,7,10); line(65,top-14,65,top+46,1.5)
        line(65,top-14,72,top-3,1.5); line(72,top-3,59,top+15,1.5)
        text(82,top+13,'4',13); text(82,top+29,'4',13)
        for bar in range(5): line(100+bar*152,top,100+bar*152,top+32,1.2)
        for i, note in enumerate(data['notes']):
            bar, pos = divmod(i,5)
            x = 114 + bar*152 + pos*28
            y = top + 40 - note['diatonicStep']*4
            if note['diatonicStep'] == 0: line(x-8,y,x+8,y,.9)
            ellipse(x,y,5,3.5); line(x+5,y,x+5,y-27,1.1)
            if note['beats'] == .5:
                line(x+5,y-27,x+12,y-20,1.5); line(x+12,y-20,x+10,y-13,1.1)
            lyric_width=pdfmetrics.stringWidth(note['lyric'],'BenchmarkNoto',10)
            text(x-lyric_width/2,top+72,note['lyric'],10)
        text(52,top+96,f'{page["number"]}.{system+1}   Andante - hát rõ dấu tiếng Việt',10)
    text(52,1026,'Tự soạn cho benchmark • cùng dữ liệu nốt / lời / bố cục ở mọi định dạng',10)
    text(661,1026,f'{page["number"]} / 4',11)
    return {'width':W,'height':H,'shapes':shapes,'texts':texts}


def vector_page(display):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" aria-label="Khuông và nốt nhạc vector">']
    for s in display['shapes']:
        if s['type']=='line': parts.append(f'<line x1="{s["x1"]}" y1="{s["y1"]}" x2="{s["x2"]}" y2="{s["y2"]}" stroke="#192329" stroke-width="{s["width"]}"/>')
        else: parts.append(f'<ellipse cx="{s["x"]}" cy="{s["y"]}" rx="{s["rx"]}" ry="{s["ry"]}" fill="#192329"/>')
    parts.append('</svg>')
    return {'width':W,'height':H,'svg':''.join(parts),'texts':display['texts']}


def generate(out, font):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont('BenchmarkNoto', str(font)))
    score = structured_score()
    (out/'score.json').write_text(json.dumps(score,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    pdf = canvas.Canvas(str(out/'original.pdf'), pagesize=(W,H), invariant=1, pageCompression=1)
    pdf.setTitle(score['title']); pdf.setAuthor('AudioTP self-authored benchmark generator')
    for page in score['pages']:
        display = layout(score,page)
        (out/f'page-{page["number"]}.vector.json').write_text(json.dumps(vector_page(display),ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        pdf.setStrokeColorRGB(.098,.137,.16); pdf.setFillColorRGB(.098,.137,.16)
        for s in display['shapes']:
            if s['type']=='line':
                pdf.setLineWidth(s['width']); pdf.line(s['x1'],H-s['y1'],s['x2'],H-s['y2'])
            else: pdf.ellipse(s['x']-s['rx'],H-s['y']-s['ry'],s['x']+s['rx'],H-s['y']+s['ry'],stroke=0,fill=1)
        for t in display['texts']:
            pdf.setFont('BenchmarkNoto',t['size']); pdf.drawString(t['x'],H-t['y'],t['text'])
        pdf.showPage()
    pdf.save()
    # Same glyph outlines, subset to this fixture's actual Unicode text.
    all_text=''.join(t['text'] for p in score['pages'] for t in layout(score,p)['texts'])
    font_options=subset.Options(); font_options.name_IDs=['*']; font_options.name_legacy=True
    subset_font=subset.load_font(str(font),font_options)
    subsetter=subset.Subsetter(options=font_options); subsetter.populate(text=all_text)
    subsetter.subset(subset_font); subset.save_font(subset_font,str(out/'score-font.ttf'),font_options)
    quality=[]
    with pymupdf.open(out/'original.pdf') as doc:
        for number,page in enumerate(doc,1):
            pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False)
            source=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
            for codec,options in [('png',{}),('webp',{'lossless':True,'quality':100,'method':6}),
                                  ('avif',{'quality':90,'subsampling':'4:4:4','speed':6,'max_threads':2})]:
                path=out/f'page-{number}.{codec}'; start=time.perf_counter(); source.save(path,**options)
                encode_ms=(time.perf_counter()-start)*1000
                with Image.open(path) as decoded:
                    diff=ImageChops.difference(source,decoded.convert('RGB'))
                    quality.append({'page':number,'codec':codec,'maxPixelError':max(high for low,high in diff.getextrema()),
                                    'meanAbsoluteError':sum(ImageStat.Stat(diff).mean)/3,'encodeMs':encode_ms})
    assets=[]
    for path in sorted(out.iterdir()):
        if path.name=='original.pdf' or path.suffix in ('.png','.webp','.avif') or path.name.endswith('.vector.json'):
            data=path.read_bytes(); assets.append({'file':path.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    result={'schemaVersion':1,'pages':4,'width':W,'height':H,'rasterScale':2,'rasterWidth':W*2,'rasterHeight':H*2,
            'source':'score.json','assets':assets,'quality':quality,
            'font':{'file':'score-font.ttf','bytes':(out/'score-font.ttf').stat().st_size,'sha256':hashlib.sha256((out/'score-font.ttf').read_bytes()).hexdigest(),'license':'../vendor/NOTO-LICENSE'},
            'environment':{'python':platform.python_version(),'Pillow':PIL.__version__,'reportlab':reportlab.Version,'PyMuPDF':pymupdf.VersionBind,'fonttools':fontTools.__version__},
            'encoding':{'png':'lossless RGB','webp':'lossless quality=100 method=6','avif':'quality=90 4:4:4 speed=6, lossy'}}
    (out/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    result=generate(ROOT/'fixtures',ROOT/'vendor/NotoSans-Regular.ttf')
    print(json.dumps({'status':'PASS','pages':result['pages'],'assets':len(result['assets'])}))
