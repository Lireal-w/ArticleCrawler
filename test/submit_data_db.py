# 读取 /outfile/20260610/affpapa_1781088465.json 文件中的数据，并提交到数据库
import json
import os
from datetime import datetime
import mysql.connector
from dotenv import load_dotenv

# 新增 is_published 字段，默认0未发布
INIT_TABLE_SQL = """
CREATE TABLE `article` (
  `url` VARCHAR(2048) NOT NULL COMMENT '文章网址（唯一标识）',
  `title` VARCHAR(255) NOT NULL COMMENT '文章标题',
  `summary` TEXT COMMENT '文章摘要',
  `author_name` VARCHAR(100) COMMENT '作者姓名',
  `author_avatar` VARCHAR(2048) COMMENT '作者头像URL',
  `publish_time` DATETIME COMMENT '发布时间',
  `modified_time` DATETIME COMMENT '最后修改时间',
  `read_time` INT COMMENT '预计阅读时间（单位：分钟）',
  `content` MEDIUMTEXT COMMENT '正文 HTML（图片替换后）',
  `image_urls` JSON COMMENT '临时存储图片 URL 列表',
  `images` JSON COMMENT 'ImagesPipeline 结果',
  `cover_image` VARCHAR(2048) COMMENT '封面图 URL',
  `is_published` TINYINT(1) DEFAULT 0 COMMENT '是否发布 0=未发布 1=已发布',
  `create_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `update_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
  PRIMARY KEY (`url`(767))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文章信息表';
"""

load_dotenv()
SQL_DATABASE_NAME = os.environ.get("SQL_DATABASE_NAME")
SQL_USER_NAME = os.environ.get("SQL_USER_NAME")
SQL_PASSWORD = os.environ.get("SQL_PASSWORD")
SQL_HOST = os.environ.get("SQL_HOST")
SQL_PORT = os.environ.get("SQL_PORT")


class DB:
    def __init__(self):
        self.conn = None
        self.cursor = None

    # 连接数据库
    def connect(self):
        self.conn = mysql.connector.connect(
            host=SQL_HOST,
            port=SQL_PORT,
            user=SQL_USER_NAME,
            password=SQL_PASSWORD,
            database=SQL_DATABASE_NAME
        )
        self.cursor = self.conn.cursor()
        if not self.table_exists('article'):
            self.init_table()
        else:
            # 表已存在则自动补加is_published字段，避免重建丢数据
            self.cursor.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='article' AND COLUMN_NAME='is_published'
            """, (SQL_DATABASE_NAME,))
            col_exist = self.cursor.fetchone()
            if not col_exist:
                self.cursor.execute("ALTER TABLE article ADD COLUMN is_published TINYINT(1) DEFAULT 0 COMMENT '是否发布 0=未发布 1=已发布' AFTER cover_image;")
                self.conn.commit()

    # 安全关闭连接
    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def init_table(self):
        self.cursor.execute(INIT_TABLE_SQL)
        self.conn.commit()

    # 判断表是否存在
    def table_exists(self, table_name):
        self.cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        result = self.cursor.fetchone()
        return result is not None

    # 插入增加is_published参数
    def insert(self,
               url, title, summary, author_name, author_avatar,
               publish_time, modified_time, read_time, content,
               image_urls=None, images=None, cover_image=None, is_published=0):
        insert_sql = """
        INSERT INTO article 
        (url, title, summary, author_name, author_avatar, publish_time, modified_time, read_time, content, image_urls, images, cover_image, is_published)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        title=VALUES(title),
        summary=VALUES(summary),
        publish_time=VALUES(publish_time),
        modified_time=VALUES(modified_time),
        read_time=VALUES(read_time),
        content=VALUES(content),
        image_urls=VALUES(image_urls),
        images=VALUES(images),
        cover_image=VALUES(cover_image),
        is_published=VALUES(is_published)
        """
        params = (
            url, title, summary, author_name, author_avatar,
            publish_time, modified_time, read_time, content,
            image_urls, images, cover_image, is_published
        )
        self.cursor.execute(insert_sql, params)
        self.conn.commit()


# 工具函数：时间戳转 Y-m-d H:i:s，空/异常返回None
def ts_to_datetime(ts_val):
    if ts_val is None or ts_val == "":
        return None
    try:
        ts = int(ts_val)
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return ts_val


if __name__ == '__main__':
    db = DB()
    try:
        db.connect()
        file_path = './outfile/20260610/affpapa_1781088465.json'
        with open(file_path, 'r', encoding='utf-8') as f:
            data_list = json.load(f)
            for item in data_list:
                pub_dt = ts_to_datetime(item.get("publish_time"))
                mod_dt = ts_to_datetime(item.get("modified_time"))
                # 没有is_published键则默认0未发布
                pub_status = int(item.get("is_published", 0))

                insert_kwargs = {
                    "url": item.get("url"),
                    "title": item.get("title"),
                    "summary": item.get("summary"),
                    "author_name": item.get("author_name"),
                    "author_avatar": item.get("author_avatar"),
                    "publish_time": pub_dt,
                    "modified_time": mod_dt,
                    "read_time": item.get("read_time"),
                    "content": item.get("content"),
                    "image_urls": json.dumps(item["image_urls"]) if "image_urls" in item else None,
                    "images": json.dumps(item["images"]) if "images" in item else None,
                    "cover_image": item.get("cover_image"),
                    "is_published": pub_status
                }
                db.insert(**insert_kwargs)
                print(f"插入/更新成功: {insert_kwargs['title']}")
                break  # 测试只插一条，正式运行删除break
    except Exception as e:
        print(f"执行异常: {e}")
    finally:
        db.close()