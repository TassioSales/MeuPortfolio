#!/usr/bin/env python
"""
Simple script to validate a Google Gemini API key without pytest or Streamlit.
Usage:
  python scripts/test_gemini_key.py --key YOUR_API_KEY
or set environment variable GEMINI_API_KEY and run without --key.
"""

import argparse
import os
import sys
import time

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: google-genai client is not installed. Install with: pip install google-genai", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Google Gemini API key with a simple request.")
    parser.add_argument("--key", dest="api_key", default=None, help="Google Gemini API key. If omitted, reads GEMINI_API_KEY from environment.")
    parser.add_argument("--model", dest="model", default="gemini-2.5-flash", help="Model name to test (default: gemini-2.5-flash)")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: No API key provided. Use --key or set GEMINI_API_KEY env var.", file=sys.stderr)
        return 2

    try:
        # Instantiate the new GenAI client
        client = genai.Client(api_key=api_key)
        prompt = "Você é um consultor de tecnologia preparando um resumo para um CEO. Explique, em três tópicos curtos e diretos, como a IA funciona do ponto de vista prático para uma empresa. Foque no 'o quê' ela faz (ex: identifica padrões, faz previsões) e no 'o que' ela precisa (dados), em vez de jargões técnicos."
        print(f"Testing model '{args.model}'...", flush=True)
        start = time.time()
        response = client.models.generate_content(
            model=args.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
        )
        duration = time.time() - start

        text = getattr(response, "text", "").strip()
        usage = getattr(response, "usage_metadata", None)
        total_tokens = getattr(usage, "total_token_count", None) if usage else None

        print("Success!\n--- Result ---")
        print(f"Text: {text!r}")
        if total_tokens is not None:
            print(f"Total tokens used: {total_tokens}")
        print(f"Duration: {duration:.2f}s")
        return 0

    except Exception as e:
        print("Failure!\n--- Error ---", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
