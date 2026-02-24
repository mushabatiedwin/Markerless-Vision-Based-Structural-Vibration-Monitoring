import matplotlib.pyplot as plt

def save_plot(x, y, title, xlabel, ylabel, path):
    plt.figure()
    plt.plot(x, y)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.savefig(path)
    plt.close()