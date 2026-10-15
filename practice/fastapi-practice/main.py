"""FastAPI 挖空练习 — 电影管理 API 入口（对照课件《02-FastAPI 快速入门课件.md》完成所有 TODO）

Java 对照：FastAPI ≈ Spring Boot，本文件 ≈ Application 启动类；
uvicorn ≈ 内嵌 Tomcat；pyproject.toml ≈ pom.xml；uv ≈ Maven。

启动步骤（在 fastapi-practice 目录下依次执行）：
    uv init                              # 首次：生成 pyproject.toml（不会覆盖本文件）
    uv add fastapi "uvicorn[standard]"   # 加依赖
    uv run uvicorn main:app --reload     # main = main.py 模块名，app = 下面你创建的实例变量名

验收标准（三条全过才算完成）：
    1. 浏览器打开 http://127.0.0.1:8000/ 能看到你返回的 JSON
    2. http://127.0.0.1:8000/docs 里能看到「电影」分组下的全部接口
    3. 在 /docs 里点 Try it out 调 GET /movies，能拿到假数据列表
"""

from fastapi import FastAPI

# TODO 1: 从 api/movies.py 导入 router（提示：from api.movies import ...）
#   Java 对照：Spring 会自动扫描 @RestController，Python 没有自动扫描，
#   路由必须显式 import 进来再注册。
from api.movies import router as movies_router


app=FastAPI(title="电影管理API-msy")

# TODO 2: 创建 FastAPI 应用实例，变量名必须叫 app（启动命令 main:app 靠名字找它），
#   并设置 title="电影管理 API"（会显示在 /docs 文档顶部）


# TODO 3: 用装饰器把下面的函数绑定到 GET /
#   Java 对照：@GetMapping("/")。Python 装饰器写在函数定义的上一行，以 @ 开头。
@app.get("/")
async def get_home():
    # TODO 4: 返回一个 dict，比如 {"code": 200, "message": "电影管理 API 运行正常"}
    #   FastAPI 会自动把 dict 转成 JSON（≈ Java 返回 Map/DTO + @ResponseBody）。
    #   Java 高频坑：Python 忘写 return 时函数返回 None，页面会显示 null。
      # ← 完成后删掉这行
    return {
        "code":200,
        "message":"电影管理API运行正常"
    }


# TODO 5: 把电影路由注册进应用：
#   app.include_router(路由对象, prefix="/movies", tags=["电影"])
#   Java 对照：prefix ≈ Controller 类上的 @RequestMapping("/movies")，
#   tags 只影响 /docs 文档里的分组名。

app.include_router(movies_router,prefix="/movies",tags=["电影"])


def main():
    return get_home()

if __name__ == "__main__":
    main()
