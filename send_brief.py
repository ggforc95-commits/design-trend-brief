"""Weekly design research and WeCom delivery. Python standard library only."""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, parse_qs
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

def post_json(url, body, headers=None, timeout=60):
    request = Request(url, data=json.dumps(body).encode("utf-8"),
                      headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"Remote service returned HTTP {error.code}; check credentials and service availability.") from None
    except (URLError, TimeoutError):
        raise RuntimeError("Remote service connection failed; no automatic retry to avoid duplicate sends.") from None

def chunks(text, limit=3500):
    """Split by UTF-8 bytes, preferring whole lines."""
    result, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(line.encode("utf-8")) > limit:
            if current:
                result.append(current)
                current = ""
            for char in line:
                if len((current + char).encode("utf-8")) > limit:
                    result.append(current)
                    current = ""
                current += char
        elif len((current + line).encode("utf-8")) > limit:
            result.append(current)
            current = line
        else:
            current += line
    if current:
        result.append(current)
    return result

def extract_text(response):
    if response.get("status") != "completed":
        raise RuntimeError("Research did not complete; nothing sent.")
    if not any(item.get("type") == "web_search_call" for item in response.get("output", [])):
        raise RuntimeError("Research did not use web search; nothing sent.")
    texts, sources = [], []
    for item in response.get("output", []):
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                texts.append(part["text"])
                for annotation in part.get("annotations", []):
                    if annotation.get("type") == "url_citation":
                        url = annotation.get("url", "")
                        if url.startswith("https://") and url not in sources:
                            sources.append(url)
    text = "\n".join(texts).strip()
    if not text:
        raise RuntimeError("Research returned no text; nothing sent.")
    if not sources:
        raise RuntimeError("Research returned no verifiable citations; nothing sent.")
    return text + "\n\n来源链接\n" + "\n".join(sources)

def validate_webhook(url):
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != "qyapi.weixin.qq.com"
            or parts.path != "/cgi-bin/webhook/send" or not parse_qs(parts.query).get("key")):
        raise RuntimeError("WECOM_WEBHOOK_URL must be an official WeCom group webhook.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-message", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    webhook = os.environ.get("WECOM_WEBHOOK_URL", "")
    if not args.dry_run:
        validate_webhook(webhook)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    if args.test_message:
        text = "设计趋势助手已连接。每周一北京时间上午9点左右，将推送视觉设计趋势简报。"
    else:
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("Missing OPENAI_API_KEY in repository Secrets.")
        start = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
        end = now.strftime("%Y-%m-%d %H:%M")
        brief = Path("brief.md").read_text(encoding="utf-8")
        response = post_json(
            "https://api.openai.com/v1/responses",
            {"model": os.environ.get("OPENAI_MODEL") or "gpt-4.1",
             "tools": [{"type": "web_search"}], "tool_choice": "required",
             "store": False, "max_output_tokens": 5000,
             "input": f"本期时间范围：{start} 至 {end}，北京时间。\n\n{brief}"},
            {"Authorization": f"Bearer {key}"}, timeout=240)
        text = f"视觉设计趋势简报｜{now:%Y-%m-%d}\n\n" + extract_text(response)
    Path("output").mkdir(exist_ok=True)
    Path("output/brief.txt").write_text(text, encoding="utf-8")
    if args.dry_run:
        print("Brief generated and saved; delivery skipped.")
        return
    pieces = chunks(text)
    for index, piece in enumerate(pieces, 1):
        prefix = f"【设计趋势简报 {index}/{len(pieces)}】\n" if len(pieces) > 1 else ""
        response = post_json(webhook, {"msgtype": "text", "text": {"content": prefix + piece}})
        if response.get("errcode") != 0:
            raise RuntimeError(f"WeCom rejected message {index}/{len(pieces)} (code {response.get('errcode')}); check webhook. Earlier parts may have been delivered.")
    print(f"Delivered {len(pieces)} message(s).")

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Do not print request URLs, headers, response bodies or credentials.
        print(str(error) if isinstance(error, RuntimeError) else "Unexpected failure; check configuration.", file=sys.stderr)
        sys.exit(1)
