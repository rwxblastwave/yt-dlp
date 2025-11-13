from __future__ import annotations

import functools

from yt_dlp.extractor.youtube.jsc._builtin.ejs import EJSBaseJCP
from yt_dlp.extractor.youtube.jsc.provider import (
    JsChallengeProvider,
    JsChallengeProviderError,
    JsChallengeRequest,
    register_preference,
    register_provider,
)
from yt_dlp.extractor.youtube.pot._provider import BuiltinIEContentProvider
from yt_dlp.utils._jscore import JavaScriptCoreError, JavaScriptCoreEvaluator


@register_provider
class JavaScriptCoreJCP(EJSBaseJCP, BuiltinIEContentProvider):
    PROVIDER_NAME = 'javascriptcore'
    JS_RUNTIME_NAME = 'javascriptcore'

    @functools.cached_property
    def _evaluator(self) -> JavaScriptCoreEvaluator:
        return JavaScriptCoreEvaluator()

    def _run_js_runtime(self, stdin: str, /) -> str:
        try:
            return self._evaluator.evaluate(stdin)
        except JavaScriptCoreError as err:
            raise JsChallengeProviderError(f'JavaScriptCore runtime failed: {err}') from err


@register_preference(JavaScriptCoreJCP)
def preference(provider: JsChallengeProvider, requests: list[JsChallengeRequest]) -> int:
    return 600
