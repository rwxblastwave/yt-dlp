from __future__ import annotations

import ctypes
import ctypes.util
from typing import Iterable


class JavaScriptCoreError(RuntimeError):
    """Raised when JavaScriptCore evaluation fails."""


class JavaScriptCoreEvaluator:
    """Minimal wrapper around JavaScriptCore's C API."""

    def __init__(self):
        self._library = self._load_library()
        if not self._library:
            raise JavaScriptCoreError('JavaScriptCore framework is not available')
        self._configure_functions()

    @property
    def library_path(self) -> str:
        return getattr(self._library, '_name', 'JavaScriptCore')

    @property
    def version(self) -> str:
        return 'JavaScriptCore'

    @property
    def version_tuple(self) -> tuple[int, ...]:
        # JavaScriptCore does not expose a simple public version API we can rely on.
        # Returning (0,) keeps the runtime marked as supported.
        return (0,)

    def evaluate(self, script: str) -> str:
        """Evaluate *script* and return the joined console output."""
        wrapped_script = self._wrap_script(script)
        context = self._library.JSGlobalContextCreate(None)
        if not context:
            raise JavaScriptCoreError('Failed to create JavaScriptCore context')
        try:
            return self._evaluate_script(context, wrapped_script)
        finally:
            self._library.JSGlobalContextRelease(context)

    def _evaluate_script(self, context, script: str) -> str:
        encoded = script.encode('utf-8')
        js_string = self._library.JSStringCreateWithUTF8CString(encoded)
        if not js_string:
            raise JavaScriptCoreError('Failed to allocate script string')
        try:
            exception = ctypes.c_void_p()
            result = self._library.JSEvaluateScript(
                context, js_string, None, None, 0, ctypes.byref(exception))
        finally:
            self._library.JSStringRelease(js_string)

        if exception.value:
            message = self._value_to_string(context, exception.value)
            raise JavaScriptCoreError(message or 'JavaScriptCore raised an exception')

        return self._value_to_string(context, result)

    def _value_to_string(self, context, value) -> str:
        if not value:
            return ''
        exception = ctypes.c_void_p()
        string_ref = self._library.JSValueToStringCopy(
            context, value, ctypes.byref(exception))
        if exception.value:
            return ''
        try:
            return self._string_to_python(string_ref)
        finally:
            self._library.JSStringRelease(string_ref)

    def _string_to_python(self, string_ref) -> str:
        if not string_ref:
            return ''
        size = self._library.JSStringGetMaximumUTF8CStringSize(string_ref)
        buffer = ctypes.create_string_buffer(size)
        self._library.JSStringGetUTF8CString(string_ref, buffer, size)
        return buffer.value.decode('utf-8', 'replace')

    def _wrap_script(self, script: str) -> str:
        # Capture console.log output and expose it as the return value.
        return (
            "(() => {\n"
            "    'use strict';\n"
            "    const __yt_console_output = [];\n"
            "    const __yt_console_log = (...args) => __yt_console_output.push(args.map((arg) => {\n"
            "        if (typeof arg === 'string') {\n"
            "            return arg;\n"
            "        }\n"
            "        try {\n"
            "            return JSON.stringify(arg);\n"
            "        } catch (err) {\n"
            "            return String(arg);\n"
            "        }\n"
            "    }).join(' '));\n"
            "    const existingConsole = globalThis.console || {};\n"
            "    globalThis.console = { ...existingConsole, log: __yt_console_log };\n"
            f"    {script}\n"
            "    return __yt_console_output.join('\\n');\n"
            "})()" )

    @staticmethod
    def _candidate_libraries() -> Iterable[str]:
        frameworks = '/System/Library/Frameworks/JavaScriptCore.framework/JavaScriptCore'
        yield frameworks
        for name in (
            'JavaScriptCore',
            'javascriptcoregtk-4.1',
            'javascriptcoregtk-4.0',
            'javascriptcoregtk-3.0',
        ):
            path = ctypes.util.find_library(name)
            if path:
                yield path

    def _load_library(self):
        for path in self._candidate_libraries():
            try:
                return ctypes.CDLL(path)
            except OSError:
                continue
        return None

    def _configure_functions(self):
        lib = self._library
        lib.JSGlobalContextCreate.restype = ctypes.c_void_p
        lib.JSGlobalContextCreate.argtypes = [ctypes.c_void_p]
        lib.JSGlobalContextRelease.argtypes = [ctypes.c_void_p]
        lib.JSStringCreateWithUTF8CString.restype = ctypes.c_void_p
        lib.JSStringCreateWithUTF8CString.argtypes = [ctypes.c_char_p]
        lib.JSStringRelease.argtypes = [ctypes.c_void_p]
        lib.JSEvaluateScript.restype = ctypes.c_void_p
        lib.JSEvaluateScript.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        lib.JSValueToStringCopy.restype = ctypes.c_void_p
        lib.JSValueToStringCopy.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        lib.JSStringGetMaximumUTF8CStringSize.restype = ctypes.c_size_t
        lib.JSStringGetMaximumUTF8CStringSize.argtypes = [ctypes.c_void_p]
        lib.JSStringGetUTF8CString.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_size_t,
        ]
