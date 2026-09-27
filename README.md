# FastMCP HTTP starter

Mẫu dự án MCP bằng Python với **Streamable HTTP**. FastMCP cung cấp giao thức MCP; Uvicorn chạy ứng dụng ASGI. Client kết nối tới `http://127.0.0.1:8000/mcp`, còn `GET /health` dùng để kiểm tra tiến trình HTTP.

## Cấu trúc

```text
src/mcp_starter/
├── app.py             # ASGI app và endpoint /mcp
├── __main__.py        # Chạy HTTP, đọc MCP_HOST và MCP_PORT
├── config.py          # Cấu hình cổng và địa chỉ lắng nghe
├── server.py          # Tạo FastMCP, đăng ký thành phần, /health
├── tools/             # Các hàm mà MCP client gọi
├── resources/         # Dữ liệu mà MCP client đọc
└── prompts/           # Mẫu prompt cho MCP client
tests/                 # Kiểm thử giao thức và health endpoint
Dockerfile             # Image chạy bằng user không có quyền root
compose.yaml          # Chạy container trên localhost
pyproject.toml         # Metadata và dependency của package
.github/workflows/ci.yml # CI chạy kiểm thử khi push hoặc mở PR
```

## Chạy tại máy

Yêu cầu Python 3.10 trở lên. Tại thư mục dự án:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m mcp_starter
```

Trên Windows, kích hoạt môi trường bằng `.venv\Scripts\activate`. Mặc định server chỉ lắng nghe trên `127.0.0.1:8000`. Nếu muốn đổi địa chỉ hoặc cổng, đặt `MCP_HOST` và `MCP_PORT` trong môi trường trước khi chạy. File `.env.example` liệt kê các biến; Python không tự nạp file `.env`.

Để chạy kiểm thử:

```bash
pytest
```

## Chạy bằng Docker

```bash
docker compose up --build -d
docker compose ps
```

Compose chỉ xuất cổng trên localhost. Kiểm tra HTTP:

```bash
curl http://127.0.0.1:8000/health
```

Kết quả mong đợi là `{"status":"ok"}`. `/mcp` là endpoint **MCP Streamable HTTP**, cần MCP client để gửi yêu cầu giao thức; mở bằng trình duyệt hoặc `curl` GET thông thường không phải phép thử tool.

## Kết nối MCP client

Cấu hình HTTP URL của client là `http://127.0.0.1:8000/mcp`. Có thể thử bằng FastMCP Client trong terminal khác:

```python
import asyncio
from fastmcp import Client


async def main():
    async with Client("http://127.0.0.1:8000/mcp") as client:
        result = await client.call_tool("greet", {"name": "An"})
        print(result.data)  # Xin chào, An!


asyncio.run(main())
```

Mẫu còn có resource `info://server` và prompt `welcome(name)` để minh họa đủ ba thành phần MCP. Thêm nghiệp vụ vào thư mục tương ứng và đăng ký trong `register_tools`, `register_resources` hoặc `register_prompts`.

## Khi triển khai ra Internet

Mẫu này chưa cấu hình xác thực. Trước khi mở cổng ra mạng công cộng, thêm cơ chế xác thực của FastMCP hoặc đặt phía sau gateway có xác thực và TLS. Nếu chạy nhiều worker hoặc nhiều instance, ứng dụng đã bật `stateless_http=True`; các tool cần trạng thái lâu dài phải dùng kho dữ liệu chung thay vì bộ nhớ tiến trình.

Tham khảo: [FastMCP HTTP deployment](https://gofastmcp.com/deployment/http), [FastMCP server components](https://gofastmcp.com/servers/server), [FastMCP testing](https://gofastmcp.com/servers/testing).
