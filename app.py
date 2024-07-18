from flask import Flask, request, render_template, abort
from markupsafe import Markup
import OpenDartReader
import requests
from bs4 import BeautifulSoup, Tag
import re
from typing import List, Tuple, Dict, Any
import logging
import os
app = Flask(__name__)

# 상수
API_KEY = 'DART_API_KEY'
SIBLING_LIMIT = 100

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenDartReader 초기화
dart = OpenDartReader(API_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        stock_code = request.form['stock_code']
        report_year = request.form['report_year']
        report_kind = request.form['report_kind']

        report_list = dart.list(stock_code, start=report_year, kind=report_kind, final=False)
        if report_list.empty:
            return render_template('error.html', message="No reports found for the given criteria.")
        
        report_list_df = report_list[['rcept_no', 'report_nm']]
        return render_template('report_list.html', report_list=report_list_df.to_dict('records'))
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return render_template('error.html', message="An error occurred while searching for reports.")

@app.route('/extract', methods=['POST'])
def extract():
    try:
        rcept_no = request.form['rcept_no']
        keyword = request.form['keyword']
        
        # 재무제표 주석 URL 찾기
        sub_docs = dart.sub_docs(rcept_no)
        section_url = next((doc.url for doc in sub_docs.itertuples() if '재무제표 주석' in doc.title), None)
        
        if not section_url:
            return render_template('error.html', message="재무제표 주석을 찾을 수 없습니다.")

        result_html = extract_and_highlight(section_url, keyword)
        if result_html:
            safe_content = Markup(result_html)
            return render_template('result.html', content=safe_content, keyword=keyword)
        else:
            return render_template('error.html', message=f"키워드 '{keyword}'를 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"Error in extract: {str(e)}")
        return render_template('error.html', message="데이터 추출 중 오류가 발생했습니다.")

def extract_and_highlight(url: str, keyword: str) -> str:
    response = requests.get(url)
    response.raise_for_status()
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.content, 'html.parser')

    keyword_element = soup.find(text=re.compile(re.escape(keyword)))
    if not keyword_element:
        return ""

    parent = keyword_element.find_parent()
    siblings = (
        list(parent.find_all_previous(limit=SIBLING_LIMIT)) + 
        [parent] + 
        list(parent.find_all_next(limit=SIBLING_LIMIT))
    )

    context = BeautifulSoup('<div id="extract-result"></div>', 'html.parser')
    result_div = context.find(id="extract-result")

    for sibling in siblings:
        if isinstance(sibling, Tag):
            new_tag = context.new_tag(sibling.name, attrs=sibling.attrs)
            new_tag.extend(sibling.contents)
            result_div.append(new_tag)
        else:
            result_div.append(sibling)

    for element in result_div.find_all(text=re.compile(re.escape(keyword))):
        highlighted = context.new_tag("mark")
        highlighted.string = element
        element.replace_with(highlighted)

    return str(result_div)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)