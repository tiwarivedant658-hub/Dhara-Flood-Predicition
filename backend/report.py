from pathlib import Path
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = BASE_DIR / 'backend' / 'generated_reports'
REPORT_DIR.mkdir(parents=True, exist_ok=True)
CONTACTS_PATH = BASE_DIR / 'data' / 'emergency_contacts.json'


def _contacts_for(loc):
    import json
    data=json.loads(CONTACTS_PATH.read_text(encoding='utf-8'))
    out=list(data['national'])
    state=data['states'].get(loc.get('state'), {})
    out.extend(state.get('state_contacts', []))
    district=state.get('districts', {}).get(loc.get('district'), {})
    if district.get('district_office'):
        out.append({'name':'District Disaster / Administration Office','service':'District office / control room','phone':district['district_office'],'type':'district'})
    if district.get('police'):
        out.append({'name':'Police / Emergency Response','service':'Police control / emergency','phone':district['police'],'type':'police'})
    # De-duplicate while preserving order.
    seen=set(); clean=[]
    for c in out:
        key=(c['name'],c['phone'])
        if key not in seen:
            clean.append(c); seen.add(key)
    return clean


def build_report(loc, live, risk, evidence_items):
    ts=datetime.now().strftime('%d %b %Y, %H:%M:%S')
    path=REPORT_DIR / f"dhara-{loc['id']}-report.pdf"
    doc=SimpleDocTemplate(str(path), pagesize=A4, rightMargin=15*mm,leftMargin=15*mm,topMargin=14*mm,bottomMargin=14*mm,
                          title=f"Dhara District Prediction Report - {loc['district']}")
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Small', parent=styles['BodyText'], fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name='Kicker', parent=styles['BodyText'], fontSize=8, leading=10, textColor=colors.HexColor('#5B6459'), spaceAfter=3))
    story=[Paragraph('DHARA — DISTRICT FLASH FLOOD PREDICTION REPORT', styles['Title']),
           Paragraph(f"{loc['district']} · {loc['state']}", styles['Heading1']),
           Paragraph(f"Generated {ts}. This report contains a prototype predictive forecast and should be verified against official local advisories before operational use.", styles['Small']), Spacer(1,8)]
    prediction=risk.get('prediction', {})
    summary=[['Next 6h event probability',f"{prediction.get('probability', risk.get('score','—'))}%"],['Prediction level',prediction.get('label', risk.get('label','—'))],['Estimated lead time',prediction.get('lead_time',{}).get('label','—')],['Model confidence (inputs)',f"{prediction.get('confidence','—')}%"],['Prediction horizon','6 hours'],['Rainfall next 6h',f"{live.get('rainfall_next_6h_mm','—')} mm"],['Rainfall next 24h',f"{live.get('rainfall_next_24h_mm','—')} mm"],['Peak hourly intensity',f"{live.get('max_hourly_intensity_mm','—')} mm/hr"],['Soil moisture',f"{(live.get('soil_moisture_0_7cm',0)*100):.0f}%"],['Elevation',f"{loc.get('elevation_m','—')} m"],['River basin',loc.get('river_basin','—')],['Slope class',loc.get('slope_class','—')],['Soil type',loc.get('soil_type','—')]]
    t=Table(summary,colWidths=[55*mm,120*mm]); t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#D8DDD4')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#EDEEE6')),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),5)])); story += [t,Spacer(1,10)]
    story += [Paragraph('Model drivers', styles['Heading2'])]
    drivers=prediction.get('drivers', [])
    ft=Table([['Driver','Relative importance']]+[[d.get('name','—'),f"{d.get('importance','—')}%"] for d in drivers], colWidths=[120*mm,55*mm], repeatRows=1); ft.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#D8DDD4')),('PADDING',(0,0),(-1,-1),5)])); story += [ft,Spacer(1,10)]
    story += [Paragraph('Emergency contacts', styles['Heading2'])]
    ct=_contacts_for(loc)
    rows=[['Service','Purpose','Phone']]+[[c['name'],c['service'],c['phone']] for c in ct]
    tt=Table(rows,colWidths=[55*mm,75*mm,45*mm],repeatRows=1); tt.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#D8DDD4')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EDEEE6')),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('PADDING',(0,0),(-1,-1),4),('VALIGN',(0,0),(-1,-1),'TOP')])); story += [tt,Spacer(1,10)]
    story += [Paragraph('Field evidence', styles['Heading2'])]
    if evidence_items:
        rows=[]
        for item in evidence_items:
            from backend.evidence import image_path
            ip=image_path(loc['id'], item.get('category',''))
            if ip.exists():
                try: img=Image(str(ip),width=65*mm,height=42*mm); rows.append([Paragraph(item.get('category_label',item.get('category','Evidence')),styles['Small']),img])
                except Exception: pass
        if rows:
            et=Table(rows,colWidths=[45*mm,80*mm]); et.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#D8DDD4')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('PADDING',(0,0),(-1,-1),5)])); story += [et]
        else: story.append(Paragraph('Evidence metadata exists, but images were unavailable for embedding.',styles['Small']))
    else: story.append(Paragraph('No field evidence has been uploaded for this district.',styles['Small']))
    story += [Spacer(1,10),Paragraph('Prediction note', styles['Heading2']),Paragraph(f"Live source: {live.get('source','—')}. Forecast: {prediction.get('description', risk.get('description','—'))}. Model: {prediction.get('model','—')}. This prototype model must be validated against labelled historical Indian events before operational deployment.",styles['Small'])]
    doc.build(story)
    return path
