"""Read-only catalog inspection and bounded upstream checks; never prints secrets."""
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
import httpx

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "apps/api"))
from app.core.config import settings
from app.repositories.supabase_rest import rest_select


async def main():
    rows = await rest_select("/rest/v1/models", {"select":"slug,provider_model_id,enabled,input_price_per_million,output_price_per_million,discount_percent", "order":"slug.asc"})
    print("Current configured catalog:")
    for row in rows:
        print(row)
    targets = {
        "gpt-6-astra":"gpt-6-astra", "gpt-5.6-sol":"gpt-5.6-sol",
        "gpt-5.6-luna":"gpt-5.6-luna", "gpt-5.4":"gpt-5.4",
        "grok-4.6":"grok-4.6", "deepseek-v4-pro":"DeepSeek-V4-Pro",
        "deepseek-v4-flash":"DeepSeek-V4-Flash", "kimi-k2.7-code":"Kimi-K2.7-Code",
    }
    if len(sys.argv) > 1:
        targets = {slug: target for slug, target in targets.items() if slug in sys.argv[1:]}
    async with httpx.AsyncClient(timeout=90, follow_redirects=False) as client:
        for slug, target in targets.items():
            try:
                response = await client.post(settings.azure_endpoint.rstrip('/') + '/chat/completions',
                    headers={'api-key':settings.azure_api_key},
                    json={'model':target, 'messages':[{'role':'user','content':'Say OK.'}], 'max_completion_tokens':32})
                data = response.json()
                usable = response.status_code == 200 and bool(data.get('choices')) and isinstance(data.get('usage'),dict)
                print(slug, 'http_status=',response.status_code,'choices_and_usage=',usable)
            except (httpx.HTTPError, ValueError):
                print(slug,'unverified: transport or response error')


if __name__ == '__main__':
    asyncio.run(main())
