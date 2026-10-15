# 模块六:大模型 LoRA 微调

> 对应课件:《1.大模型LoRA微调.md》全篇(四章)+ 录播 `1_Lora微调/Lora微调_01、_02.sz`
> 代码:第 1–3 站 `C:\workspace\deepLearning\lora\`(纯 torch,每站一个文件,讲解写在文件顶部 docstring);
>       第 4 站 `C:\workspace\meishiyi\09_HuggingFace\lora\`(需要 transformers 4.51.3 / peft 0.15.2,该目录 venv 已装好)
> 状态:2026-09-21 开学;5 站地图见 `lora/s1_memory.py` 顶部。2026-09-22:第 1、2 站过完(含 demo),第 3 站按用户要求只过概念、demo 数字由 Claude 代跑引用;进第 4 站
> 本机无 NVIDIA 卡:课件 4.3 的 7B 训练跑不了,第 4 站用"本地拼一个几十万参数的迷你 Qwen2 结构 + 真 tokenizer"在 CPU 上把同一套 PEFT/Trainer 流程走通。
> 真跑 7B:课件最新代码在 `C:\workspace\code\lora\`(01 清洗、02 切分、lora_train.py、train/validation.json 17,660/4,415 条);Claude 补了 `lora_train_fixed.py`(修正版,顶部按原文件行号逐条对照 bug)、`merge.py`、`infer.py`、`README.md`(AutoDL 八步清单含验收点)。2026-09-23 已写好并通过语法检查,尚未在 GPU 上实跑。实测 1024 截断率 2.7%,先抽 2000 条跑通再决定全量。
> 课件核查(对照 transformers 4.51.3 / peft 0.15.2 源码、DeepSeek-R1-Distill-Qwen-7B 官方 tokenizer_config、LoRA 论文 arXiv 2106.09685),勘误随各站补充:
>   ①2.2 第二个 ```python 代码块里混着中文散文,不是能跑的 Python,当伪代码看。
>   ②3.1 "r 远小于 d 和 d"是笔误:W 一般是 d×k(输出维×输入维),B 是 d×r、A 是 r×k,r ≪ min(d,k)。
>   ③3.3 "A 用高斯初始化"是论文原文;PEFT 库默认对 A 用 kaiming_uniform(和 nn.Linear 默认一样)、B 置零,`init_lora_weights="gaussian"` 才是高斯(std=1/r)。结论(B·A 起点为 0)不变。
>   ④3.2 "7B 全量 60GB / LoRA 23GB"是量级估计:按 fp32 权重+梯度+Adam 两份状态 = 每参数 16 字节,7B 全量光这三项就 112GB;60GB 对应全 bf16(每参数约 8 字节)的省内存配置。量级一致,第 1 站 demo 亲手算。
>   ⑤4.3 训练代码(第 4 站逐条复现验证):正文说"QLoRA 4bit 加载"但代码没有 BitsAndBytesConfig 也没指定 dtype,7B fp32 光权重 28GB;`tokenizer.encode(..., padding="max_length")` 把 prompt_ids 也填满到 1024(该 tokenizer 默认左填充,pad 在前),`prompt_len` 恒等于 1024 → labels 全是 -100;即使不 pad,prompt_text 末尾多出的 `<｜Assistant｜><think>\n` 在 full_text 里也不存在,prompt 不是 full 的前缀;Step 4 的截断分支永远走不到(truncation=True 已截);attention_mask 对 pad 位置也填 1;`DataCollatorForLanguageModeling(mlm=False)` 会用 input_ids 重新生成 labels 把前面精心做的 prompt 屏蔽整个覆盖掉(data_collator.py:1028-1031);DeepSeek 该 tokenizer pad_token == eos_token,collator 把 pad 置 -100 时连 EOS 一起屏蔽 → 模型学不会停;DeepSeek chat template 对 assistant 消息会 `split('</think>')[-1]` 只保留 think 之后的内容 → 课件拼进去的 Complex_CoT 在训练文本里根本不存在;`num_train_epochs=20` 与 4.4 "3 个 epoch"自相矛盾;给了 eval_dataset 却没设 eval_strategy → 训练中从不评估;save_steps 在 save_strategy="epoch" 下无效。
>   ⑥4.3 推理代码用 Alpaca 风格 `prompt_style`,训练却用 chat template —— 违反课件自己 4.2 的"铁律:训练/推理模板必须一致"。

## 三问(自己填;理解已过关的站可跳过正文)

### 是什么

1. 微调解决什么问题?和提示词、RAG 的分工是什么(哪类需求不该拿去微调)?
2. 秩是什么?"低秩"为什么意味着"能用两个小矩阵装下"?
3. LoRA 的一行公式 `W' = W + (α/r)·B·A` 里每个符号是什么、形状各是多少?

(待填)

### 为什么

1. 为什么全量微调显存吃这么多?四笔账各是什么、LoRA 砍掉了哪几笔、哪一笔省不掉?
2. 为什么 A 随机、B 置零?"都置零"和"都随机"各死在哪?
3. 为什么优先挂 q_proj+v_proj、r=8 就够?"多挂几个矩阵 > 单个矩阵加大 r"的依据是什么?
4. 为什么 LoRA 擅长调"行为"、不擅长灌"知识"?

(待填)

### 怎么做

1. 给一个 3×3 矩阵手判秩;给 d=6、r=2 手算 LoRA 参数量和压缩比。
2. 用 PEFT 给模型挂 LoRA 的三步(LoraConfig → get_peft_model → Trainer)各写什么?训练完 merge 和 adapter 两种用法各怎么写?
3. SFT 数据处理里 labels 的 -100 是干什么的?chat template 训练/推理不一致会怎样?
4. 超参起手式:r / α / lr / epoch / target_modules 各取多少,为什么?

(待填)

---

## 学习中问过的问题(Claude 整理)

### 第一章 微调与显存账(第 1 站)

**Q:"7B 乘 16 字节就是 112 GB",为什么单位是 GB?7B × 16 Byte 不是 112 B 吗?**
A:两个 B 撞名了。"7B"的 B 是 billion(十亿),不是 Byte:7B 模型 = 7×10⁹ 个参数。7×10⁹ 个 × 16 字节 = 112×10⁹ 字节,1 GB ≈ 10⁹ 字节,所以是 112 GB。手算小例子:1B 模型 = 10⁹ 个参数 × 16 字节 = 16 GB;demo 里 0.5B → 8 GB 就是 0.5×16。记法:参数量后面的 B 读"十亿",内存后面的 B 读"字节"。(demo 的 MB 用 1024²、GB 用 10⁹,两种口径差 7%,估显存时忽略。)

**Q:为什么 16 GB = 16×10⁹ 字节,不是 16×10⁶?**
A:阶梯记错一级:MB 才是 10⁶,GB 是 10⁹。字节阶梯每级乘 1000(严格 1024):B=1 → KB=10³ → MB=10⁶ → GB=10⁹ → TB=10¹²。生活对照:照片几 MB、电影几 GB、电脑内存 16 GB、硬盘 1 TB。demo 里 4096×4096 矩阵 1677 万参数 × 4 字节 ≈ 6700 万字节 = 64 MB,是 MB 级;要到 GB 级得再乘 1000,即十亿级参数(几 B 的模型)才会出现 GB。

**Q:(小题 1b 答成 24.09 GB)冻结原参数、只训新增 750 万参数后,显存怎么算?**
A:0.09 GB(750 万 × 12 字节)那半边对;前半边 24 GB 是原参数"权重+梯度+m+v"四项全记的账,冻结后原参数只剩权重一笔:1.5×10⁹ × 4 字节 = 6 GB,合计 ≈ 6.09 GB。省掉的 18 GB 全是原参数的②梯度③优化器状态,对应 demo 2 里 `W.grad = None`、优化器状态只剩 bias 一个参数。PEFT 家族的账就是:①权重省不掉,②③几乎归零。

**Q:(复述时说"冻结后原参数占梯度和权重,不占 m/v")冻结的参数还有梯度吗?**
A:没有,只剩权重一笔。梯度这块内存唯一的用途是告诉优化器往哪改该参数;参数 requires_grad=False 后不会被改,autograd 根本不为它算梯度、不分配内存。权重留着是因为前向传播仍要用它算输出。demo 2 输出 `W.grad = None`(不是 0,是没分配)就是实证。

### 第三章 LoRA 原理(第 3 站)

**Q:为什么 A 随机、B 置零?**
A:目标是起点旁路 B·A·x = 0(模型和原模型一样),办法有三:B 零 / A 零 / 都零,选哪个看训练能否启动。缩成单个数看梯度:h = W·x + B·A·x,loss 对 h 的导数记 g,则 ∂loss/∂B = g·A·x、∂loss/∂A = g·B·x,即 **B 的梯度正比于 A,A 的梯度正比于 B**。①都零:g=1,x=2 → 两个梯度都是 1×0×2=0,一步走不动,永远锁死(demo 2 both_zero loss 不动)。②A=0.5、B=0:第 0 步 B 梯度 =1×0.5×2=1 非零先动,A 梯度 =0 暂不动;B 变成 -0.01 后 A 梯度 =1×(-0.01)×2 非零也动了——一个非零就能带动另一个("对称性破缺";demo 2 paper 方案第 0 步 A=0、B=0.0355)。③都随机:能启动但起点 B·A≠0,模型没训先被改(demo 2 实测输出偏离 122%)。结论:零一个保证起点干净,随机一个保证梯度能流;零哪个都行,论文选 B 零、A 随机,反过来也能训。

**Q:3.5 LoRA 挂在哪些层,再讲讲?**
A:①一层 7 个 nn.Linear 都能挂:q/k/v/o_proj = 模块五的 W_Q/W_K/W_V/W_O;gate/up_proj = FFN 升维(SwiGLU 拆两个)、down_proj = 降维。②论文 Table 5:GPT-3 上固定 18M 预算(一种矩阵 r=8、两种 r=4、四种 r=2),WikiSQL 准确率:只 Wq 70.4 / 只 Wk 70.0 / 只 Wv 73.0 / 只 Wo 73.2 / Wq+Wk 71.4 / Wq+Wv 73.7 / 四个全挂 73.7 → 钱全押 Wq 或 Wk 最差,多挂小 r 最好;Table 6:Wq+Wv r=1 就 73.4、r=64 才 73.5,只挂 Wq r=64 仍不到 71 → r 加大没用,矩阵种类加多才有用。直觉:Q 管注意力分给谁、V 管混进什么内容,是注意力两头;Q、K 配对打分,同时改重复。③手算:每个矩阵 LoRA 参数 =(输入维+输出维)×r;迷你模型 hidden 64、kv 32、r=8:q 1024 + k 768 + v 768 + o 1024 = 3584/层 × 2 层 = 7168,与 demo 打印一致。④课件没说的补充:QLoRA 论文(2023,arXiv 2305.14314)在 LLaMA-7B 上发现只挂 q、v 追不上全量微调,所有线性层都挂才能追平、r 影响不大;PEFT 有 `target_modules="all-linear"`。现在做法:显存够就全挂,紧才 q+v 起步。⑤嵌入层大但变动小、LayerNorm/bias 参数极少想训直接放开,都不用 LoRA。

### 第四章 工程实战(第 4 站)

**Q:torch_dtype=bfloat16 "每个权重 2 字节、15.2 GB;bf16 范围和 fp32 一样大"怎么理解?"基座 4bit"是什么意思?**
A:计算机存小数 = 科学记数法(正负号 + 有效数字位 + 指数位),占的位数决定类型:fp32 4 字节(23 位有效数字、8 位指数,最大 3.4e38);fp16 2 字节(10 位有效、5 位指数,最大 65,504);bf16 2 字节(7 位有效、8 位指数,范围同 fp32);int4 半字节(16 个档位 + 每组一个缩放系数)。显存 = 参数个数 × 字节:7.6e9 × 4 = 30.4 GB(课件按 7B 算 28)/× 2 = 15.2 GB/× 0.5 ≈ 3.8 GB(加缩放系数 4–5 GB)。选 bf16 不选 fp16:存 70000 → fp16 溢出成 inf(训练一次 NaN 全盘炸),bf16 存成 70,144;存 1234.5678 → fp16 1235(误差 0.4),bf16 1232(误差 2.6)——bf16 用"更粗"换"不溢出",训练里梯度/激活动辄上万,溢出比粗糙致命。"4090 原生支持"= 计算单元直接做 bf16 乘加。**基座 4bit** = 把冻结的 W 每 32 个左右权重分一组记一个缩放系数、组内每个数只存 16 档之一(例:范围 [-1,1] 档距 0.13,0.37 存成 0.33);用时临时解压成 bf16 做矩阵乘(`load_in_4bit` + `bnb_4bit_compute_dtype=bfloat16` = 存 4 位算 16 位);只压 W,LoRA 的 A、B 正常精度正常训——这就是 QLoRA,权重那笔 15 GB → 4–5 GB。
