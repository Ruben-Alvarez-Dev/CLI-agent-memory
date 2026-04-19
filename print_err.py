import sys
import asyncio
from pathlib import Path
from CLI_agent_memory.domain.loop import LoopEngine
from CLI_agent_memory.config import LoopConfig
from tests.domain.test_loop import make_engine

async def main():
    engine = make_engine(Path("/tmp"))
    res = await engine.run("test", Path("/tmp"))
    print("STATUS:", res.status)
    print("ERROR:", res.error)

asyncio.run(main())
