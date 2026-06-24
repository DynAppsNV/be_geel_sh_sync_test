# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import threading
import time
from contextlib import contextmanager

_logger = logging.getLogger(__name__)
_logging_sessions = threading.local()


def estimate_tokens(content) -> int:
    """Estimate token count using OpenAI's heuristic of 1 token ~= 4 characters.

    :param content: Content to estimate tokens for (string, dict, list, or any object)
    :return: Estimated number of tokens
    """
    if isinstance(content, str):
        text = content
    elif isinstance(content, (dict, list)):
        text = json.dumps(content, separators=(",", ":"))
    else:
        text = str(content)

    return len(text) // 4


def get_ai_logging_session():
    """Get the current AI logging session if one exists.

    :return: Current session dict or None
    """
    try:
        return _logging_sessions.ai_logging_session
    except AttributeError:
        return None


@contextmanager
def ai_response_logging(llm_model: str):
    """Context manager for logging AI responses.

    Tracks API calls, tool executions, token usage, and timing information
    for a single AI response generation session.

    :param llm_model: Name of the LLM model being used
    """
    session = {
        "llm_model": llm_model,
        "start_time": time.perf_counter(),
        "api_calls": 0,
        "tool_calls": 0,
        "tokens_in": 0,
        "real_input_tokens": 0,
        "output_tokens": 0,
        "cached_tokens": 0,
        "api_time": 0.0,
        "tool_time": 0.0,
        "batch_count": 0,
        "current_batch_id": None,
    }

    _logger.debug("[AI Response] Starting generation for model '%s'", llm_model)
    _logging_sessions.ai_logging_session = session

    try:
        yield
    finally:
        if session["api_calls"]:
            duration = time.perf_counter() - session["start_time"]
            _logger.info(
                "[AI Summary] Total: %.2fs | API calls: %d (%.2fs) | Tools: %d (%.2fs) | "
                "Tokens: %d (in: %d, out: %d, cached: %d) | Batches: %d",
                duration,
                session["api_calls"],
                session["api_time"],
                session["tool_calls"],
                session["tool_time"],
                session["real_input_tokens"] + session["output_tokens"],
                session["real_input_tokens"],
                session["output_tokens"],
                session["cached_tokens"],
                session["batch_count"],
            )
        _logging_sessions.ai_logging_session = None


@contextmanager
def api_call_logging(messages, tools=None):
    """Context manager for logging API calls with automatic timing and response tracking.

    Tracks API request/response, estimates token usage, and handles timing even if
    exceptions occur during the API call.

    :param messages: Messages being sent to the API
    :param tools: Optional tools/functions available to the API
    :yields: Function to record response data, or None if no session
    """
    session = get_ai_logging_session()
    if not session:
        yield None
        return

    session["api_calls"] += 1
    call_id = session["api_calls"]
    tokens_in = estimate_tokens(messages)

    if tools:
        tool_data = {}
        for name, (desc, __, __, schema) in tools.items():
            tool_data[name] = {"description": desc, "schema": schema}
        tokens_in += estimate_tokens(tool_data)

    session["tokens_in"] += tokens_in
    _logger.debug("[AI API Call #%d] Sending request with estimated %d tokens", call_id, tokens_in)

    start_time = time.perf_counter()
    response_data = {"tool_calls": [], "real_input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}

    def record_response(tool_calls, response, request_token_usage):
        """Record the API response data.

        :param tool_calls: List of tool calls in the response
        :param response: The API response
        """
        response_data["tool_calls"] = tool_calls or []
        if request_token_usage:
            response_data["real_input_tokens"] = request_token_usage.get("input_tokens")
            response_data["output_tokens"] = request_token_usage.get("output_tokens")
            response_data["cached_tokens"] = request_token_usage.get("cached_tokens")

    try:
        yield record_response
    finally:
        duration = time.perf_counter() - start_time
        session["api_time"] += duration
        session["real_input_tokens"] += response_data["real_input_tokens"]
        session["output_tokens"] += response_data["output_tokens"]
        session["cached_tokens"] = response_data["cached_tokens"]  # should already by cumulative

        if response_data["tool_calls"]:
            num_tools = len(response_data["tool_calls"])
            is_batch = num_tools > 1
            if is_batch:
                session["batch_count"] += 1
                session["current_batch_id"] = session["batch_count"]
                _logger.debug(
                    "[AI API Call #%d - ⚡] Received Batch #%d, %d tool calls (%.2fs, %d tokens)",
                    call_id,
                    session["current_batch_id"],
                    num_tools,
                    duration,
                    response_data["output_tokens"],
                )
            else:
                session["current_batch_id"] = None
                _logger.debug(
                    "[AI API Call #%d - →] Received single tool call (%.2fs, %d tokens)",
                    call_id,
                    duration,
                    response_data["output_tokens"],
                )
        else:
            session["current_batch_id"] = None
            _logger.debug(
                "[AI API Call #%d] Completed (%.2fs, %d tokens)",
                call_id,
                duration,
                response_data["output_tokens"],
            )
