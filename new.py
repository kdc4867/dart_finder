import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import OpenDartReader
import requests
from bs4 import BeautifulSoup, Tag
import re
from markupsafe import Markup

class DartApp:
    def __init__(self, master):
        self.master = master
        master.title("DART 검색 애플리케이션")
        master.geometry("800x600")

        self.api_key = '5ec6628d8d7615759fa05045ee03363bc49a080b'  # 여기에 실제 API 키를 입력하세요
        self.dart = OpenDartReader(self.api_key)

        # 입력 프레임
        input_frame = ttk.Frame(master, padding="10")
        input_frame.pack(fill=tk.X)

        ttk.Label(input_frame, text="종목코드:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.stock_code = ttk.Entry(input_frame, width=20)
        self.stock_code.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="연도:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.year = ttk.Entry(input_frame, width=10)
        self.year.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(input_frame, text="보고서 종류:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.report_type = ttk.Combobox(input_frame, values=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'])
        self.report_type.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="키워드:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.keyword = ttk.Entry(input_frame, width=20)
        self.keyword.grid(row=1, column=3, padx=5, pady=5)

        ttk.Button(input_frame, text="검색", command=self.search).grid(row=2, column=0, columnspan=4, pady=10)

        # 결과 표시 영역
        self.result_text = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=80, height=30)
        self.result_text.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

    def search(self):
        stock_code = self.stock_code.get()
        year = self.year.get()
        report_type = self.report_type.get()
        keyword = self.keyword.get()

        try:
            report_list = self.dart.list(stock_code, start=year, kind=report_type, final=False)
            if report_list.empty:
                messagebox.showinfo("결과", "해당하는 보고서를 찾을 수 없습니다.")
                return

            rcept_no = report_list.iloc[0]['rcept_no']
            sub_docs = self.dart.sub_docs(rcept_no)
            
            url = None
            for doc in sub_docs.itertuples():
                if '재무제표 주석' in doc.title:
                    url = doc.url
                    break

            if not url:
                messagebox.showinfo("결과", "재무제표 주석을 찾을 수 없습니다.")
                return

            response = requests.get(url)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')

            keyword_element = soup.find(text=re.compile(re.escape(keyword)))

            if keyword_element:
                parent = keyword_element.find_parent()
                siblings = list(parent.find_all_previous(limit=10)) + [parent] + list(parent.find_all_next(limit=10))
                
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

                result_html = str(result_div)
                
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, result_html)
            else:
                messagebox.showinfo("결과", f"키워드 '{keyword}'를 찾을 수 없습니다.")

        except Exception as e:
            messagebox.showerror("오류", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = DartApp(root)
    root.mainloop()