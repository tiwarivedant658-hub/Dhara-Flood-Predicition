"""Field evidence photos for monitored locations.

Stores one latest image per factor/category for each location. Categories are
soil, terrain, river, landuse and flood_evidence. Images are evidence for a
human/operator to inspect; they are not treated as calibrated measurements.
"""
import json, time
from pathlib import Path
from PIL import Image

BASE_DIR=Path(__file__).resolve().parent.parent
EVIDENCE_DIR=BASE_DIR/'data'/'evidence'
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS={'.jpg','.jpeg','.png','.webp'}
MAX_FILE_BYTES=8*1024*1024
CATEGORIES={
 'soil':'Soil', 'terrain':'Terrain / slope', 'river':'River / drainage',
 'landuse':'Land use / vegetation', 'flood_evidence':'Flood evidence'
}

def _dir(location_id, category):
 d=EVIDENCE_DIR/location_id/category; d.mkdir(parents=True,exist_ok=True); return d

def _meta(location_id, category): return _dir(location_id,category)/'meta.json'
def _image(location_id, category):
 d=_dir(location_id,category)
 for ext in ALLOWED_EXTENSIONS:
  p=d/f'latest{ext}'
  if p.exists(): return p
 return None

def _analysis(path):
 with Image.open(path) as im:
  im=im.convert('RGB'); im.thumbnail((160,160)); px=list(im.getdata())
 n=max(1,len(px)); r=sum(x[0] for x in px)/n; g=sum(x[1] for x in px)/n; b=sum(x[2] for x in px)/n
 brightness=(r+g+b)/3
 return {'avg_brightness':round(brightness,1),'avg_rgb':[round(r,1),round(g,1),round(b,1)],'visual_note':'Image stored as field evidence; visual values are descriptive only.'}

def save(location_id, category, file_storage):
 if category not in CATEGORIES: raise ValueError('Unsupported evidence category')
 name=(file_storage.filename or '').lower(); ext=Path(name).suffix
 if ext not in ALLOWED_EXTENSIONS: raise ValueError('Unsupported file type. Use JPG, PNG or WEBP.')
 d=_dir(location_id,category)
 for old in d.glob('latest.*'): old.unlink(missing_ok=True)
 dest=d/f'latest{ext}'; file_storage.save(dest)
 meta={'location_id':location_id,'category':category,'category_label':CATEGORIES[category],'filename':dest.name,'uploaded_at':int(time.time()),'analysis':_analysis(dest)}
 _meta(location_id,category).write_text(json.dumps(meta,indent=2),encoding='utf-8')
 return get_one(location_id,category)

def get_one(location_id, category):
 mp=_meta(location_id,category)
 img=_image(location_id,category)
 if not mp.exists() or not img: return None
 meta=json.loads(mp.read_text(encoding='utf-8'))
 meta['image_url']=f'/api/evidence/{location_id}/{category}/image'
 return meta

def list_for(location_id):
 out=[]
 for category in CATEGORIES:
  item=get_one(location_id,category)
  if item: out.append(item)
 return out

def image_path(location_id,category): return _image(location_id,category)
