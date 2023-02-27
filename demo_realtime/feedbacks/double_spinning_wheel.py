from multiprocessing import Process, Value
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

try:
    from importlib.resources import files  # type: ignore
except ImportError:
    from importlib_resources import files  # type: ignore

from ..utils._checks import _check_type
from ..utils._imports import import_optional_dependency
from ..utils._logs import logger


class DoubleSpinningWheel:
    """Feedback visual using 2 counter-spinning wheel.

    Parameters
    ----------
    size : float
        Normalized size of the wheel image. The provided value will be
        converted to retain the aspect ratio of the image.
    offset : float
        Normalized offset to position the image on the left and right side of
        the screen.
    **kwargs : dict
        Additional keyword arguments are provided to `psychopy.visual.Window`.
        The already defined values are:
        * ``units='norm'``
        * ``winType="pyglet"``
        * ``color=(-1, -1, -1)``
    """

    def __init__(
        self,
        size: float = 0.4,
        offset: float = 0.5,
        **kwargs,
    ) -> None:
        import_optional_dependency("psychopy")

        # prepare psychopy settings
        if "units" not in kwargs:
            kwargs["units"] = "norm"
        elif kwargs["units"] != "norm":
            raise ValueError(
                f"The unit used should be 'norm'. Provided {kwargs['units']} "
                "is not supported."
            )
        if "winType" not in kwargs:
            kwargs["winType"] = "pyglet"
        elif kwargs["winType"] != "pyglet":
            logger.warning(
                "The 'pyglet' window type is recommanded above the provided "
                "'%s'",
                kwargs["winType"],
            )

        if "color" not in kwargs:
            kwargs["color"] = (-1, -1, -1)
        elif kwargs["color"] != (-1, -1, -1):
            logger.warning(
                "The color '(-1, -1, -1)' is recommanded above the provided "
                "'%s'",
                kwargs["color"],
            )

        self._winkwargs = kwargs

        # store image path
        image = files("demo_realtime.feedbacks").joinpath(
            "resources/wheel.png"
        )
        assert image.is_file() and image.suffix == ".png"  # sanity-check
        self._image = image

        # and image settings
        _check_type(size, ("numeric",), "size")
        _check_type(offset, ("numeric",), "offset")
        for var, name in [(size, "size"), (offset, "offset")]:
            if var < -1 or var > 1:
                logger.warning(
                    "Normalized %s should be in the range (-1, 1). Values "
                    "outside this range might yield an image outside of the "
                    "window.",
                    name,
                )
        self._size = size
        self._offset = offset

        # prepare shared variables and process to control the wheel
        self._speed = Value("i", 0)
        self._status = Value("i", 0)
        self._process = Process(
            target=DoubleSpinningWheel._main_loop,
            args=(
                self._winkwargs,
                self._image,
                self._size,
                self._offset,
                self._speed,
                self._status,
            ),
        )

    def start(self) -> None:
        """Start the visual feedback."""
        if self._status.value == 1:
            raise RuntimeError("The feedback is already started.")

        with self._status.get_lock():
            self._status.value = 1
        self._process.start()

    def stop(self) -> None:
        """Stop the visual feedback."""
        if self._status.value == 0:
            raise RuntimeError("The feedback is already stopped.")
        with self._status.get_lock():
            self._status.value = 0
        self._process.join(5)

    def __del__(self):
        """Make sure to stop the feedback and close the window before del."""
        if self._status.value == 1:
            self.stop()

    # -------------------------------------------------------------------------
    @staticmethod
    def _main_loop(
        winkargs: dict,
        image: Path,
        size: float,
        offset: float,
        speed: Value,
        status: Value,
    ) -> None:
        from psychopy.visual import ImageStim, Window

        # open window
        win = Window(**winkargs)
        # normalize the image size to retain the aspect ratio
        size = DoubleSpinningWheel._normalize_size(win.size, size)
        lwheel = ImageStim(
            win, image=image, size=size * [1, 1], pos=[-offset, 0]
        )
        rwheel = ImageStim(
            win, image=image, size=size * [-1, 1], pos=[offset, 0]
        )
        lwheel.autoDraw = True
        rwheel.autoDraw = True
        win.flip()

        # run infinite display-loop
        while True:
            if status.value == 0:
                break

            lwheel.ori += speed.value
            rwheel.ori -= speed.value
            lwheel.draw()
            rwheel.draw()
            win.flip()

        # close window after a stop is requested
        win.close()

    @staticmethod
    def _normalize_size(winsize: NDArray[int], size: float) -> NDArray[float]:
        """Normalize the size to retain the aspect ratio of the image.

        Parameters
        ----------
        winsize : array of shape (2,)
            Size of the PsychoPy window.
        size : float
            Normalized size of the image, between -1 and 1.
        """
        if winsize[0] == winsize[1]:
            size = (size, size)
        elif winsize[1] < winsize[0]:
            size = (size, size * winsize[0] / winsize[1])
        elif winsize[0] < winsize[1]:
            size = (size * winsize[1] / winsize[0], size)
        return np.array(size)

    # -------------------------------------------------------------------------
    @property
    def image(self) -> Path:
        """Path to the image of the wheel displayed."""
        return self._iamge

    @property
    def offset(self) -> float:
        """Normalized offset of the images."""
        return self._offset

    @property
    def size(self) -> float:
        """Normalized size of the images."""
        return self._size

    @property
    def speed(self) -> int:
        """Speed of the rotation.

        :type: int
        """
        return self._speed.value

    @speed.setter
    def speed(self, speed: int) -> None:
        """Setter used to change the rotation speed."""
        assert speed == int(speed), "The provided speed must be an integer."
        with self._speed.get_lock():
            self._speed.value = speed

    @property
    def active(self) -> bool:
        """Return True if the feedback is running.

        :type: bool
        """
        return bool(self._status.value)