"""AI Analysis Service — core LLM integration for BugSense AI."""

import json
import httpx
import structlog
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── Prompt templates ──

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


class AIService:
    """Handles all AI/LLM interactions for analysis."""

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
<<<<<<< HEAD
        if self._client is None or self._client.is_closed:
            # Configure client with better timeout handling
            timeout = httpx.Timeout(
                connect=10.0,    # Connection timeout
                read=60.0,       # Read timeout
                write=30.0,      # Write timeout
                pool=20.0        # Pool timeout
            )
            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    
            )
        return self._client
=======
    if self._client is None or self._client.is_closed:
        timeout = httpx.Timeout(
            connect=10.0,
            read=60.0,
            write=30.0,
            pool=20.0
        )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    return self._client
>>>>>>> e4823c2a71025b50cee1b809eaf97ecaa35aac11

    @staticmethod
    def _require_secret(name: str, value: str) -> str:
        secret = value.strip()
        if not secret:
            raise ValueError(f"{name} is not configured")
        return secret

    def _get_api_config(self) -> tuple[str, dict]:
        """Returns (base_url, headers) based on configured provider."""
        if self.settings.ai_provider == "nvidia":
            api_key = self._require_secret("NVIDIA_API_KEY", self.settings.nvidia_api_key)
            return (
                "https://integrate.api.nvidia.com/v1/chat/completions",
                {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
        elif self.settings.ai_provider == "gemini":
            api_key = self._require_secret("GEMINI_API_KEY", self.settings.gemini_api_key)
            return (
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.ai_model}:generateContent?key={api_key}",
                {
                    "Content-Type": "application/json",
                },
            )
        elif self.settings.ai_provider == "anthropic":
            api_key = self._require_secret("ANTHROPIC_API_KEY", self.settings.anthropic_api_key)
            return (
                "https://api.anthropic.com/v1/messages",
                {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
            )
        elif self.settings.ai_provider == "openai":
            api_key = self._require_secret("OPENAI_API_KEY", self.settings.openai_api_key)
            return (
                "https://api.openai.com/v1/chat/completions",
                {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
        else:  # openrouter
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)),
        reraise=True
    )
    async def _call_llm(self, prompt: str) -> dict:
        """Make a request to the configured LLM provider with enhanced error handling."""
        url, headers = self._get_api_config()
        client = await self._get_client()

        if self.settings.ai_provider == "gemini":
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": "You are BugSense AI, an expert debugging assistant. Always respond with valid JSON only.\n\n" + prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 2000,
                    "responseMimeType": "application/json",
                },
            }
        elif self.settings.ai_provider == "anthropic":
            payload = {
                "model": self.settings.ai_model,
                "system": "You are BugSense AI, an expert debugging assistant. Always respond with valid JSON only.",
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            }
        else:
            payload = {
                "model": self.settings.ai_model,
                "messages": [
                    {"role": "system", "content": "You are BugSense AI, an expert debugging assistant. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            }

        logger.info(
            "llm_request",
            provider=self.settings.ai_provider,
            model=self.settings.ai_model,
            prompt_length=len(prompt)
        )

        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()

            if self.settings.ai_provider == "gemini":
                content = data["candidates"][0]["content"]["parts"][0]["text"]
            elif self.settings.ai_provider == "anthropic":
                content = data["content"][0]["text"]
            else:
                content = data["choices"][0]["message"]["content"]

            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            content = content.strip()
            content = content.replace("\n", " ")
            content = content.replace("\t", " ")

            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(
                    "json_parse_error",
                    error=str(e),
                    raw_content_length=len(content),
                )
                result = {
                    "language": "unknown",
                    "environment": "unknown",
                    "error_type": "ParsingError",
                    "explanation": "AI response format invalid",
                    "root_cause": "Generated output was not valid JSON",
                    "fix": "Retry analysis request",
                    "example_solution": ""
                }

            required_keys = ["language", "environment", "error_type", "explanation", "root_cause", "fix", "example_solution"]
            for key in required_keys:
                if key not in result:
                    result[key] = "Not available"
                elif isinstance(result[key], list):
                    if key == "fix":
                        result[key] = "\n".join(f"- {step}" for step in result[key])
                    else:
                        result[key] = " ".join(str(item) for item in result[key])

            logger.info("llm_response_parsed", error_type=result.get("error_type"))
            return result

        except httpx.TimeoutException as e:
            logger.error("llm_timeout_error", error=str(e), provider=self.settings.ai_provider)
            raise
        except httpx.NetworkError as e:
            logger.error("llm_network_error", error=str(e), provider=self.settings.ai_provider)
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "llm_http_error",
                error=str(e),
                status_code=e.response.status_code,
                provider=self.settings.ai_provider
            )
            raise
        except Exception as e:
            logger.error("llm_unexpected_error", error=str(e), provider=self.settings.ai_provider)
            raise

    async def analyze_error(self, input_text: str, language_hint: Optional[str] = None) -> dict:
        lang_ctx = f"The code is written in {language_hint}." if language_hint else "Detect the programming language from the error."
        prompt = ERROR_ANALYSIS_PROMPT.format(input_text=input_text, language_context=lang_ctx)
        return await self._call_llm(prompt)

    async def analyze_log(self, input_text: str, ci_platform: Optional[str] = None) -> dict:
        platform_ctx = f"This is from {ci_platform}." if ci_platform else "Detect the CI/CD platform from the log."
        prompt = LOG_ANALYSIS_PROMPT.format(input_text=input_text, platform_context=platform_ctx)
        return await self._call_llm(prompt)

    async def analyze_issue(self, input_text: str, repo_url: Optional[str] = None) -> dict:
        repo_ctx = f"Repository: {repo_url}" if repo_url else ""
        prompt = ISSUE_ANALYSIS_PROMPT.format(input_text=input_text, repo_context=repo_ctx)
        return await self._call_llm(prompt)

    async def fix_code(self, buggy_code: str, error_message: Optional[str] = None, language: Optional[str] = None) -> dict:
        lang_ctx = f"The code is written in {language}." if language else "Detect the programming language."
        err_ctx = f"Error message: {error_message}" if error_message else ""
        prompt = CODE_FIX_PROMPT.format(input_text=buggy_code, language_context=lang_ctx, error_context=err_ctx)
        return await self._call_llm(prompt)

    async def detect_language(self, text: str) -> Optional[str]:
        """Heuristic language detection from error/code text."""
        indicators = {
            "python": ["Traceback", "File \"", "ImportError", "IndentationError", ".py", "def ", "class "],
            "javascript": ["TypeError:", "ReferenceError:", "node_modules", ".js", "const ", "let ", "=>"],
            "typescript": [".ts", "interface ", "type ", "as ", ": string", ": number"],
            "java": ["Exception in thread", ".java", "at com.", "NullPointerException", "public class"],
            "rust": ["panic!", "thread 'main'", ".rs", "fn ", "let mut"],
            "go": ["goroutine", ".go", "panic:", "func ", "package main"],
            "csharp": [".cs", "System.", "NullReferenceException", "namespace ", "public void"],
            "ruby": [".rb", "NoMethodError", "undefined method", "gems/"],
            "php": [".php", "Fatal error:", "Uncaught", "->", "<?php"],
        }
        text_lower = text.lower()
        scores = {}
        for lang, keywords in indicators.items():
            scores[lang] = sum(1 for kw in keywords if kw.lower() in text_lower)
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else None

    async def ping(self):
        """Test AI provider connectivity with a simple request."""
        try:
            prompt = "Test connectivity. Respond with: {\"status\": \"ok\"}"
            url, headers = self._get_api_config()
            client = await self._get_client()

            if self.settings.ai_provider == "gemini":
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 10}
                }
            elif self.settings.ai_provider == "anthropic":
                payload = {
                    "model": self.settings.ai_model,
                    "system": "Respond with valid JSON only.",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 10
                }
            else:
                payload = {
                    "model": self.settings.ai_model,
                    "messages": [
                        {"role": "system", "content": "Respond with valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.0,
                    "max_tokens": 10
                }

            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("ai_provider_ping_failed", error=str(e))
            return False

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton
ai_service = AIService()
