import httpx
import io

async def get_qr_code(data: str, size: int) -> io.BytesIO:
    url = "https://api.qrserver.com/v1/create-qr-code/"
    params = {"data": data, "size": size}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        
        if response.status_code == 200:
            image_bytes = io.BytesIO(response.content)
            image_bytes.seek(0)
            return image_bytes
        else:
            print("Error:", response.status_code, response.text)
            return None

