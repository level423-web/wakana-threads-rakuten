"""
楽天ウェブサービス IchibaItem Search API を使って、
おさくさんの属性キーワードにマッチする商品を検索・スコアリングする。

事前準備:
  pip install -r scripts/requirements.txt
  .env に RAKUTEN_APP_ID / RAKUTEN_AFFILIATE_ID / RAKUTEN_ACCESS_KEY / RAKUTEN_SITE_URL を設定

使い方:
  python scripts/search_rakuten.py --keyword "山崎実業 収納" --hits 20
  python scripts/search_rakuten.py --all   # config/product_keywords.yaml の全キーワードを一括実行
"""

import argparse
import json
import os
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("RAKUTEN_APP_ID")
AFFILIATE_ID = os.getenv("RAKUTEN_AFFILIATE_ID")
ACCESS_KEY = os.getenv("RAKUTEN_ACCESS_KEY")
SITE_URL = os.getenv("RAKUTEN_SITE_URL")
ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "product_keywords.yaml"
OUTPUT_DIR = ROOT / "output"

IMAGE_SIZE = "600x600"


def _resize_image_url(url: str, size: str = IMAGE_SIZE) -> str:
    """楽天の画像CDN(thumbnail.image.rakuten.co.jp)が提供する公式リサイズパラメータ
    (_ex=WxH)を大きいサイズに差し替える。取得元は楽天APIのURLのまま変わらない。"""
    return re.sub(r"_ex=\d+x\d+", f"_ex={size}", url)


def search_items(keyword: str, hits: int = 20, min_reviews: int = 5):
    params = {
        "applicationId": APP_ID,
        "accessKey": ACCESS_KEY,
        "affiliateId": AFFILIATE_ID,
        "keyword": keyword,
        "hits": hits,
        "sort": "-reviewAverage",
        "format": "json",
    }
    origin = f"{urlparse(SITE_URL).scheme}://{urlparse(SITE_URL).netloc}" if SITE_URL else None
    headers = {
        "Referer": SITE_URL,
        "Origin": origin,
    }
    res = requests.get(ENDPOINT, params=params, headers=headers, timeout=15)
    res.raise_for_status()
    data = res.json()

    items = []
    for entry in data.get("Items", []):
        item = entry["Item"]
        if item.get("reviewCount", 0) < min_reviews:
            continue
        items.append(
            {
                "name": item["itemName"],
                "price": item["itemPrice"],
                "review_avg": item["reviewAverage"],
                "review_count": item["reviewCount"],
                "url": item["affiliateUrl"] or item["itemUrl"],
                "shop": item["shopName"],
                "images": [
                    _resize_image_url(entry["imageUrl"])
                    for entry in item.get("mediumImageUrls", [])
                ],
            }
        )
    return items


def score_item(item: dict) -> float:
    import math

    review_weight = math.log10(item["review_count"] + 1)
    return round(item["review_avg"] * review_weight, 3)


def run(keyword: str, hits: int):
    items = search_items(keyword, hits=hits)
    for item in items:
        item["score"] = score_item(item)
    items.sort(key=lambda x: x["score"], reverse=True)
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", type=str, help="検索キーワード")
    parser.add_argument("--hits", type=int, default=20)
    parser.add_argument("--all", action="store_true", help="config内の全キーワードを実行")
    args = parser.parse_args()

    if not APP_ID:
        raise SystemExit("RAKUTEN_APP_ID が未設定です。.env を確認してください。")
    if not ACCESS_KEY:
        raise SystemExit("RAKUTEN_ACCESS_KEY が未設定です。.env を確認してください。")
    if not SITE_URL:
        raise SystemExit("RAKUTEN_SITE_URL が未設定です。.env を確認してください。")

    OUTPUT_DIR.mkdir(exist_ok=True)
    results = {}

    if args.all:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        for keyword in config.get("keywords", []):
            print(f"検索中: {keyword}")
            results[keyword] = run(keyword, args.hits)
            time.sleep(1)
    elif args.keyword:
        results[args.keyword] = run(args.keyword, args.hits)
    else:
        raise SystemExit("--keyword か --all を指定してください")

    out_path = OUTPUT_DIR / f"rakuten_candidates_{date.today():%Y%m%d}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"保存先: {out_path}")


if __name__ == "__main__":
    main()
