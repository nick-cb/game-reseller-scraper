from pathlib import Path
from random import randrange
from typing import Any, Optional, cast
from scrapy import Spider
from scrapy.http.request.json_request import json
from scrapy.utils.response import os
from typing_extensions import override
from scrapy.http import Response
from GameResellerScraper.items import GameItem
from GameResellerScraper.settings import IS_MOCK
from scrapy.utils.log import SpiderLoggerAdapter


class ItemParser:
    logger: SpiderLoggerAdapter
    scrapped_slugs = []

    def __init__(self, logger: Any, scrapped_slugs: list[str]):
        self.logger = logger
        self.scrapped_slugs = scrapped_slugs

    def parse(self, response: Response, **kwargs: Any) -> Optional[GameItem]:
        pass


class ItemParser1(ItemParser):
    @override
    def parse(self, response: Response, **kwargs: Any) -> Optional[GameItem]:
        url: str = response.url.split("/")[-1]
        queries = (
            self.extract_queries_from_file(url) if IS_MOCK else self.extract_queries(response, url)
        )
        if not queries:
            return None
        catalog_offer = self.extract_catalog_offer(queries=queries, url=url)
        product_home_config = self.extract_product_home_config(queries=queries, url=url)
        store_config = self.extract_store_config(
            queries=queries, url=url, current_game_title=catalog_offer["title"]
        )
        egs_platform = self.extract_egs_platform(queries=queries, url=url)
        product_result = self.extract_product_result(queries=queries, url=url)
        mapping_by_page_slug = self.extract_mapping_by_page_slug(queries=queries, url=url)
        item = GameItem(
            title=catalog_offer.get("title"),
            ref_id=catalog_offer.get("ref_id"),
            ref_namespace=catalog_offer.get("ref_namespace"),
            developer_display_name=catalog_offer.get("developer_display_name"),
            short_description=catalog_offer.get("short_description"),
            item_type=catalog_offer.get("game_type"),
            publisher_display_name=catalog_offer.get("publisher_display_name"),
            tags=catalog_offer.get("tags"),
            price=catalog_offer.get("price"),
            release_date=catalog_offer.get("release_date"),
            images=(catalog_offer.get("images") or [])
            + (product_home_config.get("images") or [])
            + (store_config.get("images") or []),
            long_description=product_home_config.get("long_description")
            or catalog_offer.get("long_description"),
            ref_slug=mapping_by_page_slug.get("ref_slug"),
            supported_audio=store_config.get("supported_audio"),
            supported_text=store_config.get("supported_text"),
            technical_requirements=store_config.get("technical_requirements"),
            theme=store_config.get("theme"),
            branding=egs_platform.get("branding"),
            critic_avg=egs_platform.get("critic_avg"),
            critic_rating=egs_platform.get("critic_rating"),
            critic_recommend_pct=egs_platform.get("critic_recommend_pct"),
            critic_reviews=egs_platform.get("critic_reviews"),
            polls=product_result.get("polls"),
            avg_rating=product_result.get("avg_rating"),
            base_item=response.request and response.request.cb_kwargs.get("item") or None,
            mappings=catalog_offer["mappings"],
            url=url,
        )

        return item

    def extract_catalog_offer(self, queries: dict[Any, Any], url: str):
        self.logger.info(f"parse {url} -> extract getCatalogOffer")
        catalog_offer_query = next(x for x in queries if x["queryKey"][0] == "getCatalogOffer")
        if not catalog_offer_query:
            self.logger.warning(f"parse {url} -> not found getCatalogOffer")
            return cast(dict[Any, Any], {})
        catalog_offer = cast(
            dict[Any, Any], get_nested(catalog_offer_query, "state.data.Catalog.catalogOffer")
        )

        item: dict[Any, Any] = {
            "title": catalog_offer.get("title"),
            "ref_id": catalog_offer.get("id"),
            "ref_namespace": catalog_offer.get("namespace"),
            "developer_display_name": catalog_offer.get("developerDisplayName"),
            "short_description": catalog_offer.get("description"),
            "game_type": catalog_offer.get("offerType"),
            "publisher_display_name": catalog_offer.get("publisherDisplayName"),
            "tags": list(
                map(
                    lambda x: {
                        "ref_id": x.get("id"),
                        "name": x.get("name"),
                        "group_name": x.get("groupName"),
                    },
                    catalog_offer.get("tags") or [],
                )
            ),
            "images": get_nested(catalog_offer, "keyImages") or [],
            "mappings": get_nested(catalog_offer, "catalogNs.mappings"),
            "price": {
                "discount_price": get_nested(catalog_offer, "price.totalPrice.discountPrice"),
                "origin_price": get_nested(catalog_offer, "price.totalPrice.originalPrice"),
                "discount": get_nested(catalog_offer, "price.totalPrice.discount"),
            },
            "long_description": get_nested(catalog_offer, "longDescription"),
            "release_date": get_nested(catalog_offer, "releaseDate"),
        }

        return item

    def extract_product_home_config(self, queries: dict[Any, Any], url: str):
        self.logger.info(f"parse {url} -> extract getProductHomeConfig")
        query = next((x for x in queries if x["queryKey"][0] == "getProductHomeConfig"), None)
        sandbox_config = cast(
            list[Any], get_nested(query, "state.data.Product.sandbox.configuration")
        )
        if not sandbox_config:
            self.logger.warning(f"parse {url} -> not found getProductHomeConfig")
            return {}

        item = {
            "long_description": get_nested(sandbox_config[1], "configs.longDescription"),
            "images": get_nested(sandbox_config[1], "configs.keyImages"),
        }

        return item

    def extract_store_config(self, queries: dict[Any, Any], url: str, current_game_title: str):
        self.logger.info(f"parse {url} -> extract getStoreConfig")
        query = next(x for x in queries if x["queryKey"][0] == "getStoreConfig")
        sandbox_config: list[Any] = (
            get_nested(query, "state.data.Product.sandbox.configuration") or []
        )
        if not sandbox_config:
            self.logger.warning(f"parse {url} -> not found getStoreConfig")
            return {}
        current_game_config = next(
            (
                x
                for x in sandbox_config
                if get_nested(x, "configs.productDisplayName") == current_game_title
            ),
            None,
        )

        item = {
            "supported_audio": get_nested(current_game_config, "configs.supportedAudio"),
            "supported_text": get_nested(current_game_config, "configs.supportedText"),
            "technical_requirements": get_nested(
                current_game_config, "configs.technicalRequirements"
            ),
            "theme": get_nested(current_game_config, "configs.theme"),
        }
        item["images"] = get_nested(current_game_config, "configs.keyImages") or []

        return item

    def extract_egs_platform(self, queries: dict[Any, Any], url: str):
        self.logger.info(f"parse {url} -> extract egs-platform(s)")
        item: dict[Any, Any] = {
            "branding": None,
            "critic_avg": None,
            "critic_rating": None,
            "critic_recommend_pct": None,
            "critic_reviews": None,
        }
        for query in queries:
            if query["queryKey"][0] == "egs-platform":
                self.logger.info(f"parse {url} -> found egs-platform")
                item["branding"] = get_nested(query, "state.data.branding") or item["branding"]

                criticReviews = get_nested(query, "state.data.criticReviews")
                if type(criticReviews) is not dict:
                    continue
                item["critic_avg"] = criticReviews.get("criticAverage") or item["critic_avg"]
                item["critic_rating"] = criticReviews.get("criticRating") or item["critic_rating"]
                item["critic_recommend_pct"] = (
                    criticReviews.get("recommendPercentage") or item["critic_recommend_pct"]
                )
                reviews = criticReviews.get("reviews")
                if not reviews or type(reviews) is not dict:
                    continue
                if not item["critic_reviews"]:
                    item["critic_reviews"] = []
                for review in reviews.get("data") or []:
                    _ = item["critic_reviews"].append(
                        {
                            "author": review.get("author"),
                            "body": review.get("body"),
                            "outlet": review.get("outlet"),
                            "score": {
                                "type": review.get("score").get("__typename"),
                                "earned_score": review.get("score").get("earnedScore"),
                                "total_score": review.get("score").get("totalScore"),
                            },
                            "url": review.get("url"),
                        }
                    )

        return item

    def extract_product_result(self, queries: dict[Any, Any], url: str):
        self.logger.info(f"parse {url} -> extract getProductResult")
        query = next((x for x in queries if x["queryKey"][0] == "getProductResult"), None)
        if not query:
            self.logger.warning(f"parse {url} -> not found getProductResult")
            return {}

        product_result = get_nested(query, "state.data.RatingsPolls.getProductResult") or {}
        poll_result: list[Any] = get_nested(product_result, "pollResult") or []
        if not poll_result:
            self.logger.warning(f"parse {url} -> not found pollResult")
            return {}

        polls: Any = map(
            lambda x: {
                "ref_id": x.get("id"),
                "ref_tag_id": x.get("tagId"),
                "ref_poll_definition_id": x.get("pollDefinitionId"),
                "text": get_nested(x, "localizations.text"),
                "emoji": get_nested(x, "localizations.emoji"),
                "result_emoji": get_nested(x, "localizations.resultEmoji"),
                "result_title": get_nested(x, "localizations.resultTitle"),
                "result_text": get_nested(x, "localizations.resultText"),
                "total": x.get("total"),
            },
            poll_result,
        )

        return {"polls": list(polls), "avg_rating": product_result.get("averageRating")}

    def extract_mapping_by_page_slug(self, queries: dict[Any, Any], url: str):
        self.logger.info(f"parse {url} -> extract getMappingByPageSlug")
        query = next(x for x in queries if x["queryKey"][0] == "getMappingByPageSlug")
        if not query:
            self.logger.warning(f"parse {url} -> not found getMappingByPageSlug")
            return {}

        return {"ref_slug": get_nested(query, "state.data.StorePageMapping.mapping.pageSlug")}

    def extract_queries(self, response: Response, url: str):
        script_contents = cast(Any, response.xpath("//script/text()").getall())
        self.scrapped_slugs.append(url)
        if url not in self.slugs:
            return {}

        self.logger.info(f"parse {url} -> extract __REACT_QUERY_INITIAL_QUERIES__")
        data = {}
        for script_content in script_contents:
            if "__REACT_QUERY_INITIAL_QUERIES__" in script_content:
                self.logger.info(
                    f"parse {url} -> saving __REACT_QUERY_INITIAL_QUERIES__ to {url}.json"
                )
                start_index = script_content.find("__REACT_QUERY_INITIAL_QUERIES__")
                next_space_index = script_content.find(" ", start_index) + 2
                next_line_index = script_content.find("\n", start_index) - 1
                data = json.loads(script_content[next_space_index:next_line_index])

        queries: dict[Any, Any] = data["queries"]

        return queries

    def extract_queries_from_file(self, url: str):
        filename = "GameResellerScraper/test/" + url + ".json"
        p = Path(os.getcwd()) / filename
        if not p.exists():
            self.logger.error(f"parse {url} -> building item -> not found file", p)
            return None

        text = p.read_text()
        data: dict[Any, Any] = json.loads(text)
        queries: dict[Any, Any] = data["queries"]

        return queries


def random_str():
    result = ""
    characters = "abcdefghijklmnopqrstuvwxyz0123456789"
    for _ in range(0, 5):
        rand = randrange(36)
        result = result + characters[rand]

    return result


def get_nested(d: Optional[dict[Any, Any]], keys: str, delimiter: str = "."):
    splited_keys = keys.split(delimiter)
    result: Any = d
    if not d:
        return None
    for key in splited_keys:
        result = result.get(key, None)
        if result is None:
            return None
    return result
