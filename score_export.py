"""Generate a real XLSX workbook using standard-library OOXML only."""
import io,re,zipfile
from xml.etree.ElementTree import Element,SubElement,tostring
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
def column(number):
 out=''
 while number:number,r=divmod(number-1,26);out=chr(65+r)+out
 return out

def sheet(rows):
 root=Element('worksheet',xmlns=NS)
 views=SubElement(root,'sheetViews');view=SubElement(views,'sheetView',workbookViewId='0');SubElement(view,'pane',xSplit='2',ySplit='1',topLeftCell='C2',activePane='bottomRight',state='frozen')
 cols=SubElement(root,'cols')
 for i in range(1,len(rows[0])+1):SubElement(cols,'col',min=str(i),max=str(i),width='16',customWidth='1')
 data=SubElement(root,'sheetData')
 for ri,values in enumerate(rows,1):
  row=SubElement(data,'row',r=str(ri),ht='28' if ri==1 else '23',customHeight='1')
  for ci,value in enumerate(values,1):
   if value is None:continue
   cell=SubElement(row,'c',r=column(ci)+str(ri),s='1' if ri==1 else '0')
   if type(value) in (int,float):SubElement(cell,'v').text=str(value)
   else:
    cell.set('t','inlineStr');inline=SubElement(cell,'is');text=SubElement(inline,'t');text.set('{http://www.w3.org/XML/1998/namespace}space','preserve');text.text=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '',str(value))
 SubElement(root,'autoFilter',ref='A1:'+column(len(rows[0]))+str(len(rows)))
 return tostring(root,encoding='utf-8',xml_declaration=True)

def workbook(students,classes,empty_exam=None):
 question_ids=sorted({q['id'] for s in students for q in s['exam']} or {q['id'] for q in (empty_exam or [])})
 rows=[['학번','이름']+[f'{i}번 정오답' for i in question_ids]+['총점','만점','반','제출 상태','서술형 채점 상태']]
 names={c['id']:c['name'] for c in classes}
 for s in sorted(students,key=lambda s:(names.get(s['class_id'],''),s['student_id'],s['name'],s['recordId'])):
  g=s['grade'];values={}
  if g:
   for item in g['items']:values[item['id']]='O' if item['score']==item['maximum'] else 'X'
   for item in g['essays']:
    result='O' if item['score']==item['maximum'] else 'X' if item['score']==0 else '부분정답'
    values[item['id']]=f"{result} ({item['score']}/{item['maximum']}점)"
  present={q['id'] for q in s['exam']}
  marks=[values.get(i,'미제출') if i in present else '해당 없음' for i in question_ids]
  rows.append([s['student_id'],s['name']]+marks+[g['total'] if g else None,g['maximum'] if g else None,names.get(s['class_id'],''),'제출 완료' if s['submitted'] else '미제출',('교사 수정' if g['manual'] else '자동 제안 · 교사 확인 전') if g and g['essays'] else ''])
 notes=[['안내'],['객관식: O=정답, X=오답. 서술형: 획득 점수에 따라 O/X/부분정답 및 점수를 표시합니다.'],['총점에는 현재 서술형 점수가 반영됩니다. 자동 제안 상태인 학생은 교사가 검토해 주세요.'],['미제출 학생의 점수는 빈칸입니다. 해당 없음은 그 학생의 시험 버전에 없는 문항입니다.'],['학번과 이름은 텍스트로 보관하여 앞자리 0과 수식처럼 보이는 문자를 그대로 유지합니다.']]
 output=io.BytesIO()
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('[Content_Types].xml','''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>''')
  z.writestr('_rels/.rels','''<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''')
  z.writestr('xl/workbook.xml','''<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="학생점수" sheetId="1" r:id="rId1"/><sheet name="안내" sheetId="2" r:id="rId2"/></sheets></workbook>''')
  z.writestr('xl/_rels/workbook.xml.rels','''<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>''')
  z.writestr('xl/styles.xml','''<?xml version="1.0"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="맑은 고딕"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="맑은 고딕"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF245A40"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>''')
  z.writestr('xl/worksheets/sheet1.xml',sheet(rows));z.writestr('xl/worksheets/sheet2.xml',sheet(notes))
 return output.getvalue()
