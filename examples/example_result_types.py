"""
Example demonstrating standardized Result types (TICKET-CODE-02)

This example shows how to use Result[T], ParserResult, and AdapterResult
to standardize return values across the codebase.
"""

from janus.runtime.core.contracts import AdapterResult, ErrorType, Intent, ParserResult, Result


def example_generic_result():
    """Example using Result[T] for generic operations"""
    print("=" * 60)
    print("Example 1: Generic Result[T]")
    print("=" * 60)

    # Success case
    def process_data(data: str) -> Result[dict]:
        if not data:
            return Result.err("Empty data", error_type=ErrorType.VALIDATION_ERROR)

        processed = {"data": data.upper(), "length": len(data)}
        return Result.ok(processed, message="Data processed successfully")

    # Test success
    result = process_data("hello")
    if result.is_ok():
        print(f"✅ Success: {result.message}")
        print(f"   Value: {result.value}")
        print(f"   Unwrapped: {result.unwrap()}")

    # Test failure
    result = process_data("")
    if result.is_err():
        print(f"❌ Error: {result.error}")
        print(f"   Type: {result.error_type.value}")
        print(f"   With default: {result.unwrap_or({'default': 'value'})}")

    print()


def example_parser_result():
    """Example using ParserResult for command parsing"""
    print("=" * 60)
    print("Example 2: ParserResult for Parsers")
    print("=" * 60)

    def parse_command(text: str) -> ParserResult:
        """Simple command parser returning ParserResult"""
        text = text.strip().lower()

        if not text:
            return ParserResult.from_error(
                "Empty command", error_type=ErrorType.PARSE_ERROR, raw_command=text
            )

        if "open" in text and "chrome" in text:
            intent = Intent(
                action="open_app", confidence=0.95, parameters={"app": "Chrome"}, raw_command=text
            )
            return ParserResult.from_intent(intent, raw_command=text)

        elif "open" in text:
            # Ambiguous - could be multiple apps
            intent1 = Intent(action="open_app", confidence=0.5, parameters={"app": "Chrome"})
            intent2 = Intent(action="open_app", confidence=0.5, parameters={"app": "Safari"})
            return ParserResult.from_ambiguous(
                [intent1, intent2], reason="Multiple apps match 'open'", raw_command=text
            )

        else:
            return ParserResult.from_error(
                f"Unknown command: {text}", error_type=ErrorType.UNKNOWN_COMMAND, raw_command=text
            )

    # Test successful parsing
    result = parse_command("open chrome")
    if result.ok():
        intent = result.get_intent()
        print(f"✅ Parsed successfully")
        print(f"   Action: {intent.action}")
        print(f"   Confidence: {intent.confidence}")
        print(f"   Parameters: {intent.parameters}")

    # Test ambiguous parsing
    result = parse_command("open")
    if result.is_ambiguous:
        print(f"⚠️  Ambiguous parse")
        print(f"   Reason: {result.ambiguity_reason}")
        print(f"   Candidates: {[i.parameters for i in result.get_intents()]}")

    # Test parse error
    result = parse_command("xyz")
    if not result.ok():
        print(f"❌ Parse failed")
        print(f"   Error: {result.error}")
        print(f"   Type: {result.error_type.value}")

    print()


def example_adapter_result():
    """Example using AdapterResult for application adapters"""
    print("=" * 60)
    print("Example 3: AdapterResult for Adapters")
    print("=" * 60)

    def open_url(url: str, retry_count: int = 0) -> AdapterResult:
        """Simulate opening a URL"""
        import time

        start = time.time()

        if not url:
            return AdapterResult.from_failure(
                "open_url",
                "URL is required",
                error_type=ErrorType.VALIDATION_ERROR,
                retryable=False,
            )

        # Simulate work
        time.sleep(0.01)
        duration_ms = int((time.time() - start) * 1000)

        if "invalid" in url:
            return AdapterResult.from_failure(
                "open_url",
                f"Failed to open {url}",
                error_type=ErrorType.EXECUTION_ERROR,
                retryable=True,
                duration_ms=duration_ms,
                retry_count=retry_count,
            )

        return AdapterResult.from_success(
            "open_url",
            message=f"Successfully opened {url}",
            data={"url": url, "title": "Example Page"},
            duration_ms=duration_ms,
        )

    # Test success
    result = open_url("https://github.com")
    if result.ok():
        print(f"✅ Action succeeded")
        print(f"   Action: {result.action}")
        print(f"   Message: {result.message}")
        print(f"   Data: {result.data}")
        print(f"   Duration: {result.duration_ms}ms")

    # Test retryable failure
    result = open_url("https://invalid.com")
    if not result.ok():
        print(f"❌ Action failed")
        print(f"   Error: {result.error}")
        print(f"   Retryable: {result.is_retryable}")
        if result.is_retryable:
            print(f"   → Can retry this operation")

    # Test backward compatibility
    print("\n📦 Backward Compatibility:")
    result = open_url("https://example.com")
    legacy_dict = result.to_dict()
    print(f"   Legacy dict: {legacy_dict}")
    print(f"   Status: {legacy_dict['status']}")
    print(f"   execution_time: {legacy_dict.get('execution_time')}s")

    # From legacy dict
    new_result = AdapterResult.from_dict(legacy_dict)
    print(f"   Converted back: ok={new_result.ok()}, action={new_result.action}")

    print()


def example_complete_flow():
    """Example showing complete parse → execute → result flow"""
    print("=" * 60)
    print("Example 4: Complete Parse → Execute → Result Flow")
    print("=" * 60)

    # 1. Parse command
    def simple_parse(text: str) -> ParserResult:
        if "github" in text.lower():
            intent = Intent(
                action="open_url",
                confidence=0.9,
                parameters={"url": "https://github.com"},
                raw_command=text,
            )
            return ParserResult.from_intent(intent, raw_command=text)
        return ParserResult.from_error("Unknown command")

    # 2. Execute if parse succeeds
    def execute_intent(intent: Intent) -> AdapterResult:
        return AdapterResult.from_success(intent.action, data=intent.parameters, duration_ms=100)

    # 3. Complete flow
    command = "open github"
    print(f"Command: '{command}'")

    # Parse
    parse_result = simple_parse(command)
    if not parse_result.ok():
        print(f"❌ Parse failed: {parse_result.error}")
        return

    print(f"✅ Parse succeeded: {parse_result.get_intent().action}")

    # Execute
    intent = parse_result.get_intent()
    exec_result = execute_intent(intent)

    if exec_result.ok():
        print(f"✅ Execution succeeded")
        print(f"   Action: {exec_result.action}")
        print(f"   Duration: {exec_result.duration_ms}ms")
        print(f"   Data: {exec_result.data}")
    else:
        print(f"❌ Execution failed: {exec_result.error}")

    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print(" Standardized Result Types - Examples (TICKET-CODE-02)")
    print("=" * 60 + "\n")

    example_generic_result()
    example_parser_result()
    example_adapter_result()
    example_complete_flow()

    print("=" * 60)
    print("✨ All examples completed!")
    print("=" * 60)
    print("\nFor more details, see:")
    print("  - RESULT_TYPES_MIGRATION.md")
    print("  - tests/test_result_types.py")
    print()


if __name__ == "__main__":
    main()
