import io,zipfile,unittest
from xml.etree import ElementTree as ET
from score_export import workbook
from grading import grade
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def read_workbook(data):
 with zipfile.ZipFile(io.BytesIO(data)) as z:root=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
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
 return rows
class ScoreExportTests(unittest.TestCase):
 def test_real_xlsx_text_safety_and_partial_scores(self):
  exam=[{'id':1,'options':['a','b'],'correct':1,'points':1},{'id':2,'options':['a','b'],'correct':2,'points':2},{'id':16,'options':[],'points':5,'rubric':'international'}]
  answers={'1':1,'2':1,'16':{'government':'작성','citizen':'작성'}}
  students=[{'recordId':1,'class_id':'a','student_id':'00123','name':'=1+1','exam':exam,'submitted':'now','grade':grade(answers,4,exam)},{'recordId':2,'class_id':'a','student_id':'00124','name':'미제출 학생','exam':exam,'submitted':None,'grade':None}]
  data=workbook(students,[{'id':'a','name':'3-1'}]);rows=read_workbook(data);self.assertEqual(rows[1][:2],['00123','=1+1']);self.assertEqual(rows[1][2:5],['O','X','부분정답 (4/5점)']);self.assertEqual(rows[1][5],5);self.assertEqual(rows[2][2:5],['미제출']*3);self.assertIsNone(rows[2][5])
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   root=ET.fromstring(z.read('xl/worksheets/sheet1.xml'));self.assertFalse(root.findall('.//s:f',NS));self.assertEqual(root.find('.//s:c[@r="A2"]',NS).get('t'),'inlineStr')
 def test_empty_workbook_headers(self):
  rows=read_workbook(workbook([],[],[{'id':1}]))
  self.assertEqual(rows[0][2],'1번 정오답');self.assertEqual(len(rows),1)
if __name__=='__main__':unittest.main(verbosity=2)
