import random

import matplotlib.pyplot as plt

def main():
    # 场景：房价预测。已知 100 套房的面积和成交价，要找出估价公式：价格 = w * 面积 + b
    w = random.random()  # 随便猜一个"每平米单价"
    b = random.random()  # 随便猜一个"基础价"

    _x = [i/100 for i in range(100)]  # 100 套房，面积 0~0.99（按百平米计，即 0~99 平米）
    # 真实行情是 价格 = 3 * 面积 + 10（面积按百平米、价格按十万计）
    # random.random() 是 0~1 的正数，模拟装修、楼层带来的溢价，所以每套房都比基准价略高
    _y = [3*e + 10 + random.random() for e in _x]

    # 接下来一遍一遍地复习这 100 套房，慢慢把估价公式修正到最准
    while True:
        # 首先迭代x, y  因为x,y是不相关的数组 zip打包成元组
        # 内部循环100次，每次拿出一套房的面积 x 和真实成交价 y
        for x, y in zip(_x, _y):
            # 用当前公式给这套房估价
            # h 是估计的价格
            h = w * x + b
            # y是真实成交价（标准答案）
            # 根据当前w b 值计算这套房估得有多离谱(损失函数)，平方让误差永远为正
            loss = (y-h)**2
            # 现在有损失我们需要更新 权重 w 和 b
            # 更新权重使用梯度下降法 当前x 和 y是确定的 需要确定w 和 b
            # y = w * x + b
            # f(w,b) 二元函数求导：估低了(y-h为正)就把 w b 调大，估高了就调小
            dw = -2 * x * (y-h)
            db = -2 * (y-h)


            # 求 dw 和 db目的是修正估价公式的 w 和 b
            # 0.01 是学习率，即每次修正的幅度：太大来回震荡，太小学得太慢
            w -= dw * 0.01
            b -= db * 0.01

            print(f'loss:{loss}---w:{w}---b:{b}')
            # 开启交互模式
            plt.ion()
            # 清屏
            plt.cla()
            # _x, _y是100套真实成交的房子
            plt.plot(_x, _y, '.')
            # 间隔0.01s
            # 用修正后的 w, b 画出当前的估价直线
            plt.plot(_x, [w * e + b for e in _x])
            plt.pause(0.01)

        plt.show()

if __name__ == "__main__":
    main()