# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface

from datetime import datetime
from itemadapter.adapter import ItemAdapter
from mysql.connector.abstracts import MySQLCursorAbstract
from scrapy import Spider
from scrapy.http.request.json_request import json

from GameResellerScraper.items import GameItem
import mysql.connector
from mysql.connector import errorcode


class GameItemPipeline:
    def process_item(self, item: GameItem, _: Spider):
        ref_slug = item.get("ref_slug")
        if ref_slug == None or type(ref_slug) != str:
            return
        line = json.dumps(ItemAdapter(item).asdict()) + "\n"
        with open(f"./GameResellerScraper/data/{ref_slug}.json", "w", encoding="utf-8") as f:
            __ = f.write(line)
        return item


class MysqlPipline:
    def __init__(self):
        try:
            self.cnx = mysql.connector.connect(
                user="root", host="127.0.0.1", database="game_reseller"
            )
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist")
            else:
                print(err)
        else:
            print("CONNECTED TO DATABASE")

    def process_item(self, item: GameItem, _: Spider):
        cursor = self.cnx.cursor()
        cursor = self.insert_item(cursor, item)
        item_id = cursor.lastrowid
        if not item_id:
            cursor.close()
            __ = self.cnx.close()
            return

        self.insert_images(cursor, item, item_id)
        self.insert_systems(cursor, item, item_id)
        self.insert_reviews(cursor, item, item_id)
        self.insert_polls(cursor, item, item_id)

        __ = self.cnx.commit()
        cursor.close()
        __ = self.cnx.close()

    def insert_item(self, cursor: MySQLCursorAbstract, item: GameItem):
        add_item = (
            "INSERT INTO items "
            "(title, ref_id, ref_namespace, developer_display_name, short_description, item_type, publisher_display_name, long_description, ref_slug, critic_avg, critic_rating, critic_recommend_pct, text, audio, sale_price, release_date, avg_rating) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        data_item = (
            item.get("title"),
            item.get("ref_id"),
            item.get("ref_namespace"),
            item.get("developer_display_name"),
            item.get("short_description"),
            item.get("item_type"),
            item.get("publisher_display_name"),
            item.get("long_description"),
            item.get("ref_slug"),
            item.get("critic_avg"),
            item.get("critic_rating"),
            item.get("critic_recommend_pct"),
            ",".join(item.get("supported_text") or []),
            ",".join(item.get("supported_audio") or []),
            (item.get("price") or {}).get("origin_price") or 0,
            int(
                datetime.strptime(
                    item.get("release_date") or "2023-01-25T06:00:00.000Z", "%Y-%m-%dT%H:%M:%S.%fZ"
                ).timestamp()
                * 1000
            ),
            item.get("avg_rating"),
        )
        __ = cursor.execute(add_item, data_item)

        return cursor

    def insert_images(self, cursor: MySQLCursorAbstract, item: GameItem, item_id: int):
        add_image = (
            "INSERT INTO images "
            "(url, image_type, alt, item_id, image_row) "
            "VALUES (%s, %s, %s, %s, %s)"
        )
        for image in item.get("images") or []:
            data_image = (image.get("url"), image.get("type"), image.get("alt"), item_id, None)
            __ = cursor.execute(add_image, data_image)

    def insert_systems(self, cursor: MySQLCursorAbstract, item: GameItem, item_id: int):
        add_system = "INSERT INTO systems " + "(os, item_id) " + "VALUES (%s, %s)"
        technical_requirements = item.get("technical_requirements")
        if not technical_requirements:
            return
        systems = list(technical_requirements.items())
        for system_name, details in systems or []:
            if not details:
                continue
            system_data = (system_name, item_id)
            __ = cursor.execute(add_system, system_data)
            system_id = cursor.lastrowid
            for detail in details:
                add_detail = (
                    "INSERT INTO system_details "
                    "(title, minimum, recommended, system_id) "
                    "VALUES (%s, %s, %s, %s)"
                )
                detail_data = (
                    detail.get("title"),
                    detail.get("minimum"),
                    detail.get("recommended"),
                    system_id,
                )
                __ = cursor.execute(add_detail, detail_data)

    def insert_reviews(self, cursor: MySQLCursorAbstract, item: GameItem, item_id: int):
        add_reviews = (
            "INSERT INTO reviews "
            "(author, body, outlet, earned_score, total_score, type, item_id, url) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        )
        for review in item.get("critic_reviews") or []:
            review_data = (
                review.get("author"),
                review.get("body"),
                review.get("outlet"),
                review.get("score").get("earned_score"),
                review.get("score").get("total_score"),
                (
                    "star"
                    if review.get("score").get("type") == "CriticReviewNumericScore"
                    else "numeric"
                ),
                item_id,
                review.get("url"),
            )
            __ = cursor.execute(add_reviews, review_data)

    def insert_polls(self, cursor: MySQLCursorAbstract, item: GameItem, item_id: int):
        add_polls = (
            "INSERT INTO polls "
            "(text, emoji, result_emoji, result_title, result_text, item_id, ref_id, ref_tag_id, ref_poll_definition_id, total) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        for poll in item.get("polls") or []:
            poll_data = (
                poll.get("text"),
                poll.get("emoji"),
                poll.get("result_emoji"),
                poll.get("result_title"),
                poll.get("result_text"),
                item_id,
                poll.get("ref_id"),
                poll.get("ref_tag_id"),
                poll.get("ref_poll_definition_id"),
                poll.get("total"),
            )
            __ = cursor.execute(add_polls, poll_data)
