import json
import os
from datetime import datetime
import mysql.connector
from dotenv import load_dotenv

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

    def get_unpublished_articles(self, limit=10):
        """
        获取未发布的最新文章
        
        Args:
            limit (int): 获取文章的数量限制，默认10条
            
        Returns:
            list: 包含未发布文章的字典列表，每篇文章是一个字典
        """
        sql = """
        SELECT url, title, summary, author_name, author_avatar, 
               publish_time, modified_time, read_time, content,
               image_urls, images, cover_image
        FROM article 
        WHERE is_published = 0 
        ORDER BY publish_time DESC
        LIMIT %s
        """
        self.cursor.execute(sql, (limit,))
        columns = [desc[0] for desc in self.cursor.description]
        results = []
        for row in self.cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results

    def mark_article_published(self, url):
        """
        将指定文章标记为已发布
        
        Args:
            url (str): 文章的唯一标识URL
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        sql = "UPDATE article SET is_published = 1 WHERE url = %s"
        try:
            self.cursor.execute(sql, (url,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception:
            self.conn.rollback()
            return False



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

db = DB();

