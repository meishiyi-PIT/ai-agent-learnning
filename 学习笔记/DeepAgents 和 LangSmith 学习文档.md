# DeepAgents 和 LangSmith 学习文档

## DeepAgents 是什么？

理解 deepagents 框架在 langgraph 和 langchain之上

![image-20260802105342226](C:\Users\meish\AppData\Roaming\Typora\typora-user-images\image-20260802105342226.png)

DeepAgents 内置了很多的工具和能力，使用起来更方便。

DeepAgents 能做到动态路由规划，实际上来说还是不太确定性的，因为llm本身就不一定是严谨的。



## 为什么需要使用到 DeepAgents 





## DeepAgents 怎么使用

七大特性，自己的理解和需要注意的点：

### vitrual Filesystem 虚拟文件系统

目前其实还是为了压缩上下文，减少token的消耗。

分为五种：

- 文件存储的backed-- filesystembackend
- 内存的backed--statebackend
- 持久化的backed--storebackend
- 沙箱的backed--sandboxbackend
- 混合backed （包括以上的内容）

路径固定 不固定 可以手动指定 以当前为例：

> create_agent 时指定 skills 和 memeories的目录，在buile_backend时指定 store文件的目录去，其他的文件可以在system_prompt中指定。具体表现为：
>
> 这里涉及到的几个文件 输入：/data-room  /polices  /skills  可写工作区：/workspaces/findings 草稿 reports 产出的报告 禁区：report-history
>
> system_prompt可指定：/data-room  /polices  /reports  /report-history
>
>  FilesystemBackend(root_dir=项目根) 的作用就是:把 root_dir 下磁盘上已有的文件,原样暴露成虚拟路径

### context compression 上下文压缩

两种情况：

- contenxt offloading（结果卸载）：工具输入或者结果太大的时候 会自动写入到backend中，注意：这里是原文写入，所以内容是无损的
- sumarization（历史总结）：上下文快到窗口的限制，且当前没有内容可以卸载时，压缩。会丢失精度。

一般的过程：

![image-20260802143213141](C:\Users\meish\AppData\Roaming\Typora\typora-user-images\image-20260802143213141.png)

### subagent delegation 子智能委派

最主要的是上下文隔离，串行还是并行不会影响上下文。



### planning 任务规划

类似于 todolist ，在supervisor agent的system_prompt中表述。表示得先生成一个write_todos。agent会按照计划进行。决策权在：agent。

格式类似于：

~~~
[{"contenxt":"xxxx","state":"固定值pending / in_progress / completed"}]
~~~



### skills 技能包

与我们理解的skill相同，只是它做了skill的管理，通过在create_agent中指定skills的路径，可以读到当前这个项目下所有的skills，并且按照description和name存储在上下文中，涉及到需要调用它的时候，才会去读skill.md 以及它参考的内容。agent在执行过程中，根据它的描述，决定是否需要调用它。

>  方向是:你配路径 → 中间件扫目录 → 中间件把 name+description 注入 system_prompt。

我理解主要的也是为了节省上下文。



### filesystem-backed memory 文件化长期记忆

memories/agent.md存储长期回忆



是怎么加载的？

首次加载会直接加载

> 为什么知道在哪？createagent的时候指定了文件路径。

每轮都会加载这里的数据，大模型会自己调用edit_file写入。然后下一次的新的thread进来的会加载。

> 每个thread进来的时候都会读一次记忆



### permissions and hitl 权限和人工审批

**permissions**：

~~~
  FilesystemPermission(operations=["write"],
                       paths=["/data-room/**", "/policies/**", "/skills/**"], mode="deny")
  FilesystemPermission(operations=["read", "write"],
                       paths=["/report-history/**"], mode="deny")
~~~

关键在它在哪儿生效:在文件工具的执行层。不是在 SUPERVISOR_PROMPT
  里写"请不要修改原始材料"——那种写法模型可能听、可能不听、可能被诱导。而是工具真要写 /data-room/
  时,权限层直接把这次写操作挡回去。模型再怎么"被说服"也写不进去。/report-history/
  连读都禁,是防它把上一次的审批结论继承过来(你之前学过这点)。

**HITL**

~~~
  interrupt_on={"submit_onboarding_decision": {"allowed_decisions": ["approve", "reject"]}}
~~~

 这里藏着一个依赖,也是课件专门点名的:HITL 依赖 Checkpointer。
  为什么?第①步暂停时,得把整张图的状态快照存下来;第③步人工决定后,才能凭同一个 thread_id 精确地"接着上次那一刻"往下走。没有
  Checkpointer(项目里是 InMemorySaver()),就没有可恢复的存档,暂停完就再也接不上了——HITL 直接失效。





## LangSmith  是什么？

追踪

评估



## 为什么需要使用到 LangSmith 



## LangSmith 怎么使用

trace：



评测：

是输入这里的input的description的内容，然后output的内容需要满足required_terms吗



什么是回归测试



ps：一个用ai的小技巧 不要给他对应的代码库 他会自己复制和偷懒



## Langchain  / Langgraph / deepagents 的区别



deepagents：在langchain和langgraph之上。我理解为类似spring类似的框架。内置很多可以直接使用的工具。

langchain：负责与llm对话，以及tool。

langgraph：图示编排，（langgraph 如果需要做到和大模型的对话，内部肯定是需要调用langchain的）



确定性：

langchain和deepagents不确定

langgraph 确定

: question :

1. deepagents可以嵌套langgraph的图，为什么还是不确定的？



## 项目

动态任务规划：





seetings：

~~~
@dataclass(frozen=True)

class Settings:
	project_root:Path
	
@dataclass
  装饰器会根据你声明的字段自动生成构造函数——你只要像上面这样"字段名: 类型 = 默认值"列出来,__init__ 就自动有了。等于 Java
  的 record / Lombok @Data,但是语言内置。

  - frozen=True = 造好后不可改(想改字段会直接报错)。相当于 Java 的 final 字段 /
  record。注释说得很清楚:防止运行中途被某个组件偷偷改配置。要改只能用 dataclasses.replace() 造个新实例。
  - 这正是你 memory 里那条"[[user-python-pitfalls]] 空构造+setter"的正确 Python 姿势:声明式定义 +
  不可变,而不是可变对象到处 set。
  
  
@classmethod
它类似 Java 的静态工厂方法(带参数、返回一个造好的对象)

~~~



backend.py

目录是虚拟目录：

/workspace/ → StateBackend → 内存。 它的内容存进 LangGraph 的图状态,而图状态由谁保管?看 agent.py:

  checkpointer = InMemorySaver()   # ← In-Memory,内存实现

  所以专家写的 /workspace/findings/security.md 实际是"图状态这个大字典里的一个条目",活在 RAM 里,跟着 thread_id
  走、能参与暂停/恢复,但进程结束即蒸发。

  /memories/ → StoreBackend → 也是内存! 这是容易被名字骗的地方——它设计定位是"长期记忆",但存到哪取决于你塞给它什么 Store,而 agent.py 里:

  store = InMemoryStore()   # ← 同样是内存实现

  agent.py 的注释其实明说了:"当前 Store 和 Checkpointer 都是内存实现,进程退出后不会持久化"。生产环境会换成 Postgres 之类的持久化
  Store,到那时 /memories/ 才真正"长期";换 Store 不用改 backends.py 一行——路由语义(谁该存哪类数据)和存储实现(数据真放哪)是两层独立的决定。

  实证:之前 ls 过项目根目录——有 data-room/、reports/、policies/、skills/、fixtures/(这些走默认 FilesystemBackend,真在磁盘上),但没有
  workspace/ 和 memories/ 目录。虚拟路径三分法里,只有"默认"那一档是真文件。

  ⚠️ 顺带防个坑:你电脑上恰好有个真实目录叫 C:\workspace(你的学习工作区)——它和 Agent 眼里的虚拟路径 /workspace/
  毫无关系,纯属重名巧合,别把两者对上号。

  一句话总结三档:

  ┌────────────────────────────────┬───────────────────────┬────────────┬──────────────────────┐
  │            虚拟路径            │         落点          │ 磁盘上有吗 │       生命周期       │
  ├────────────────────────────────┼───────────────────────┼────────────┼──────────────────────┤
  │ 默认(/data-room/ /reports/ 等) │ 真文件系统            │ ✅ 有      │ 永久                 │
  ├────────────────────────────────┼───────────────────────┼────────────┼──────────────────────┤
  │ /workspace/                    │ 图状态(InMemorySaver) │ ❌ 无      │ 本线程、本进程       │
  ├────────────────────────────────┼───────────────────────┼────────────┼──────────────────────┤
  │ /memories/                     │ Store(InMemoryStore)  │ ❌ 无      │ 跨线程、但仍限本进程 │
  └────────────────────────────────┴───────────────────────┴────────────┴──────────────────────┘