import json
import os
from random import randrange

import scrapy
from pathlib import Path

class GameResellerScraper(scrapy.Spider):
    name = "game-item"
    host = "https://store.epicgames.com/en-US/p/"
    slugs = ["rain-world-4c860c"]

    def start_requests(self):
        for slug in self.slugs:
            yield scrapy.Request(f"{self.host}{slug}", meta={"playwright": True})

    def parse(self, response, **kwargs):
        script_contents = response.xpath('//script/text()').getall()
        url = response.url.split("/")[-1]

        with open(f'{url}.json', 'w', encoding='utf-8') as f:
            for script_content in script_contents:
                if "__REACT_QUERY_INITIAL_QUERIES__" in script_content:
                    start_index = script_content.find("__REACT_QUERY_INITIAL_QUERIES__")
                    next_space_index = script_content.find(' ', start_index) + 2
                    next_line_index = script_content.find('\n', start_index) - 1
                    f.write(script_content[next_space_index:next_line_index] + '\n\n')

        filename = url + '.json'
        p = Path(os.getcwd()) / filename
        if not p.exists():
            print("NOT EXIST", p)
            return
        text = p.read_text()
        data = json.loads(text)
        queries = data['queries']
        item = {
            'title': None,
            'ref_id': None,
            'ref_namespace': None,
            'developer_display_name': None,
            'short_description': None,
            'game_type': None,
            'publisher_display_name': None,
            'tags': None,
            'price': None,
            'images': None,
            'long_description': None,
            'origin_slug': None,
            'supported_audio': None,
            'supported_text': None,
            'technical_requirements': None,
            'theme': None,
            'branding': None,
            'critic_avg': None,
            'critic_rating': None,
            'critic_recommend_pct': None,
            'critic_reviews': None,
            'poll': None
        }

        catalog_offer = next(x for x in queries if x['queryKey'][0] == 'getCatalogOffer')
        item['title'] = get_nested(catalog_offer, 'state.data.Catalog.catalogOffer.title')
        item['ref_id'] = get_nested(catalog_offer, 'state.data.Catalog.catalogOffer.id')
        item['ref_namespace'] = get_nested(catalog_offer, 'state.data.Catalog.catalogOffer.namespace')
        item['developer_display_name'] = get_nested(catalog_offer, 'state.data.Catalog.catalogOffer.developerDisplayName')
        item['short_description'] = get_nested(catalog_offer, 'state.data.Catalog.catalogOffer.description')
        item['game_type'] = get_nested(catalog_offer, 'state.data.Catalog.catalogOffer.offerType')
        item['publisher_display_name'] = get_nested(catalog_offer, 'state.data.Catalog.catalogOffer.publisherDisplayName')
        catalog_offer_tags = get_nested(catalog_offer, 'state.data.Catalog.catalogOffer.tags')
        if type(item['tags']) is not list:
            item['tags'] = []
        for tag in catalog_offer_tags:
            item['tags'].append({
                'ref_id': tag.get('id'),
                'name': tag.get('name'),
                'group_name': tag.get('groupName')
            })
        catalog_offer_price = get_nested(catalog_offer, 'state.data.Catalog.catalogOffer.price')
        item['price'] = {
            'discount_price': get_nested(catalog_offer_price, 'totalPrice.discountPrice'),
            'origin_price': get_nested(catalog_offer_price, 'totalPrice.originalPrice'),
            'discount': get_nested(catalog_offer_price, 'totalPrice.discount'),
        }
        catalog_offer_images = get_nested(catalog_offer, 'state.data.Catalog.catalogOffer.keyImages')
        if type(item['images']) is not list:
            item['images'] = []
        for image in catalog_offer_images:
            item['images'].append({
                'type': image.get('type'),
                'url': image.get('url'),
                'alt': item.get('title') + random_str()
            })
        # catalog_offer_mappings = catalog_offer.state.data.Catalog.catalogOffer.catalogNs.mappings
        # if catalog_offer_mappings and item['game_type'] == 'BASE_GAME':
        #     for mapping in catalog_offer_mappings:
        #         yield scrapy.Request(f"${self.host}${mapping.pageSlug}", callback=self.parse)

        product_home_config = next(x for x in queries if x['queryKey'][0] == 'getProductHomeConfig')
        if product_home_config:
            product_home_config_config = get_nested(product_home_config, 'state.data.Product.sandbox.configuration')[1]
            item['long_description'] = get_nested(product_home_config_config, 'configs.longDescription')
            product_home_config_images = get_nested(product_home_config_config, 'configs.keyImages')
            if type(item['images']) is not list:
                item['images'] = []
            item['images'] = item.get('images') + product_home_config_images

        store_config = next(x for x in queries if x['queryKey'][0] == 'getStoreConfig')
        store_config_sandbox_config = get_nested(store_config, 'state.data.Product.sandbox.configuration')
        if store_config_sandbox_config:
            print('STORE_CONFIG_SANDBOX_CONFIG: ', store_config_sandbox_config)
            game_store_config = next(x for x in store_config_sandbox_config if get_nested(x, 'configs.productDisplayName') == item['title'])
            print('GAME_STORE_CONFIG:', game_store_config)
            item['supported_audio'] = get_nested(game_store_config, 'configs.supportedAudio')
            item['supported_text'] = get_nested(game_store_config, 'configs.supportedText')
            item['technical_requirements'] = get_nested(game_store_config, 'configs.technicalRequirements')
            item['theme'] = get_nested(game_store_config, 'configs.theme')
            if type(item['images']) is not list:
                item['images'] = []
            item['images'] = item.get('images') + get_nested(game_store_config, 'configs.keyImages')

        for query in queries:
            if query['queryKey'][0] == 'egs-platform':
                item['branding'] = get_nested(query, 'state.data.branding') or item['branding']
                item['critic_avg'] = get_nested(query, 'state.data.criticReviews.criticAverage') or item['critic_avg']
                item['critic_rating'] = get_nested(query, 'state.data.criticReviews.criticRating') or item['critic_rating']
                item['critic_recommend_pct'] = get_nested(query, 'state.data.criticReviews.recommendPercentage') or item['critic_recommend_pct']
                item['critic_reviews'] = get_nested(query, 'state.data.criticReviews.reviews') or item['critic_reviews']

        item['poll'] = []
        product_result = next(x for x in queries if x['queryKey'][0] == 'getProductResult')
        product_result_poll = get_nested(product_result, 'state.data.RatingsPolls.getProductResult.pollResult')
        for poll in product_result_poll:
            item['poll'].append({
                'ref_id': poll['id'],
                'ref_tag_id': poll['tagId'],
                'ref_poll_definition_id': poll['pollDefinitionId'],
                'text': get_nested(poll, 'localizations.text'),
                'emoji': get_nested(poll, 'localizations.emoji'),
                'result_emoji': get_nested(poll, 'localizations.result_emoji'),
                'result_title': get_nested(poll, 'localizations.result_title'),
                'result_text': get_nested(poll, 'localizations.result_text'),
                'total': poll.get('total'),
            })

        mapping_by_page_slug = next(x for x in queries if x['queryKey'][0] == 'getMappingByPageSlug')
        item['origin_slug'] = get_nested(mapping_by_page_slug, "state.data.StorePageMapping.mapping.pageSlug")

        with open(f'{url}-parsed.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(item))

def random_str():
    result = ""
    characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    for i in range(0, 5):
        rand = randrange(36)
        result = result + characters[rand]

    return result

def get_nested(d, keys, delimiter="."):
    keys = keys.split(delimiter)
    for key in keys:
        d = d.get(key, None)
        if d is None:
            return None
    return d


''' launcherVersion
    - Nothing important, just some metadata
'''

''' getMappingByPageSlug
    - Some information about the product
        - sandboxId: c8b495f1a9a34972ba0b0c46e8afec31
        - productId: da2d8e4b946b4b50b1ad818727469873
        - mappings.offerId: 1efa9febbd9744caab24276d9c273862
        - mappings.namespace: c8b495f1a9a34972ba0b0c46e8afec31
        - mappings.pageSlug
'''

''' getCatalogOffer (multiple)
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
'''

''' getStoreConfig
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
'''

''' getRelatedOfferIdsByCategory (multiple)
    - Nothing important
'''

''' egs-platform: Multiple
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
'''

''' Achievement
    - Nothing important
'''

''' getCatalogNamespace
    - Product relates (addons, editions...)
'''

''' getProductResult
    - averageRating
    - pollResult
'''

''' getProductHomeConfig
    - keyImages (heroCarousel)
    - longDescriptions
'''

''' getVideoById
    - Videos
'''

''' getProductInBundles?
'''

''' abafd6e0aa80535c43676f533f0283c7f5214a59e9fae6ebfb37bed1b1bb2e9b (Hash that appear in queryKey - multiples)
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
'''


'''
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
    origin_slug:
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
'''