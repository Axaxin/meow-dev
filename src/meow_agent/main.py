"""Main entry point for the MemU-Powered Interactive Agent."""

import argparse
import asyncio
import sys
from typing import NoReturn

from meow_agent.agents.main_agent import MainAgent
from meow_agent.agents.memu_bot import MemUBot
from meow_agent.config import settings
from meow_agent.event_bus import EventBus
from meow_agent.memu.client import MemUClient


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MemU-Powered Interactive Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default=settings.mode,
        help="Storage mode: 'local' for JSON storage, 'cloud' for MemU API",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=settings.verbose,
        help="Enable verbose output",
    )

    parser.add_argument(
        "--session-id",
        "-s",
        default="default_session",
        help="Session ID for the conversation",
    )

    parser.add_argument(
        "--proactive-interval",
        type=int,
        default=settings.proactive_interval,
        help="Interval for proactive tasks in seconds",
    )

    return parser.parse_args()


async def run_interactive(
    session_id: str,
    mode: str,
    verbose: bool,
    proactive_interval: int,
) -> None:
    """Run the interactive agent loop.

    Args:
        session_id: Session identifier.
        mode: Storage mode ('local' or 'cloud').
        verbose: Enable verbose output.
        proactive_interval: Interval for proactive tasks.
    """
    # Update settings
    if verbose:
        import meow_agent.config as config

        config.settings.verbose = True

    # Check API key configuration
    if not settings.dashscope_api_key or settings.dashscope_api_key == "your_dashscope_api_key_here":
        print("\n⚠️  警告: API Key 未配置！")
        print("   请在 .env 文件中设置 DASHSCOPE_API_KEY")
        print("   示例: DASHSCOPE_API_KEY=sk-xxxxx\n")
        print("   你可以继续使用，但 AI 回答功能将不可用。\n")

    # Initialize components
    print("Initializing MemU-Powered Agent...")

    use_cloud = mode == "cloud"
    memu_client = MemUClient(use_cloud=use_cloud)
    event_bus = EventBus()

    main_agent = MainAgent(memu_client, event_bus)
    memu_bot = MemUBot(memu_client, event_bus)

    # Start MemU Bot in background
    bot_task = asyncio.create_task(memu_bot.monitor_loop())

    # Start periodic tick task
    async def tick_loop():
        while True:
            await asyncio.sleep(proactive_interval)
            await event_bus.publish_tick(session_id)

    tick_task = asyncio.create_task(tick_loop())

    print(f"\n🤖 MemU-Powered Agent Ready!")
    print(f"   Mode: {mode}")
    print(f"   Session: {session_id}")
    print(f"   Type 'exit' or 'quit' to stop.\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "bye"]:
                print("\nGoodbye!")
                break

            if user_input.lower() == "clear":
                print("\n" * 50)
                continue

            # Handle the query
            try:
                response = await main_agent.handle(user_input, session_id)
                print(f"\nAgent: {response.content}\n")

                # Check for proactive suggestions
                if response.proactive_suggestions:
                    for suggestion in response.proactive_suggestions:
                        print(f"💡 Suggestion: {suggestion}\n")

            except Exception as e:
                if verbose:
                    import traceback

                    traceback.print_exc()
                else:
                    print(f"\nError: {e}\n")

    finally:
        # Wait for pending memory storage to complete
        if verbose:
            print("\nSaving memories...")
        await main_agent.wait_for_storage()

        # Cleanup
        memu_bot.stop()
        event_bus.stop()
        bot_task.cancel()
        tick_task.cancel()

        try:
            await asyncio.gather(bot_task, tick_task, return_exceptions=True)
        except asyncio.CancelledError:
            pass


def main() -> NoReturn:
    """Main entry point."""
    args = parse_args()

    try:
        asyncio.run(
            run_interactive(
                session_id=args.session_id,
                mode=args.mode,
                verbose=args.verbose,
                proactive_interval=args.proactive_interval,
            )
        )
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()