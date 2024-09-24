# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface

from itemadapter.adapter import ItemAdapter
from scrapy import Spider
from scrapy.http.request.json_request import json

from GameResellerScraper.items import GameItem


class GameItemPipeline:
    def process_item(self, item: GameItem, _: Spider):
        ref_slug = item.get("ref_slug")
        if ref_slug == None or type(ref_slug) != str:
            return
        line = json.dumps(ItemAdapter(item).asdict()) + "\n"
        with open(f"./GameResellerScraper/data/{ref_slug}.json", "w", encoding="utf-8") as f:
            __ = f.write(line)
        return item
