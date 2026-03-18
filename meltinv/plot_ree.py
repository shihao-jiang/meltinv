import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, LogLocator


def plot_ree(ax, one_sample, color, linewidth, linestyle='-', label=None):
    CI_REE = np.array([0.2472, 0.6308, 0.0950, 0.4793, 0.1542, 0.0592, 0.2059,
                       0.0375, 0.2540, 0.0554, 0.1645, 0.0258, 0.1684, 0.0251])

    ree = ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd',
           'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu']
    ree_array = np.array(one_sample)
    normalised_array = np.array([])
    for i in range(len(ree_array)):
        if ree_array[i] is None:
            normalised_array = np.append(normalised_array, None)
        elif ree_array[i] <=1e-3:
            normalised_array = np.append(normalised_array, 1e-2)
        else:
            normalised_array = np.append(normalised_array, ree_array[i] / CI_REE[i])


    ax.plot(normalised_array, color=color, marker='o', markeredgecolor=color, markerfacecolor='white',
            markersize=3.9, linewidth=linewidth, linestyle=linestyle, label=label, zorder=6)
    ax.set_ylim(1, 200)
    ax.set_yscale('log')
    ax.set_ylabel(r'c$_\mathrm{sample}$/c$_\mathrm{CI}$')
    ax.set_xticks([i for i in range(14)])
    ax.set_xticklabels(ree)

    ax.yaxis.set_major_locator(LogLocator(subs='all'))
    # ax.yaxis.set_minor_locator(LogLocator(subs='all'))

    ax.grid(linestyle='--', color='lightgray')
    if label is not None:
        ax.legend()

def plot_ree_range(ax, sample_mean, sample_a, sample_b):
    CI_REE = np.array([0.2472, 0.6308, 0.0950, 0.4793, 0.1542, 0.0592, 0.2059,
                       0.0375, 0.2540, 0.0554, 0.1645, 0.0258, 0.1684, 0.0251])

    ree = ['La', 'Ce', 'Pr', 'Nd', 'Sm', 'Eu', 'Gd',
           'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu']
    k = []
    for i in [sample_mean, sample_a, sample_b]:
        ree_array = np.array(i)
        normalised_array = np.array([])
        for i in range(len(ree_array)):
            if ree_array[i] is None:
                normalised_array = np.append(normalised_array, None)
            elif ree_array[i] <= 1e-3:
                normalised_array = np.append(normalised_array, 1e-2)
            else:
                normalised_array = np.append(normalised_array, ree_array[i] / CI_REE[i])
        k.append(normalised_array)

    x, y1, y2 = range(len(ree_array)), k[1], k[0]
    for frac, color in zip(np.linspace(1/10, 1, 10), plt.cm.Reds(np.linspace(0.1, 1, 10))):
        y_mid = y1 + frac * (y2 - y1)
        ax.fill_between(x, y1, y_mid, color=color, alpha=0.8, linewidth=0, zorder=5)
        y1 = y_mid


    x, y1, y2 = range(len(ree_array)), k[2], k[0]
    for frac, color in zip(np.linspace(1/10, 1, 10), plt.cm.Reds(np.linspace(0.1, 1, 10))):
        y_mid = y1 + frac * (y2 - y1)
        ax.fill_between(x, y1, y_mid, color=color, alpha=0.8, linewidth=0, zorder=5)
        y1 = y_mid

    # ax.fill_between(range(len(ree_array)), k[0], k[1], color='tab:red', alpha=0.3, zorder=5)