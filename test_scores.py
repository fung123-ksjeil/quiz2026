import io,zipfile,unittest
from xml.etree import ElementTree as ET
from score_export import workbook,format_submission
from grading import grade
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def read_workbook(data,sheet_name='학생점수'):
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  book=ET.fromstring(z.read('xl/workbook.xml'))
  rel_ns='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
  sheet=next(s for s in book.findall('s:sheets/s:sheet',NS) if s.get('name')==sheet_name)
  relations=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
  target=next(r.get('Target') for r in relations if r.get('Id')==sheet.get(f'{{{rel_ns}}}id'))
  root=ET.fromstring(z.read('xl/'+target))
 rows=[]
 for row in root.findall('s:sheetData/s:row',NS):
  cells={}
  for cell in row.findall('s:c',NS):
   column=''.join(c for c in cell.attrib['r'] if c.isalpha());position=0
   for c in column:position=position*26+ord(c)-64
   text=cell.find('s:is/s:t',NS) if cell.get('t')=='inlineStr' else cell.find('s:v',NS)
   value=text.text or '' if text is not None else None
   cells[position]=value if cell.get('t')=='inlineStr' or value is None else float(value) if '.' in value else int(value)
  rows.append([cells.get(i) for i in range(1,max(cells,default=0)+1)])
 width=len(rows[0]) if rows else 0
 return [row+[None]*(width-len(row)) for row in rows]
class ScoreExportTests(unittest.TestCase):
 def test_real_xlsx_text_safety_and_partial_scores(self):
  exam=[{'id':1,'options':['a','b'],'correct':1,'points':1},{'id':2,'options':['a','b'],'correct':2,'points':2},{'id':16,'options':[],'points':5,'rubric':'international'}]
  answers={'1':1,'2':1,'16':{'government':'작성','citizen':'작성'}}
  students=[{'recordId':1,'class_id':'a','student_id':'00123','name':'=1+1','exam':exam,'submitted':'2026-10-31T15:04:09Z','grade':grade(answers,4,exam)},{'recordId':2,'class_id':'a','student_id':'00124','name':'미제출 학생','exam':exam,'submitted':None,'grade':None}]
  data=workbook(students,[{'id':'a','name':'3-1'}]);rows=read_workbook(data);self.assertEqual(rows[1][:2],['00123','=1+1']);self.assertEqual(rows[1][2:5],['O','X','부분정답 (4/5점)']);self.assertEqual(rows[1][5],5);self.assertEqual(rows[2][2:5],['미제출']*3);self.assertIsNone(rows[2][5]);self.assertEqual(rows[1][rows[0].index('제출 시각 (한국 시간)')],'2026-11-01 00:04:09');self.assertIsNone(rows[2][rows[0].index('제출 시각 (한국 시간)')])
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   root=ET.fromstring(z.read('xl/worksheets/sheet1.xml'));self.assertFalse(root.findall('.//s:f',NS));self.assertEqual(root.find('.//s:c[@r="A2"]',NS).get('t'),'inlineStr')
 def test_answer_sheets_sort_by_student_id_and_preserve_text(self):
  first_exam=[{'id':1,'options':['이전 보기']},{'id':16,'options':[]}]
  second_exam=[{'id':1,'options':['새 보기']},{'id':2,'options':['추가 보기']},{'id':16,'options':[]}]
  government='  =1+1\r\n정부 답안  '
  citizen='\t시민 & <답안>\n'
  students=[
   {'recordId':1,'class_id':'a','student_id':'00124','name':'이전 학생','exam':first_exam,
    'answers':{'1':1,'16':'이전 통합 답안'},'submitted':None,'grade':None},
   {'recordId':2,'class_id':'b','student_id':'00123','name':'새 학생','exam':second_exam,
    'answers':{'1':1,'2':1,'16':{'government':government,'citizen':citizen}},
    'submitted':'2026-10-31T15:04:09Z','grade':{'items':[],'essays':[],'total':3,'maximum':7}},
   {'recordId':3,'class_id':'a','student_id':'00125','name':'미응답','exam':first_exam,
    'submitted':None,'grade':None},
  ]
  data=workbook(students,[{'id':'a','name':'3-1'},{'id':'b','name':'3-2'}])
  points=read_workbook(data)
  choices=read_workbook(data,'학생답안')
  essays=read_workbook(data,'서술형답안')
  for rows in (points,choices,essays):
   self.assertEqual([row[0] for row in rows[1:]],['00123','00124','00125'])
  base=['00123','새 학생','3-2',3,7,'2026-11-01 00:04:09']
  self.assertEqual(choices[1],base+[1,'새 보기',1,'추가 보기'])
  self.assertEqual(choices[2][6:],[1,'이전 보기',None,None])
  self.assertEqual(choices[3][6:],[None]*4)
  self.assertEqual(essays[1],base+[government,citizen,None])
  self.assertEqual(essays[2][6:],[None,None,'이전 통합 답안'])
  self.assertEqual(essays[3][6:],[None]*3)

 def test_submission_timezone_and_seconds(self):
  self.assertEqual(format_submission('2026-10-31T15:00:01Z'),'2026-11-01 00:00:01')
  self.assertEqual(format_submission('2026-11-01T00:04:09+09:00'),'2026-11-01 00:04:09')
  self.assertEqual(format_submission(None),'')
  self.assertEqual(format_submission('invalid'),'확인 필요')
 def test_empty_workbook_headers(self):
  data=workbook([],[],[{'id':1,'options':['보기']}])
  rows=read_workbook(data)
  self.assertEqual(rows[0][2],'1번 정오답');self.assertEqual(len(rows),1)
  self.assertEqual(read_workbook(data,'학생답안')[0][6:],['1번 선택 번호','1번 선택 내용'])
  self.assertEqual(read_workbook(data,'서술형답안')[0][6:8],['16번 government','16번 citizen'])
if __name__=='__main__':unittest.main(verbosity=2)
