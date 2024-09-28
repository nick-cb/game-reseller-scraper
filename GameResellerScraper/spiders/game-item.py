from typing import Any
from typing_extensions import override

import scrapy

from scrapy.http import Response

from GameResellerScraper.items import GameItem
from GameResellerScraper.parser import ItemParser1


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
    def parse(self, response: Response, **kwargs: Any):
        parser = ItemParser1(self.logger, self.scrapped_slugs)
        item = parser.parse(response)

        yield item
        if item:
            yield from self.next_request(item)

    def next_request(self, item: GameItem):
        url = item.get("url")
        for mapping in item.get("mappings") or []:
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
                cb_kwargs: dict[Any, Any] = {"item": item}
                yield scrapy.Request(
                    url=f"{self.host}{mapping['pageSlug']}",
                    headers=headers,
                    callback=self.parse,
                    meta={"playwright": True},
                    cb_kwargs=cb_kwargs,
                )


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
        - releaseDate
    
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
