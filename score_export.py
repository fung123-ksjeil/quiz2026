"""Generate a real XLSX workbook using standard-library OOXML only."""
import io,re,zipfile
from datetime import datetime,timedelta,timezone
from xml.etree.ElementTree import Element,SubElement,tostring
OFFICE_RELS='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PACKAGE_RELS='http://schemas.openxmlformats.org/package/2006/relationships'
CONTENT_TYPES='http://schemas.openxmlformats.org/package/2006/content-types'
XLSX_TYPE='application/vnd.openxmlformats-officedocument.spreadsheetml.'
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
def format_submission(value):
 if not value:return ''
 if not isinstance(value,str):return '확인 필요'
 try:
  instant=datetime.fromisoformat(value.replace('Z','+00:00'))
  if instant.tzinfo is None:instant=instant.replace(tzinfo=timezone.utc)
  return instant.astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
 except ValueError:return '확인 필요'

def column(number):
 out=''
 while number:number,r=divmod(number-1,26);out=chr(65+r)+out
 return out

def sheet(rows,answer_columns=()):
 root=Element('worksheet',xmlns=NS)
 views=SubElement(root,'sheetViews');view=SubElement(views,'sheetView',workbookViewId='0');SubElement(view,'pane',xSplit='2',ySplit='1',topLeftCell='C2',activePane='bottomRight',state='frozen')
 cols=SubElement(root,'cols')
 for i,header in enumerate(rows[0],1):
  width=48 if i in answer_columns else 26 if header=='제출 시각 (한국 시간)' else 16
  SubElement(cols,'col',min=str(i),max=str(i),width=str(width),customWidth='1')
 data=SubElement(root,'sheetData')
 for ri,values in enumerate(rows,1):
  row=SubElement(data,'row',r=str(ri))
  if ri==1 or not answer_columns:
   row.attrib.update(ht='28' if ri==1 else '23',customHeight='1')
  for ci,value in enumerate(values,1):
   if value is None:continue
   cell=SubElement(row,'c',r=column(ci)+str(ri),s='1' if ri==1 else '0')
   if type(value) in (int,float):SubElement(cell,'v').text=str(value)
   else:
    cell.set('t','inlineStr');inline=SubElement(cell,'is');text=SubElement(inline,'t');text.set('{http://www.w3.org/XML/1998/namespace}space','preserve');text.text=re.sub(
     r'_[xX][0-9a-fA-F]{4}_|[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]',
     lambda match: '_x005F_'+match[0][1:] if match[0].startswith('_') else f'_x{ord(match[0]):04X}_',
     str(value),
    )
 SubElement(root,'autoFilter',ref='A1:'+column(len(rows[0]))+str(len(rows)))
 return tostring(root,encoding='utf-8',xml_declaration=True).replace(b'\r',b'&#13;')

def workbook(students,classes,empty_exam=None):
 exams=[s['exam'] for s in students] or [empty_exam or []]
 question_ids=sorted({q['id'] for exam in exams for q in exam})
 choice_ids=sorted({q['id'] for exam in exams for q in exam if q.get('options')})
 rows=[['학번','이름']+[f'{i}번 정오답' for i in question_ids]+['총점','만점','반','제출 상태','서술형 채점 상태','제출 시각 (한국 시간)']]
 metadata=['학번','이름','반','총점','만점','제출 시각 (한국 시간)']
 choices=[metadata+[header for i in choice_ids for header in (f'{i}번 선택 번호',f'{i}번 선택 내용')]]
 essays=[metadata+['16번 government','16번 citizen','16번 이전 형식 통합 답안']]
 names={c['id']:c['name'] for c in classes}
 for s in sorted(students,key=lambda s:(str(s['student_id']),names.get(s['class_id'],''),s['name'],s['recordId'])):
  g=s['grade'];values={}
  if g:
   for item in g['items']:values[item['id']]='O' if item['score']==item['maximum'] else 'X'
   for item in g['essays']:
    result='O' if item['score']==item['maximum'] else 'X' if item['score']==0 else '부분정답'
    values[item['id']]=f"{result} ({item['score']}/{item['maximum']}점)"
  present={q['id'] for q in s['exam']}
  marks=[values.get(i,'미제출') if i in present else '해당 없음' for i in question_ids]
  identity=[str(s['student_id']),s['name']]
  class_name=names.get(s['class_id'],'')
  scores=[g['total'],g['maximum']] if g else [None,None]
  submitted=format_submission(s['submitted']) or None
  essay_status=('교사 수정' if g['manual'] else '자동 제안 · 교사 확인 전') if g and g['essays'] else ''
  rows.append(identity+marks+scores+[class_name,'제출 완료' if s['submitted'] else '미제출',essay_status,submitted])

  base=identity+[class_name]+scores+[submitted]
  answers=s.get('answers') or {}
  options_by_id={q['id']:q['options'] for q in s['exam'] if q.get('options')}
  choice_row=base.copy()
  for i in choice_ids:
   options=options_by_id.get(i,[])
   selection=answers.get(str(i))
   if type(selection) is int and 1<=selection<=len(options):
    choice_row.extend([selection,options[selection-1]])
   else:
    choice_row.extend([None,None])
  choices.append(choice_row)

  answer=None if 16 in options_by_id else answers.get('16')
  parts=answer if isinstance(answer,dict) else {}
  essays.append(base+[parts.get('government'),parts.get('citizen'),answer if isinstance(answer,str) else None])
 notes=[['안내'],['제출 시각은 서버가 기록한 최종 제출 시각을 한국 시간(UTC+9)으로 변환하여 날짜·시·분·초까지 표시합니다. 미제출은 빈칸입니다.'],['객관식: O=정답, X=오답. 서술형: 획득 점수에 따라 O/X/부분정답 및 점수를 표시합니다.'],['총점에는 현재 서술형 점수가 반영됩니다. 자동 제안 상태인 학생은 교사가 검토해 주세요.'],['미제출 학생의 점수는 빈칸입니다. 해당 없음은 그 학생의 시험 버전에 없는 문항입니다.'],['학번과 이름은 텍스트로 보관하여 앞자리 0과 수식처럼 보이는 문자를 그대로 유지합니다.']]
 sheets=[
  ('학생점수',rows,()),
  ('학생답안',choices,range(len(metadata)+2,len(choices[0])+1,2)),
  ('서술형답안',essays,range(len(metadata)+1,len(essays[0])+1)),
  ('안내',notes,()),
 ]
 types=Element('Types',xmlns=CONTENT_TYPES)
 SubElement(types,'Default',Extension='rels',ContentType='application/vnd.openxmlformats-package.relationships+xml')
 SubElement(types,'Default',Extension='xml',ContentType='application/xml')
 SubElement(types,'Override',PartName='/xl/workbook.xml',ContentType=XLSX_TYPE+'sheet.main+xml')
 SubElement(types,'Override',PartName='/xl/styles.xml',ContentType=XLSX_TYPE+'styles+xml')
 book=Element('workbook',xmlns=NS,attrib={'xmlns:r':OFFICE_RELS})
 sheet_list=SubElement(book,'sheets')
 relationships=Element('Relationships',xmlns=PACKAGE_RELS)
 output=io.BytesIO()
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
  for index,(name,data,answer_columns) in enumerate(sheets,1):
   target=f'worksheets/sheet{index}.xml'
   relationship_id=f'rId{index}'
   SubElement(sheet_list,'sheet',name=name,sheetId=str(index),attrib={'r:id':relationship_id})
   SubElement(relationships,'Relationship',Id=relationship_id,Type=OFFICE_RELS+'/worksheet',Target=target)
   SubElement(types,'Override',PartName='/xl/'+target,ContentType=XLSX_TYPE+'worksheet+xml')
   z.writestr('xl/'+target,sheet(data,answer_columns))
  SubElement(relationships,'Relationship',Id=f'rId{len(sheets)+1}',Type=OFFICE_RELS+'/styles',Target='styles.xml')
  z.writestr('[Content_Types].xml',tostring(types,encoding='utf-8'))
  z.writestr('xl/workbook.xml',tostring(book,encoding='utf-8'))
  z.writestr('xl/_rels/workbook.xml.rels',tostring(relationships,encoding='utf-8'))
  z.writestr('_rels/.rels','''<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''')
  z.writestr('xl/styles.xml','''<?xml version="1.0"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="맑은 고딕"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="맑은 고딕"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF245A40"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>''')
 return output.getvalue()
