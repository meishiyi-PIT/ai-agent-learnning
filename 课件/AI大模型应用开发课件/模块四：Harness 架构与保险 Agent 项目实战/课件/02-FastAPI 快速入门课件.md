# FastAPI 与项目搭建
FastAPI 是一个用于构建 Web API 的 Python 框架。它支持 Python 类型提示、异步函数和自动接口文档，适合开发前后端分离项目。

本文以电影管理程序为例，介绍 FastAPI 的安装、RESTful 风格、项目结构、接口文档、路由分发、`Request` 对象、静态文件和模板文件。

项目地址：[fastApi 示例项目](https://git.miaoatech.cn/yangxiaolong/fastApi)

## 1. 安装 FastAPI
本文使用 uv 管理 Python 版本、虚拟环境和项目依赖。

```bash
uv init
```

FastAPI 负责定义接口，还需要 ASGI 服务器运行应用：

```bash
uv add fastapi "uvicorn[standard]"
```

如果需要渲染 HTML 模板，再添加 Jinja2：

```bash
uv add jinja2
```

各依赖的作用如下：

| 依赖 | 作用 |
| --- | --- |
| `fastapi` | 创建应用、定义路由、处理请求和响应 |
| `uvicorn` | 启动并运行 FastAPI 应用 |
| `jinja2` | 将数据填充到 HTML 模板 |


安装完成后，可以用下面的命令检查 FastAPI 是否可用：

```bash
uv run python -c "import fastapi; print(fastapi.__version__)"
```

`uv add` 会把依赖写入 `pyproject.toml`，同时更新 `uv.lock` 和项目虚拟环境。通常不需要手动创建或激活虚拟环境。

## 2. RESTful 风格
RESTful 使用 URL 表示资源，使用 HTTP 方法表示对资源的操作。URL 一般使用名词，操作则由请求方法表达。

以电影资源为例：

| HTTP 方法 | 路径 | 含义 |
| --- | --- | --- |
| `GET` | `/movies` | 查询电影列表 |
| `POST` | `/movies` | 新增电影 |
| `GET` | `/movies/1` | 查询编号为 1 的电影 |
| `PUT` | `/movies/1` | 更新编号为 1 的电影 |
| `DELETE` | `/movies/1` | 删除编号为 1 的电影 |


不推荐把动作写进路径，例如 `/getMovies` 和 `/deleteMovie`。更清晰的写法是让 `/movies` 表示资源，通过 `GET`、`POST`、`PUT` 和 `DELETE` 表示操作。

常见状态码包括：

| 状态码 | 含义 |
| --- | --- |
| `200` | 请求成功 |
| `201` | 资源创建成功 |
| `400` | 请求数据有误 |
| `404` | 资源不存在 |
| `500` | 服务器内部错误 |


## 3. 快速创建 FastAPI 项目
创建一个项目目录，并在其中新建 `main.py`：

```python
from fastapi import FastAPI

app = FastAPI(title="电影管理 API")


@app.get("/")
async def get_home():
    return {
        "code": 200,
        "message": "电影管理 API 运行正常",
        "data": {"docs": "/docs"},
    }
```

在项目目录执行：

```bash
uv run uvicorn main:app --reload
```

命令含义：

+ `main`：表示 `main.py` 模块；
+ `app`：表示模块中的 FastAPI 实例；
+ `--reload`：代码修改后自动重启，仅用于开发环境。

打开 `http://127.0.0.1:8000/`，浏览器会显示接口返回的 JSON 数据。

`@app.get("/")` 是路径操作装饰器。它表示当客户端使用 `GET` 方法访问 `/` 时，FastAPI 调用下面的 `get_home()` 函数。

## 4. 项目目录与文件说明
电影管理程序采用下面的目录结构：

```latex
fastapi/
├── api/
│   ├── actors.py
│   ├── movies.py
│   ├── responses.py
│   └── studios.py
├── templates/
│   └── index.html
├── upimg/
│   └── img.png
├── main.py
├── models.py
├── settings.py
├── .python-version
├── pyproject.toml
├── uv.lock
└── README.md
```

### 4.1 `main.py`
`main.py` 是程序入口，主要负责：

+ 创建 FastAPI 应用；
+ 注册各业务路由；
+ 挂载静态文件目录；
+ 配置模板目录；
+ 注册中间件和数据库；
+ 定义少量公共接口。

应用启动命令中的 `main:app` 指向的就是这个文件和其中的 `app` 对象。

### 4.2 `api/`
`api` 目录存放接口代码。不同资源放在不同文件中：

+ `movies.py`：电影接口；
+ `actors.py`：演员接口；
+ `studios.py`：制片公司接口；
+ `responses.py`：统一响应格式。

这种拆分可以避免把所有接口都写进 `main.py`。新增或修改某类接口时，只需要进入对应文件。

### 4.3 `models.py`
`models.py` 用于定义数据模型及数据库表之间的关系。

示例项目中包含 `Movie`、`Actor` 和 `Studio` 三个模型，描述电影、演员、制片公司的字段，以及它们之间的关联。

模型负责说明“数据长什么样”，接口文件负责说明“如何访问这些数据”，两者职责不同。

### 4.4 `settings.py`
`settings.py` 用于集中保存项目配置，例如：

+ 数据库类型；
+ 数据库地址和端口；
+ 用户名与密码；
+ 数据库名称；
+ 时区；
+ 连接池大小。

教学项目可以直接写简单配置。实际项目不应把密码提交到代码仓库，一般通过环境变量或 `.env` 文件读取敏感信息。

### 4.5 `templates/`
`templates` 目录保存 Jinja2 HTML 模板。模板负责页面结构，FastAPI 负责把后端数据传给模板。

例如，`index.html` 可以接收电影列表，然后循环生成多个电影名称。

### 4.6 `upimg/`
`upimg` 是示例项目的静态资源目录，用于保存图片。

项目也可以使用更通用的目录名 `static`，并在其中继续建立 `css`、`js` 和 `images` 子目录。

### 4.7 `pyproject.toml` 与 `uv.lock`
`pyproject.toml` 声明项目元数据、Python 版本要求和直接依赖。例如：

```toml
[project]
name = "fastapi-movie"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi",
    "jinja2",
    "tortoise-orm[aiomysql]",
    "uvicorn[standard]",
]
```

依赖应通过命令维护，而不是直接手写版本解析结果：

```bash
uv add fastapi "uvicorn[standard]" "tortoise-orm[aiomysql]" jinja2
```

`uv.lock` 保存解析后的精确依赖版本，用于确保不同机器获得一致环境。该文件由 uv 自动维护，应提交到版本控制，不要手动编辑。

其他开发者拿到项目后，在项目目录执行：

```bash
uv sync
```

uv 会根据 `pyproject.toml` 和 `uv.lock` 创建或更新 `.venv`。运行项目命令时使用 `uv run`，可以确保命令在该项目环境中执行。

### 4.8 `README.md`
`README.md` 是项目说明文档，通常包含项目用途、安装方法、启动命令、目录结构和接口入口。

它不会参与程序运行，但能帮助使用者快速了解如何启动和维护项目。

## 5. FastAPI 接口文档
FastAPI 会根据路由和类型声明自动生成 OpenAPI 文档。服务启动后可以访问：

+ `http://127.0.0.1:8000/docs`：Swagger UI，可在线调试接口；
+ `http://127.0.0.1:8000/redoc`：ReDoc 接口说明；
+ `http://127.0.0.1:8000/openapi.json`：OpenAPI 原始数据。

可以在创建应用时设置文档信息：

```python
app = FastAPI(
    title="电影管理 API",
    description="电影、演员和制片公司管理接口",
    version="0.1.0",
)
```

接口的 `tags` 用于分组，`summary` 用于简要说明：

```python
@app.get(
    "/movies",
    tags=["电影"],
    summary="查询电影列表",
)
async def list_movies():
    return {"data": []}
```

接口定义、参数校验和文档来自同一份代码。修改路由后，接口文档会同步更新。

## 6. 路由分发与分包管理
### 6.1 模块、包与分包
一个 `.py` 文件就是一个 Python 模块，例如 `movies.py`。包含多个模块的目录可以作为 Python 包，例如 `api/`。

通常建议在代码包中添加 `__init__.py`：

```latex
api/
├── __init__.py
├── movies.py
├── actors.py
├── studios.py
└── responses.py
```

`__init__.py` 表明该目录是普通 Python 包，也可以统一导出包内对象。虽然新版 Python 支持没有 `__init__.py` 的命名空间包，但普通业务项目显式添加它更直观。

分包管理不是把每个文件都放进不同目录，而是把职责相关、会一起变化的代码放在同一个包中。

### 6.2 当前电影项目是否已经分包
当前代码已经完成了初步拆分：

+ `api/movies.py` 管理电影路由；
+ `api/actors.py` 管理演员路由；
+ `api/studios.py` 管理制片公司路由；
+ `api/responses.py` 管理统一响应；
+ `main.py` 负责创建应用并注册 Router。

因此，它不是所有代码都堆在一个文件中的单文件项目，已经具备“按资源拆分路由模块”的结构。

不过，当前 `api/` 中没有 `__init__.py`，`models.py` 和 `settings.py` 仍位于项目根目录，也没有进一步区分数据模型、配置与业务逻辑。

更准确的结论是：

> 当前项目做了路由模块化，但只完成了初级分包，还没有形成完整的分层包结构。
>

对于入门示例，这种结构已经够用。项目继续增长时，再逐步增加包，不需要一开始就建立很多空目录。

### 6.3 使用 APIRouter 分发路由
接口数量增加后，可以使用 `APIRouter` 将不同业务接口拆到不同文件。

在 `api/movies.py` 中定义电影路由：

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_movies():
    return {"message": "获取电影列表成功"}


@router.post("", status_code=201)
async def create_movie():
    return {"message": "创建电影成功"}


@router.put("/{movie_id}")
async def update_movie(movie_id: int):
    return {"message": "更新电影成功", "id": movie_id}


@router.delete("/{movie_id}")
async def delete_movie(movie_id: int):
    return {"message": "删除电影成功", "id": movie_id}
```

在 `main.py` 中导入并注册：

```python
from fastapi import FastAPI

from api.movies import router as movies_router

app = FastAPI(title="电影管理 API")

app.include_router(
    movies_router,
    prefix="/movies",
    tags=["电影"],
)
```

`prefix="/movies"` 为这一组路由添加统一前缀。`tags=["电影"]` 让这些接口显示在接口文档的“电影”分组中。

路由分发的目的不是增加文件数量，而是让每个文件只负责一类资源。

### 6.4 推荐的分包结构
随着模型、接口和业务逻辑增加，可以调整为：

```latex
fastapi/
├── api/
│   ├── __init__.py
│   ├── movies.py
│   ├── actors.py
│   └── studios.py
├── core/
│   ├── __init__.py
│   └── settings.py
├── schemas/
│   ├── __init__.py
│   └── movie.py
├── models/
│   ├── __init__.py
│   └── movie.py
├── services/
│   ├── __init__.py
│   └── movie.py
├── templates/
├── static/
└── main.py
```

各包的职责如下：

| 包 | 职责 |
| --- | --- |
| `api` | HTTP 路径、请求方法、状态码和路由注册 |
| `core` | 配置、安全、日志等公共能力 |
| `schemas` | 请求体和响应体的数据结构 |
| `models` | 数据库模型及表关系 |
| `services` | 业务规则和业务流程 |
| `templates` | HTML 模板 |
| `static` | 图片、CSS 和 JavaScript |


推荐的调用方向是：

```latex
main.py → api → services → models
```

`main.py` 只负责组装应用，Router 只处理 HTTP，Service 处理业务规则，Model 负责数据库结构。职责明确后，代码更容易测试和维护。

小型教学项目可以保留当前结构；当某个文件越来越长、同类功能不断增加，或业务逻辑开始在多个接口间重复时，再拆出对应的包。

## 7. Request 对象
在接口函数中声明 `request: Request`，可以读取当前请求的完整信息。

### 7.1 读取查询参数
```python
from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/demo/query")
async def get_query_parameters(request: Request):
    return {
        "data": dict(request.query_params),
    }
```

访问：

```latex
/demo/query?keyword=科幻&page=1
```

`request.query_params` 中会包含 `keyword` 和 `page`。

### 7.2 读取 JSON 请求体
```python
@app.post("/demo/body")
async def get_request_body(request: Request):
    body = await request.json()
    return {"data": body}
```

请求体需要异步读取，因此使用 `await request.json()`。

结构固定的业务数据通常使用 Pydantic 模型接收；`Request` 更适合读取请求头、客户端地址、Cookie 或未预先定义的原始数据。

## 8. 挂载静态文件
图片、CSS 和 JavaScript 等资源可以通过 `StaticFiles` 对外提供：

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "upimg"),
    name="static",
)
```

如果 `upimg` 目录中存在 `img.png`，浏览器可以通过下面的地址访问：

```latex
http://127.0.0.1:8000/static/img.png
```

这里的三个关键参数分别表示：

+ `"/static"`：浏览器访问时使用的 URL 前缀；
+ `directory`：静态文件在本地磁盘中的目录；
+ `name`：该静态文件服务的内部名称。

`BASE_DIR` 根据 `main.py` 的位置计算项目目录，不依赖启动命令所在的位置。

## 9. 使用模板文件
FastAPI 可以配合 Jinja2 返回动态 HTML 页面。

首先创建 `templates/index.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>电影列表</title>
</head>
<body>
    {% for movie in movies %}
    <p>{{ movie }}</p>
    {% endfor %}
</body>
</html>

```

在 `main.py` 中配置模板目录：

```python
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(
    directory=BASE_DIR / "templates",
)


@app.get("/pages/movies")
async def render_movies_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "movies": [
                "肖申克的救赎",
                "霸王别姬",
                "星际穿越",
            ],
        },
    )
```

主要参数含义：

+ `request`：当前请求对象；
+ `name`：需要渲染的模板文件；
+ `context`：传递给模板的数据。

Jinja2 使用 `{{ ... }}` 输出变量，使用 `{% ... %}` 编写循环或判断。

FastAPI 通常用于返回 JSON API。如果项目需要少量管理页面、邮件预览或服务端渲染页面，也可以使用模板。

## 10. 总结
本课件需要掌握的内容如下：

+ FastAPI 用于创建 Web API，Uvicorn 用于运行应用；
+ uv 通过 `pyproject.toml`、`uv.lock` 和 `.venv` 统一管理项目依赖与运行环境；
+ RESTful 使用资源路径和 HTTP 方法表达接口语义；
+ `main.py` 是应用入口，`api/` 存放分类后的路由；
+ `models.py` 描述数据模型，`settings.py` 保存项目配置；
+ FastAPI 会根据代码自动生成接口文档；
+ `APIRouter` 用于拆分和注册业务路由；
+ Python 模块是 `.py` 文件，代码包通常是带有 `__init__.py` 的目录；
+ 当前电影项目已拆分路由模块，但尚未形成完整的分层包结构；
+ `Request` 可以读取完整请求信息；
+ `StaticFiles` 用于提供静态资源；
+ Jinja2 用于渲染 HTML 模板。

