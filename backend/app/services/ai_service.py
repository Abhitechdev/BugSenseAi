"""AI Analysis Service — core LLM integration for BugSense AI."""

import json
from typing import Optional

import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app import config as app_config

logger = structlog.get_logger(__name__)


ERROR_ANALYSIS_PROMPT = """You are an expert software debugging assistant. Analyze the following error/stack trace and provide a structured analysis.

{language_context}

IMPORTANT — Node.js / JavaScript error naming rules:
If the error is from Node.js or JavaScript, you MUST use a more descriptive, human-friendly name for the "error_type" field instead of the raw error class. Examples:
- "MODULE_NOT_FOUND" or "Cannot find module" → "ModuleResolutionError"
- "TypeError: X is not a function" → "InvalidFunctionCallError"
- "ReferenceError: X is not defined" → "UndefinedVariableError"
- "SyntaxError: Unexpected token" → "SyntaxParsingError"
- "RangeError: Maximum call stack" → "StackOverflowError"
- "ECONNREFUSED" → "ConnectionRefusedError"
- "ENOENT" → "FileNotFoundError"
- "ERR_HTTP_HEADERS_SENT" → "DuplicateHeaderError"
- "EADDRINUSE" → "PortAlreadyInUseError"
- "UnhandledPromiseRejection" → "UnhandledAsyncError"
Use similar descriptive naming for any other Node.js errors not listed above.
For non-JavaScript/Node.js errors, use the standard error class name as-is.

ERROR INPUT:
```
{input_text}
```

Respond ONLY with valid JSON in this exact format.
Do not include markdown, comments, or explanations outside the JSON structure.
Do not include raw line breaks inside string values.
{{
    "language": "Detect the programming language (e.g., nodejs, python, java, go) or 'unknown'",
    "environment": "Detect the execution environment (e.g., runtime, docker, cicd) or 'unknown'",
    "error_type": "The specific type/class of the error (use descriptive names for Node.js errors as instructed above)",
    "explanation": "A clear, developer-friendly explanation of what this error means",
    "root_cause": "The most likely root cause of this error",
    "fix": "Step-by-step instructions to fix this error",
    "example_solution": "A code example showing the fix (use markdown code blocks)"
}}"""

LOG_ANALYSIS_PROMPT = """You are an expert CI/CD and DevOps engineer. Analyze the following build/CI log and identify the failing step.

{platform_context}

IMPORTANT — CI/CD Pipeline Error Detection Rules:
1. Detect CI/CD Environment: Determine whether the input log comes from a CI/CD pipeline. Use pattern matching on common pipeline log signatures.
   - If "npm ERR!" in log -> "cicd"
   - If "failed to solve" in log -> "docker"
   - If "BUILD FAILED" in log -> "cicd"
   - If "Error: Process completed with exit code" in log -> "cicd"
   Default to "runtime" if not matched. Returns this in "environment".

2. Extract Build Step Failure: Identify which pipeline step failed (e.g., dependency installation, build step, test execution, Docker image build, deployment step). Include this in your "explanation".

3. Classify CI/CD Error Type: Map the error to a standardized error type in "error_type":
   - "Missing script" -> "BuildScriptError"
   - "ERESOLVE", "npm ERR! code ERESOLVE" -> "DependencyInstallError"
   - "failed to solve" -> "DockerBuildError"
   - "BUILD FAILED" -> "PipelineExecutionError"
   - "test failed" -> "TestFailureError"
   - "Cannot find module" -> "DependencyInstallError"
   Choose from: BuildScriptError, DependencyInstallError, DockerBuildError, PipelineExecutionError, TestFailureError, or provide an accurate related type if none fit perfectly.

4. Generate Root Cause Analysis: Provide a clear explanation of why the pipeline failed in "root_cause".

5. Provide Fix Instructions: Generate practical fix instructions developers can apply immediately in "fix".

6. Provide Example Solution: Output a concrete configuration example or code snippet demonstrating how to fix the error in "example_solution".

CI/CD LOG:
```
{input_text}
```

Respond ONLY with valid JSON in this exact format.
Do not include markdown, comments, or explanations outside the JSON structure.
Do not include raw line breaks inside string values.
{{
    "language": "Detect the programming language involved (if any), otherwise 'unknown'",
    "environment": "The detected environment (cicd, docker, runtime) based on rule 1",
    "error_type": "The classified CI/CD error type based on rule 3",
    "explanation": "What happened in the pipeline and which step failed",
    "root_cause": "The root cause of the pipeline failure",
    "fix": "Step-by-step instructions to fix the pipeline",
    "example_solution": "Example configuration or code fix (use markdown code blocks)"
}}"""

ISSUE_ANALYSIS_PROMPT = """You are an expert software engineer. Analyze the following GitHub issue text and extract technical context.

{repo_context}

GITHUB ISSUE:
```
{input_text}
```

Respond ONLY with valid JSON in this exact format.
Do not include markdown, comments, or explanations outside the JSON structure.
Do not include raw line breaks inside string values.
{{
    "language": "Extract the programming language based on issue text or dependencies, or 'unknown'",
    "environment": "runtime, build, deployment, etc.",
    "error_type": "ModuleResolutionError, ModuleNotFoundError, DependencyResolutionError, or specific bug category",
    "explanation": "Summary of the issue and its technical implications (extract dependency names if relevant)",
    "root_cause": "The most likely technical root cause limit",
    "fix": "Suggested approach or installation commands to resolve this issue",
    "example_solution": "Example code or configuration to address the issue (use markdown code blocks)"
}}"""

CODE_FIX_PROMPT = """You are an expert code reviewer and debugger. The following code contains bugs. Fix it and explain the changes.

{language_context}

{error_context}

BUGGY CODE:
```
{input_text}
```

Respond ONLY with valid JSON in this exact format.
Do not include markdown, comments, or explanations outside the JSON structure.
Do not include raw line breaks inside string values.
{{
    "language": "Detect the programming language of the snippet",
    "environment": "runtime",
    "error_type": "The type of bug found (SyntaxError, LogicError, TypeError, MissingCheck, etc.)",
    "explanation": "Explanation of what the bugs are (missing checks, variable misuse, etc.)",
    "root_cause": "Why the code is failing or incorrect",
    "fix": "Description of all changes made to fix the code",
    "example_solution": "The complete corrected code (use markdown code blocks)"
}}"""

REQUIRED_RESPONSE_KEYS = (
    "language",
    "environment",
    "error_type",
    "explanation",
    "root_cause",
    "fix",
    "example_solution",
)

LANGUAGE_INDICATORS = {
    "python": ["traceback", 'file "', "importerror", "indentationerror", ".py", "def ", "class "],
    "javascript": ["typeerror:", "referenceerror:", "node_modules", ".js", "const ", "let ", "=>"],
    "typescript": [".ts", "interface ", "type ", " as ", ": string", ": number"],
    "java": ["exception in thread", ".java", "at com.", "nullpointerexception", "public class"],
    "rust": ["panic!", "thread 'main'", ".rs", "fn ", "let mut"],
    "go": ["goroutine", ".go", "panic:", "func ", "package main"],
    "csharp": [".cs", "system.", "nullreferenceexception", "namespace ", "public void"],
    "ruby": [".rb", "nomethoderror", "undefined method", "gems/"],
    "php": [".php", "fatal error:", "uncaught", "->", "<?php"],
}


class AIService:
    """Handles all AI/LLM interactions for analysis."""

    def __init__(self):
        self.settings = app_config.get_settings()
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=20.0)
            limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
            self._client = httpx.AsyncClient(timeout=timeout, limits=limits)
        return self._client

    @staticmethod
    def _require_secret(name: str, value: str) -> str:
        secret = value.strip()
        if not secret:
            raise ValueError(f"{name} is not configured")
        return secret

    def _get_api_config(self) -> tuple[str, dict[str, str]]:
        """Return the provider URL and headers."""
        provider = self.settings.ai_provider

        if provider == "nvidia":
            api_key = self._require_secret("NVIDIA_API_KEY", self.settings.nvidia_api_key)
            return (
                "https://integrate.api.nvidia.com/v1/chat/completions",
                {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )

        if provider == "gemini":
            api_key = self._require_secret("GEMINI_API_KEY", self.settings.gemini_api_key)
            return (
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.ai_model}:generateContent?key={api_key}",
                {"Content-Type": "application/json"},
            )

        if provider == "anthropic":
            api_key = self._require_secret("ANTHROPIC_API_KEY", self.settings.anthropic_api_key)
            return (
                "https://api.anthropic.com/v1/messages",
                {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
            )

        if provider == "openai":
            api_key = self._require_secret("OPENAI_API_KEY", self.settings.openai_api_key)
            return (
                "https://api.openai.com/v1/chat/completions",
                {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )

        api_key = self._require_secret("OPENROUTER_API_KEY", self.settings.openrouter_api_key)
        return (
            "https://openrouter.ai/api/v1/chat/completions",
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://bugsense.ai",
                "X-Title": "BugSense AI",
            },
        )

    def _build_payload(self, prompt: str) -> dict:
        provider = self.settings.ai_provider

        if provider == "gemini":
            return {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": (
                                    "You are BugSense AI, an expert debugging assistant. "
                                    "Always respond with valid JSON only.\n\n"
                                    f"{prompt}"
                                )
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 2000,
                    "responseMimeType": "application/json",
                },
            }

        if provider == "anthropic":
            return {
                "model": self.settings.ai_model,
                "system": "You are BugSense AI, an expert debugging assistant. Always respond with valid JSON only.",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2000,
            }

        return {
            "model": self.settings.ai_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are BugSense AI, an expert debugging assistant. Always respond with valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

    def _extract_content(self, data: dict) -> str:
        provider = self.settings.ai_provider

        if provider == "gemini":
            return data["candidates"][0]["content"]["parts"][0]["text"]
        if provider == "anthropic":
            return data["content"][0]["text"]
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _normalize_result(result: dict) -> dict:
        normalized = dict(result)
        for key in REQUIRED_RESPONSE_KEYS:
            value = normalized.get(key)
            if value is None or value == "":
                normalized[key] = "Not available"
            elif isinstance(value, list):
                if key == "fix":
                    normalized[key] = "\n".join(f"- {step}" for step in value)
                else:
                    normalized[key] = " ".join(str(item) for item in value)
        return normalized

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def _call_llm(self, prompt: str) -> dict:
        url, headers = self._get_api_config()
        payload = self._build_payload(prompt)
        client = self._get_client()

        logger.info(
            "llm_request",
            provider=self.settings.ai_provider,
            model=self.settings.ai_model,
            prompt_length=len(prompt),
        )

        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        raw = self._extract_content(response.json()).strip()

        if raw.startswith("```json"):
            raw = raw[7:]
        elif raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]

        cleaned = raw.strip().replace("\t", " ")

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("json_parse_error", error=str(exc), raw_content_length=len(cleaned))
            return {
                "language": "unknown",
                "environment": "unknown",
                "error_type": "ParsingError",
                "explanation": "AI response format invalid",
                "root_cause": "Generated output was not valid JSON",
                "fix": "Retry analysis request",
                "example_solution": "",
            }

        logger.info("llm_response_parsed", error_type=parsed.get("error_type"))
        return self._normalize_result(parsed)

    async def analyze_error(self, input_text: str, language_hint: Optional[str] = None) -> dict:
        language_context = (
            f"The code is written in {language_hint}."
            if language_hint
            else "Detect the programming language from the error."
        )
        prompt = ERROR_ANALYSIS_PROMPT.format(
            input_text=input_text,
            language_context=language_context,
        )
        return await self._call_llm(prompt)

    async def analyze_log(self, input_text: str, ci_platform: Optional[str] = None) -> dict:
        platform_context = (
            f"This is from {ci_platform}."
            if ci_platform
            else "Detect the CI/CD platform from the log."
        )
        prompt = LOG_ANALYSIS_PROMPT.format(
            input_text=input_text,
            platform_context=platform_context,
        )
        return await self._call_llm(prompt)

    async def analyze_issue(self, input_text: str, repo_url: Optional[str] = None) -> dict:
        repo_context = f"Repository: {repo_url}" if repo_url else ""
        prompt = ISSUE_ANALYSIS_PROMPT.format(input_text=input_text, repo_context=repo_context)
        return await self._call_llm(prompt)

    async def fix_code(
        self,
        buggy_code: str,
        error_message: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        language_context = f"The code is written in {language}." if language else "Detect the programming language."
        error_context = f"Error message: {error_message}" if error_message else ""
        prompt = CODE_FIX_PROMPT.format(
            input_text=buggy_code,
            language_context=language_context,
            error_context=error_context,
        )
        return await self._call_llm(prompt)

    def detect_language(self, text: str) -> Optional[str]:
        """Heuristic language detection from error or code text."""
        text_lower = text.lower()
        scores = {
            language: sum(1 for indicator in indicators if indicator in text_lower)
            for language, indicators in LANGUAGE_INDICATORS.items()
        }
        best_match = max(scores, key=scores.get)
        return best_match if scores[best_match] > 0 else None

    async def ping(self) -> bool:
        """Check whether provider configuration is usable."""
        self._get_api_config()
        self._get_client()
        return True

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


ai_service = AIService()
