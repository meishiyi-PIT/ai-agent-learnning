import torch

def main():
    x = torch.tensor([2.0,3.0])
    print(x.requires_grad)

    w = torch.tensor([1.5],requires_grad=True)
    print(w.requires_grad)


    y = w*3

    loss = (y-9) ** 2
    loss.backward()
    print(w.grad)

if __name__ == "__main__":
    main()
