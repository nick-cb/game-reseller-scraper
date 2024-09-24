import json
from random import randrange
from typing import Any, cast, Optional
from typing_extensions import override

import scrapy

from scrapy.http import Response


class GameResellerScraper(scrapy.Spider):
    name = "game-item"
    host = "https://store.epicgames.com/en-US/p/"
    slugs = ["rain-world-4c860c"]
    scrapped_slugs = []

    @override
    def start_requests(self):
        for slug in self.slugs:
            yield scrapy.Request(f"{self.host}{slug}", meta={"playwright": True})

    @override
    def parse(self, response: Response, **_):
        script_contents = cast(Any, response.xpath("//script/text()").getall())
        url: str = response.url.split("/")[-1]
        self.scrapped_slugs.append(url)
        if url not in self.slugs:
            return

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
        catalog_offer = self.extract_catalog_offer(queries=queries, url=url)
        product_home_config = self.extract_product_home_config(queries=queries, url=url)
        store_config = self.extract_store_config(
            queries=queries, url=url, current_game_title=catalog_offer["title"]
        )
        egs_platform = self.extract_egs_platform(queries=queries, url=url)
        product_result = self.extract_product_result(queries=queries, url=url)
        item: dict[str, Any] = {
            "title": catalog_offer["title"],
            "ref_id": catalog_offer["ref_id"],
            "ref_namespace": catalog_offer["ref_namespace"],
            "developer_display_name": catalog_offer["developer_display_name"],
            "short_description": catalog_offer["short_description"],
            "game_type": catalog_offer["game_type"],
            "publisher_display_name": catalog_offer["publisher_display_name"],
            "tags": catalog_offer["tags"],
            "price": catalog_offer["price"],
            "images": catalog_offer["images"]
            + product_home_config["images"]
            + store_config["images"],
            "long_description": product_home_config["long_description"],
            "ref_slug": None,
            "supported_audio": store_config["supported_audio"],
            "supported_text": store_config["supported_text"],
            "technical_requirements": store_config["technical_requirements"],
            "theme": store_config["theme"],
            "branding": egs_platform["branding"],
            "critic_avg": egs_platform["critic_avg"],
            "critic_rating": egs_platform["critic_rating"],
            "critic_recommend_pct": egs_platform["critic_recommend_pct"],
            "critic_reviews": egs_platform["critic_reviews"],
            "polls": product_result["polls"],
        }

        yield item
        yield next_request(catalog_offer["mappings"], url)

    def next_request(self, mappings: list[Any], url: str):
        for mapping in mappings:
            if mapping["pageSlug"] and mapping["pageSlug"] not in self.scrapped_slugs:
                self.slugs.append(mapping["pageSlug"])
                self.logger.info(f"parse {url} -> following link {self.host}{mapping['pageSlug']}")
                headers = {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Alt-Used": "store.epicgames.com",
                    "Connection": "keep-alive",
                    "Cookie": "EPIC_LOCALE_COOKIE=en-US; __cf_bm=j3hez.1HwFAKhyOHIKsSs8uQoHk3WRb32g_ATgU_psE-1726660815-1.0.1.1-DQVFkMkfrzO2Kuil7mORLVYZecyaO2Ft6WbMvCNkECrQlZuk0anaSMZIDaTt953YZwxyumLh3XBuX9EBjZBPYg; cf_clearance=q9H8qPIKxf.EuNFtvPY7PQ6_SozfEWq9PTu1YtGKbNo-1726660816-1.2.1.1-n0UeIgE5ugJOBq77Hewti57OjTwVrNiZRudzK.Djl0vD0zSmvrnzICY1tffjt6z3gufRj5qZqYZVuu7sCFsY9Qa4g7C9lHWQS4pEqFx14sStnoAGY..NXyewlZUCoPk9kWHdDyG2wL2vJjBrpJDWA53iOqL1AoFKDlMLyNL.38dzzEJ29Ix.Mk_tCWe45WkWglYaygigZnlbSHWIVMV4NWSVnQvtt5dbKoWSvBKUG7TJ9KjfO3wf7hxofPYKfXyVbMVSCz8jh_UxUWDm.XUxPBEHZNpXTMfhjRTkz2D4ao_uKarjQeAOTmRV5K7aez7pRX8ceQOgiW5w8mRG_p6yyA; _epicSID=cab998b78e6244d881e0150515483fe6",
                    "Host": "store.epicgames.com",
                    "Priority": "u=0, i",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "TE": "trailers",
                    "Upgrade-Insecure-Requests": "1",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:130.0) Gecko/20100101 Firefox/130.0",
                }
                yield scrapy.Request(
                    url=f"{self.host}{mapping['pageSlug']}",
                    headers=headers,
                    callback=self.parse,
                    meta={"playwright": True},
                )

    def extract_catalog_offer(self, queries: dict[Any, Any], url: str):
        self.logger.info(f"parse {url} -> extract getCatalogOffer")
        catalog_offer_query = next(x for x in queries if x["queryKey"][0] == "getCatalogOffer")
        if not catalog_offer_query:
            self.logger.warning(f"parse {url} -> not found getCatalogOffer")
        catalog_offer = cast(
            dict[Any, Any], get_nested(catalog_offer_query, "state.data.Catalog.catalogOffer")
        )

        item = {
            "title": catalog_offer["title"],
            "ref_id": catalog_offer["ref_id"],
            "ref_namespace": catalog_offer["namespace"],
            "developer_display_name": catalog_offer["developerDisplayName"],
            "short_description": catalog_offer["description"],
            "game_type": catalog_offer["game_type"],
            "publisher_display_name": catalog_offer["publisherDisplayName"],
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
            "images": get_nested(catalog_offer, "state.data.Catalog.catalogOffer.keyImages") or [],
            "mappings": get_nested(catalog_offer, "catalogNs.mappings"),
        }

        return item

    def extract_product_home_config(self, queries: dict[Any, Any], url: str):
        self.logger.info(f"parse {url} -> extract getProductHomeConfig")
        query = next((x for x in queries if x["queryKey"][0] == "getProductHomeConfig"), None)
        sandbox_config: list[Any] = (
            get_nested(query, "state.data.Product.sandbox.configuration") or []
        )
        if not sandbox_config:
            self.logger.warning(f"parse {url} -> not found getProductHomeConfig")
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
        item: dict[Any, Any] = {}
        for query in queries:
            if query["queryKey"][0] == "egs-platform":
                self.logger.info(f"parse {url} -> found egs-platform")
                item["branding"] = get_nested(query, "state.data.branding") or item["branding"]

                criticReviews = cast(dict[Any, Any], get_nested(query, "state.data.criticReviews"))
                item["critic_avg"] = criticReviews.get("criticAverage") or item["critic_avg"]
                item["critic_rating"] = criticReviews.get("criticRating") or item["critic_rating"]
                item["critic_recommend_pct"] = (
                    criticReviews.get("recommendPercentage") or item["critic_recommend_pct"]
                )
                item["critic_reviews"] = criticReviews.get("reviews") or item["critic_reviews"]

        return item

    def extract_product_result(self, queries: dict[Any, Any], url: str):
        self.logger.info(f"parse {url} -> extract getProductResult")
        query = next((x for x in queries if x["queryKey"][0] == "getProductResult"), None)
        if not query:
            self.logger.warning(f"parse {url} -> not found getProductResult")
            return

        poll_result: list[Any] = (
            get_nested(query, "state.data.RatingsPolls.getProductResult.pollResult") or []
        )
        if not poll_result:
            self.logger.warning(f"parse {url} -> not found pollResult")
            return

        polls: Any = map(
            lambda x: {
                "ref_id": x.get("id"),
                "ref_tag_id": x.get("tagId"),
                "ref_poll_definition_id": x.get("pollDefinitionId"),
                "text": get_nested(x, "localizations.text"),
                "emoji": get_nested(x, "localizations.emoji"),
                "result_emoji": get_nested(x, "localizations.result_emoji"),
                "result_title": get_nested(x, "localizations.result_title"),
                "result_text": get_nested(x, "localizations.result_text"),
                "total": x.get("total"),
            },
            poll_result,
        )

        return list(polls)

    def extract_mapping_by_page_slug(self, queries: dict[Any, Any], url: str):
        self.logger.info(f"parse {url} -> extract getMappingByPageSlug")
        query = next(x for x in queries if x["queryKey"][0] == "getMappingByPageSlug")
        if not query:
            self.logger.warning(f"parse {url} -> not found getMappingByPageSlug")

        return {"ref_slug": get_nested(query, "state.data.StorePageMapping.mapping.pageSlug")}


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


""" launcherVersion
    - Nothing important, just some metadata
"""

""" getMappingByPageSlug
    - Some information about the product
        - sandboxId: c8b495f1a9a34972ba0b0c46e8afec31
        - productId: da2d8e4b946b4b50b1ad818727469873
        - mappings.offerId: 1efa9febbd9744caab24276d9c273862
        - mappings.namespace: c8b495f1a9a34972ba0b0c46e8afec31
        - mappings.pageSlug
"""

""" getCatalogOffer (multiple)
    - Original Game
        - title
        - developerDisplayName
        - description
        - longDescription: nullable
        - keyImages
        - seller
        - productSlug: nullable
        - urlSlug: A hash
        - tags
        - item?
        - catalogNs.mappings: Dlc, addons, other version
        - price
        - mappings.pageSlug
    
    - Addons
        - title
        - developerDisplayName
        - description
        - keyImages
        - longDescription
        - seller
        - productSlug: nullable
        - publisherDisplayName
        - urlSlug
        - tags
        - items?
        - categories
        - price
        - catalogNs.mappings
"""

""" getStoreConfig
    - Includes several important information:
        - banner: nullable
        - developerDisplayName
        - keyImages: (ProductLogo)
        - productDisplayName
        - publisherDisplayName
        - shortDescription
        - supportedAudio
        - supportedText
        - tags
        - technicalRequirements
        - theme
"""

""" getRelatedOfferIdsByCategory (multiple)
    - Nothing important
"""

""" egs-platform: Multiple
    - ageRating
    
    - branding (colors)
    - developers
    - mapping.slug
    - media (portrait, landscape, logo)
    - publishers
    - shortDescription
    - supportedModules (whether this game support addons, editions, ...)
    - tags (organized)
    
    - criticReviews
"""

""" Achievement
    - Nothing important
"""

""" getCatalogNamespace
    - Product relates (addons, editions...)
"""

""" getProductResult
    - averageRating
    - pollResult
"""

""" getProductHomeConfig
    - keyImages (heroCarousel)
    - longDescriptions
"""

""" getVideoById
    - Videos
"""

""" getProductInBundles?
"""

""" abafd6e0aa80535c43676f533f0283c7f5214a59e9fae6ebfb37bed1b1bb2e9b (Hash that appear in queryKey - multiples)
    - List of item include current game and relate contents
        - title
        - developerDisplayName
        - description
        - offerType
        - keyImages
        - longDescription: nullable
        - seller
        - productSlug: nullable
        - publisherDisplayName
        - tags
        - categories
        - catalogNs.mapping.pageSlug
        - price
"""

"""
* Using getCatalogOffer.state.data.Catalog.catalogOffer.catalogNs.mappings to iterate all relate contents,
* Using egs-platform.state.data.supportedModules to check if the game has addon or edition
{
    title: getCatalogOffer.state.data.Catalog.catalogOffer.title,
    ref_id: getCatalogOffer.state.data.Catalog.catalogOffer.id,
    ref_namespace: getCatalogOffer.state.data.Catalog.catalogOffer.namespace,
    developer_display_name: getCatalogOffer.state.data.Catalog.catalogOffer.developerDisplayName,
    short_description: getCatalogOffer.state.data.Catalog.catalogOffer.description,
    long_description: getProductHomeConfig.state.data.Product.sandbox.configuration[1].configs.longDescription,
    images: [
        - getProductHomeConfig.state.data.Product.sandbox.configuration[1].configs.keyImages
        - getCatalogOffer.state.data.Catalog.catalogOffer.keyImages
        - getStoreConfig.state.data.Product.sandbox.configuration['configs.productDisplayName=title'].keyImages
        - egs-platform.state.data.media
    ]
    game_type: getCatalogOffer.state.data.Catalog.catalogOffer.offerType,
    publisher_display_name: getCatalogOffer.state.data.Catalog.catalogOffer.publisherDisplayName,
    tags: getCatalogOffer.state.data.Catalog.catalogOffer.tags,
    page_slug: ?
    price: getCatalogOffer.state.data.Catalog.catalogOffer.price,
    ref_slug:
        - getMappingByPageSlug.state.data.StorePageMapping.mapping.pageSlug
        - getCatalogOffer.state.data.Catalog.catalogOffer.catalogNs.mappings['pageType=productHome'].pageSlug
        - egs-platform.state.data.mapping.slug
        - getCatalogNamespace.state.data.Catalog.catalogNs.mappings['pageType=productHome'].pageSlug
    supported_audio: getStoreConfig.state.data.Product.sandbox.configuration['configs.productDisplayName=title'].supportedAudio,
    supported_text: getStoreConfig.state.data.Product.sandbox.configuration['configs.productDisplayName=title'].supportedText,
    technicalRequirements: getStoreConfig.state.data.Product.sandbox.configuration['configs.productDisplayName=title'].technicalRequirements
    theme: getStoreConfig.state.data.Product.sandbox.configuration['configs.productDisplayName=title'].theme
    branding: egs-platform.state.data.branding
    critic_avg: egs-platform.state.data.criticReviews.criticAverage
    critic_rating: egs-platform.state.data.criticReviews.criticRating
    critic_recommend_pct: egs-platform.state.data.criticReviews.recommendPercentage
    critic_reviews: egs-platform.state.data.criticReviews.reviews
    polls: getProductResult.state.data.RatingsPolls.getProductResult.pollResult
    videos: getVideoById.state.data.Video.fetchVideoByLocale
}
"""
