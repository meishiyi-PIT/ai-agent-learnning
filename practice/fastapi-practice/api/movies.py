"""电影路由 — 挖空练习（对照课件 6.3 节「使用 APIRouter 分发路由」）

Java 对照：本文件 ≈ 一个 @RestController 类；router ≈ 这个类本身；
下面每个函数 ≈ 类里一个 @GetMapping/@PostMapping/@DeleteMapping 方法。

注意：统一前缀 /movies 是在 main.py 注册时用 prefix 加的，
所以本文件里的路径只写 "" 或 "/{movie_id}"，不要重复写 /movies。
"""

from fastapi import APIRouter

# TODO 1: 创建 APIRouter 实例，变量名叫 router（main.py 会按这个名字 import）
router = APIRouter()

# 内存假数据，先不连数据库——先把接口层跑通，数据层以后再换
FAKE_MOVIES = [
    {"id": 1, "title": "肖申克的救赎"},
    {"id": 2, "title": "星际穿越"},
]


# TODO 2: 用装饰器绑定 GET ""（配合 prefix 后，实际访问路径是 GET /movies）
@router.get("")
async def list_movies():
    # TODO 3: 返回 {"data": FAKE_MOVIES}
    #  # ← 完成后删掉
    return {
        "data":FAKE_MOVIES,
        "method":"get",
        "code":200
    }


# TODO 4: 绑定 POST ""，并让成功响应码为 201（提示：装饰器参数 status_code=201，
#   对应课件第 2 节：201 = 资源创建成功）
@router.post("", status_code=201)
async def create_movie():
    # 状态码写在装饰器的 status_code 上（真正的 HTTP 状态），返回体只放数据
    return {"message": "创建电影成功"}


# TODO 5: 绑定 DELETE "/{movie_id}"，并给函数加参数 movie_id: int
#   Java 对照：{movie_id} ≈ @PathVariable；类型写 int 后 FastAPI 自动转换 + 校验，
#   请求 /movies/abc 会直接返回 422 参数错误，不用自己写校验代码——这是比
#   SpringMVC 手动校验更省事的地方，也是"类型提示"在 FastAPI 里的真实用途。
@router.delete("/{movie_id}")
async def delete_movie(movie_id: int):
    # 路径 {movie_id}、函数参数 movie_id、返回体 movie_id —— 三处名字必须完全一致
    return {"message": "删除电影成功", "id": movie_id}

