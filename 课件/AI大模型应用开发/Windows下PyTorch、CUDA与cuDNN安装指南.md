# Windows 下 PyTorch、CUDA 与 cuDNN 安装指南
  
官方参考：  

> + PyTorch 安装页：[https://pytorch.org/get-started/locally/](https://pytorch.org/get-started/locally/)  
> + CUDA Windows 安装指南：[https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/](https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/)  
> + cuDNN Windows 安装指南：[https://docs.nvidia.com/deeplearning/cudnn/installation/latest/windows.html](https://docs.nvidia.com/deeplearning/cudnn/installation/latest/windows.html)
>

---

## 1. 先把关系讲清楚
第一次装深度学习环境，可能会被几个词绕晕：

+ PyTorch
+ CUDA
+ cuDNN
+ NVIDIA Driver

先理解它们各自负责什么：

| 名称 | 通俗理解 | 主要作用 |
| --- | --- | --- |
| NVIDIA Driver | 显卡驱动 | 让 Windows 能识别并调用 NVIDIA 显卡 |
| CUDA | GPU 通用计算工具箱 | 让程序能把计算任务交给 NVIDIA GPU |
| cuDNN | 深度学习加速库 | 专门加速卷积、归一化、RNN 等神经网络算子 |
| PyTorch | 深度学习框架 | 让我们用 Python 写模型、训练模型、调用 GPU |


总结：

> Driver 负责让系统认识显卡，CUDA 负责让 GPU 能做通用计算，cuDNN 负责让深度学习算子跑得更快，PyTorch 负责让我们用 Python 写深度学习代码。
>

它们的调用链大致是：

<!-- 这是一个文本绘图，源码为：flowchart LR
    A[Windows 系统] --> B[NVIDIA 显卡驱动]
    B --> C[CUDA Runtime / Toolkit]
    C --> D[cuDNN 深度学习加速库]
    D --> E[PyTorch]
    E --> F[模型训练 / 推理] -->
![](https://cdn.nlark.com/yuque/__mermaid_v3/aff989b4ef6e9520006cfd0bbe6f7811.svg)

---

## 2. 一个最容易误解的点
很多时候以为：

> 想用 PyTorch 跑 GPU，就必须先手动安装 CUDA Toolkit 和 cuDNN。
>

不完全对。

对于大多数只想训练 PyTorch 模型，通常直接安装 **PyTorch 官方提供的 CUDA 版 wheel** 就够了。它会带上运行 PyTorch 所需的一批 CUDA 运行时相关组件。

需要手动安装完整 CUDA Toolkit 的情况包括：

1. 要写 CUDA C++ 代码；
2. 要编译自定义 PyTorch CUDA 算子；
3. 要从源码编译某些深度学习库；
4. 明确需要 `nvcc` 编译器。

如果跑类似 MNIST、YOLO、Transformer、DeepSeek/Qwen 微调这类 PyTorch 训练代码，优先按 PyTorch 官网安装命令来。

---

## 3. 安装前检查
### 3.1 确认是不是 NVIDIA 显卡
CUDA 是 NVIDIA 的 GPU 计算生态。  
如果电脑是 AMD 显卡或 Intel 核显，就不能用 CUDA。

Windows 上可以看：

1. 右键“此电脑”；
2. 打开“管理”；
3. 找到“设备管理器”；
4. 展开“显示适配器”；
5. 看里面有没有 NVIDIA 显卡。

常见名称：

```latex
NVIDIA GeForce RTX 3060
NVIDIA GeForce RTX 4070
NVIDIA GeForce RTX 4090
NVIDIA RTX A4000
```

### 3.2 检查显卡驱动
打开 PowerShell 或 CMD：

```powershell
nvidia-smi
```

如果正常，会看到：

```latex
NVIDIA-SMI 5xx.xx
Driver Version: 5xx.xx
CUDA Version: 12.x
```

注意这里的 `CUDA Version` 很容易误导。

它表示当前驱动最高支持的 CUDA 运行能力，不等于电脑已经安装了完整 CUDA Toolkit。

也就是：

```latex
nvidia-smi 看到 CUDA Version
```

不代表：

```latex
nvcc --version 一定可用
```

### 3.3 检查 Python
PyTorch 官方 Windows 安装说明要求使用受支持的 Python 版本。当前官方页面说明 Windows 上支持 Python 3.10 到 3.14。

检查命令：

```powershell
python --version
```

建议实验先用：

```latex
Python 3.10 或 Python 3.11
```

原因：生态兼容通常更稳，少踩坑。

---

## 4. 推荐安装路线
建议按这两种情况选。

| 场景 | 推荐安装方式 |
| --- | --- |
| 有 NVIDIA GPU | 安装 PyTorch CUDA 版、CUDA、cuDNN |
| 没有 NVIDIA GPU | 安装 PyTorch CPU 版 |


---

## 5. 创建 Python 虚拟环境
### 5.1 uv 方式
```powershell
uv python install 3.11.15
uv init . -p 3.11
uv venv
```

---

## 6. 安装 PyTorch
### 6.1 使用官网命令
打开 PyTorch 官方安装页：

```latex
https://pytorch.org/get-started/locally/
```

选择：

```latex
OS: Windows
Package: Pip
Language: Python
Compute Platform: CUDA 或 CPU
```

官网会自动生成安装命令。

如果有 NVIDIA 显卡，通常选择最新稳定 CUDA 版本。  
如果没有 NVIDIA 显卡，选择 CPU。

### 6.2 CUDA 版 PyTorch 示例
下面是示例，具体版本请以官网选择器为准：

```powershell
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
```

解释：

+ `torch`：PyTorch 核心库；
+ `torchvision`：图像任务常用库；
+ `torchaudio`：音频任务常用库；
+ `cu126`：表示这个 PyTorch 包面向 CUDA 12.6 运行环境。

如官网显示的是别的 CUDA 版本，比如 `cu130`、`cu121`，按照官网来，不要硬抄。

### 6.3 CPU 版 PyTorch 示例
如没有 NVIDIA 显卡：

```powershell
pip install torch torchvision torchaudio
```

CPU 版也能学习 PyTorch，只是训练大模型或大图像模型会慢很多。

---

## 7. 验证 PyTorch 安装
进入 Python：

```powershell
python
```

输入：

```python
import torch

# 查看 PyTorch 版本
print("PyTorch version:", torch.__version__)

# 创建一个随机张量，确认 torch 基本可用
x = torch.rand(5, 3)
print(x)
```

如果能打印出一个 5 行 3 列的张量，说明 PyTorch 基本安装成功。

---

## 8. 验证 GPU 是否可用
继续运行：

```python
import torch

print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU count:", torch.cuda.device_count())
    print("GPU name:", torch.cuda.get_device_name(0))
    print("PyTorch CUDA version:", torch.version.cuda)
```

如果输出：

```latex
CUDA available: True
```

说明 PyTorch 已经能调用 NVIDIA GPU。

如果：

```latex
CUDA available: False
```

---

## 10. CUDA Toolkit 是什么
CUDA Toolkit 是 NVIDIA 提供的开发工具包。

里面包括：

+ CUDA 编译器 `nvcc`；
+ 头文件；
+ 库文件；
+ 示例程序；
+ 命令行工具。

如果只是用 PyTorch 训练模型，不一定需要手动安装 CUDA Toolkit。

但如果要：

+ 编译 CUDA C++；
+ 编译自定义算子；
+ 从源码构建某些库；
+ 使用 `nvcc --version`；

需要安装 CUDA Toolkit。

---

## 11. 安装 CUDA Toolkit
### 11.1 下载
进入 NVIDIA CUDA Toolkit 下载页：

```latex
https://developer.nvidia.com/cuda-downloads
```

选择：

```latex
Operating System: Windows
Architecture: x86_64
Version: Windows 10 或 Windows 11
Installer Type: exe local 或 exe network
```

### 11.2 Local Installer 和 Network Installer
| 类型 | 特点 |
| --- | --- |
| Network Installer | 文件小，安装时在线下载 |
| Local Installer | 文件大，但离线安装更稳 |


课堂机房或网络不稳定时，推荐提前下载 Local Installer。

### 11.3 安装选项
普通选默认安装。

如果已经安装了较新的 NVIDIA 驱动，不想安装器覆盖驱动，可以选择自定义安装，取消 Driver。  
刚开始不建议太折腾，默认安装通常更省心。

---

## 12. 验证 CUDA Toolkit
安装完成后，重新打开 PowerShell。

检查 `nvcc`：

```powershell
nvcc --version
```

如正常，会看到 CUDA 编译器版本。

检查环境变量：

```powershell
echo $env:CUDA_PATH
```

通常会看到类似：

```latex
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0
```

检查驱动：

```powershell
nvidia-smi
```

记住：

+ `nvcc --version` 看的是本地 CUDA Toolkit；
+ `nvidia-smi` 里 CUDA Version 看的是驱动支持能力；
+ 两者不完全是一回事。

---

## 13. cuDNN 是什么
cuDNN 是 NVIDIA 给深度学习准备的加速库。

它专门优化这些操作：

+ 卷积；
+ 池化；
+ 归一化；
+ RNN；
+ 部分前向和反向计算。

如果 CUDA 是“GPU 通用计算工具箱”，cuDNN 更像是：

> 深度学习专用加速插件。
>

PyTorch 在很多情况下会自动使用 cuDNN。  
不一定要手动调用它，但它可能在背后帮助加速。

---

## 14. 手动安装 cuDNN
手动安装通常适合底层开发者。

基本思路是：

1. 下载对应 CUDA 版本的 cuDNN；[https://developer.nvidia.com/rdp/cudnn-archive](https://developer.nvidia.com/rdp/cudnn-archive)

<!-- 这是一张图片，ocr 内容为： -->
![](https://cdn.nlark.com/yuque/0/2026/png/21571931/1786434551176-f3242f70-3d06-4869-978b-f6049bb9ede4.png)

2. 解压；

<!-- 这是一张图片，ocr 内容为： -->
![](https://cdn.nlark.com/yuque/0/2026/png/21571931/1786434483590-08d1f138-041b-453e-997f-140b0ee232ae.png)

3. 把 `bin`、`include`、`lib` 中的文件放到 CUDA Toolkit 对应目录；

<!-- 这是一张图片，ocr 内容为： -->
![](https://cdn.nlark.com/yuque/0/2026/png/21571931/1786434653775-62d63dde-b48a-4acd-a1bc-b886e408c5e8.png)

常见 CUDA 路径：

```latex
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0
```

手动复制时要特别小心版本对应关系。  


---

