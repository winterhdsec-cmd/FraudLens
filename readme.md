

```text
my_fraud_project/
├── backend/              # 后端 (Python)
│   ├── app.py            # Flask 主程序 (在这里写 Agent 逻辑)
│   ├── tools.py          # 放 BGE, HDBSCAN, OCR 的函数
│   └── requirements.txt  # Python 依赖
├── frontend/             # 前端 (Vue)
│   ├── src/
│   │   ├── App.vue       # 主页面
│   │   └── components/   # 上传组件、图表组件
│   └── package.json
└── README.md
```

>vue如何启动(前端)
>(以下命令在前端frontend目录下bash进行)
>npm create vite@latest            . -- --template vue
>#然后安装依赖
>npm install 
>npm install npm install element-plus @element-plus/icons-vue axios
>
>npm run dev(安装后启动命令)

>后端如何启动
>(在backend目录下运行)
>python app.py
>
>
