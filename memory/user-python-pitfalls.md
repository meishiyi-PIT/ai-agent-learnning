---
name: user-python-pitfalls
description: 用户从 Java 带来的高频 Python 坑清单（2026-07-30 tools.py 评审实测），教学与代码评审时重点盯
metadata: 
  node_type: memory
  type: user
  originSessionId: f6aac3af-871f-43fc-9f3c-c037246a6971
  modified: 2026-08-08T06:24:14.316Z
---

2026-07-30 评审用户手写的 tools.py 时实际踩到的坑（Java→Python 迁移型错误），后续讲解/评审重点盯：

1. **先 new 空对象再逐个 setter**：`ToolResult()` 空构造 → Pydantic 必填字段直接 ValidationError。要教"先收集局部变量，最后一次性带参构造"。
2. **元组返回值当 dict 取**：`data = f(); data['key']` → 应教元组解包 `a, b = f()`。对"返回值的形状"不敏感，评审时先核对每个调用的返回类型。
3. **忘记 return**：方法结尾漏 return（当时还残留 raise NotImplementedError）。
4. **列表推导与 for 循环混写**：`e.metadata for e in xs:` 语法错误。推导式语法未熟。
5. **用内置名当变量**：`list = []` 遮蔽内置 list。同类risk：dict/str/id/type。
6. **枚举 key 用裸大写字符串**：`{"MILVUS_SEARCH": ...}` 而契约是 dict[RouteName,...]（StrEnum 值是小写）→ KeyError。
7. **camelCase 命名**：sQLQueryTool → 应 snake_case。
8. 分支处理不全：except 分支忘了设置关键字段（status="error"）。

2026-07-31 评审 decision_engine.py 第一版新增（部分为复发）：

9. **dict.items() 单变量遍历（坑2复发）**：`for error in ERROR_ALIASES.items():` 拿到的是 (键,值) 元组；要 `for alias, token in d.items():` 双变量解包。
10. **TypedDict 当对象用**：`state.original_query` → AttributeError；TypedDict 是 dict，要 `state.get("key")`。
11. **该构造 Pydantic 模型时返回裸 dict**：方法签名 `-> RouteDecision` 却 return {...}；键名还拼错（need_retrievel/fall_back/greetting）、缺必填 intent。
12. **变量只在 if 分支里赋值** → 另一条路径 NameError；且裸类型注解 `x: bool` 不创建变量（Java 声明习惯）。布尔应直接 `x = len(routes) > 1`。
13. **含空 list 的 dict 误判**：`{"k": []}` 是真值（dict 判空看 key 数）；用值该单串就单串、缺就不放 key。

2026-08-08 评审 fastapi-practice(FastAPI 挖空练习)新增:

14. **keyword-only 参数按位置传**(当天踩 2 次):FastAPI 签名里 `*` 后的参数(title/prefix/status_code…)只能写参数名。`FastAPI("标题")`、`include_router(r, "/movies")` 都 TypeError;必须 `FastAPI(title=...)`、`include_router(r, prefix=...)`。Java 按位置传参的习惯直接撞墙——教学口径:见 FastAPI 参数一律写 `名=值`。
15. **路径参数三处名字要一致 + 别漏 `: int`**:路由 `{movie_id}`、函数参 `movie_id: int`、返回体 `movie_id`,任一拼错/漏类型就崩。`move_id` 打错 → NameError 且路径绑不进;漏 `: int` → 返回字符串且 `/abc` 不返回 422(自动校验没开)。
16. **status_code 塞进返回体**:把 `{"code":201}` 放 return 里以为就是状态码;真正的 HTTP 状态码在装饰器 `status_code=201`,返回体只是数据。
17. **import 类而非实例**:`from api.movies import APIRouter`(类)写成本该是 `router`(配好路由的实例)。

关联：[[user-python-level]]、[[learning-requirements]]
