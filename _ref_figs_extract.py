import fitz, re, os

REF = "E:/FraudLens/paper/参考文献"
OUT = "E:/FraudLens/_ref_figs"
os.makedirs(OUT, exist_ok=True)

papers = [
    "“私教”还是“枪手”：基于大模型的计算机实践教学探索_李清勇.pdf",
    "人工智能技术赋能计算机实践教学创新_刘莞玲.pdf",
    "基于智能体编程的智创编程教学模式探索_谢鑫.pdf",
    "基于通用大语言模型的计算机系统创新实验设计_张金 (1).pdf",
    "集成AI大语言模型的在线编程实验平台设计与实现_厉旭杰.pdf",
    "“知识图谱+大模型”赋能《Python数据分析及应用》课程教学模式创新_王平水.pdf",
    "新工科背景下“解决复杂工程问题”能力培养研究——以信息安全专业综合实习为例_向尕.pdf",
    "网络空间安全专业研究生课程思政教育的探索与实践_李剑.pdf",
]

cap_re = re.compile(r'图\s*[一二三四五六七八九十0-9]+|Figure\s*\d+', re.IGNORECASE)

for p in papers:
    path = os.path.join(REF, p)
    if not os.path.exists(path):
        print("MISS", p); continue
    doc = fitz.open(path)
    short = re.sub(r'[\\/:*?"<>|]', '_', p).replace('.pdf','')
    pages_hit = []
    for i, page in enumerate(doc):
        txt = page.get_text("text")
        if cap_re.search(txt):
            pages_hit.append(i)
    pages_hit = pages_hit[:12]
    cnt = 0
    for i in pages_hit:
        page = doc[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5,1.5))
        fn = f"{short}_p{i+1:02d}.png"
        pix.save(os.path.join(OUT, fn))
        cnt += 1
    print(f"{short}: {doc.page_count}页, 渲染图页 {cnt} 张 -> {pages_hit}")
    doc.close()
print("DONE")
