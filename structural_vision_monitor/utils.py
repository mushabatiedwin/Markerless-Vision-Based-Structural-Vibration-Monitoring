import matplotlib.pyplot as plt
import numpy as np
import os


def save_plot(x, y, title, xlabel, ylabel, path, color="#1f77b4", xlim=None, ylim=None):
    """Save a simple line plot to disk."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(x, y, linewidth=0.9, color=color)
    ax.set_title(title, fontsize=13)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)
    fig.tight_layout()
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_annotated_frame(frame, path, text_lines=None):
    """Save a single video frame (BGR numpy array) with optional text overlay."""
    import cv2
    annotated = frame.copy()
    if text_lines:
        for i, line in enumerate(text_lines):
            cv2.putText(annotated, line, (10, 30 + i * 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imwrite(path, annotated)
