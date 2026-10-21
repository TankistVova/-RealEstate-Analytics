from io import BytesIO
from pathlib import Path
from html import escape
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

def report(valuation):
    font=next((p for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','C:/Windows/Fonts/arial.ttf'] if Path(p).exists()),None)
    if font is None:
        raise RuntimeError('Не найден шрифт с поддержкой кириллицы')
    pdfmetrics.registerFont(TTFont('Cyrillic',font))
    styles=getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName='Cyrillic'
        style.leading=15
    styles['Title'].fontSize=22
    styles['Title'].leading=28
    data=valuation.result_data
    target=valuation.input_parameters
    stream=BytesIO()
    doc=SimpleDocTemplate(stream, rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=40,title='Отчёт об экспресс-оценке')
    story=[]
    def paragraph(value, style='BodyText'):
        story.extend([Paragraph(escape(str(value)),styles[style]),Spacer(1,9)])
    def money(value): return f'{value:,.0f}'.replace(',',' ')+' руб.'
    paragraph('RealEstate Analytics','Title')
    paragraph(f'Отчёт об экспресс-оценке №{valuation.id}','Heading2')
    created=valuation.created_at
    if created.tzinfo is None: created=created.replace(tzinfo=timezone.utc)
    paragraph(f'Дата расчёта: {created.astimezone(ZoneInfo("Europe/Moscow")):%d.%m.%Y %H:%M} МСК')
    paragraph(f'Дата формирования отчёта: {datetime.now(ZoneInfo("Europe/Moscow")):%d.%m.%Y %H:%M} МСК')
    paragraph('Характеристики квартиры','Heading2')
    labels={'city':'Город','district':'Район','address':'Адрес','total_area':'Площадь, м²','rooms':'Комнат','floor':'Этаж','floors_total':'Этажность','year_built':'Год постройки','building_type':'Тип дома','condition':'Ремонт'}
    translated={'panel':'Панельный','brick':'Кирпичный','monolith':'Монолитный','other':'Другой','needs_repair':'Требует ремонта','normal':'Обычное','good':'Хорошее','excellent':'Отличное'}
    for key,label in labels.items():
        value=target.get(key)
        if value is not None: paragraph(f'{label}: {translated.get(str(value),value)}')
    paragraph('Результат: '+money(data['estimated_price']),'Heading2')
    paragraph('Цена за м²: '+money(data['price_per_m2']))
    paragraph('Диапазон: '+money(data['min_price'])+' - '+money(data['max_price']))
    paragraph(data['range_note'])
    paragraph(data['method'])
    paragraph('Расчёт: сумма скорректированных цен за м² × нормализованные веса; затем × площадь. Итог округляется до тысячи рублей.')
    for warning in data['warnings']: paragraph('Внимание: '+warning)
    paragraph('Результат сформирован информационно-аналитической системой на основе сравнительного анализа цен предложений и носит справочный характер. Документ не является официальным отчётом об оценке недвижимости.')
    story.append(PageBreak())
    paragraph('Использованные аналоги','Heading1')
    rows=[['№','Район / м²','Цена за м²','После поправок','Вес']]
    for p in data['analogs']:
        rows.append([str(p['id']),Paragraph(escape(f"{p['district']} / {p['total_area']}"),styles['BodyText']),f"{p['price_per_m2']:,.0f}",f"{p['corrected_price_per_m2']:,.0f}",f"{p['weight']:.1%}"])
    table=Table(rows,colWidths=[32,145,90,110,55],repeatRows=1)
    table.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Cyrillic'),('FONTSIZE',(0,0),(-1,-1),9),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e6eff4')),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#cbd5e1')),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.extend([table,Spacer(1,16)])
    for p in data['analogs']:
        paragraph(f"Аналог №{p['id']}: {p['rooms']} комн.; этаж {p['floor']}/{p['floors_total']}; {translated.get(p['condition'],p['condition'])}; {translated.get(p['building_type'],p['building_type'])}; цена {money(p['price_rub'])}.")
        paragraph(f"Поправки: ремонт {p['corrections']['condition']:.4f}; дом {p['corrections']['building']:.4f}; этаж {p['corrections']['floor']:.4f}; итог {p['total_correction']:.4f}. Схожесть {p['similarity']:.4f}.")
    snapshot=valuation.coefficients_snapshot
    paragraph(f"Настройки расчёта: версия {snapshot['version']}. Допустимая итоговая поправка: {snapshot['coefficients']['correction_min']} - {snapshot['coefficients']['correction_max']}. Диапазон оценки: ±{snapshot['coefficients']['range_percent']:.0%}.")
    paragraph(f"Диагностика: исключено записей / событий: {len(data['diagnostics'])}. Этап поиска: {data['search_stage']}.")
    def footer(canvas, doc):
        canvas.setFont('Cyrillic',8)
        canvas.drawString(40,24,'RealEstate Analytics | Информационная экспресс-оценка')
        canvas.drawRightString(555,24,str(doc.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return stream.getvalue()
