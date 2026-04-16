import asyncio
import sys
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
import mcp.types as types

async def bridge():
    url = "https://taskmaster-mcp-2.onrender.com/sse"
    
    # Connect to the remote SSE server
    async with sse_client(url) as streams:
        read_stream, write_stream = streams
        
        # Bridge local stdio to the remote streams
        # 1. Read from local stdin and pipe to remote write_stream
        # 2. Read from remote read_stream and pipe to local stdout
        
        async def pipe_in():
            while True:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line: break
                await write_stream.send(line)

        async def pipe_out():
            async for message in read_stream:
                if isinstance(message, Exception): continue
                # MCP messages are usually JSON strings or objects
                if not isinstance(message, str):
                    import json
                    message = json.dumps(message)
                sys.stdout.write(message + "\n")
                sys.stdout.flush()

        await asyncio.gather(pipe_in(), pipe_out())

if __name__ == "__main__":
    try:
        asyncio.run(bridge())
    except KeyboardInterrupt:
        pass
