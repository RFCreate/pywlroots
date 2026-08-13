# Copyright (c) Sean Vig 2019
# Copyright (c) Matt Colligan 2021

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from pywayland.protocol.wayland import WlOutput
from pywayland.server import Display, Signal
from pywayland.utils import wl_list_for_each

from wlroots import Ptr, PtrHasData, ffi, lib, ptr_or_null, str_or_none

if TYPE_CHECKING:
    from collections.abc import Iterator

    from wlroots.allocator import Allocator
    from wlroots.renderer import Renderer


class Output(PtrHasData):
    def __init__(self, ptr: ffi.CData) -> None:
        """A compositor output region

        This typically corresponds to a monitor that displays part of the
        compositor space.

        The `frame` event will be emitted when it is a good time for the
        compositor to submit a new frame.

        To render a new frame compositors should call `begin_render_pass`,
        perform rendering on that render pass, and finally call `commit_state`.

        :param ptr:
            The wlr_output cdata pointer
        """
        self._ptr = ffi.cast("struct wlr_output *", ptr)

        self.frame_event = Signal(ptr=ffi.addressof(self._ptr.events.frame))
        self.damage_event = Signal(ptr=ffi.addressof(self._ptr.events.damage))
        self.needs_frame_event = Signal(ptr=ffi.addressof(self._ptr.events.needs_frame))
        self.precommit_event = Signal(ptr=ffi.addressof(self._ptr.events.precommit))
        self.commit_event = Signal(ptr=ffi.addressof(self._ptr.events.commit))
        self.present_event = Signal(ptr=ffi.addressof(self._ptr.events.present))
        self.bind_event = Signal(ptr=ffi.addressof(self._ptr.events.bind))
        self.description_event = Signal(ptr=ffi.addressof(self._ptr.events.description))
        self.request_state_event = Signal(
            ptr=ffi.addressof(self._ptr.events.request_state),
            data_wrapper=OutputEventRequestState,
        )
        self.destroy_event = Signal(ptr=ffi.addressof(self._ptr.events.destroy))

    @property
    def name(self) -> str | None:
        """The name of the output"""
        return str_or_none(self._ptr.name)

    @property
    def description(self) -> str | None:
        """The description of the output"""
        return str_or_none(self._ptr.description)

    @property
    def make(self) -> str | None:
        return str_or_none(self._ptr.make)

    @property
    def model(self) -> str | None:
        return str_or_none(self._ptr.model)

    @property
    def serial(self) -> str | None:
        return str_or_none(self._ptr.serial)

    @property
    def phys_width(self) -> int:
        """Returns the physical width of the output, in millimeters"""
        return self._ptr.phys_width

    @property
    def phys_height(self) -> int:
        """Returns the physical height of the output, in millimeters"""
        return self._ptr.phys_height

    @property
    def modes(self) -> Iterator[OutputMode]:
        for ptr in wl_list_for_each(
            "struct wlr_output_mode *",
            self._ptr.modes,
            "link",
            ffi=ffi,
        ):
            yield OutputMode(ptr)

    @property
    def enabled(self) -> bool:
        return self._ptr.enabled

    @property
    def current_mode(self) -> OutputMode | None:
        if self._ptr.current_mode == ffi.NULL:
            return None
        return OutputMode(self._ptr.current_mode)

    @property
    def scale(self) -> float:
        return self._ptr.scale

    @property
    def transform(self) -> WlOutput.transform:
        return WlOutput.transform(self._ptr.transform)

    def preferred_mode(self) -> OutputMode | None:
        """Returns the preferred mode for this output

        If the output doesn't support modes, returns None.
        """
        output_mode_ptr = lib.wlr_output_preferred_mode(self._ptr)
        if output_mode_ptr == ffi.NULL:
            return None

        return OutputMode(output_mode_ptr)

    def create_global(self, display: Display) -> None:
        """Create the global corresponding to the output"""
        lib.wlr_output_create_global(self._ptr, display._ptr)

    def __enter__(self) -> Output:
        """Start rendering frame"""
        return self

    def init_render(self, allocator: Allocator, renderer: Renderer) -> None:
        """
        Initialize the output's rendering subsystem with the provided allocator and
        renderer. After initialization, this function may invoked again to reinitialize
        the allocator and renderer to different values.

        Call this function prior to any call to `begin_render_pass`,
        `commit_state` or `cursor_create`.

        The buffer capabilities of the provided must match the capabilities of the
        output's backend. Returns false otherwise.
        """
        if not lib.wlr_output_init_render(self._ptr, allocator._ptr, renderer._ptr):
            raise RuntimeError(
                "Output capabilities must match the capabilities of the output's backend."
            )

    def commit_state(self, output_state: OutputState) -> bool:
        """
        Attempts to apply the state to this output. This function may fail for any
        reason and return false. If failed, none of the state would have been applied,
        this function is atomic. If the commit succeeded, true is returned.

        Note: `state_finish` would typically be called after the state
        has been committed.
        """
        return lib.wlr_output_commit_state(self._ptr, output_state._ptr)

    def effective_resolution(self) -> tuple[int, int]:
        """Computes the transformed and scaled output resolution"""
        width_ptr = ffi.new("int *")
        height_ptr = ffi.new("int *")
        lib.wlr_output_effective_resolution(self._ptr, width_ptr, height_ptr)
        width = width_ptr[0]
        height = height_ptr[0]
        return width, height

    def transformed_resolution(self) -> tuple[int, int]:
        """Computes the transformed output resolution"""
        width_ptr = ffi.new("int *")
        height_ptr = ffi.new("int *")
        lib.wlr_output_transformed_resolution(self._ptr, width_ptr, height_ptr)
        width = width_ptr[0]
        height = height_ptr[0]
        return width, height

    def test_state(self, output_state: OutputState) -> bool:
        """
        Test whether this output state would be accepted by the backend. If this
        function returns true, `commit_state` will only fail due to a
        runtime error. This function does not change the current state of the
        output.
        """
        return lib.wlr_output_test_state(self._ptr, output_state._ptr)

    @property
    def is_headless(self) -> bool:
        return lib.wlr_output_is_headless(self._ptr)


class OutputMode(Ptr):
    def __init__(self, ptr: ffi.CData) -> None:
        self._ptr = ptr

    @property
    def width(self) -> int:
        return self._ptr.width

    @property
    def height(self) -> int:
        return self._ptr.height

    @property
    def refresh(self) -> int:
        return self._ptr.refresh

    @property
    def preferred(self) -> int:
        return self._ptr.preferred


class CustomMode(NamedTuple):
    """
    Custom mode which specifies the width and height, and the refresh rate
    of an Output.

    If refresh is zero (default), the backend uses a reasonable default value.
    """

    width: int
    height: int
    refresh: int = 0


class OutputState(Ptr):
    def __init__(self, ptr: ffi.CData | None = None) -> None:
        if ptr is None:
            ptr = ffi.new("struct wlr_output_state *")
            lib.wlr_output_state_init(ptr)
        self._ptr = ptr

    @property
    def enabled(self) -> bool:
        return self._ptr.enabled

    def set_enabled(self, enabled: bool) -> None:
        lib.wlr_output_state_set_enabled(self._ptr, enabled)

    @property
    def scale(self) -> float:
        return self._ptr.scale

    def set_scale(self, scale: float) -> None:
        lib.wlr_output_state_set_scale(self._ptr, scale)

    @property
    def transform(self) -> WlOutput.transform:
        return WlOutput.transform(self._ptr.transform)

    def set_transform(self, transform: WlOutput.transform) -> None:
        lib.wlr_output_state_set_transform(self._ptr, transform)

    @property
    def adaptive_sync_enabled(self) -> bool:
        return self._ptr.adaptive_sync_enabled

    def set_adaptive_sync_enabled(self, enabled: bool) -> None:
        lib.wlr_output_state_set_adaptive_sync_enabled(self._ptr, enabled)

    @property
    def render_format(self) -> int:
        return self._ptr.render_format

    def set_render_format(self, format: int) -> None:
        lib.wlr_output_state_set_render_format(self._ptr, format)

    @property
    def subpixel(self) -> WlOutput.subpixel:
        return WlOutput.subpixel(self._ptr.subpixel)

    def set_subpixel(self, subpixel: WlOutput.subpixel) -> None:
        lib.wlr_output_state_set_subpixel(self._ptr, subpixel)

    @property
    def mode(self) -> OutputMode | None:
        mode_ptr = self._ptr.mode
        return OutputMode(mode_ptr) if mode_ptr != ffi.NULL else None

    def set_mode(self, mode: OutputMode | None) -> None:
        lib.wlr_output_state_set_mode(self._ptr, ptr_or_null(mode))

    @property
    def custom_mode(self) -> CustomMode:
        mode = self._ptr.custom_mode
        return CustomMode(width=mode.width, height=mode.height, refresh=mode.refresh)

    def set_custom_mode(self, mode: CustomMode) -> None:
        lib.wlr_output_state_set_custom_mode(
            self._ptr, mode.width, mode.height, mode.refresh
        )

    def state_finish(self) -> None:
        lib.wlr_output_state_finish(self._ptr)


class OutputEventRequestState(Ptr):
    def __init__(self, ptr: ffi.CData) -> None:
        self._ptr = ffi.cast("struct wlr_output_event_request_state *", ptr)

    @property
    def output(self) -> Output:
        return Output(self._ptr.output)

    @property
    def state(self) -> OutputState:
        return OutputState(self._ptr.state)
