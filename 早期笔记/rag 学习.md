# rag 学习

常用的命令：

~~~
-- 初始化环境
uv init . -p 3.11
uv venv

--langchain 下载
uv pip install langchain-openai -i https://pypi.tuna.tsinghua.edu.cn/simple

-- mysql下载
uv pip install mysql

-- mysql
connectormysql-connector-python

--langchain_community 指定版本（新版本的类和方法不一样）
uv pip install langchain_community==0.4.1




~~~



EAD2374F-A44A-4D8D-A091-21CC7B41C883/20260705063043



1. 创建数据库，创建数据表
2. init.py 初始化数据 uv run init.py
3. 



**分块大小怎么定：看文档段落大概多少长度**



rag优化：

最快看到效果：向量模型



## 消息写法

  一条消息有三种等价写法(前面讲过):
  ("user", "你好")                              # 元组
  {"role": "user", "content": "你好"}           # 字典
  HumanMessage(content="你好")                  # 类对象
  三个都行,看你顺手。字典版是 OpenAI 官方风格,课件里常用。





一些没理解的场景：

- agent中的context怎么理解，一般怎么使用
- 