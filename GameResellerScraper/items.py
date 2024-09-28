# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class GameItem(scrapy.Item):
    title = scrapy.Field()
    ref_id = scrapy.Field()
    ref_namespace = scrapy.Field()
    developer_display_name = scrapy.Field()
    short_description = scrapy.Field()
    item_type = scrapy.Field()
    publisher_display_name = scrapy.Field()
    tags = scrapy.Field()
    price = scrapy.Field()
    release_date = scrapy.Field()
    images = scrapy.Field()
    long_description = scrapy.Field()
    ref_slug = scrapy.Field()
    supported_audio = scrapy.Field()
    supported_text = scrapy.Field()
    technical_requirements = scrapy.Field()
    theme = scrapy.Field()
    branding = scrapy.Field()
    avg_rating = scrapy.Field()
    critic_avg = scrapy.Field()
    critic_rating = scrapy.Field()
    critic_recommend_pct = scrapy.Field()
    critic_reviews = scrapy.Field()
    polls = scrapy.Field()
    base_item = scrapy.Field()
    mappings = scrapy.Field()
    url = scrapy.Field()
