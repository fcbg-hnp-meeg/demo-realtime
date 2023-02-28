import time
from typing import Optional, Union

import numpy as np
from bsl import StreamReceiver

from .feedbacks import DoubleSpinningWheel
from .metrics import bandpower
from .utils._checks import _check_type
from .utils._docs import fill_doc
from .utils._logs import set_log_level


@fill_doc
def nfb_double_spinning_wheel(
    stream_name: str,
    winsize: float = 3,
    duration: float = 30,
    verbose: Optional[Union[str, int]] = None,
) -> None:
    """Real-time neurofeedback loop using a double spinning wheel as feedback.

    The feedback represents the alpha-band power on the occipital electrodes
    ``O1`` and ``O2``.

    Parameters
    ----------
    %(stream_name)s
    %(winsize)s
    %(duration)s
    %(verbose)s
    """
    set_log_level(verbose)
    # check inputs
    _check_type(stream_name, (str,), "stream_name")
    _check_type(winsize, ("numeric",), "winsize")
    assert 0 < winsize
    _check_type(duration, ("numeric",), "duration")
    assert 0 < duration

    # create receiver and feedback
    sr = StreamReceiver(
        bufsize=winsize, winsize=winsize, stream_name=stream_name
    )
    feedback = DoubleSpinningWheel(size=(800, 800))

    # store 100 points to compute percentile for min/max
    metrics = np.ones(100) * np.nan
    inc = 0

    # retrieve sampling rate and channels
    fs = sr.streams[stream_name].sample_rate
    ch_names = sr.streams[stream_name].ch_list
    ch_idx = [k for k, ch in enumerate(ch_names) if ch in ("O1", "O2")]
    assert len(ch_idx) == 2

    # wait to fill one buffer
    time.sleep(winsize)

    # main loop
    start = time.time()
    while time.time() - start <= duration:
        # retrieve data
        sr.acquire()
        data, _ = sr.get_window()
        # compute metric
        metric = bandpower(
            data[:, ch_idx].T, fs=fs, method="multitaper", band=(8, 13)
        )
        metric = np.average(metric)  # average across selected channels

        # store metric
        metrics[inc % 100] = metric
        inc += 1
        # skip until we have enough points to define the feedback range
        if inc < metrics.size:
            start = time.time()  # reset start time
            continue
        elif inc == metrics.size:
            feedback.start()
        # define the feedback range
        min_ = np.percentile(metrics, 5)
        max_ = np.percentile(metrics, 95)
        feedback_perc = np.clip((metric - min_) / (max_ - min_), 0, 1) * 100

        # update feedback
        feedback.speed = int(feedback_perc)

    # close the feedback window
    feedback.stop()
