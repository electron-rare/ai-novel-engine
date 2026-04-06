from __future__ import annotations

import json
import re


def strip_code_fence(text: str) -> str:
    payload = text.strip()
    if not payload.startswith("```"):
        return payload
    lines = payload.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return payload


def remove_trailing_commas(payload: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", payload)


def extract_json_object(payload: str) -> str | None:
    start = payload.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(payload)):
        char = payload[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return payload[start : index + 1]
    return payload[start:]


def close_json_delimiters(payload: str) -> str:
    stack: list[str] = []
    in_string = False
    escaped = False
    output: list[str] = []

    for char in payload:
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            output.append(char)
        elif char == "{":
            stack.append("}")
            output.append(char)
        elif char == "[":
            stack.append("]")
            output.append(char)
        elif char in {"}", "]"}:
            if stack and stack[-1] == char:
                stack.pop()
                output.append(char)
            elif char in stack:
                while stack and stack[-1] != char:
                    output.append(stack.pop())
                if stack:
                    stack.pop()
                    output.append(char)
        else:
            output.append(char)

    repaired = "".join(output).rstrip()
    if repaired.endswith(","):
        repaired = repaired[:-1].rstrip()
    if in_string:
        repaired += '"'
    return repaired + "".join(reversed(stack))


def json_candidates(text: str) -> list[str]:
    payload = strip_code_fence(text)
    candidates = [payload]

    extracted = extract_json_object(payload)
    if extracted and extracted not in candidates:
        candidates.append(extracted)

    repaired: list[str] = []
    for candidate in list(candidates):
        trimmed = remove_trailing_commas(candidate)
        if trimmed not in candidates and trimmed not in repaired:
            repaired.append(trimmed)
        closed = close_json_delimiters(trimmed)
        if closed not in candidates and closed not in repaired:
            repaired.append(closed)
    candidates.extend(repaired)
    return candidates


def parse_json_object(text: str) -> dict[str, object]:
    last_error: Exception | None = None
    for candidate in json_candidates(text):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if not isinstance(data, dict):
            raise ValueError("La réponse JSON attendue doit être un objet.")
        return data
    raise ValueError(str(last_error) if last_error else "Réponse JSON illisible.")


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def record_list(value: object, required_key: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        record = {str(key): str(val).strip() for key, val in item.items() if str(val).strip()}
        if record.get(required_key):
            normalized.append(record)
    return normalized
