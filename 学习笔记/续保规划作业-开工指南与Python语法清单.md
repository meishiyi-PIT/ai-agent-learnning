# 智保通·续保规划 Agent 作业 —— 开工指南 + Python 语法清单

> 对应作业:`AI大模型应用开发\模块四…\03-项目一…\04-智保通·续保规划 Agent(智能体)开发指南.md`
> 代码仓库:`harness_zbt`,**在 `phaseThree` 分支上做**(动手前 `git rev-parse --abbrev-ref HEAD` 确认)。
> 本文自包含,换电脑可独立使用。文件行号以 2026-08-10 的 phaseThree 代码为准,若对不上就按符号名搜索。

---

# 第一部分:这个作业怎么做

## 1. 定位:考的是什么

这份作业 90% 考 phaseOne/phaseTwo 已吃透的东西,phaseThree 只是借了个壳(trace 透传、`send_customer_message` 返回结构)。对照已吸收的要点,几乎逐条重演:

- `submit_renewal_advice` 的"引用只能来自本次检索" = **引用闭环(声称∩真实执行)**
- 服务层预校验 + 工具内校验各一遍 = **闸门下沉/深层不信上层**
- `context.h5_user` 拿用户、模型只传 `policy_id` = **身份从 context 焊死**
- "不存在/别人的/失效"返回同一个错误 = 数据隔离,不泄露存在性
- "选哪个方案由 Agent 判断、服务不写 if/else" = **软硬分工**的正面用例

所以它本质是对前两阶段理解的**实战验收**,不用等 phaseThree 读码全部完成才开工,两边可并行。

## 2. 哪些抄、哪些亲手写(别平均用力)

**直接抄(约 30 分钟,让骨架立起来)**:
- 步骤 1(请求模型)、步骤 2(响应类型全文已给)
- 步骤 4(领域模型全文已给)
- 步骤 10(知识文档 + SEED_DOCUMENTS 全文已给)
- 步骤 7 的 registries 替换段(customer 人格定义已给)

**亲手写(真正的作业,按含金量排序)**:
1. **步骤 6 `submit_renewal_advice` 的 7 条校验** —— 全作业核心,闸门思想全在这
2. **步骤 8 `RenewalAdviceService`** —— 编排:预校验 → 建会话 → 发消息 → 从 cards 提块 → 补全响应
3. **步骤 5 `get_policy_context`** —— 统一错误 + 字段裁剪(不返回敏感字段)
4. 步骤 3 Block、步骤 9 路由装配 —— 照现有样板仿写,难度低

**步骤 7 SKILL.md**:用课件给的"学习用提示词"让 AI 生成,然后**逐条校验**(front matter 的 id/tools 必须与代码注册的工具名完全一致)——校验动作本身就是课件设计的练习。

**可以放过的点**:金额/预算比较不写任何业务逻辑,课件明确说了不是重点,别在步骤 4 上多花时间。

## 3. 动手前 30 分钟预习地图(🔴精读 / 🟡扫 / 🟢略)

均为 `harness_zbt/backend/src/zbt/` 下的路径:

- 🔴 `domains/agent/tools.py:644` —— `search_insurance_knowledge`,三个新工具的现成样板;**特别看 :650 附近它怎么用 `context.executions` 数检索轮次**,这就是校验"引用来自本次检索"的现成招式
- 🔴 `domains/agent/tools.py:100`(ToolArguments 基类)、`:967`(注册项写法)
- 🔴 `harness/schemas.py:56`(QuoteBlock 样板)、`:124`(UiBlock 联合类型,新 Block 要加进去)
- 🔴 `domains/agent/service.py:53` / `:79` —— `create_customer_thread` / `send_customer_message` 的返回结构,步骤 8 全靠它
- 🟡 `api/v1/agent.py:39`(current_h5_user 鉴权写法)、`main.py:355/371/518`(装配三处)、`domains/enrollment/service.py:377`(`list_policies` 返回 `{"items": [...], "total": n}`,决定怎么过滤保单)
- 🟢 `harness/kernel.py` 不用动,工具卡片自动透传

## 4. 两道预测题(写步骤 6 之前先自己答,不许先看代码找答案)

1. `cited_chunk_ids` 要求"必须来自本次 `search_insurance_knowledge` 返回的切片"——你打算**从哪里拿到"本次检索到底返回过哪些 chunk_id"**?模型自己报的算不算数?
2. 保单校验做了两遍(步骤 8 服务层预校验、步骤 5 工具内校验),课件说两处错误码要一致。**如果只保留其中一遍,删哪一遍会出安全问题?为什么?**

## 5. 节奏与验收

- 预习地图(30min)→ 抄完骨架部分(30min)→ 写步骤 3、5(约 1h)
- 答完两道预测题 → 写步骤 6(核心,预留 1.5h)→ 步骤 8、9(1h)
- 步骤 11 联调:课件里"5 个典型问题 → 预期结果"表就是验收标准,逐条跑
- 老规矩:教练模式,卡壳 20 分钟必须来问,不自己死磕

---

# 第二部分:涉及的 Python 语法清单

按写作业时遇到的顺序列,每条最小例子;⚠️ 标注的是(Java 转 Python)高频坑。卡语法先查这里,再查 `python-for-agents/README.md`。

## A. Pydantic 模型(步骤 1/2/3 全靠它)

**1. 类字段声明 = 类型注解 + Field 约束**(不是 Java 的 private + getter/setter)
```python
class RenewalAdviceRequest(BaseModel):
    policy_id: str = Field(min_length=16, max_length=64)   # 冒号后是类型,等号后是约束/默认值
    question: str = Field(min_length=5, max_length=500)
```
⚠️ 对应"空构造+setter"坑:Pydantic 用 `RenewalAdviceRequest(policy_id=..., question=...)` 一次性构造,没有 setter。

**2. 可选字段:`| None = None`**(≈ Java 的 `@Nullable`,`|` 读作"或")
```python
selected_option_code: str | None = None   # 可以不传,不传就是 None
trace_id: str | None = None
```

**3. `Literal` = 轻量枚举**,值只能是列出来的几个
```python
decision: Literal["RENEW_ORIGINAL", "UPGRADE", "NEED_MORE_INFORMATION", "CANNOT_DETERMINE"]
status: Literal["COMPLETED"] = "COMPLETED"   # 只允许一个值 + 默认值 = 常量字段
```
⚠️ 对应"枚举 key 用裸字符串"坑:传 `"UPGRADE"` 字符串本身没错(Literal 就是字符串),错的是拼写不在名单里——Pydantic 会当场报错,这正是要它的原因。

**4. 列表字段默认值必须用 `default_factory`,不能 `= []`**
```python
reasons: list[str] = Field(default_factory=list, max_length=3)   # ✅
# reasons: list[str] = []   # ❌ 普通类里这是全实例共享一个列表的大坑
```
Java 没有这个坑,记结论:**可变默认值(list/dict)一律 default_factory**。

**5. `model_config = ConfigDict(extra="forbid")`**:多余字段直接拒绝。作业里 `StrictModel` 已经带了,继承它即可,别自己重写。

**6. 类型别名**(步骤 4,给 Literal 起名字复用)
```python
RenewalDecision = Literal["RENEW_ORIGINAL", "UPGRADE", ...]   # 顶层赋值,之后当类型用
decision: RenewalDecision
```

## B. dataclass 与元组(步骤 4,可以抄,但要看懂)

**7. `@dataclass(frozen=True)` ≈ Java 的 record**:自动生成构造器,frozen = 字段不可改。`@` 开头是装饰器,加在类/函数头上给它加能力。

**8. 元组字面量 + 数字下划线**
```python
RENEWAL_OPTIONS = (        # 圆括号 = 元组,不可变的 list,当只读常量表用
    RenewalOption(option_code="RENEW_ORIGINAL", option_name="原方案续保", premium_cents=39_900),
    RenewalOption(...),    # 39_900 就是 39900,下划线只为肉眼分位
)
```
⚠️ 对应"元组当 dict"坑:元组**只能遍历或按下标取**,不能 `RENEWAL_OPTIONS["UPGRADE"]`——所以课件才给了 `find_renewal_option()` 做查找。

**9. "找到返回/找不到返回 None"模式**
```python
def find_renewal_option(option_code: str) -> RenewalOption | None:
    for option in RENEWAL_OPTIONS:
        if option.option_code == option_code:
            return option      # 找到,提前返回
    return None                # 循环走完没找到
```
⚠️ "忘 return"坑:最后那行漏了函数也返回 None(Python 默认),但要**显式写出来**;调用方必须处理 None 分支:`if option is None: raise ...`。

## C. 干活的集合操作(步骤 5/6/8 的核心语法,重点)

**10. 列表推导式过滤**——步骤 5 按 policy_id 过滤保单就用它
```python
matched = [p for p in policies["items"] if p["policy_id"] == args.policy_id]
# 读法:对 items 里每个 p,留下满足 if 的,装进新列表
```
⚠️ 推导式坑,记牢语序:**[要什么 for 变量 in 哪里 if 条件]**,for 在前 if 在后。

**11. `next(生成器, None)`——取第一个匹配,没有就 None**(步骤 8 从 cards 里找块)
```python
card = next((c for c in cards if c.get("type") == "renewal_advice"), None)
if card is None:
    raise AppError("RENEWAL_ADVICE_NOT_SUBMITTED", "...", 502)
```

**12. `sum(布尔生成器)` 计数**——现有代码 `tools.py:650` 数检索轮次就是这么写的
```python
attempt = sum(e.name == "search_insurance_knowledge" for e in context.executions)
# True 算 1、False 算 0,加起来就是出现次数
```

**13. set(集合)+ `in` 成员判断**——步骤 6 校验"引用来自本次检索"的关键
```python
allowed_ids = {item["chunk_id"] for e in context.executions ...}   # 花括号推导式 = set
for chunk_id in args.cited_chunk_ids:
    if chunk_id not in allowed_ids:
        raise AppError(...)
```
(具体从 executions 哪里挖出 chunk_id,是预测题 Q1,自己先想。)

**14. dict 取值两种写法**
```python
run_id = result["run_id"]          # 键必须存在,不存在抛 KeyError
trace = result.get("trace_id")     # 不存在返回 None,不炸
```
协议里必有的字段用 `[]`(炸了正好暴露问题),可有可无的用 `.get()`。

**15. dict 展开合并 `{**a, "k": v}`**:在 a 的基础上加/覆盖字段,组装响应 data 时会用。

**16. 空列表是"假"**
```python
if not args.missing_information:   # 列表为空时成立
    raise AppError(...)            # "无法确定时 missing_information 不能为空"就这么校验
```

## D. 函数与调用约定

**17. `*` 之后全是 keyword-only 参数**(步骤 8 的 `get_advice` 签名)
```python
def get_advice(self, user: H5User, *, policy_id: str, question: str) -> dict: ...

service.get_advice(user, policy_id=pid, question=q)   # ✅ 必须写参数名
service.get_advice(user, pid, q)                      # ❌ TypeError,高频坑
```

**18. 工具函数开头的类型转换**——现有工具的固定第一行,照抄这个模式
```python
def get_policy_context(context: ToolExecutionContext, arguments: BaseModel) -> HarnessToolResult:
    args = _arguments(arguments, GetPolicyContextArgs)   # 转成具体类型
    # 之后用 args.policy_id 点号访问,IDE 才有提示
```

**19. 抛业务异常 = `raise AppError(错误码, 消息, HTTP状态码)`**,三个位置参数,照现有风格
```python
raise AppError("RENEWAL_POLICY_NOT_AVAILABLE", "保单不可用于续保规划", 404)
```
≈ Java 的 `throw`,不 try/catch 就一路向上冒,由框架统一转成错误响应——工具里只管抛。

**20. f-string 拼消息**:`f"共{len(items)}条"`,花括号里可放任意表达式。

## E. 装配层(步骤 8 `__init__` / 步骤 9 路由工厂)

**21. 构造器注入**——Python 版依赖注入就是构造器赋值
```python
class RenewalAdviceService:
    def __init__(self, thread_service: AgentThreadService, enrollment: EnrollmentService) -> None:
        self._thread_service = thread_service   # 前缀下划线 = "私有"约定(没有 private 关键字)
        self._enrollment = enrollment
```

**22. 工厂函数里嵌套定义路由**——函数里可以再 def 函数(闭包),内层函数能直接用外层参数,照 `api/v1/agent.py` 的 `create_agent_router` 仿写
```python
def create_renewal_advice_router(service, h5_auth_service) -> APIRouter:
    router = APIRouter()

    @router.post("/h5/agent/renewal-advice", response_model=RenewalAdviceResponse)
    def get_renewal_advice(...):
        return success_response(request, service.get_advice(...))   # ⚠️ 别忘 return

    return router
```
⚠️ FastAPI 坑在这步集中出没:`response_model` 声明在装饰器里、别把 status_code 塞进返回体。

---

## 三道 30 秒自测(答得出再开写)

1. `reasons: list[str] = Field(default_factory=list)` 里为什么不直接写 `= []`?
2. `[p for p in items if p["status"] == "ACTIVE"]`——items 里没有 ACTIVE 保单时,这个表达式返回什么?(炸异常还是别的?)
3. `service.get_advice(user, "POL123", "该续保吗")` 会发生什么?

写作业时自己验证;拿不准就丢给 Claude 判。撞见清单外的语法直接贴给 Claude 问,不自己猜超过 20 分钟。
