import asyncio
import websockets

async def handler(websocket):
    async for message in websocket:
        print(f"收到客户端消息: {message}")
        greeting = f"你好，客户端！你发送了: {message}"
        await websocket.send(greeting)


async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("WebSocket 服务器启动，监听 localhost:8765")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
